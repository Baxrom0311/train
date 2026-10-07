"""Ssenariy jadvallari va submissions kengaytmasi (CONTRACT.md §9.7)."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.enums import RunStatus, ScenarioVersionStatus
from app.models.scenario import (
    DocumentChunk,
    Run,
    RunEvent,
    ScenarioDocument,
    ScenarioVersion,
)
from app.models.simulation import Submission
from app.scenario.importer import import_scenario, publish_version
from app.scenario.schema import ScenarioDefinition

FIXTURE = Path(__file__).parent / "fixtures" / "scenarios" / "elon-market-backend-day1.yaml"


def _defn(**changes) -> ScenarioDefinition:
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    data.update(changes)
    return ScenarioDefinition.model_validate(data)


async def _run(db, user, version, status=RunStatus.ACTIVE) -> Run:
    now = datetime.now(timezone.utc)
    run = Run(user_id=user.id, scenario_version_id=version.id, status=status,
              start_at=now, ends_at=now + timedelta(days=3))
    db.add(run)
    await db.flush()
    return run


async def test_import_is_idempotent_and_versions(db_session):
    v1, created = await import_scenario(db_session, _defn())
    assert created and v1.version == 1 and v1.status == ScenarioVersionStatus.DRAFT
    assert v1.definition["nodes"][1]["from"] == "dilnoza"

    again, created = await import_scenario(db_session, _defn())
    assert not created and again.id == v1.id

    v2, created = await import_scenario(db_session, _defn(title="Elon Market — yangilangan"))
    assert created and v2.version == 2

    docs = (await db_session.execute(
        select(ScenarioDocument).where(ScenarioDocument.scenario_version_id == v1.id)
    )).scalars().all()
    by_key = {d.key: d.visible_to_personas for d in docs}
    assert by_key == {"doc_onboarding": ["dilnoza", "kamron"], "doc_orders_api": ["dilnoza"]}
    await db_session.commit()


async def test_publish_archives_previous(db_session):
    v1, _ = await import_scenario(db_session, _defn())
    await publish_version(db_session, v1)
    v2, _ = await import_scenario(db_session, _defn(title="v2"))
    await publish_version(db_session, v2)
    await db_session.refresh(v1)
    assert (v1.status, v2.status) == (ScenarioVersionStatus.ARCHIVED, ScenarioVersionStatus.PUBLISHED)
    with pytest.raises(ValueError):
        await publish_version(db_session, v1)


async def test_one_open_run_per_version(db_session, test_user_factory):
    user = await test_user_factory("run1@example.com", "pass")
    version, _ = await import_scenario(db_session, _defn())
    await _run(db_session, user, version)
    await _run(db_session, user, version, status=RunStatus.EXPIRED)   # yopilgani to'sqinlik qilmaydi
    await db_session.commit()
    with pytest.raises(IntegrityError):
        await _run(db_session, user, version, status=RunStatus.SCHEDULED)
    await db_session.rollback()


async def test_run_event_node_unique(db_session, test_user_factory):
    user = await test_user_factory("run2@example.com", "pass")
    version, _ = await import_scenario(db_session, _defn())
    run = await _run(db_session, user, version)
    now = datetime.now(timezone.utc)
    db_session.add(RunEvent(run_id=run.id, node_id="standup", scheduled_at=now))
    await db_session.flush()
    db_session.add(RunEvent(run_id=run.id, node_id="standup", scheduled_at=now))
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_submission_target_and_attempts(db_session, test_user_factory):
    user = await test_user_factory("run3@example.com", "pass")
    version, _ = await import_scenario(db_session, _defn())
    run = await _run(db_session, user, version)
    event = RunEvent(run_id=run.id, node_id="bug_orders", scheduled_at=datetime.now(timezone.utc))
    db_session.add(event)
    await db_session.flush()

    # rollback() obyektlarni expire qiladi — id'lar oldindan olinadi
    user_id, run_id, event_id = user.id, run.id, event.id
    for attempt in (1, 2):
        db_session.add(Submission(user_id=user_id, run_id=run_id, run_event_id=event_id,
                                  attempt=attempt, content=f"urinish {attempt}"))
    await db_session.commit()

    db_session.add(Submission(user_id=user_id, run_id=run_id, run_event_id=event_id, attempt=2, content="dublikat"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    db_session.add(Submission(user_id=user_id, content="na task, na run"))   # CHECK
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_chunk_vector_and_tsv(db_session):
    version, _ = await import_scenario(db_session, _defn())
    doc = (await db_session.execute(
        select(ScenarioDocument).where(ScenarioDocument.scenario_version_id == version.id)
    )).scalars().first()
    chunk = DocumentChunk(document_id=doc.id, chunk_index=0, text="Standup har kuni 09:00 da",
                          embedding=[0.1] * 768, embedding_model="test")
    db_session.add(chunk)
    await db_session.commit()

    hit = await db_session.scalar(text(
        "SELECT count(*) FROM document_chunks WHERE tsv @@ plainto_tsquery('simple', 'standup')"
    ))
    assert hit == 1
    distance = await db_session.scalar(text(
        "SELECT embedding <=> CAST(:q AS vector) FROM document_chunks"
    ), {"q": str([0.1] * 768)})
    assert distance == pytest.approx(0.0, abs=1e-6)
