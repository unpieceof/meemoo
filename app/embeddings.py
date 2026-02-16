"""OpenAI embedding client (text-embedding-3-small, 1536 dims)."""
from __future__ import annotations

import httpx
from .config import OPENAI_API_KEY

_URL = "https://api.openai.com/v1/embeddings"
_MODEL = "text-embedding-3-small"  # 1536 dims


def embed(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via OpenAI API."""
    resp = httpx.post(
        _URL,
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={"input": texts, "model": _MODEL},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    return [d["embedding"] for d in data]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
