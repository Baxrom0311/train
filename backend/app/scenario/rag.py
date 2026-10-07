"""
Ssenariy hujjatlari bo'yicha RAG (CONTRACT.md §9.4).

- **Indeks:** import paytida hujjatlar bo'laklanadi (`build_chunks`),
  embedding'lar keyin fon job'ida to'ldiriladi (`embed_pending_chunks`) —
  import tashqi API'ga bog'liq emas. Embedding bo'lmagan bo'lak ham
  full-text qidiruvda qatnashadi.
- **Qidiruv:** faqat shu `scenario_version` va personajning `knows`
  ro'yxatidagi hujjatlar. Personaj biladigan hujjatlar kichik bo'lsa
  (`SMALL_CORPUS_CHARS`) — qidirilmaydi, butunligicha beriladi. Aks holda
  gibrid: pgvector cosine + Postgres full-text, Reciprocal Rank Fusion.
- Rubrika, namunaviy javob, hint va `checks` bu yerga **hech qachon**
  kirmaydi — ular `scenario_documents`da yo'q (§9.4, 1-qavat).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings import embed
from app.ai.persona_chat import Passage
from app.config import settings
from app.models.scenario import DocumentChunk, ScenarioDocument, ScenarioVersion

CHUNK_CHARS = 1200
CHUNK_OVERLAP = 150
SMALL_CORPUS_CHARS = 6000
CANDIDATES = 20
RRF_K = 60
EMBED_BATCH = 200

_PARAGRAPHS = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_QUERY_WORD = re.compile(r"\w{2,}", re.UNICODE)


# ── Bo'laklash ────────────────────────────────────────────────────────


def _split_long(text: str, size: int, overlap: int) -> list[str]:
    """Juda uzun paragraf: gaplar bo'yicha, bitta gap ham sig'masa — qattiq kesish."""
    pieces: list[str] = []
    for sentence in _SENTENCE_END.split(text):
        while len(sentence) > size:
            pieces.append(sentence[:size])
            sentence = sentence[size - overlap:]
        pieces.append(sentence)
    return pieces


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Paragraflarni `size`gacha yig'adi; keyingi bo'lak oldingisining oxiridan `overlap` belgi oladi."""
    units: list[str] = []
    for para in _PARAGRAPHS.split(text.strip()):
        para = para.strip()
        if not para:
            continue
        units += _split_long(para, size, overlap) if len(para) > size else [para]

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= size:
            current = candidate
            continue
        chunks.append(current)
        tail = current[-overlap:] if overlap else ""
        current = f"{tail}\n\n{unit}" if tail and len(tail) + len(unit) + 2 <= size else unit
    if current:
        chunks.append(current)
    return chunks


async def build_chunks(db: AsyncSession, version_id: uuid.UUID) -> int:
    """Versiya hujjatlarini bo'laklaydi (embedding'siz). Commit chaqiruvchida."""
    docs = (await db.execute(
        select(ScenarioDocument).where(ScenarioDocument.scenario_version_id == version_id)
    )).scalars().all()
    count = 0
    for doc in docs:
        for i, text in enumerate(chunk_text(doc.content)):
            db.add(DocumentChunk(document_id=doc.id, chunk_index=i, text=text))
            count += 1
    await db.flush()
    return count


async def embed_pending_chunks(db: AsyncSession, limit: int = EMBED_BATCH, embed_fn=embed) -> int:
    """Embedding'i yo'q bo'laklarni to'ldiradi. API ishlamasa 0 — keyingi safar qayta urinadi."""
    rows = (await db.execute(
        select(DocumentChunk, ScenarioDocument.title)
        .join(ScenarioDocument, ScenarioDocument.id == DocumentChunk.document_id)
        .where(DocumentChunk.embedding.is_(None))
        .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        .limit(limit)
    )).all()
    if not rows:
        return 0
    vectors = await embed_fn([f"title: {title} | text: {chunk.text}" for chunk, title in rows], "RETRIEVAL_DOCUMENT")
    if not vectors:
        return 0
    for (chunk, _), vec in zip(rows, vectors):
        chunk.embedding = vec
        chunk.embedding_model = settings.EMBEDDING_MODEL
    await db.flush()
    return len(rows)


# ── Qidiruv ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class _Hit:
    chunk_id: uuid.UUID
    title: str
    text: str


def or_tsquery(query: str) -> str | None:
    """Savoldagi so'zlardan `a | b | c` — `plainto_tsquery` hammasini AND qiladi, savol uchun juda qattiq."""
    words = list(dict.fromkeys(w.lower() for w in _QUERY_WORD.findall(query)))[:20]
    return " | ".join(words) if words else None


def rrf(rankings: list[list[uuid.UUID]], k: int = RRF_K) -> list[uuid.UUID]:
    scores: dict[uuid.UUID, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda item: -scores[item])


def _visible(version_id: uuid.UUID, persona_key: str):
    return (
        ScenarioDocument.scenario_version_id == version_id,
        ScenarioDocument.visible_to_personas.contains([persona_key]),
    )


async def search(
    db: AsyncSession,
    version: ScenarioVersion,
    persona_key: str,
    query: str,
    k: int = 4,
    embed_fn=embed,
) -> list[Passage]:
    docs = (await db.execute(
        select(ScenarioDocument).where(*_visible(version.id, persona_key)).order_by(ScenarioDocument.key)
    )).scalars().all()
    if not docs:
        return []
    if sum(len(d.content) for d in docs) <= SMALL_CORPUS_CHARS:
        return [Passage(title=d.title, text=d.content) for d in docs]

    base = (
        select(DocumentChunk.id, ScenarioDocument.title, DocumentChunk.text)
        .join(ScenarioDocument, ScenarioDocument.id == DocumentChunk.document_id)
        .where(*_visible(version.id, persona_key))
    )
    rankings: list[list[uuid.UUID]] = []
    hits: dict[uuid.UUID, _Hit] = {}

    def collect(rows) -> list[uuid.UUID]:
        for cid, title, text in rows:
            hits[cid] = _Hit(cid, title, text)
        return [cid for cid, _, _ in rows]

    tsq = or_tsquery(query)
    if tsq:
        q = func.to_tsquery("simple", tsq)
        rows = (await db.execute(
            base.where(DocumentChunk.tsv.op("@@")(q))
            .order_by(func.ts_rank(DocumentChunk.tsv, q).desc())
            .limit(CANDIDATES)
        )).all()
        rankings.append(collect(rows))

    vectors = await embed_fn([query], "RETRIEVAL_QUERY")
    if vectors:
        rows = (await db.execute(
            base.where(DocumentChunk.embedding.is_not(None))
            .order_by(DocumentChunk.embedding.cosine_distance(vectors[0]))
            .limit(CANDIDATES)
        )).all()
        rankings.append(collect(rows))

    return [Passage(title=hits[cid].title, text=hits[cid].text) for cid in rrf(rankings)[:k]]
