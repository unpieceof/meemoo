"""케미담당(🎭) — one-line banter for Telegram."""
from __future__ import annotations

import logging
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger(__name__)
_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def generate_banter(signals: dict) -> str:
    """Generate exactly one Korean banter line from minimal signals."""
    system = (
        "You are 케미담당(🎭). Output EXACTLY one line of casual Korean banter (<= 15 words). "
        "No quotes, no extra lines, no explanations. "
        "You MAY reference the title as a short quote fragment (<= 6 words) or noun phrase. "
        "Do NOT mention URLs, summaries, or tag text. Do NOT infer facts beyond the title. "
    )
    if signals.get("is_night"):
        system += "Make it subtly late-night. "

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


def maybe_banter(signals: dict) -> str | None:
    """Always return banter for memo inputs."""
    try:
        return generate_banter(signals)
    except Exception as e:
        log.warning("Banter failed: %s", e)
        return None
