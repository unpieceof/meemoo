"""Supabase client wrapper for memo CRUD."""
from __future__ import annotations

from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_ANON_KEY

_sb: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
TABLE = "memos"


def upsert_memo(memo: dict) -> dict:
    """Insert or update memo by source_url."""
    return _sb.table(TABLE).upsert(memo, on_conflict="source_url").execute().data


def list_memos(limit: int = 20) -> list[dict]:
    return (
        _sb.table(TABLE)
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


def search_memos(query: str) -> list[dict]:
    """Simple ilike search on title and tags."""
    like = f"%{query}%"
    return (
        _sb.table(TABLE)
        .select("*")
        .or_(f"title.ilike.{like},tags.cs.{{{query}}}")
        .limit(20)
        .execute()
        .data
    )


def delete_memo(memo_id: str) -> bool:
    res = _sb.table(TABLE).delete().eq("id", memo_id).execute()
    return len(res.data) > 0


def get_all_memos_meta() -> list[dict]:
    """Lightweight fetch for recommender (id, title, category, tags only)."""
    return (
        _sb.table(TABLE)
        .select("id,title,category,tags")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
    )


# ── Users ────────────────────────────────────────────────────
USERS_TABLE = "users"


def upsert_user(chat_id: int, username: str | None = None) -> None:
    """Register or update user chat_id."""
    row = {"chat_id": chat_id}
    if username:
        row["username"] = username
    _sb.table(USERS_TABLE).upsert(row, on_conflict="chat_id").execute()


def list_users() -> list[dict]:
    return _sb.table(USERS_TABLE).select("chat_id").execute().data
