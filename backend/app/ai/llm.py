"""
Umumiy LLM chaqiruvi (CONTRACT.md §9.10, Modul 2).

    result = await chat(messages, schema=RubricOut)

- `messages` — OpenAI uslubida `[{"role": "system"|"user"|"assistant", "content": str}]`.
- Provayderlar `settings.LLM_PROVIDERS` tartibida sinab ko'riladi; kaliti
  yo'q provayder o'tkazib yuboriladi.
- `schema` berilsa: JSON-rejim yoqiladi, javob Pydantic bilan tekshiriladi;
  yaroqsiz JSON — keyingi provayder.
- Token hisobi provayder javobidan olinadi (`LLMResult.tokens`).
- Hammasi muvaffaqiyatsiz → `None` (chaqiruvchi `queued_retry`/zaxira javobga o'tadi).

Model nomlari va kalitlar faqat `.env`dan (`app/config.py`).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings

log = logging.getLogger(__name__)

Message = dict[str, str]


@dataclass(frozen=True)
class RawReply:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0


@dataclass(frozen=True)
class LLMResult:
    text: str
    data: BaseModel | None
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0

    @property
    def tokens(self) -> int:
        return self.tokens_in + self.tokens_out


ProviderCall = Callable[
    [httpx.AsyncClient, list[Message], bool, float, int], Awaitable[RawReply]
]


# ── Provayderlar ──────────────────────────────────────────────────────


async def _openai_compatible(
    client: httpx.AsyncClient, url: str, key: str, model: str,
    messages: list[Message], json_mode: bool, temperature: float, max_tokens: int,
) -> RawReply:
    body = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    resp = await client.post(
        url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=settings.LLM_TIMEOUT_SECONDS
    )
    resp.raise_for_status()
    payload = resp.json()
    usage = payload.get("usage") or {}
    return RawReply(
        text=payload["choices"][0]["message"]["content"] or "",
        tokens_in=int(usage.get("prompt_tokens", 0)),
        tokens_out=int(usage.get("completion_tokens", 0)),
    )


async def _deepseek(client, messages, json_mode, temperature, max_tokens) -> RawReply:
    return await _openai_compatible(
        client, "https://api.deepseek.com/v1/chat/completions", settings.DEEPSEEK_API_KEY,
        settings.DEEPSEEK_MODEL, messages, json_mode, temperature, max_tokens,
    )


async def _openai(client, messages, json_mode, temperature, max_tokens) -> RawReply:
    return await _openai_compatible(
        client, "https://api.openai.com/v1/chat/completions", settings.OPENAI_API_KEY,
        settings.OPENAI_MODEL, messages, json_mode, temperature, max_tokens,
    )


async def _gemini(client, messages, json_mode, temperature, max_tokens) -> RawReply:
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    contents = [
        {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
        for m in messages if m["role"] != "system"
    ]
    config: dict = {"temperature": temperature, "maxOutputTokens": max_tokens}
    if json_mode:
        config["responseMimeType"] = "application/json"
    body: dict = {"contents": contents, "generationConfig": config}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    resp = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": settings.GEMINI_API_KEY},
        json=body,
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    payload = resp.json()
    parts = payload["candidates"][0]["content"].get("parts", [])
    usage = payload.get("usageMetadata") or {}
    return RawReply(
        text="".join(p.get("text", "") for p in parts),
        tokens_in=int(usage.get("promptTokenCount", 0)),
        tokens_out=int(usage.get("candidatesTokenCount", 0)),
    )


# nom → (chaqiruv, kalit, model)
PROVIDERS: dict[str, tuple[ProviderCall, Callable[[], str], Callable[[], str]]] = {
    "deepseek": (_deepseek, lambda: settings.DEEPSEEK_API_KEY, lambda: settings.DEEPSEEK_MODEL),
    "gemini": (_gemini, lambda: settings.GEMINI_API_KEY, lambda: settings.GEMINI_MODEL),
    "openai": (_openai, lambda: settings.OPENAI_API_KEY, lambda: settings.OPENAI_MODEL),
}


# ── JSON ──────────────────────────────────────────────────────────────

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json(text: str, schema: type[BaseModel]) -> BaseModel:
    """Model ba'zan JSON'ni ``` ichida qaytaradi — o'rab turgan fence olib tashlanadi."""
    cleaned = _FENCE.sub("", text.strip())
    return schema.model_validate(json.loads(cleaned))


# ── Asosiy chaqiruv ───────────────────────────────────────────────────


async def chat(
    messages: list[Message],
    schema: type[BaseModel] | None = None,
    *,
    temperature: float = 0.3,
    max_tokens: int = 800,
    client: httpx.AsyncClient | None = None,
) -> LLMResult | None:
    own_client = client is None
    client = client or httpx.AsyncClient()
    try:
        for name in settings.llm_providers_list:
            entry = PROVIDERS.get(name)
            if entry is None:
                log.warning("noma'lum LLM provayderi: %s", name)
                continue
            call, key, model = entry
            if not key():
                continue
            try:
                raw = await call(client, messages, schema is not None, temperature, max_tokens)
                data = parse_json(raw.text, schema) if schema is not None else None
            except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
                # ValidationError va json.JSONDecodeError — ValueError avlodi
                log.warning("LLM %s muvaffaqiyatsiz: %s", name, exc)
                continue
            if schema is None and not raw.text.strip():
                log.warning("LLM %s bo'sh javob qaytardi", name)
                continue
            return LLMResult(
                text=raw.text, data=data, provider=name, model=model(),
                tokens_in=raw.tokens_in, tokens_out=raw.tokens_out,
            )
        return None
    finally:
        if own_client:
            await client.aclose()
