"""Pipeline workers: Analyst, Librarian, Recommender."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import claude_client, supabase_client, extractor
from .schemas import ANALYST_SCHEMA, RECOMMENDER_SCHEMA


# ── Analyst (🔍) ────────────────────────────────────────────
def analyst_run(url: str) -> dict:
    """Extract URL -> call Claude -> return analysis JSON."""
    source_type, text = extractor.extract_text(url)
    result = claude_client.ask_json(
        system=(
            "You are a concise analyst. Given webpage text, produce a memo with: "
            "title (Korean), 3 bullet summary (Korean), category, tags."
        ),
        user=text,
        schema=ANALYST_SCHEMA,
    )
    result["source_url"] = url
    result["source_type"] = source_type
    return result


# ── Librarian (📚) ──────────────────────────────────────────
def librarian_run(action_payload: str, analyst_result: dict | None = None) -> dict:
    """Handle save/list/search/delete."""
    action, _, payload = action_payload.partition(":")

    if action == "save" or analyst_result is not None:
        # Save analyst result to Supabase
        if analyst_result is None:
            return {"error": "No analyst result to save"}
        memo = {
            "title": analyst_result["title"],
            "summary_bullets": analyst_result["bullets"],
            "category": analyst_result["category"],
            "tags": analyst_result["tags"],
            "source_url": analyst_result["source_url"],
            "source_type": analyst_result["source_type"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        saved = supabase_client.upsert_memo(memo)
        return {"action": "saved", "memo": saved[0] if saved else memo}

    if action == "list":
        memos = supabase_client.list_memos()
        return {"action": "list", "memos": memos}

    if action == "search":
        memos = supabase_client.search_memos(payload)
        return {"action": "search", "query": payload, "memos": memos}

    if action == "delete":
        ok = supabase_client.delete_memo(payload)
        return {"action": "delete", "memo_id": payload, "success": ok}

    return {"error": f"Unknown librarian action: {action}"}


# ── Recommender (💡) ────────────────────────────────────────
def recommender_run(payload: str) -> dict:
    """Recommend memos based on existing metadata. Only when explicitly requested."""
    metas = supabase_client.get_all_memos_meta()
    if not metas:
        return {"recommendations": []}
    result = claude_client.ask_json(
        system=(
            "You are a recommender. Given a list of saved memos (JSON), "
            "pick top 3 the user might want to revisit. "
            "Return recommendations with memo_id and short Korean reason."
        ),
        user=json.dumps(metas, ensure_ascii=False),
        schema=RECOMMENDER_SCHEMA,
    )
    return result
