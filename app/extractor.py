"""Lightweight URL content extractor."""
from __future__ import annotations

import re
import httpx
from .config import MAX_EXTRACT_CHARS


def extract_text(url: str) -> tuple[str, str]:
    """Fetch URL and return (source_type, trimmed_text).

    source_type: 'web' | 'x' | 'instagram'
    """
    source_type = _detect_source(url)
    resp = httpx.get(url, follow_redirects=True, timeout=15,
                     headers={"User-Agent": "MemoBot/1.0"})
    resp.raise_for_status()
    text = _strip_html(resp.text)[:MAX_EXTRACT_CHARS]
    return source_type, text


def _detect_source(url: str) -> str:
    if re.search(r"(twitter\.com|x\.com)", url):
        return "x"
    if "instagram.com" in url:
        return "instagram"
    return "web"


def _strip_html(html: str) -> str:
    """Naive HTML tag removal."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
