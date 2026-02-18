"""Scheduled jobs: morning greeting + memo recommendations."""
from __future__ import annotations

import logging
from datetime import date

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from . import supabase_client, formatter as fmt
from .workers import recommender_run
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

log = logging.getLogger(__name__)

RECOMMEND_HOURS = [9, 20]  # 오전 9시, 오후 8시

# 대한민국 주요 공휴일/기념일 (월, 일) -> 이름
KR_HOLIDAYS = {
    (1, 1): "신정",
    (3, 1): "삼일절",
    (5, 5): "어린이날",
    (6, 6): "현충일",
    (8, 15): "광복절",
    (10, 3): "개천절",
    (10, 9): "한글날",
    (12, 25): "크리스마스",
}


def _get_weather_mapo() -> str:
    """Fetch current weather for Mapo-gu via wttr.in (no API key)."""
    try:
        resp = httpx.get(
            "https://wttr.in/Mapo-gu,Seoul?format=%C+%t+%h+%w",
            headers={"Accept-Language": "ko"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.text.strip()
    except Exception as e:
        log.warning("Weather fetch failed: %s", e)
        return "날씨 정보 없음"


def _get_date_info() -> str:
    """Return date string with holiday info if applicable."""
    today = date.today()
    weekday = ["월", "화", "수", "목", "금", "토", "일"][today.weekday()]
    base = f"{today.month}월 {today.day}일 ({weekday})"
    holiday = KR_HOLIDAYS.get((today.month, today.day))
    if holiday:
        base += f" — {holiday}"
    return base


async def _generate_morning_msg() -> str:
    """Generate morning greeting with weather via Claude."""
    date_info = _get_date_info()
    weather = _get_weather_mapo()

    resp = _anthropic.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=80,
        system=(
            "You are 케미담당(💖). Output EXACTLY one line of casual Korean (15~30자). "
            "No quotes, no extra lines, no explanations. "
            "Use speaker prefix: 팀장: or 분석가: or 사서:. "
            "날짜와 날씨 정보를 자연스럽게 녹여서 아침 인사 한 마디. "
            "기념일이 있으면 언급해줘. 날씨는 반드시 포함. "
            "Warm, witty, slightly poetic."
        ),
        messages=[{"role": "user", "content": f"날짜: {date_info}\n날씨(마포구): {weather}"}],
    )
    return resp.content[0].text.strip().split("\n")[0].strip()


def setup_scheduler(app: Application) -> AsyncIOScheduler:
    """Register cron jobs and return scheduler."""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    # Morning greeting at 6 AM KST
    scheduler.add_job(
        _push_morning,
        "cron",
        hour=6,
        minute=0,
        args=[app],
        id="morning_greeting",
        replace_existing=True,
    )

    # Memo recommendations
    for hour in RECOMMEND_HOURS:
        scheduler.add_job(
            _push_recommendations,
            "cron",
            hour=hour,
            minute=0,
            args=[app],
            id=f"recommend_{hour}",
            replace_existing=True,
        )
    scheduler.start()
    log.info("Scheduler started: morning=6, recommendations=%s KST", RECOMMEND_HOURS)
    return scheduler


async def _push_morning(app: Application) -> None:
    """Send morning greeting with weather to all users."""
    users = supabase_client.list_users()
    if not users:
        return

    try:
        msg = await _generate_morning_msg()
    except Exception:
        log.exception("Morning greeting generation failed")
        return

    bot = app.bot
    for u in users:
        try:
            await bot.send_message(u["chat_id"], f"🎭 {msg}")
        except Exception:
            log.warning("Failed to send morning to chat_id=%s", u["chat_id"])


async def _push_recommendations(app: Application) -> None:
    """Run recommender with 1 category and send to all registered users."""
    users = supabase_client.list_users()
    if not users:
        return

    try:
        result = recommender_run("", max_categories=1)
    except Exception:
        log.exception("Scheduled recommend failed")
        return

    text = fmt.fmt_recommend(result)
    if not text or "아직 없" in text:
        return

    bot = app.bot
    for u in users:
        try:
            await bot.send_message(u["chat_id"], text, parse_mode="Markdown")
        except Exception:
            log.warning("Failed to send to chat_id=%s", u["chat_id"])
