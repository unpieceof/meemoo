"""Thin Claude API wrapper with strict JSON schema prompting."""
from __future__ import annotations

import json
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_json(system: str, user: str, schema: dict) -> dict:
    """Call Claude and enforce JSON-only response matching *schema*."""
    schema_str = json.dumps(schema, ensure_ascii=False)
    full_system = (
        f"{system}\n\n"
        "IMPORTANT: respond with ONLY valid JSON matching this schema, "
        f"no commentary:\n{schema_str}"
    )
    resp = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=full_system,
        messages=[{"role": "user", "content": user}],
    )
    text = resp.content[0].text.strip()
    # Strip markdown fences if model wraps output
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)
