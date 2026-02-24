"""Scheduled jobs: morning greeting + memo recommendations."""
from __future__ import annotations

import logging
import random
from datetime import date

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from . import supabase_client, formatter as fmt
from .workers import recommender_run
from anthropic import AsyncAnthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from .schemas import CHARACTER_RULES

_anthropic = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

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


# WMO weather code → Korean description
_WMO_KO = {
    0: "맑음",
    1: "대체로 맑음", 2: "구름 조금", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비", 53: "이슬비", 55: "강한 이슬비",
    56: "빙결 이슬비", 57: "빙결 이슬비",
    61: "비", 63: "비", 65: "폭우",
    66: "빙결 비", 67: "빙결 비",
    71: "눈", 73: "눈", 75: "폭설",
    77: "싸락눈",
    80: "소나기", 81: "소나기", 82: "강한 소나기",
    85: "눈보라", 86: "눈보라",
    95: "뇌우", 96: "우박 뇌우", 99: "우박 뇌우",
}


async def _get_weather_mapo() -> str:
    """Fetch weather for Mapo-gu. Primary: Open-Meteo, fallback: wttr.in."""
    weather = await _try_open_meteo()
    if weather:
        return weather
    weather = await _try_wttr()
    if weather:
        return weather
    return "날씨 정보 없음"


async def _try_open_meteo() -> str | None:
    """Open-Meteo: free, no key, server-friendly."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": 37.5538,
                    "longitude": 126.9097,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                    "timezone": "Asia/Seoul",
                },
                timeout=10,
            )
            resp.raise_for_status()
            cur = resp.json()["current"]
            cond = _WMO_KO.get(cur["weather_code"], "알 수 없음")
            temp = cur["temperature_2m"]
            humid = cur["relative_humidity_2m"]
            wind = cur["wind_speed_10m"]
            return f"{cond} {temp}°C 습도{humid}% 바람{wind}km/h"
    except Exception as e:
        log.warning("Open-Meteo failed: %s", e)
        return None


async def _try_wttr() -> str | None:
    """wttr.in fallback."""
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(
                "https://wttr.in/Mapo-gu,Seoul?format=%C+%t+%h+%w",
                headers={"Accept-Language": "ko", "User-Agent": "meemoo-bot/1.0"},
                timeout=10,
            )
            resp.raise_for_status()
            text = resp.text.strip()
            if text and "Unknown" not in text:
                return text
            return None
    except Exception as e:
        log.warning("wttr.in fallback failed: %s", e)
        return None


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
    weather = await _get_weather_mapo()

    speaker = random.choice(["팀장", "분석가", "사서"])
    resp = await _anthropic.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=80,
        system=(
            "You are 케미담당(💖). Output EXACTLY one line of casual Korean (15~30자). "
            "No quotes, no extra lines, no explanations. "
            f"The speaker is fixed as {speaker}:. Use ONLY '{speaker}:' as prefix. "
            "날짜와 날씨 정보를 자연스럽게 녹여서 아침 인사 한 마디. "
            "기념일이 있으면 언급해줘. 날씨는 반드시 포함. "
        ) + CHARACTER_RULES,
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
            await bot.send_message(u["chat_id"], f"🧃 {msg}")
        except Exception:
            log.warning("Failed to send morning to chat_id=%s", u["chat_id"])


async def _push_recommendations(app: Application) -> None:
    """전체 메모 중 랜덤 1개를 Claude 거쳐 모든 유저에게 전송."""
    users = supabase_client.list_users()
    if not users:
        return

    memo = supabase_client.get_one_random_memo()
    if not memo:
        return

    try:
        result = recommender_run("", memos=[memo])
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
