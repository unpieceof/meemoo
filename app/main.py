"""Telegram bot entry point."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from .config import TELEGRAM_TOKEN, VERBOSE_DEFAULT
from .router import route
from .workers import analyst_run, librarian_run, recommender_run, PAGE_SIZE
from . import formatter as fmt
from . import supabase_client
from .scheduler import setup_scheduler
from .banter import maybe_banter

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Per-chat verbose setting
_verbose: dict[int, bool] = {}


async def _send(update: Update, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


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
        if action == "help":
            await _send(update, fmt.fmt_help())
            return

        if action == "setting":
            on = payload.lower() in ("on", "1", "true")
            _verbose[chat_id] = on
            await _send(update, f"🔧 Verbose 모드: `{'ON' if on else 'OFF'}`")
            return

        if action == "sms":
            from .banter import generate_sms
            try:
                msg = generate_sms()
                await update.message.reply_text(f"🧃 {msg}")
            except Exception as e:
                log.exception("SMS banter failed")
                await _send(update, fmt.fmt_error(f"오류 발생: {e}"))
            return

        if action == "unknown":
            await _send(update, fmt.fmt_error("알 수 없는 명령입니다. /help 를 확인하세요."))
            return

        # ── Pipeline ──
        is_night = datetime.now(timezone.utc).hour >= 14  # UTC 14 = KST 23

        # Instant status message
        _status = {
            "analyst": "🔍 분석가: 핵심 정리 중...",
            "librarian": {
                "list": "📚 사서: 목록 정리해서 꺼내는 중...",
                "search": "📚 사서: 색인 뒤지는 중...",
                "category": "📚 사서: 분류표 확인 중...",
                "view": "📚 사서: 해당 메모 찾는 중...",
                "delete": "📚 사서: 기록 정리 중...",
            },
            "recommender": "💡 큐레이터: 연결 고리 탐색 중...",
        }

        if action == "analyst":
            await _send(update, _status["analyst"])
        elif action == "librarian":
            sub = payload.partition(":")[0]
            await _send(update, _status["librarian"].get(sub, "⏳ 처리 중..."))
        elif action == "recommender":
            await _send(update, _status["recommender"])

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
                await _send(update, f"✏️ {banter}")

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
                    await _send(update, f"✏️ {dup_banter}")
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
                kb = fmt.build_page_keyboard("list", lib_result.get("page", 0), lib_result.get("total", 0), PAGE_SIZE)
                await _send(update, fmt.fmt_list(lib_result), reply_markup=kb)
            elif act == "search":
                kb = fmt.build_page_keyboard("search", lib_result.get("page", 0), lib_result.get("total", 0), PAGE_SIZE, query=lib_result.get("query"))
                await _send(update, fmt.fmt_search(lib_result), reply_markup=kb)
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


async def _page_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard pagination button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    try:
        if data.startswith("list:"):
            # "list:{page}"
            page = int(data.split(":")[1])
            lib_result = librarian_run(f"list:{page}")
            text = fmt.fmt_list(lib_result)
            kb = fmt.build_page_keyboard("list", lib_result.get("page", 0), lib_result.get("total", 0), PAGE_SIZE)
        elif data.startswith("search:"):
            # "search:{query}:{page}"
            parts = data.split(":")
            page = int(parts[-1])
            search_query = ":".join(parts[1:-1])
            lib_result = librarian_run(f"search:{search_query}:{page}")
            text = fmt.fmt_search(lib_result)
            kb = fmt.build_page_keyboard("search", lib_result.get("page", 0), lib_result.get("total", 0), PAGE_SIZE, query=search_query)
        else:
            return

        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        log.exception("Pagination callback error")
        await query.edit_message_text(f"⚠️ 페이지 이동 오류: {e}")


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
    app.add_handler(CommandHandler("sms", _handle))
    app.add_handler(CallbackQueryHandler(_page_callback, pattern=r"^(list|search):"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle))
    log.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
