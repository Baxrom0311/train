"""AI qatlami: llm.chat, embed, evaluate_rubric, anti-spoiler, persona prompt (CONTRACT.md §9.4, §9.10)."""
import json

import httpx
import pytest
from pydantic import BaseModel

from app.ai import embeddings
from app.ai.evaluator import RubricOut, _schema_for, build_messages as grader_messages, evaluate_rubric
from app.ai.llm import LLMResult, chat, parse_json
from app.ai.persona_chat import ChatTurn, Passage, PersonaContext, PersonaProfile, build_messages
from app.ai.spoiler import is_spoiler, ngram_overlap
from app.config import settings
from app.models.scenario import EMBEDDING_DIM
from app.scenario.schema import RubricCriterion


class Echo(BaseModel):
    answer: str


@pytest.fixture
def keys(monkeypatch):
    for name, value in {
        "DEEPSEEK_API_KEY": "test-deepseek", "GEMINI_API_KEY": "test-gemini",
        "OPENAI_API_KEY": "", "LLM_PROVIDERS": "deepseek,gemini,openai",
    }.items():
        monkeypatch.setattr(settings, name, value)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _gemini_reply(text: str) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
    }


# ── llm.chat ──────────────────────────────────────────────────────────


async def test_chat_falls_back_and_counts_tokens(keys):
    seen = []

    def handler(request: httpx.Request):
        seen.append(request.url.host)
        if request.url.host == "api.deepseek.com":
            return httpx.Response(500)
        body = json.loads(request.content)
        assert body["systemInstruction"]["parts"][0]["text"] == "sys"
        assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert request.headers["x-goog-api-key"] == "test-gemini"
        return httpx.Response(200, json=_gemini_reply('```json\n{"answer": "ok"}\n```'))

    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]
    async with _client(handler) as client:
        result = await chat(messages, schema=Echo, client=client)
    assert seen == ["api.deepseek.com", "generativelanguage.googleapis.com"]
    assert result.provider == "gemini" and result.data.answer == "ok" and result.tokens == 18


async def test_chat_invalid_json_tries_next(keys):
    def handler(request):
        if request.url.host == "api.deepseek.com":
            return httpx.Response(200, json={"choices": [{"message": {"content": "{\"wrong\": 1}"}}]})
        return httpx.Response(200, json=_gemini_reply('{"answer": "fixed"}'))

    async with _client(handler) as client:
        result = await chat([{"role": "user", "content": "x"}], schema=Echo, client=client)
    assert result.provider == "gemini" and result.data.answer == "fixed"


async def test_chat_openai_compatible_json_mode(keys, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDERS", "deepseek")

    def handler(request):
        body = json.loads(request.content)
        assert body["response_format"] == {"type": "json_object"} and body["model"] == settings.DEEPSEEK_MODEL
        assert request.headers["authorization"] == "Bearer test-deepseek"
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "{\"answer\": \"a\"}"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        })

    async with _client(handler) as client:
        result = await chat([{"role": "user", "content": "x"}], schema=Echo, client=client)
    assert result.provider == "deepseek" and result.tokens == 7


async def test_chat_without_keys_returns_none(monkeypatch):
    for name in ("DEEPSEEK_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setattr(settings, name, "")

    def handler(request):  # pragma: no cover — chaqirilmasligi kerak
        raise AssertionError("tarmoqqa chiqmasin")

    async with _client(handler) as client:
        assert await chat([{"role": "user", "content": "x"}], client=client) is None


def test_parse_json_strips_fence():
    assert parse_json('```\n{"answer": "x"}\n```', Echo).answer == "x"


# ── embed ─────────────────────────────────────────────────────────────


async def test_embed_normalizes_and_checks_dimension(keys):
    def handler(request):
        body = json.loads(request.content)
        assert body["requests"][0]["outputDimensionality"] == EMBEDDING_DIM
        return httpx.Response(200, json={"embeddings": [{"values": [3.0, 4.0] + [0.0] * (EMBEDDING_DIM - 2)}]})

    async with _client(handler) as client:
        [vec] = await embeddings.embed(["salom"], client=client)
    assert vec[:2] == pytest.approx([0.6, 0.8])

    async with _client(lambda r: httpx.Response(200, json={"embeddings": [{"values": [1.0]}]})) as client:
        assert await embeddings.embed(["salom"], client=client) is None


async def test_embed_without_key(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    assert await embeddings.embed(["x"]) is None


# ── evaluate_rubric ───────────────────────────────────────────────────

RUBRIC = [
    RubricCriterion(id="root_cause", description="Sababni topgan", weight=2),
    RubricCriterion(id="fix_quality", description="Tuzatish sifati"),
]


def _fake_chat(payload: dict):
    calls = []

    async def fake(messages, schema=None, **kwargs):
        calls.append(messages)
        try:
            data = schema.model_validate(payload)
        except ValueError:
            return None
        return LLMResult(text=json.dumps(payload), data=data, provider="fake", model="m", tokens_in=3, tokens_out=4)

    return fake, calls


async def test_evaluate_rubric_weighted_score():
    fake, calls = _fake_chat({
        "criteria": [
            {"id": "root_cause", "score": 80, "evidence": "refund topilgan"},
            {"id": "fix_quality", "score": 50},
        ],
        "short_feedback": "Sabab to'g'ri topilgan. Test qo'shing.",
    })
    result = await evaluate_rubric("Bug", "javob", RUBRIC, reference_answer="REF", sector="IT", chat_fn=fake)
    assert result.score == 70.0                     # (80·2 + 50·1) / 3
    assert result.as_json()["criteria"][0]["evidence"] == "refund topilgan"
    user_prompt = calls[0][1]["content"]
    assert "<answer>\njavob\n</answer>" in user_prompt and "REF" in user_prompt


async def test_evaluate_rubric_rejects_wrong_criteria():
    fake, _ = _fake_chat({"criteria": [{"id": "root_cause", "score": 80}], "short_feedback": "x"})
    assert await evaluate_rubric("Bug", "javob", RUBRIC, chat_fn=fake) is None


async def test_evaluate_rubric_default_criterion():
    fake, _ = _fake_chat({"criteria": [{"id": "overall", "score": 64}], "short_feedback": "ok"})
    result = await evaluate_rubric("Standup", "reja", [], chat_fn=fake)
    assert result.score == 64.0


def test_rubric_schema_validator():
    schema = _schema_for(["a", "b"])
    assert issubclass(schema, RubricOut)
    schema.model_validate({"criteria": [{"id": "b", "score": 1}, {"id": "a", "score": 2}], "short_feedback": "x"})
    with pytest.raises(ValueError):
        schema.model_validate({"criteria": [{"id": "a", "score": 1}, {"id": "c", "score": 2}], "short_feedback": "x"})
    with pytest.raises(ValueError):
        schema.model_validate({"criteria": [{"id": "a", "score": 101}, {"id": "b", "score": 2}], "short_feedback": "x"})


def test_grader_uses_sector_mentor():
    banking = grader_messages("b", "a", RUBRIC, None, "Banking")[0]["content"]
    it = grader_messages("b", "a", RUBRIC, None, "IT")[0]["content"]
    assert "Dilnoza" in banking and "Kamron" in it and "GRADER" in it
    names = {s: grader_messages("b", "a", RUBRIC, None, s)[0]["content"] for s in ("Marketing", "Data", "HR")}
    assert "Madina" in names["Marketing"] and "Javohir" in names["Data"] and "Nargiza" in names["HR"]
    # noma'lum yoki bo'sh soha (eski simulyatsiyalar) — IT
    assert "Kamron" in grader_messages("b", "a", RUBRIC, None, None)[0]["content"]
    assert "Kamron" in grader_messages("b", "a", RUBRIC, None, "Logistics")[0]["content"]


# ── anti-spoiler ──────────────────────────────────────────────────────

REFERENCE = "Refund qilingan buyurtmada amount None bo'ladi; None tekshiruvi qo'shish kerak."


async def _no_embed(texts, task):
    return None


async def test_spoiler_ngram():
    leak = "Gap shundaki, refund qilingan buyurtmada amount None bo'ladi, shuni tekshiring."
    hint = "Qaysi buyurtmalarda xato chiqishini solishtirib ko'ring."
    assert ngram_overlap(leak, REFERENCE) >= 0.3
    assert await is_spoiler(leak, [REFERENCE], embed_fn=_no_embed)
    assert not await is_spoiler(hint, [REFERENCE], embed_fn=_no_embed)
    assert not await is_spoiler(leak, [], embed_fn=_no_embed)
    assert ngram_overlap("ha ha", "ha ha") == 0.0              # juda qisqa namunaviy javob


async def test_spoiler_embedding_paraphrase():
    async def fake_embed(texts, task):
        assert task == "SEMANTIC_SIMILARITY"
        return [[1.0, 0.0], [0.95, 0.05]]

    assert await is_spoiler("Butunlay boshqa so'zlar bilan aytilgan yechim", [REFERENCE], embed_fn=fake_embed)


# ── persona prompt ────────────────────────────────────────────────────


def _ctx(kind="colleague") -> PersonaContext:
    return PersonaContext(
        persona=PersonaProfile(key="kamron", name="Kamron", role="Senior Engineer", kind=kind,
                               tone="xotirjam", secrets=("Bug faqat refund'da",)),
        company_name="Elon Market",
        scenario_title="Junior Backend, 1 kun",
        local_time="chorshanba 10:15",
        run_state=("ORD-142 — dedlayn 11:30",),
        passages=(Passage(title="Onboarding", text="Standup 09:00 da."),),
        open_tasks=("ORD-142: /orders 500 qaytaryapti",),
    )


def test_persona_messages():
    history = [ChatTurn("student", f"s{i}") for i in range(25)] + [ChatTurn("persona", "p")]
    messages = build_messages(_ctx(), history, "Salom")
    system = messages[0]["content"]
    assert "Kamron" in system and "Elon Market" in system and "MAXFIY" in system and "Standup 09:00" in system
    assert "MENTOR" not in system
    assert len(messages) == 1 + 20 + 1 and messages[-2]["role"] == "assistant"
    assert messages[-1] == {"role": "user", "content": "Salom"}


def test_mentor_messages():
    system = build_messages(_ctx(kind="mentor"), [], "Javobni ayting")[0]["content"]
    assert "MENTOR" in system and "ORD-142: /orders" in system
