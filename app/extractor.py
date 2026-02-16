"""Lightweight URL content extractor."""
from __future__ import annotations

import re
import httpx
from .config import MAX_EXTRACT_CHARS


def extract_text(url: str) -> tuple[str, str]:
    """Fetch URL and return (source_type, trimmed_text).

    source_type: 'web' | 'x' | 'instagram'
    Falls back to URL itself if content is empty (e.g. X/Instagram auth walls).
    """
    source_type = _detect_source(url)
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=15,
                         headers={"User-Agent": "MemoBot/1.0"})
        resp.raise_for_status()
        text = _strip_html(resp.text)[:MAX_EXTRACT_CHARS]
    except Exception:
        text = ""

    # Fallback: if extracted text is too short, use URL + meta description
    if len(text.strip()) < 30:
        text = f"URL: {url} (콘텐츠를 직접 추출할 수 없습니다. URL 정보만으로 분석해주세요.)"

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
