"""Run chati, hint, fayllar va SSE (CONTRACT.md §9.4, §9.5, §9.8)."""
import asyncio
import uuid

import pytest

from app.ai.llm import LLMResult
from app.config import settings
from app.core.redis_client import redis_client
from app.models.scenario import Run
from app.scenario import notify, persona
from app.scenario.engine import Note
# test_runs_api fixture'lari (clock, queue, scenario) shu modulda ham ishlatiladi
from tests.test_runs_api import _login, clock, queue, scenario  # noqa: F401,F811

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def ai(monkeypatch):
    """Soxta LLM: chaqiruvlarni yozib boradi, javobni test belgilaydi."""
    state = {"reply": "Salom! Standup 09:00 da.", "calls": [], "spoiler": False}

    async def fake_reply(ctx, history, message):
        state["calls"].append((ctx, history, message))
        if state["reply"] is None:
            return None
        return LLMResult(text=state["reply"], data=None, provider="fake", model="m", tokens_in=7, tokens_out=3)

    async def fake_spoiler(text, references):
        state["references"] = references
        return state["spoiler"]

    monkeypatch.setattr(persona, "persona_reply", fake_reply)
    monkeypatch.setattr(persona, "is_spoiler", fake_spoiler)
    return state


async def _start(client, factory, scenario_id, email="chat@example.com"):
    h = await _login(client, factory, email)
    r = await client.post("/api/v1/runs", json={"scenario_id": str(scenario_id)}, headers=h)
    return h, r.json()["run"]["id"]


async def test_scripted_messages_in_chat(client, test_user_factory, scenario, clock, queue):
    h, run_id = await _start(client, test_user_factory, scenario)
    r = await client.get(f"/api/v1/runs/{run_id}/chat/dilnoza", headers=h)
    assert r.status_code == 200
    assert [m["body"][:12] for m in r.json()] == ["Xush kelibsi", "Standup: bug"]
    assert all(not m["generated"] and m["sender"] == "persona" for m in r.json())
    assert (await client.get(f"/api/v1/runs/{run_id}/chat/nobody", headers=h)).status_code == 404


async def test_chat_reply_uses_context_and_counts_tokens(client, db_session, test_user_factory, scenario, clock, queue, ai):
    h, run_id = await _start(client, test_user_factory, scenario)
    clock.set("09:05")
    r = await client.post(f"/api/v1/runs/{run_id}/chat/dilnoza", json={"text": "Standup qachon?"}, headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["message"]["sender"] == "student" and body["reply"]["generated"]
    assert body["reply"]["body"] == "Salom! Standup 09:00 da."

    ctx, history, message = ai["calls"][0]
    assert message == "Standup qachon?"
    assert [t.sender for t in history] == ["persona", "persona"]          # skript xabarlar
    assert ctx.persona.name == "Dilnoza" and ctx.company_name == "Elon Market"
    assert ctx.local_time == "chorshanba 09:05"
    assert any("Standup" in line for line in ctx.run_state)
    assert [p.title for p in ctx.passages] == ["Onboarding", "Orders API"]   # kichik korpus — butun
    assert any("None" in ref for ref in ai["references"])

    run = await db_session.get(Run, uuid.UUID(run_id))
    await db_session.refresh(run)
    assert run.ai_tokens_used == 10

    r = await client.get(f"/api/v1/runs/{run_id}/chat/dilnoza", headers=h)
    assert [m["sender"] for m in r.json()][-2:] == ["student", "persona"]


async def test_chat_spoiler_and_ai_down(client, test_user_factory, scenario, clock, queue, ai):
    h, run_id = await _start(client, test_user_factory, scenario)
    ai["spoiler"] = True
    r = await client.post(f"/api/v1/runs/{run_id}/chat/kamron", json={"text": "Javobni ayting"}, headers=h)
    reply = r.json()["reply"]
    assert not reply["generated"] and reply["body"].startswith("Buni o'zingiz")
    assert ai["calls"][0][0].persona.kind == "mentor"

    ai["reply"] = None
    r = await client.post(f"/api/v1/runs/{run_id}/chat/kamron", json={"text": "Salom"}, headers=h)
    assert r.json()["reply"]["body"] == "Hozir band edim, keyinroq yozing."


async def test_chat_daily_limit(client, test_user_factory, scenario, clock, queue, ai, monkeypatch):
    monkeypatch.setattr(persona, "DAILY_AI_MESSAGES", 1)
    h, run_id = await _start(client, test_user_factory, scenario)
    await client.post(f"/api/v1/runs/{run_id}/chat/dilnoza", json={"text": "1"}, headers=h)
    r = await client.post(f"/api/v1/runs/{run_id}/chat/dilnoza", json={"text": "2"}, headers=h)
    assert r.json()["reply"]["body"] == "Hozir band edim, keyinroq yozing."
    assert len(ai["calls"]) == 1


async def test_chat_validation(client, test_user_factory, scenario, clock, queue, ai):
    h, run_id = await _start(client, test_user_factory, scenario)
    other = await _login(client, test_user_factory, "chat-other@example.com")
    url = f"/api/v1/runs/{run_id}/chat/dilnoza"
    assert (await client.post(url, json={"link_url": "https://x.example"}, headers=h)).status_code == 422
    assert (await client.post(url, json={"text": "x", "link_url": "ftp://x"}, headers=h)).status_code == 422
    assert (await client.post(url, json={}, headers=h)).status_code == 422
    assert (await client.post(url, json={"text": "x", "file_id": str(uuid.uuid4())}, headers=h)).status_code == 422
    assert (await client.post(url, json={"text": "x"}, headers=other)).status_code == 404
    r = await client.post(url, json={"text": "Izoh", "link_url": "https://x.example/pr/1"}, headers=h)
    assert r.json()["message"]["content_type"] == "link"
    assert ai["calls"][-1][2].endswith("[havola: https://x.example/pr/1]")


async def test_hint(client, test_user_factory, scenario, clock, queue):
    h, run_id = await _start(client, test_user_factory, scenario)
    clock.set("09:30")
    url = f"/api/v1/runs/{run_id}/events/bug_orders/hint"
    r = await client.post(url, headers=h)
    assert r.status_code == 200
    assert r.json() == {
        "hint": "Qaysi buyurtmalarda xato chiqishini solishtiring.",
        "hints_used": 1, "hints_left": 0, "penalty": 0.1,
    }
    assert (await client.post(url, headers=h)).status_code == 409
    assert (await client.post(f"/api/v1/runs/{run_id}/events/standup/hint", headers=h)).status_code == 404
    mentor = (await client.get(f"/api/v1/runs/{run_id}/chat/kamron", headers=h)).json()
    assert mentor[-1]["body"] == "Qaysi buyurtmalarda xato chiqishini solishtiring."


async def test_files_upload_and_access(client, test_user_factory, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    owner = await _login(client, test_user_factory, "file-owner@example.com")
    other = await _login(client, test_user_factory, "file-other@example.com")

    r = await client.post("/api/v1/files", files={"file": ("../../etc/screen shot.png", PNG, "image/png")}, headers=owner)
    assert r.status_code == 201, r.text
    meta = r.json()
    assert meta["mime"] == "image/png" and meta["size_bytes"] == len(PNG)
    assert list(tmp_path.iterdir())[0].name.endswith("screen_shot.png")

    r = await client.get(f"/api/v1/files/{meta['id']}", headers=owner)
    assert r.status_code == 200 and r.content == PNG
    assert (await client.get(f"/api/v1/files/{meta['id']}", headers=other)).status_code == 404

    r = await client.post("/api/v1/files", files={"file": ("x.png", b"not a png", "image/png")}, headers=owner)
    assert r.status_code == 422
    r = await client.post("/api/v1/files", files={"file": ("x.exe", PNG, "application/octet-stream")}, headers=owner)
    assert r.status_code == 422
    r = await client.post("/api/v1/files", data={"run_id": str(uuid.uuid4())},
                          files={"file": ("x.png", PNG, "image/png")}, headers=owner)
    assert r.status_code == 404


async def test_file_in_submission_and_chat(client, db_session, test_user_factory, scenario, clock, queue, ai, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    h, run_id = await _start(client, test_user_factory, scenario)
    file_id = (await client.post(
        "/api/v1/files", data={"run_id": run_id}, files={"file": ("diagram.png", PNG, "image/png")}, headers=h,
    )).json()["id"]
    r = await client.post(f"/api/v1/runs/{run_id}/chat/dilnoza", json={"file_id": file_id}, headers=h)
    assert r.status_code == 200 and r.json()["message"]["content_type"] == "file"
    assert ai["calls"][-1][2] == "[fayl: diagram.png]"


async def test_sse_generator_relays_notes():
    run_id = uuid.uuid4()
    events = notify.sse_events(redis_client, run_id, heartbeat=0.2)
    assert await events.__anext__() == "retry: 5000\n\n"
    first = asyncio.ensure_future(events.__anext__())
    await asyncio.sleep(0.05)
    await notify.publish([Note(run_id, "event_delivered", {"node_id": "standup"})])
    chunk = await asyncio.wait_for(first, 2)
    if chunk.startswith(":"):                     # heartbeat oldin kelgan bo'lsa
        chunk = await asyncio.wait_for(events.__anext__(), 2)
    assert chunk == 'event: event_delivered\ndata: {"type": "event_delivered", "node_id": "standup"}\n\n'
    assert await asyncio.wait_for(events.__anext__(), 2) == ": ping\n\n"
    await events.aclose()


async def test_stream_requires_owner(client, test_user_factory, scenario, clock, queue):
    _, run_id = await _start(client, test_user_factory, scenario)
    other = await _login(client, test_user_factory, "sse-other@example.com")
    assert (await client.get(f"/api/v1/runs/{run_id}/stream", headers=other)).status_code == 404
    assert (await client.get(f"/api/v1/runs/{run_id}/stream")).status_code == 401
