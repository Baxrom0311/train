"""
Saqlangan nomzod profillari (CONTRACT.md §33).

Asosiy kafolat: `talent_profiles` ustidagi SQL (qidiruv, moslik, CSV) eski
yo'l — har so'rovda barcha Run'lardan Python'da hisoblash — bilan aynan bir
xil natija beradi. Shuning uchun har test ma'lumotni Run'lardan qaytadan
hisoblab (`compute_profiles`) API javobi bilan solishtiradi.
"""
import asyncio
import csv
import importlib.util
import io
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml
from sqlalchemy import literal, select

from app.models.credential import Certificate
from app.models.enums import RunStatus, Sector
from app.models.rbac import Role
from app.models.scenario import Run
from app.models.talent import CandidateVisibility, TalentProfile, Vacancy
from app.models.user import User
from app.scenario.importer import import_scenario, publish_version
from app.scenario.schema import ScenarioDefinition
from app.talent import search, vacancies as matching
from app.talent.profile import Profile, compute_profiles, load_profile, load_profiles, refresh_profiles
from tests.conftest import TestingSessionLocal
from tests.test_runs_api import FIXTURE
from tests.test_talent_hunt import NOW, _company, _hr, _run, _scenario

pytestmark = pytest.mark.asyncio

COMPETENCIES = ["technical", "communication", "prioritization", "time_management", "stress_handling", "initiative"]
MIGRATION = Path(__file__).parents[1] / "alembic" / "versions" / "0030_talent_profiles.py"


@pytest.fixture(autouse=True)
def _no_expire(db_session):
    db_session.sync_session.expire_on_commit = False


async def _students(db, n):
    role = (await db.execute(select(Role).where(Role.name == "student"))).scalar_one()
    users = [
        User(email=f"s{i}@test.uz", hashed_password="x", full_name=f"Talaba {i:02d}", role_id=role.id, is_active=True)
        for i in range(n)
    ]
    db.add_all(users)
    await db.commit()
    return users


def _bare_run(user, version, *, score, days_ago, competencies=None):
    at = NOW - timedelta(days=days_ago)
    return Run(
        user_id=user.id, scenario_version_id=version.id, status=RunStatus.COMPLETED,
        start_at=at - timedelta(hours=8), ends_at=at, last_activity_at=at, competency_scores=competencies or {},
        final_report={"overall_score": score, "summary": {"strengths": []}},
    )


@pytest.fixture
async def pool(client, db_session, test_user_factory):
    """
    Tasodifiy (lekin takrorlanadigan) nomzodlar bazasi: turli ko'rinish, faol emas,
    bir ssenariyni ko'p marta o'tgan, balli yo'q, sertifikati bekor qilingan Run'lar.
    """
    rnd = random.Random(20261014)
    alpha = await _company(db_session, "Alpha")
    alpha_h = await _hr(client, db_session, test_user_factory, alpha, "hr@alpha.test")
    versions = [
        await _scenario(db_session, "it-day1", Sector.IT),
        await _scenario(db_session, "bank-day1", Sector.BANKING),
        await _scenario(db_session, "data-day1", Sector.DATA),
    ]
    students = await _students(db_session, 36)
    for i, user in enumerate(students):
        kind = i % 6
        if kind in (0, 1, 2):
            db_session.add(CandidateVisibility(user_id=user.id, is_open_to_work=True, hidden_from_company_ids=[]))
        elif kind == 3:
            db_session.add(CandidateVisibility(user_id=user.id, is_open_to_work=True,
                                               hidden_from_company_ids=[str(alpha.id)]))
        elif kind == 4:
            db_session.add(CandidateVisibility(user_id=user.id, is_open_to_work=False, hidden_from_company_ids=[]))
        if i % 11 == 7:
            user.is_active = False
    await db_session.commit()

    for user in students:
        for _ in range(rnd.randint(0, 4)):
            competencies = {k: round(rnd.uniform(5, 100), 1) for k in rnd.sample(COMPETENCIES, rnd.randint(0, 4))}
            score = None if rnd.random() < 0.12 else round(rnd.uniform(20, 100), 1)
            run = await _run(db_session, user, rnd.choice(versions), score=score, competencies=competencies,
                             days_ago=rnd.randint(0, 120) + rnd.random())
            if rnd.random() < 0.08:
                db_session.add(Certificate(
                    code=f"TJ-{rnd.randint(1000, 9999)}-{rnd.randint(1000, 9999)}", run_id=run.id, user_id=user.id,
                    issued_at=NOW, holder_name=user.full_name, scenario_title="x", company_name="x", sector="IT",
                    difficulty="junior", duration_days=1, completed_at=NOW, competency_scores={}, revoked_at=NOW,
                ))
                await db_session.commit()
                await refresh_profiles(db_session, [user.id])
                await db_session.commit()
    return {"alpha": alpha, "alpha_h": alpha_h, "students": students}


async def _reference(db, pool):
    """Eski yo'l: Run'lardan hisoblangan profillar, kompaniyaga ko'rinadiganlari (§5, §10.1)."""
    alpha = str(pool["alpha"].id)
    visibility = {v.user_id: v for v in (await db.execute(select(CandidateVisibility))).scalars()}
    users = {u.id: u for u in pool["students"]}
    profiles = await compute_profiles(db, list(users))
    return {
        uid: (users[uid], p) for uid, p in profiles.items()
        if users[uid].is_active and uid in visibility and visibility[uid].is_open_to_work
        and alpha not in (visibility[uid].hidden_from_company_ids or [])
    }


def _card(user, p):
    return {
        "id": str(user.id), "full_name": user.full_name, "overall_score": p.overall_score,
        "runs_completed": p.runs_completed, "sectors": p.sectors, "top_competencies": p.top_competencies,
        "last_completed_at": p.last_completed_at,
    }


def _normalize(card):
    """API JSON'idagi sana — solishtirish uchun datetime'ga."""
    return {**card, "last_completed_at": datetime.fromisoformat(card["last_completed_at"])}


# ── Yozish (§33.2) ───────────────────────────────────────────────────


async def test_stored_profile_matches_computed(db_session, pool):
    ids = [u.id for u in pool["students"]]
    stored = await load_profiles(db_session, ids)
    assert len(stored) > 15
    assert stored == await compute_profiles(db_session, ids)
    # Run'siz o'qish — ro'yxat bo'sh, qolgani bir xil
    light = await load_profiles(db_session, ids, runs=False)
    assert all(light[u].runs == [] and light[u].runs_completed == stored[u].runs_completed for u in stored)


async def test_refresh_removes_profile_without_eligible_runs(client, db_session, test_user_factory):
    it = await _scenario(db_session, "it-day1")
    user = (await _students(db_session, 1))[0]
    run = await _run(db_session, user, it, score=80.0, competencies={"technical": 80.0})
    assert (await load_profile(db_session, user.id)).runs_completed == 1

    db_session.add(Certificate(
        code="TJ-1111-1111", run_id=run.id, user_id=user.id, issued_at=NOW, holder_name="x", scenario_title="x",
        company_name="x", sector="IT", difficulty="junior", duration_days=1, completed_at=NOW,
        competency_scores={}, revoked_at=NOW,
    ))
    await refresh_profiles(db_session, [user.id])
    await db_session.commit()
    assert await load_profile(db_session, user.id) is None
    assert await db_session.get(TalentProfile, user.id) is None


async def test_scenario_catalog_change_rewrites_profiles(db_session):
    defn = ScenarioDefinition.model_validate(yaml.safe_load(FIXTURE.read_text(encoding="utf-8")))
    version, _ = await import_scenario(db_session, defn)
    await publish_version(db_session, version)
    await db_session.commit()
    user = (await _students(db_session, 1))[0]
    await _run(db_session, user, version, score=75.0, competencies={"technical": 70.0})
    assert (await load_profile(db_session, user.id)).runs[0].scenario_title == defn.title

    renamed = defn.model_copy(update={"title": "Yangi nom", "sector": Sector.DATA})
    draft, _ = await import_scenario(db_session, renamed, update_catalog=False)   # muharrir qoralamasi
    await db_session.commit()
    assert (await load_profile(db_session, user.id)).runs[0].scenario_title == defn.title   # nashrgacha — eski
    await publish_version(db_session, draft)
    await db_session.commit()
    p = await load_profile(db_session, user.id)
    assert p.runs[0].scenario_title == "Yangi nom" and p.sectors == ["Data"]


async def test_concurrent_completions_both_land_in_profile(db_session):
    """Ikki Run bir vaqtda yakunlanadi: qulf ikkinchisini kutdiradi, u ikkalasini ham ko'radi."""
    it = await _scenario(db_session, "it-day1")
    bank = await _scenario(db_session, "bank-day1", Sector.BANKING)
    user = (await _students(db_session, 1))[0]

    async with TestingSessionLocal() as first, TestingSessionLocal() as second:
        first.add(_bare_run(user, it, score=70.0, days_ago=2))
        await refresh_profiles(first, [user.id])   # qulf olindi, commit hali yo'q

        async def finish_second():
            second.add(_bare_run(user, bank, score=90.0, days_ago=1))
            await refresh_profiles(second, [user.id])
            await second.commit()

        task = asyncio.create_task(finish_second())
        await asyncio.sleep(0.3)
        assert not task.done()    # birinchi tranzaksiyani kutmoqda
        await first.commit()
        await task

    p = await load_profile(db_session, user.id)
    assert p.runs_completed == 2 and p.overall_score == 80.0


async def test_migration_backfill_matches_app(db_session, pool):
    """0030 to'ldirishi (§10.1 nusxasi) ilovaning hisobi bilan bir xil."""
    spec = importlib.util.spec_from_file_location("migration_0030", MIGRATION)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    rows = migration._profiles((await db_session.execute(migration.ELIGIBLE_RUNS)).all())

    stored = {
        r.user_id: r for r in (await db_session.execute(select(TalentProfile))).scalars()
    }
    assert {r["user_id"] for r in rows} == set(stored)
    for row in rows:
        s = stored[row["user_id"]]
        assert (row["overall_score"], row["runs_completed"], row["sectors"], row["competencies"],
                row["last_completed_at"]) == (s.overall_score, s.runs_completed, s.sectors, s.competencies,
                                              s.last_completed_at)
        assert row["runs"] == s.runs


# ── O'qish: SQL = eski Python yo'li (§33.3) ──────────────────────────


@pytest.mark.parametrize("params", [
    {},
    {"sort": "recent"},
    {"min_score": 60},
    {"sector": "Banking"},
    {"competency": "prioritization"},
    {"competency": "technical", "min_score": 50, "sector": "IT"},
    {"competency": "stress_handling", "sort": "recent"},
    {"min_score": 100},
])
async def test_search_equals_reference(client, db_session, pool, params):
    ref = await _reference(db_session, pool)
    competency, sector = params.get("competency"), params.get("sector")
    min_score = params.get("min_score", 0)

    def score(p):
        value = p.competencies.get(competency) if competency else p.overall_score
        return value if value is not None else -1

    expected = [
        (u, p) for u, p in ref.values()
        if (sector is None or sector in p.sectors) and (competency is None or competency in p.competencies)
        and score(p) >= min_score
    ]
    if params.get("sort") == "recent":
        expected.sort(key=lambda up: (-up[1].last_completed_at.timestamp(), up[0].id))
    else:
        expected.sort(key=lambda up: (-score(up[1]), -up[1].last_completed_at.timestamp(), up[0].id))

    r = await client.get("/api/v1/talents", params={**params, "limit": 100}, headers=pool["alpha_h"])
    assert r.status_code == 200
    assert r.json()["total"] == len(expected)
    assert [_normalize(c) for c in r.json()["items"]] == [_card(u, p) for u, p in expected]

    # sahifalar: takrorsiz va tushib qolmasdan
    pages = []
    for offset in range(0, len(expected) + 5, 5):
        page = await client.get("/api/v1/talents", params={**params, "limit": 5, "offset": offset},
                                headers=pool["alpha_h"])
        assert page.json()["total"] == len(expected)
        pages += [c["id"] for c in page.json()["items"]]
    assert pages == [str(u.id) for u, _ in expected]


@pytest.mark.parametrize("vacancy", [
    {"requirements": {"technical": 70, "communication": 60}},
    {"requirements": {"prioritization": 40}, "min_score": 65, "sector": "Banking"},
    {"requirements": {"initiative": 0, "stress_handling": 90, "technical": 33}, "sector": "Data"},
    {"requirements": {}},
    {"requirements": {}, "min_score": 80},
])
async def test_matches_equal_reference(client, db_session, pool, vacancy):
    body = {
        "title": "Junior tahlilchi", "description": "Ma'lumotlar bilan ishlash va hisobotlar tayyorlash.",
        "sector": "IT", "employment": "full_time", "work_format": "hybrid", "status": "open", **vacancy,
    }
    r = await client.post("/api/v1/company/vacancies", json=body, headers=pool["alpha_h"])
    assert r.status_code == 201, r.text
    created = r.json()
    model = Vacancy(requirements=vacancy["requirements"], min_score=vacancy.get("min_score"),
                             sector=Sector(body["sector"]))

    ref = await _reference(db_session, pool)
    fits = [(u, p, matching.fit(p, model)) for u, p in ref.values()]
    assert created["counts"]["matches"] == sum(1 for *_, f in fits if f.meets)

    expected = [x for x in fits if x[2].fit >= matching.MATCH_MIN_FIT]
    expected.sort(key=lambda x: (
        not x[2].meets, -x[2].fit, not x[2].sector_match,
        -(x[1].overall_score if x[1].overall_score is not None else -1), x[0].id,
    ))
    expected = expected[:matching.MAX_MATCHES]

    got = (await client.get(f"/api/v1/company/vacancies/{created['id']}/matches", headers=pool["alpha_h"])).json()
    assert [m["id"] for m in got] == [str(u.id) for u, _, _ in expected]
    assert [m["fit"]["fit"] for m in got] == [f.fit for *_, f in expected]
    assert [m["fit"]["meets"] for m in got] == [f.meets for *_, f in expected]


async def test_candidates_csv_equals_reference(client, db_session, pool):
    ref = await _reference(db_session, pool)
    expected = sorted(ref.values(), key=lambda up: (
        -(up[1].overall_score if up[1].overall_score is not None else -1),
        -up[1].last_completed_at.timestamp(), up[0].id,
    ))
    r = await client.get("/api/v1/talents/report/candidates.csv", headers=pool["alpha_h"])
    rows = list(csv.reader(io.StringIO(r.text.lstrip("﻿"))))[1:]
    assert [(row[0], row[2]) for row in rows] == [(u.full_name, str(p.runs_completed)) for u, p in expected]

    report = (await client.get("/api/v1/talents/report", headers=pool["alpha_h"])).json()
    assert report["pool"]["candidates"] == len(expected)


async def test_fit_sql_equals_python(db_session):
    """`search.fit_expr`/`meets_expr` = `vacancies.fit` — chegaradagi yaxlitlashda ham (0.25 → 0.3, half-up)."""
    rnd = random.Random(7)
    users = await _students(db_session, 40)
    values = [0.0, 0.1, 19.9, 20.0, 33.3, 39.9, 40.0, 49.9, 50.0, 66.7, 99.9, 100.0]
    for user in users:
        db_session.add(TalentProfile(
            user_id=user.id, overall_score=rnd.choice([None, 49.9, 65.0, 80.0]), runs_completed=1, sectors=["IT"],
            competencies={k: rnd.choice(values) for k in rnd.sample(COMPETENCIES, rnd.randint(0, 5))},
            last_completed_at=NOW, runs=[],
        ))
    await db_session.commit()

    for requirements, min_score in [
        ({"technical": 40}, None), ({"technical": 40, "prioritization": 30, "stress_handling": 70}, 65),
        ({"communication": 0, "initiative": 33}, None), ({}, None), ({}, 65),
    ]:
        vacancy = Vacancy(requirements=requirements, min_score=min_score, sector=Sector.IT)
        rows = (await db_session.execute(
            select(TalentProfile, search.fit_expr(vacancy), search.meets_expr(vacancy) if requirements or min_score
                   else literal(True))
        )).all()
        for row, fit, meets in rows:
            expected = matching.fit(Profile.from_row(row, runs=False), vacancy)
            assert (float(fit), meets) == (expected.fit, expected.meets), (requirements, row.competencies)

    half = matching.fit(Profile(uuid.uuid4(), competencies={"technical": 0.1}), Vacancy(
        requirements={"technical": 40}, min_score=None, sector=Sector.IT))
    assert half.fit == 0.3
