"""
Embedding (CONTRACT.md §9.0 Q12): Gemini `gemini-embedding-001`, 768 o'lcham.

`embed(texts, task)` → vektorlar ro'yxati yoki `None` (kalit yo'q / API
xatosi). `None` bo'lsa RAG full-text qidiruvga tushadi, anti-spoiler esa
faqat n-gram tekshiruvi bilan ishlaydi — hech narsa to'xtab qolmaydi.

768 — to'liq 3072 o'lchamning qisqartirilgani, shuning uchun vektorlar
normallashtiriladi (cosine to'g'ri ishlashi uchun).
"""

from __future__ import annotations

import logging
import math
from typing import Literal

import httpx

from app.config import settings
from app.models.scenario import EMBEDDING_DIM

log = logging.getLogger(__name__)

Task = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY"]
BATCH_SIZE = 100


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm else vec


def cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


async def embed(
    texts: list[str],
    task: Task = "RETRIEVAL_DOCUMENT",
    client: httpx.AsyncClient | None = None,
) -> list[list[float]] | None:
    if not texts:
        return []
    if not settings.GEMINI_API_KEY:
        return None
    model = settings.EMBEDDING_MODEL
    own_client = client is None
    client = client or httpx.AsyncClient()
    out: list[list[float]] = []
    try:
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents",
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json={"requests": [
                    {
                        "model": f"models/{model}",
                        "content": {"parts": [{"text": t}]},
                        "taskType": task,
                        "outputDimensionality": EMBEDDING_DIM,
                    }
                    for t in batch
                ]},
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            vectors = [e["values"] for e in resp.json()["embeddings"]]
            if len(vectors) != len(batch) or any(len(v) != EMBEDDING_DIM for v in vectors):
                raise ValueError("embedding javobi kutilgan o'lchamda emas")
            out += [normalize(v) for v in vectors]
        return out
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        log.warning("embedding muvaffaqiyatsiz: %s", exc)
        return None
    finally:
        if own_client:
            await client.aclose()
