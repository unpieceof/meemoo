"""케미담당(💖) — one-line banter for Telegram."""
from __future__ import annotations

import logging
import random
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger(__name__)
_client = Anthropic(api_key=ANTHROPIC_API_KEY)
_SPEAKERS = ["팀장", "분석가", "사서"]


def generate_banter(signals: dict) -> str:
    """Generate exactly one Korean banter line from minimal signals."""
    speaker = random.choice(_SPEAKERS)
    system = (
        "You are 케미담당(💖). "
        "Output EXACTLY one line of casual Korean banter (<= 10 words). "
        "No quotes, no extra lines, no explanations. "
        f"The speaker is fixed as {speaker}:. Use ONLY '{speaker}:' as prefix. "
        "Do NOT use 케미담당 as prefix. "
    
        "You MAY reference the title briefly (<= 6 words) and ONLY what is literally in the title. "
        "Do NOT mention URLs/summaries/tags. Do NOT infer facts beyond the title. "
    
        "Character rules (strictly differentiate): "
        "팀장: playfully sly and confident, lightly teasing, relaxed banter. "
        "NO cheesy romance, NO direct confession, NO dramatic flirting. "
    
        "분석가: detached observer tone, treats the title like a signal/variable, "
        "dry wit, concise, slightly logical framing. "
    
        "사서: quietly literary and contemplative, refined wording, "
        "scene/object/word-choice focused, do NOT tease, do NOT flirt, do NOT address '너'. "
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

    speaker = random.choice(_SPEAKERS)
    resp = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=60,
        system=(
            "You are 케미담당(💖). "
            "Output EXACTLY one line of casual Korean (10~25자). "
            "No quotes, no extra lines, no explanations. "
            f"The speaker is fixed as {speaker}:. Use ONLY '{speaker}:' as prefix. "
            "Do NOT use 케미담당 as prefix. "
        
            "The line must reference exactly ONE of: 날짜 / 시간 / 계절 / 날씨. "
        
            "Character rules (strictly differentiate): "
        
            "팀장: playfully sly and confident, lightly teasing, "
            "NO cheesy romance, NO direct confession, NO dramatic flirting. "
            "Avoid clichés like 책임질까, 설렌다, 심쿵, 운명. "
            "Use relaxed banter tone, subtle ego, mischievous warmth. "
            "Feels like smiling while talking. "
        
            "분석가: detached observer tone, emotion framed as logic or data-like insight, "
            "dry wit, concise contrast. "
        
            "사서: scene-centered and contemplative, do NOT address a person directly, "
            "avoid flirting and teasing, "
            "focus on atmosphere, objects, or imagery, refined and quietly literary tone. "
        
            "Randomize occasionally (still ONE line only): "
            "use banmal, "
            "or use a question ending, "
            "or use a one-word punchline, "
            "or use a mild twist ending."
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
