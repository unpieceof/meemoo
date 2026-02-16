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
        tags = " ".join(f"#{t}" for t in m.get("tags", []))
        lines.append(f"{i}. *[{m.get("category"}] {_esc(m.get('title',''))}*\n   `{m.get('id','')}`\n   {tags}")
    return "📚 *메모 목록*\n\n" + "\n".join(lines)


def fmt_search(data: dict) -> str:
    memos = data.get("memos", [])
    q = data.get("query", "")
    if not memos:
        return f"🔍 `{_esc(q)}` 검색 결과 없음"

    lines = [f"🔍 *검색: {_esc(q)}*\n"]

    for m in memos:
        # display_title 예: "📘 [배움 · Agent Skills] 실제제목"
        display_title = (m.get("display_title") or "").strip()
        raw_title = (m.get("title") or "").strip()

        date = (m.get("display_date") or "").strip()
        mid8 = (m.get("id") or "")[:8]

        # ---- 제목 처리 ----
        if display_title:
            # prefix 부분은 그대로 두고,
            # 실제 title 텍스트만 escape 적용
            # → 마지막 raw_title 부분만 교체
            safe_title = display_title.replace(raw_title, _esc(raw_title))
        else:
            safe_title = _esc(raw_title)

        # ---- suffix (날짜 + id코드) ----
        suffix_parts = []
        if date:
            suffix_parts.append(date)
        if mid8:
            suffix_parts.append(f"`{mid8}`")  # ← 코드블럭 처리

        suffix = "  " + "  ".join(suffix_parts) if suffix_parts else ""

        lines.append(f"  • {safe_title}{suffix}")

        # ---- preview ----
        preview = (m.get("display_preview") or "").strip()
        if preview:
            lines.append(f"    _{_esc(preview)}_")

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
    cats = data.get("categories", [])
    if not cats:
        return "💡 추천할 메모가 아직 없어…"

    lines = ["💡 *오늘 다시 보면 이득 보는 메모들* 🔥\n"]
    for c in cats:
        emoji = c.get("emoji", "💡")
        category = c.get("category", "추천")
        one_liner = c.get("one_liner", "")

        lines.append(f"{emoji} *{category}*")
        if one_liner:
            lines.append(f"> {one_liner}")

        for it in c.get("items", []):
            memo_id = it["memo_id"][:8]
            title = it.get("title", "").strip()
            preview = it.get("preview", "").strip()
            hook = it.get("hook", "").strip()
            reason = it.get("reason", "").strip()
            tags = it.get("tags", []) or []

            lines.append(f"  • `{memo_id}` **{title}**")
            if hook:
                lines.append(f"    - {hook}")
            if preview:
                lines.append(f"    - _미리보기_: {preview}")
            if tags:
                lines.append(f"    - 태그: " + ", ".join([f"`{t}`" for t in tags[:4]]))
            if reason:
                lines.append(f"    - 왜 지금?: {reason}")

        lines.append("")

    return "\n".join(lines).rstrip()



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
        """📖 이렇게 쓰면 돼요

• 링크 보내면 → 자동 분석해서 저장해요
• 메모만 보내도 → 정리해서 저장해요

🔎 찾기
• /search 키워드 → 메모 검색
• /list → 최근 메모 보기
• /category 이름 → 카테고리별 보기
• /recommend → 랜덤 메모 추천

📂 관리
• /view id → 자세히 보기
• /delete id → 삭제
"""
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
