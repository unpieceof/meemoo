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
        lines.append(f"{i}. *{_esc(m.get('title',''))}*  `{m.get('id','')[:8]}`")
    return "📚 *메모 목록*\n\n" + "\n".join(lines)


def fmt_search(data: dict) -> str:
    memos = data.get("memos", [])
    q = data.get("query", "")
    if not memos:
        return f"🔍 `{q}` 검색 결과 없음"
    lines = [f"🔍 *검색: {_esc(q)}*\n"]
    for m in memos:
        lines.append(f"  • *{_esc(m.get('title',''))}*  `{m.get('id','')[:8]}`")
    return "\n".join(lines)


def fmt_delete(data: dict) -> str:
    ok = data.get("success", False)
    mid = data.get("memo_id", "?")
    return f"🗑 `{mid}` {'삭제 완료' if ok else '삭제 실패'}"


def fmt_recommend(data: dict) -> str:
    recs = data.get("recommendations", [])
    if not recs:
        return "💡 추천할 메모가 없습니다."
    lines = ["💡 *추천 메모*\n"]
    for r in recs:
        lines.append(f"  • `{r['memo_id'][:8]}` — {r['reason']}")
    return "\n".join(lines)


def fmt_error(msg: str) -> str:
    return f"⚠️ {msg}"


def fmt_help() -> str:
    return (
        "📖 *사용법*\n\n"
        "• URL 보내기 → 자동 분석 & 저장\n"
        "• `/save <URL>` → 분석 & 저장\n"
        "• `/list` → 메모 목록\n"
        "• `/search <키워드>` → 검색\n"
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
