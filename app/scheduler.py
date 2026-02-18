"""Scheduled random memo recommendations (2x daily)."""
from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from . import supabase_client, formatter as fmt
from .workers import recommender_run

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
