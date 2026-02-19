"""Lightweight URL content extractor."""
from __future__ import annotations

import re
import httpx
from .config import MAX_EXTRACT_CHARS


def extract_text(url: str) -> tuple[str, str]:
    """Fetch URL and return (source_type, trimmed_text).

    source_type: 'web' | 'x' | 'instagram'
    Falls back to URL itself if content is empty (e.g. X/Instagram auth walls).
    Twitter/X URLs are fetched via FxTwitter API (no API key required).
    """
    source_type = _detect_source(url)

    if source_type == "x":
        text = _fetch_twitter(url)
    else:
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


def _fetch_twitter(url: str) -> str:
    """Fetch tweet content via FxTwitter API (api.fxtwitter.com). No API key needed."""
    fx_url = re.sub(r"https?://(twitter\.com|x\.com)", "https://api.fxtwitter.com", url)
    try:
        resp = httpx.get(fx_url, follow_redirects=True, timeout=15,
                         headers={"User-Agent": "MemoBot/1.0"})
        resp.raise_for_status()
        data = resp.json()
        tweet = data.get("tweet", {})
        if not tweet:
            return ""

        parts = []

        author = tweet.get("author", {})
        if author.get("name"):
            parts.append(f"작성자: {author['name']} (@{author.get('screen_name', '')})")

        if tweet.get("text"):
            parts.append(f"내용: {tweet['text']}")

        # Quote tweet
        quote = tweet.get("quote")
        if quote:
            q_author = quote.get("author", {})
            q_name = q_author.get("name", "")
            q_handle = q_author.get("screen_name", "")
            q_text = quote.get("text", "")
            parts.append(f"인용 트윗 - {q_name} (@{q_handle}): {q_text}")

        # Media
        media = tweet.get("media") or {}
        photos = media.get("photos") or []
        videos = media.get("videos") or []
        if photos:
            parts.append(f"이미지 {len(photos)}개 포함")
        if videos:
            parts.append(f"동영상 {len(videos)}개 포함")

        # Engagement stats
        stats = []
        if tweet.get("likes") is not None:
            stats.append(f"좋아요 {tweet['likes']}")
        if tweet.get("retweets") is not None:
            stats.append(f"리트윗 {tweet['retweets']}")
        if tweet.get("replies") is not None:
            stats.append(f"댓글 {tweet['replies']}")
        if stats:
            parts.append(", ".join(stats))

        return "\n".join(parts)
    except Exception:
        return ""


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
