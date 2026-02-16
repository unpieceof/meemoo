"""Rule-based router. No LLM needed."""
from __future__ import annotations

import re
from .schemas import ROUTE_COMMANDS


def route(text: str) -> tuple[str, str]:
    """Return (action, payload).

    action: 'analyst' | 'librarian' | 'recommender' | 'setting' | 'help' | 'unknown'
    """
    text = text.strip()

    # Commands: /list, /search query, /delete id, /recommend, /verbose on|off
    cmd_match = re.match(r"^/(\w+)\s*(.*)", text, re.S)
    if cmd_match:
        cmd = cmd_match.group(1).lower()
        payload = cmd_match.group(2).strip()
        action = ROUTE_COMMANDS.get(cmd, "unknown")
        # /save <url> -> analyst
        if cmd == "save":
            return "analyst", payload
        # /search, /list, /delete -> librarian with sub-action
        if action == "librarian":
            return "librarian", f"{cmd}:{payload}"
        return action, payload

    # Bare URL -> analyst (save)
    if re.match(r"https?://", text):
        return "analyst", text

    # Text containing URL -> analyst (save with context)
    url_match = re.search(r"https?://\S+", text)
    if url_match:
        return "analyst", text

    # Bare domain (e.g. "griddyicons.com") -> analyst
    if re.search(r"\b[\w-]+\.(com|net|org|io|co|dev|ai|kr|me|app|xyz)\b", text, re.I):
        return "analyst", text

    # Any text longer than 10 chars -> treat as memo save
    if len(text) > 10:
        return "analyst", text

    return "unknown", text
