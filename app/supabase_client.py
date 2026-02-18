"""Supabase client wrapper for memo CRUD."""
from __future__ import annotations

from supabase import create_client, Client
from .config import SUPABASE_URL, SUPABASE_ANON_KEY

_sb: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
TABLE = "memos"


def upsert_memo(memo: dict) -> dict:
    """Insert or update memo by source_url."""
    return _sb.table(TABLE).upsert(memo, on_conflict="source_url").execute().data


def list_memos(limit: int = 20, offset: int = 0) -> list[dict]:
    return (
        _sb.table(TABLE)
        .select("id,title,summary_bullets,category,tags,source_url,source_type,created_at")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
        .data
    )


def count_memos() -> int:
    """Return total memo count."""
    res = _sb.table(TABLE).select("id", count="exact").execute()
    return res.count or 0


def search_memos_text(query: str, limit: int = 5, offset: int = 0) -> tuple[list[dict], int]:
    """Keyword search via RPC (title, category, raw_content, tags, bullets)."""
    rows = _sb.rpc(
        "search_memos",
        {"query": query, "lim": limit, "off": offset},
    ).execute().data
    if not rows:
        return [], 0
    total = rows[0].get("total_count", len(rows))
    # Strip total_count from each row
    for r in rows:
        r.pop("total_count", None)
    return rows, total



def find_by_url(url: str) -> dict | None:
    """Check if memo with this source_url already exists."""
    rows = _sb.table(TABLE).select("id,title").eq("source_url", url).limit(1).execute().data
    return rows[0] if rows else None


def _resolve_id(memo_id: str) -> str | None:
    """Resolve full or partial UUID. Uses RPC for prefix match."""
    memo_id = memo_id.strip()
    if not memo_id:
        return None
    if len(memo_id) == 36:
        return memo_id
    # Use RPC function for prefix matching (uuid::text LIKE)
    rows = _sb.rpc("find_memo_by_prefix", {"prefix": memo_id}).execute().data
    return rows[0]["id"] if rows else None


def delete_memo(memo_id: str) -> bool:
    resolved = _resolve_id(memo_id)
    if not resolved:
        return False
    res = _sb.table(TABLE).delete().eq("id", resolved).execute()
    return len(res.data) > 0


def get_memo_by_id(memo_id: str) -> dict | None:
    """Get single memo by full or partial UUID (includes raw_content)."""
    resolved = _resolve_id(memo_id)
    if not resolved:
        return None
    rows = _sb.table(TABLE).select("*").eq("id", resolved).execute().data
    return rows[0] if rows else None


def get_memos_by_category(category: str) -> list[dict]:
    return (
        _sb.table(TABLE)
        .select("id,title,summary_bullets,category,tags,source_url,source_type,created_at")
        .ilike("category", f"%{category}%")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
    )


def get_category_counts() -> list[dict]:
    """Get memo count per category."""
    # Supabase doesn't support GROUP BY directly, fetch all categories and count in Python
    rows = _sb.table(TABLE).select("category").execute().data
    counts: dict[str, int] = {}
    for r in rows:
        cat = r.get("category", "기타")
        counts[cat] = counts.get(cat, 0) + 1
    return [{"category": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]


def get_all_memos_meta() -> list[dict]:
    """Lightweight fetch for recommender."""
    return (
        _sb.table(TABLE)
        .select("id,title,summary_bullets,category,tags")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
        .data
    )


# ── Users ────────────────────────────────────────────────────
USERS_TABLE = "users"


def upsert_user(chat_id: int, username: str | None = None) -> None:
    row = {"chat_id": chat_id}
    if username:
        row["username"] = username
    _sb.table(USERS_TABLE).upsert(row, on_conflict="chat_id").execute()


def list_users() -> list[dict]:
    return _sb.table(USERS_TABLE).select("chat_id").execute().data
