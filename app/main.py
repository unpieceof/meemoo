"""Telegram bot entry point."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .config import TELEGRAM_TOKEN, VERBOSE_DEFAULT
from .router import route
from .workers import analyst_run, librarian_run, recommender_run
from . import formatter as fmt
from . import supabase_client
from .scheduler import setup_scheduler
from .banter import maybe_banter

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Per-chat verbose setting
_verbose: dict[int, bool] = {}


async def _send(update: Update, text: str) -> None:
    await update.message.reply_text(text, parse_mode="Markdown")


async def _handle(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text or ""
    verbose = _verbose.get(chat_id, VERBOSE_DEFAULT)

    # Register user on every message
    user = update.effective_user
    supabase_client.upsert_user(chat_id, user.username if user else None)

    action, payload = route(text)
    log.info("chat=%s action=%s payload=%s", chat_id, action, payload[:80])

    try:
        if action in ("help", "start"):
            await _send(update, fmt.fmt_help())
            return

        if action == "setting":
            on = payload.lower() in ("on", "1", "true")
            _verbose[chat_id] = on
            await _send(update, f"🔧 Verbose 모드: `{'ON' if on else 'OFF'}`")
            return

        if action == "unknown":
            await _send(update, fmt.fmt_error("알 수 없는 명령입니다. /help 를 확인하세요."))
            return

        # ── Pipeline ──
        is_night = datetime.now(timezone.utc).hour >= 14  # UTC 14 = KST 23

        if action == "analyst":
            # 🎯 Router -> 🔍 Analyst -> 📚 Librarian
            analyst_result = analyst_run(payload)
            if verbose:
                await _send(update, fmt.fmt_verbose_step("🔍 Analyst", analyst_result))
                await _send(update, fmt.fmt_analyst(analyst_result))

            # 🎭 Banter after analysis
            banter = maybe_banter({
                "stage": "after_analysis", "intent": "save",
                "source_type": analyst_result.get("source_type", ""),
                "is_night": is_night, "duplicate": False,
                "category": analyst_result.get("category", ""),
                "tag_count": len(analyst_result.get("tags", [])),
                "title": analyst_result.get("title", ""),
            })
            if banter:
                await _send(update, f"🎭 {banter}")

            lib_result = librarian_run("save:", analyst_result=analyst_result)
            if verbose:
                await _send(update, fmt.fmt_verbose_step("📚 Librarian", lib_result))

            if lib_result.get("action") == "duplicate":
                dup_banter = maybe_banter({
                    "stage": "after_store", "intent": "duplicate",
                    "source_type": analyst_result.get("source_type", ""),
                    "is_night": is_night, "duplicate": True,
                    "category": analyst_result.get("category", ""),
                    "tag_count": len(analyst_result.get("tags", [])),
                    "title": analyst_result.get("title", ""),
                })
                await _send(update, fmt.fmt_duplicate(lib_result))
                if dup_banter:
                    await _send(update, f"🎭 {dup_banter}")
            else:
                await _send(update, fmt.fmt_saved(lib_result))
                if not verbose:
                    await _send(update, fmt.fmt_analyst(analyst_result))
            return

        if action == "librarian":
            sub, _, _ = payload.partition(":")
            lib_result = librarian_run(payload)
            if verbose:
                await _send(update, fmt.fmt_verbose_step("📚 Librarian", lib_result))

            act = lib_result.get("action", "")
            if act == "list":
                await _send(update, fmt.fmt_list(lib_result))
            elif act == "search":
                await _send(update, fmt.fmt_search(lib_result))
            elif act == "category_list":
                await _send(update, fmt.fmt_category_list(lib_result))
            elif act == "category":
                await _send(update, fmt.fmt_category(lib_result))
            elif act == "view":
                await _send(update, fmt.fmt_view(lib_result))
            elif act == "delete":
                await _send(update, fmt.fmt_delete(lib_result))
            else:
                await _send(update, fmt.fmt_error(str(lib_result)))
            return

        if action == "recommender":
            rec_result = recommender_run(payload)
            if verbose:
                await _send(update, fmt.fmt_verbose_step("💡 Recommender", rec_result))
            await _send(update, fmt.fmt_recommend(rec_result))
            return

    except Exception as e:
        log.exception("Error in pipeline")
        await _send(update, fmt.fmt_error(f"오류 발생: {e}"))


async def _post_init(app: Application) -> None:
    setup_scheduler(app)


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(_post_init).build()
    app.add_handler(CommandHandler("help", _handle))
    app.add_handler(CommandHandler("start", _handle))
    app.add_handler(CommandHandler("save", _handle))
    app.add_handler(CommandHandler("list", _handle))
    app.add_handler(CommandHandler("search", _handle))
    app.add_handler(CommandHandler("category", _handle))
    app.add_handler(CommandHandler("view", _handle))
    app.add_handler(CommandHandler("delete", _handle))
    app.add_handler(CommandHandler("recommend", _handle))
    app.add_handler(CommandHandler("verbose", _handle))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle))
    log.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
