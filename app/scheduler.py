"""Scheduled random memo recommendations (2x daily)."""
from __future__ import annotations

import random
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from . import supabase_client, formatter as fmt

log = logging.getLogger(__name__)

SCHEDULE_HOURS = [9, 20]  # 오전 9시, 오후 8시


def setup_scheduler(app: Application) -> AsyncIOScheduler:
    """Register cron jobs and return scheduler."""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
    for hour in SCHEDULE_HOURS:
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
    log.info("Scheduler started: recommendations at %s KST", SCHEDULE_HOURS)
    return scheduler


async def _push_recommendations(app: Application) -> None:
    """Pick random memos and send to all registered users."""
    users = supabase_client.list_users()
    memos = supabase_client.get_all_memos_meta()
    if not users or not memos:
        return

    pick = random.sample(memos, min(3, len(memos)))
    lines = ["💡 *오늘의 랜덤 메모 추천*\n"]
    for m in pick:
        tags = " ".join(f"#{t}" for t in m.get("tags", []))
        lines.append(f"• *{m.get('title', '')}*  {tags}")
    text = "\n".join(lines)

    bot = app.bot
    for u in users:
        try:
            await bot.send_message(u["chat_id"], text, parse_mode="Markdown")
        except Exception:
            log.warning("Failed to send to chat_id=%s", u["chat_id"])
