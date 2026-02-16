"""Dialogue-style Telegram message formatter.

All 'character vibe' is produced here in Python, NOT by the LLM.
"""
from __future__ import annotations


def fmt_analyst(data: dict) -> str:
    """Format analyst result for Telegram."""
    bullets = "\n".join(f"  • {b}" for b in data.get("bullets", []))
    tags = " ".join(f"#{t}" for t in data.get("tags", []))
    return (
        f"🔍 *분석 완료!*\n\n"
        f"📌 *{_esc(data.get('title', ''))}*\n\n"
        f"{bullets}\n\n"
        f"📂 카테고리: `{data.get('category', '')}`\n"
        f"🏷 {tags}"
    )


def fmt_saved(data: dict) -> str:
    memo = data.get("memo", {})
    return f"📚 *저장 완료!*\n`{memo.get('title', '(제목 없음)')}`"


def fmt_list(data: dict) -> str:
    memos = data.get("memos", [])
    if not memos:
        return "📚 저장된 메모가 없습니다."
    lines = []
    for i, m in enumerate(memos, 1):
        lines.append(f"{i}. *{_esc(m.get('title',''))}*\n   `{m.get('id','')}`")
    return "📚 *메모 목록*\n\n" + "\n".join(lines)


def fmt_search(data: dict) -> str:
    memos = data.get("memos", [])
    q = data.get("query", "")
    if not memos:
        return f"🔍 `{_esc(q)}` 검색 결과 없음"

    lines = [f"🔍 *검색: {_esc(q)}*\n"]

    for m in memos:
        # ✅ decorate가 만든 표시용 필드 우선
        title = (m.get("display_title") or m.get("title") or "").strip()
        preview = (m.get("display_preview") or "").strip()
        date = (m.get("display_date") or "").strip()

        # id는 계속 보여주고 싶으면 유지
        mid8 = (m.get("id") or "")[:8]

        # 제목 라인: date / id 같이 붙이기
        suffix_parts = [p for p in [date, mid8] if p]
        suffix = ("  " + "  ".join(suffix_parts)) if suffix_parts else ""

        lines.append(f"  • *{_esc(title)}*{_esc(suffix)}")

        if preview:
            lines.append(f"    _{_esc(preview)}_")
        else:
            # fallback: summary_bullets 1개만 짧게
            bullets = m.get("summary_bullets", [])
            if bullets:
                fb = str(bullets[0]).strip()[:80]
                lines.append(f"    _{_esc(fb)}_")

    return "\n".join(lines)



def fmt_delete(data: dict) -> str:
    ok = data.get("success", False)
    mid = data.get("memo_id", "?")
    return f"🗑 `{mid}` {'삭제 완료' if ok else '삭제 실패'}"


def fmt_category_list(data: dict) -> str:
    counts = data.get("counts", [])
    if not counts:
        return "📂 저장된 카테고리가 없습니다."
    total = sum(c["count"] for c in counts)
    lines = [f"📂 *카테고리 현황* (총 {total}개)\n"]
    for c in counts:
        lines.append(f"  • `{c['category']}` — {c['count']}개")
    lines.append(f"\n특정 카테고리 보기: `/category 카테고리명`")
    return "\n".join(lines)


def fmt_category(data: dict) -> str:
    memos = data.get("memos", [])
    cat = data.get("category", "")
    if not memos:
        return f"📂 `{cat}` 카테고리에 메모가 없습니다."
    lines = [f"📂 *카테고리: {_esc(cat)}* ({len(memos)}개)\n"]
    for i, m in enumerate(memos, 1):
        lines.append(f"{i}. *{_esc(m.get('title',''))}*\n   `{m.get('id','')}`")
    return "\n".join(lines)


def fmt_view(data: dict) -> str:
    memo = data.get("memo")
    if not memo:
        return "📄 해당 메모를 찾을 수 없습니다."
    bullets = "\n".join(f"  • {b}" for b in memo.get("summary_bullets", []))
    tags = " ".join(f"#{t}" for t in memo.get("tags", []))
    url = memo.get("source_url", "")
    url_line = f"🔗 {url}\n" if url and not url.startswith("memo://") else ""
    raw = memo.get("raw_content", "")
    raw_section = ""
    if raw:
        preview = raw[:500]
        if len(raw) > 500:
            preview += "..."
        raw_section = f"\n📝 *본문*\n{_esc(preview)}\n"
    return (
        f"📄 *{_esc(memo.get('title', ''))}*\n\n"
        f"{bullets}\n\n"
        f"📂 카테고리: `{memo.get('category', '')}`\n"
        f"🏷 {tags}\n"
        f"🕐 {memo.get('created_at', '')[:19]}\n"
        f"🆔 `{memo.get('id', '')}`\n"
        f"{url_line}"
        f"{raw_section}"
    ).strip()


def fmt_recommend(data: dict) -> str:
    recs = data.get("recommendations", [])
    if not recs:
        return "💡 추천할 메모가 없습니다."
    lines = ["💡 *추천 메모*\n"]
    for r in recs:
        lines.append(f"  • `{r['memo_id'][:8]}` — {r['reason']}")
    return "\n".join(lines)


def fmt_duplicate(data: dict) -> str:
    return (
        f"📚 *이미 저장된 메모입니다!*\n"
        f"제목: `{data.get('existing_title', '')}`\n"
        f"ID: `{data.get('existing_id', '')}`"
    )


def fmt_error(msg: str) -> str:
    return f"⚠️ {msg}"


def fmt_help() -> str:
    return (
        "📖 *사용법*\n\n"
        "• URL 보내기 → 자동 분석 & 저장\n"
        "• 텍스트 + URL → 메모와 함께 저장\n"
        "• `/save <URL>` → 분석 & 저장\n"
        "• `/list` → 메모 목록\n"
        "• `/search <키워드>` → 검색\n"
        "• `/category <이름>` → 카테고리별 보기\n"
        "• `/view <id>` → 메모 상세보기\n"
        "• `/delete <id>` → 삭제\n"
        "• `/recommend` → 추천\n"
        "• `/verbose on|off` → 단계별 메시지 표시"
    )


def fmt_verbose_step(stage: str, data: dict) -> str:
    """Verbose mode: show intermediate stage output."""
    import json
    preview = json.dumps(data, ensure_ascii=False, indent=2)
    if len(preview) > 500:
        preview = preview[:500] + "..."
    return f"🔧 *[{stage}]*\n```json\n{preview}\n```"


def _esc(text: str) -> str:
    """Escape Markdown V1 special chars."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text
