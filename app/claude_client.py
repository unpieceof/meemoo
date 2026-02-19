"""Thin Claude API wrapper with strict JSON schema via tool use."""
from __future__ import annotations

import logging
from anthropic import Anthropic
from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL

log = logging.getLogger(__name__)
_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def ask_json(system: str, user: str, schema: dict, max_tokens: int = 1024) -> dict:
    """Call Claude and enforce JSON output via tool use (guaranteed valid schema)."""
    tool = {
        "name": "structured_output",
        "description": "Return the structured result.",
        "input_schema": schema,
    }
    resp = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        tools=[tool],
        tool_choice={"type": "tool", "name": "structured_output"},
    )

    if resp.stop_reason == "max_tokens":
        log.warning("ask_json truncated (max_tokens=%d), retrying with %d", max_tokens, max_tokens * 2)
        resp = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens * 2,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],
            tool_choice={"type": "tool", "name": "structured_output"},
        )

    if resp.stop_reason == "max_tokens":
        raise ValueError(f"Response still truncated after retry (max_tokens={max_tokens * 2})")

    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("No tool_use block in response")


def ask_json_with_image(
    system: str,
    image_b64: str,
    media_type: str,
    user_text: str,
    schema: dict,
    max_tokens: int = 1024,
) -> dict:
    """Call Claude vision API with a base64 image and enforce JSON via tool use."""
    tool = {
        "name": "structured_output",
        "description": "Return the structured result.",
        "input_schema": schema,
    }
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
        {"type": "text", "text": user_text if user_text else "이미지를 분석해주세요."},
    ]
    messages = [{"role": "user", "content": content}]
    resp = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=[tool],
        tool_choice={"type": "tool", "name": "structured_output"},
    )
    if resp.stop_reason == "max_tokens":
        log.warning("ask_json_with_image truncated (max_tokens=%d), retrying with %d", max_tokens, max_tokens * 2)
        resp = _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=max_tokens * 2,
            system=system,
            messages=messages,
            tools=[tool],
            tool_choice={"type": "tool", "name": "structured_output"},
        )
    if resp.stop_reason == "max_tokens":
        raise ValueError(f"Vision response still truncated after retry (max_tokens={max_tokens * 2})")
    for block in resp.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("No tool_use block in vision response")
