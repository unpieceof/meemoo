"""케미담당(💖) — one-line banter for Telegram."""
from __future__ import annotations

import logging
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger(__name__)
_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_banter(signals: dict) -> str:
    """Generate exactly one Korean banter line from minimal signals."""
    system = (
        "You are 케미담당(💖). Output EXACTLY one line of casual Korean banter (<= 10 words). "
        "No quotes, no extra lines, no explanations. "
        "Use speaker prefix: 팀장: or 분석가: or 사서:. Do NOT use 케미담당 as prefix."
        "Optional: make it a quick back-and-forth in ONE line using two prefixes. "
        "You MAY reference the title briefly (<= 6 words). "
        "Do NOT mention URLs/summaries/tags. Do NOT infer facts beyond the title. "
        "Warm, slightly witty."
    )
    if signals.get('is_night'):
        system += " Subtle late-night vibe."

    # Sanitize title: keep only first 30 chars, strip emoji
    title = signals.get("title", "")[:30]

    user = (
        f"stage={signals.get('stage','')}, intent={signals.get('intent','')}, "
        f"source_type={signals.get('source_type','')}, "
        f"duplicate={signals.get('duplicate', False)}, "
        f"category={signals.get('category','')}, "
        f"tag_count={signals.get('tag_count', 0)}, "
        f"title={title}"
    )

    resp = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=50,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    # Take only the first line
    return resp.content[0].text.strip().split("\n")[0].strip()


def generate_sms() -> str:
    """Generate a random one-liner about date/time/weather with character vibe."""
    from datetime import datetime, timezone, timedelta
    kst = datetime.now(timezone(timedelta(hours=9)))
    time_info = kst.strftime("%m월 %d일 %A %H:%M")

    resp = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=60,
        system=(
            "You are 케미담당(💖). Output EXACTLY one line of casual Korean (10~25자). "
            "No quotes, no extra lines, no explanations. "
            "Use speaker prefix: 팀장: or 분석가: or 사서:. "
            "날짜/시간/계절/날씨 중 하나를 소재로 캐릭터성 있는 한 마디. "
            "Warm, witty, slightly poetic."
        ),
        messages=[{"role": "user", "content": f"지금: {time_info}"}],
    )
    return resp.content[0].text.strip().split("\n")[0].strip()


def maybe_banter(signals: dict) -> str | None:
    """Always return banter for memo inputs."""
    try:
        return generate_banter(signals)
    except Exception as e:
        log.warning("Banter failed: %s", e)
        return None
