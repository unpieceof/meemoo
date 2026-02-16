"""Pipeline workers: Analyst, Librarian, Recommender."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from . import claude_client, supabase_client, extractor, embeddings
from .schemas import ANALYST_SCHEMA, RECOMMENDER_SCHEMA


def _memo_text(result: dict) -> str:
    """Build searchable text for embedding from analyst result."""
    parts = [result.get("title", "")]
    parts.extend(result.get("bullets", []))
    parts.append(result.get("category", ""))
    parts.extend(result.get("tags", []))
    return " ".join(parts)

# Librarian Search용 function ────────────────────────────────────────────
CATEGORY_ICON = {
    "일": "🧑‍💻",
    "배움": "📘",
    "아이디어": "💡",
    "정보": "📰",
    "기록": "📝",
    "문화": "🎬",
    "소비": "🍽",
}

def _primary_tag(tags):
    if not tags:
        return ""
    t = str(tags[0]).strip()
    return t[:10]  # 과도하게 길면 컷(선택)

def _preview_from_bullets(bullets):
    if isinstance(bullets, list) and bullets:
        s = str(bullets[0]).strip()
        return (s[:70] + "…") if len(s) > 70 else s
    return ""

def _fmt_date(created_at: str) -> str:
    # "2026-02-16 13:09:23.779322+00"
    try:
        dt = datetime.fromisoformat(created_at.replace(" ", "T"))
        return dt.strftime("%m.%d")
    except Exception:
        return ""

def _decorate(m: dict) -> dict:
    cat = (m.get("category") or "").strip()
    icon = CATEGORY_ICON.get(cat, "🏷")
    tag = _primary_tag(m.get("tags"))
    title = (m.get("title") or "").strip()
    date = _fmt_date(m.get("created_at") or "")

    # 핵심: 직관적 1줄 타이틀
    left = []
    if cat:
        left.append(cat)
    if tag:
        left.append(tag)

    prefix = f"{icon} [{' · '.join(left)}]"
    m["display_title"] = f"{prefix} {title}".strip()

    # 핵심: 검색용 1줄 프리뷰
    m["display_preview"] = _preview_from_bullets(m.get("summary_bullets"))

    # 보조: 날짜
    if date:
        m["display_date"] = date

    # 대표 태그도 따로 (필터/칩 UI용)
    if tag:
        m["display_tag"] = tag

    return m


# ── Analyst (🔍) ────────────────────────────────────────────
def analyst_run(payload: str) -> dict:
    """Extract URL (with optional user context) -> call Claude -> return analysis JSON."""
    url_match = re.search(r"https?://\S+", payload)
    url = url_match.group(0) if url_match else ""
    user_context = payload.replace(url, "").strip() if url else payload

    source_type, extracted = extractor.extract_text(url) if url else ("web", "")

    parts = []
    if user_context:
        parts.append(f"사용자 메모: {user_context}")
    if extracted:
        parts.append(f"페이지 내용: {extracted}")
    text = "\n\n".join(parts) or payload

    result = claude_client.ask_json(
        system=(
            "You are a concise analyst. Given text (possibly with user notes and webpage content), "
            "produce a memo with: title (Korean), 3 bullet summary (Korean), category, tags."
            "[출력 규칙]"
            "title: 10~25자, 핵심 포함"
            "summary_bullets: 1~3개, 각 15~35자, 커뮤니티 말투(예: “~하면 됨”, “~인 듯”, “요약하면”), 쉬운 말 + 군더더기 제거"
            "category: [일, 배움, 아이디어, 정보, 기록, 문화, 소비] 중 1개"
            "tags: 2~5개 명사형(2~10자), 제품+개념+목적 조합"
        ),
        user=text,
        schema=ANALYST_SCHEMA,
    )
    result["source_url"] = url or ""
    result["source_type"] = source_type
    result["_raw_content"] = text  # for storage
    return result


# ── Librarian (📚) ──────────────────────────────────────────
def librarian_run(action_payload: str, analyst_result: dict | None = None) -> dict:
    """Handle save/list/search/delete."""
    action, _, payload = action_payload.partition(":")

    if action == "save" or analyst_result is not None:
        if analyst_result is None:
            return {"error": "No analyst result to save"}

        src_url = analyst_result["source_url"]

        # ── Dedup check ──
        if src_url and not src_url.startswith("memo://"):
            existing = supabase_client.find_by_url(src_url)
            if existing:
                return {
                    "action": "duplicate",
                    "existing_id": existing["id"],
                    "existing_title": existing["title"],
                }

        if not src_url:
            src_url = f"memo://{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

        # Generate embedding
        embed_text = _memo_text(analyst_result)
        emb = embeddings.embed_one(embed_text)

        memo = {
            "title": analyst_result["title"],
            "summary_bullets": analyst_result["bullets"],
            "category": analyst_result["category"],
            "tags": analyst_result["tags"],
            "source_url": src_url,
            "source_type": analyst_result["source_type"],
            "raw_content": analyst_result.get("_raw_content", "")[:8000],
            "embedding": emb,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        saved = supabase_client.upsert_memo(memo)
        return {"action": "saved", "memo": saved[0] if saved else memo}

    if action == "list":
        memos = supabase_client.list_memos()
        return {"action": "list", "memos": memos}

    if action == "search":
        # Vector search + text search, merge and dedupe
        try:
            query_emb = embeddings.embed_one(payload)
            vec_memos = supabase_client.search_memos_vector(query_emb)
        except Exception:
            vec_memos = []
    
        text_memos = supabase_client.search_memos_text(payload)
    
        seen = set()
        memos = []
        for m in vec_memos + text_memos:
            mid = m.get("id")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            memos.append(_decorate(m))
    
        return {"action": "search", "query": payload, "memos": memos}

    if action == "category":
        if not payload:
            # No category specified -> show counts per category
            counts = supabase_client.get_category_counts()
            return {"action": "category_list", "counts": counts}
        memos = supabase_client.get_memos_by_category(payload)
        return {"action": "category", "category": payload, "memos": memos}

    if action == "view":
        memo = supabase_client.get_memo_by_id(payload)
        return {"action": "view", "memo": memo}

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
