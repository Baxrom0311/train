"""RAG: bo'laklash, embedding to'ldirish, gibrid qidiruv (CONTRACT.md §9.4)."""
from pathlib import Path

import yaml
from sqlalchemy import select

from app.models.scenario import EMBEDDING_DIM, DocumentChunk
from app.scenario.importer import import_scenario
from app.scenario.rag import (
    SMALL_CORPUS_CHARS,
    chunk_text,
    embed_pending_chunks,
    or_tsquery,
    rrf,
    search,
)
from app.scenario.schema import ScenarioDefinition

FIXTURE = Path(__file__).parent / "fixtures" / "scenarios" / "elon-market-backend-day1.yaml"


def _defn(documents=None) -> ScenarioDefinition:
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    if documents is not None:
        data["documents"] = documents
        data["personas"][0]["knows"] = [d["key"] for d in documents]
        data["personas"][1]["knows"] = []
    return ScenarioDefinition.model_validate(data)


def _filler(word: str, n: int) -> str:
    return "\n\n".join(f"{word} bo'limi {i}. Bu yerda oddiy ichki qoida yozilgan." for i in range(n))


def _vec(hot: int) -> list[float]:
    v = [0.0] * EMBEDDING_DIM
    v[hot] = 1.0
    return v


async def fake_embed(texts, task):
    """`refund` so'zi bor matn → 0-o'q, qolgani → 1-o'q."""
    return [_vec(0 if "refund" in t.lower() else 1) for t in texts]


async def _no_embed(texts, task):
    return None


def test_chunk_text_packs_paragraphs_with_overlap():
    text = "\n\n".join(f"Paragraf {i}. " + "so'z " * 40 for i in range(20))
    chunks = chunk_text(text, size=600, overlap=100)
    assert len(chunks) > 3 and all(len(c) <= 600 for c in chunks)
    assert chunks[1].startswith(chunks[0][-100:])
    assert chunk_text("Qisqa matn.") == ["Qisqa matn."]


def test_chunk_text_splits_huge_paragraph():
    chunks = chunk_text("x" * 3000, size=1000, overlap=100)
    assert all(len(c) <= 1000 for c in chunks) and len(chunks) >= 3


def test_query_helpers():
    assert or_tsquery("Refund qanday ishlaydi? (orders)") == "refund | qanday | ishlaydi | orders"
    assert or_tsquery("?! .") is None
    assert rrf([["a", "b", "c"], ["c", "a"]]) == ["a", "c", "b"]


async def test_small_corpus_returned_whole_and_filtered_by_persona(db_session):
    version, _ = await import_scenario(db_session, _defn())
    await db_session.commit()
    dilnoza = await search(db_session, version, "dilnoza", "standup", embed_fn=fake_embed)
    kamron = await search(db_session, version, "kamron", "orders", embed_fn=fake_embed)
    assert [p.title for p in dilnoza] == ["Onboarding", "Orders API"]
    assert [p.title for p in kamron] == ["Onboarding"]           # knows ro'yxatidan tashqari yo'q
    assert await search(db_session, version, "nobody", "x", embed_fn=fake_embed) == []


async def test_hybrid_search_large_corpus(db_session):
    docs = [
        {"key": "doc_policy", "title": "Ichki qoidalar", "content": _filler("Qoida", 80)},
        {"key": "doc_refunds", "title": "Qaytarishlar",
         "content": _filler("Hisobot", 40) + "\n\nRefund qilingan buyurtmada amount maydoni bo'sh qoladi."},
    ]
    assert sum(len(d["content"]) for d in docs) > SMALL_CORPUS_CHARS
    version, _ = await import_scenario(db_session, _defn(docs))
    await db_session.commit()

    # embedding'siz: faqat full-text
    passages = await search(db_session, version, "dilnoza", "refund nima?", embed_fn=_no_embed)
    assert passages and "Refund" in passages[0].text

    filled = await embed_pending_chunks(db_session, embed_fn=fake_embed)
    await db_session.commit()
    total = len((await db_session.execute(select(DocumentChunk.id))).all())
    assert filled == total and await embed_pending_chunks(db_session, embed_fn=fake_embed) == 0

    # embedding bilan: vektor ham refund bo'lagini birinchi qo'yadi
    passages = await search(db_session, version, "dilnoza", "pul qaytarish refund", k=2, embed_fn=fake_embed)
    assert len(passages) == 2 and "Refund" in passages[0].text
    # personaj bilmaydigan hujjat yo'q
    assert await search(db_session, version, "kamron", "refund", embed_fn=fake_embed) == []


async def test_embed_pending_chunks_api_down(db_session):
    await import_scenario(db_session, _defn())
    await db_session.commit()

    assert await embed_pending_chunks(db_session, embed_fn=_no_embed) == 0
