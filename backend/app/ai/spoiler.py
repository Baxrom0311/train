"""
Anti-spoiler chiqish tekshiruvi (CONTRACT.md §9.4, 3-qavat).

Personaj/mentor javobi task'ning namunaviy javobiga juda o'xshasa — javob
tashlanadi va ssenariydagi zaxira javob yuboriladi. Ikki signal:

1. **n-gram** — namunaviy javobdagi so'z n-gramlarining qancha qismi AI
   javobida ham bor (embedding'siz ham ishlaydi);
2. **embedding cosine** — mazmunan bir xil, lekin boshqa so'zlar bilan
   aytilgan javob uchun (Gemini kaliti bo'lmasa o'tkazib yuboriladi).
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.ai.embeddings import cosine, embed

NGRAM_N = 5
NGRAM_THRESHOLD = 0.3
COSINE_THRESHOLD = 0.85
# Bundan qisqa namunaviy javob n-gram uchun juda umumiy
MIN_REFERENCE_WORDS = 3

_WORD = re.compile(r"\w+", re.UNICODE)


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower().replace("ʻ", "'").replace("’", "'"))


def _ngrams(words: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def ngram_overlap(reply: str, reference: str, n: int = NGRAM_N) -> float:
    """Namunaviy javob n-gramlarining AI javobida uchragan ulushi (0..1)."""
    ref = _words(reference)
    if len(ref) < MIN_REFERENCE_WORDS:
        return 0.0
    n = min(n, len(ref))
    ref_grams = _ngrams(ref, n)
    reply_grams = _ngrams(_words(reply), n)
    return len(ref_grams & reply_grams) / len(ref_grams)


async def is_spoiler(
    reply: str,
    references: Sequence[str],
    *,
    embed_fn=embed,
    ngram_threshold: float = NGRAM_THRESHOLD,
    cosine_threshold: float = COSINE_THRESHOLD,
) -> bool:
    references = [r for r in references if r and r.strip()]
    if not references or not reply.strip():
        return False
    if any(ngram_overlap(reply, ref) >= ngram_threshold for ref in references):
        return True
    vectors = await embed_fn([reply, *references], "SEMANTIC_SIMILARITY")
    if not vectors:
        return False
    return any(cosine(vectors[0], v) >= cosine_threshold for v in vectors[1:])
