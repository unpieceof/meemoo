"""Pipeline workers: Analyst, Librarian, Recommender."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from . import claude_client, supabase_client, extractor
from .schemas import ANALYST_SCHEMA, RECOMMENDER_SCHEMA

PAGE_SIZE = 5


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

    prefix = f"{icon} \\[{' · '.join(left)}\\]"
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
    # Detect bare domain (e.g. griddyicons.com) and prepend https://
    if not url:
        domain_match = re.search(r"\b([\w-]+\.(?:com|net|org|io|co|dev|ai|kr|me|app|xyz))\b", payload, re.I)
        if domain_match:
            url = f"https://{domain_match.group(1)}"
    user_context = payload.replace(url_match.group(0) if url_match else "", "").strip() if url else payload

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
            "tags: 2~5개 명사형(2~10자), 검색이 쉽도록 키워드를 추출하고, 식당/카페 관련 메모는 무조건 맛집 태그를 추가. 장소가 있으면 장소(2~5자) 키워드를 반드시 추가."
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

        memo = {
            "title": analyst_result["title"],
            "summary_bullets": analyst_result["bullets"],
            "category": analyst_result["category"],
            "tags": analyst_result["tags"],
            "source_url": src_url,
            "source_type": analyst_result["source_type"],
            "raw_content": analyst_result.get("_raw_content", "")[:8000],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        saved = supabase_client.upsert_memo(memo)
        return {"action": "saved", "memo": saved[0] if saved else memo}

    if action == "list":
        page = 0
        if payload.strip().isdigit():
            page = int(payload.strip())
        offset = page * PAGE_SIZE
        memos = supabase_client.list_memos(limit=PAGE_SIZE, offset=offset)
        total = supabase_client.count_memos()
        return {"action": "list", "memos": memos, "page": page, "total": total}

    if action == "search":
        # Parse page from payload: "query:page" or just "query"
        page = 0
        query = payload
        if ":" in payload:
            parts = payload.rsplit(":", 1)
            if parts[-1].strip().isdigit():
                query = parts[0]
                page = int(parts[-1].strip())

        offset = page * PAGE_SIZE
        memos, total = supabase_client.search_memos_text(query, limit=PAGE_SIZE, offset=offset)
        memos = [_decorate(m) for m in memos]

        return {"action": "search", "query": query, "memos": memos, "page": page, "total": total}

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
def recommender_run(payload: str, max_categories: int = 3, memos: list | None = None) -> dict:
    """Recommend memos grouped by category. Only when explicitly requested."""
    metas = memos if memos is not None else supabase_client.get_random_memos_by_category(per_category=1, max_categories=max_categories)
    if not metas:
        return {"categories": []}

    result = claude_client.ask_json(
        system=(
            "너는 '메모 추천 큐레이터'야.\n"
            "입력은 메모 목록(JSON 배열)이고, 각 메모는 id/title/summary_bullets/category/tags를 가진다.\n\n"
            "목표: 각 메모에 대해 카테고리별 추천 결과(JSON)를 반환.\n\n"
            "규칙:\n"
            "1) memo.category를 기준으로 묶어.\n"
            "   - category가 너무 넓으면 tags를 참고해 더 직관적인 이름으로 바꿔도 됨.\n"
            f"2) 카테고리는 최대 {max_categories}개.\n"
            "3) 각 카테고리에는 emoji 1개, one_liner(커뮤니티 말투로 자극적인 한 줄 소개) 1개.\n"
            "4) 각 카테고리 items는 입력된 메모 전부 포함.\n"
            "5) 각 item에는:\n"
            "   - memo_id: 입력의 id 그대로\n"
            "   - title: 입력의 title 그대로\n"
            "   - preview: summary_bullets 중 가장 '아 이거!' 싶은 1개\n"
            "   - reason: 짧고 직관적으로 왜 지금 봐야 하는지\n"
            "   - tags: 입력 tags 중 핵심 2~4개만\n"
            "6) 말투: 친근 + 살짝 자극(커뮤니티 톤). 정보는 정확하게.\n"
        ),
        user=json.dumps(metas, ensure_ascii=False),
        schema=RECOMMENDER_SCHEMA,
        max_tokens=1024,
    )
    return result

