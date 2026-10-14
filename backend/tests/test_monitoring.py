"""
Xatolarni kuzatish va loglar (CONTRACT.md §32).

So'rov: `X-Request-ID`, access log (query string'siz), kutilmagan xato — 500
`{detail, request_id}` va bitta guruh. Guruhlash: bir xil xato id/argumentdan
qat'i nazar bitta qator, hal qilingani qaytsa qayta ochiladi, yangi guruhlar
soatlik chegarasi. Brauzer xatolari, admin API, email ogohlantirish, tozalash.
"""
import json
import logging
import sys
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core import monitoring
from app.core.logging import JsonFormatter, _Handler, request_id_var, setup_logging
from app.core.monitoring import Event, event_from_record, monitor, record_events
from app.main import app
from app.models.monitoring import ErrorGroup
from tests.test_talent_hunt import _headers

NOW = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)

# Test uchun ataylab yiqiladigan endpointlar — faqat shu modul davomida ulanadi
boom = APIRouter(prefix="/api/v1/_test")


@boom.get("/boom/{item_id}")
async def _boom(item_id: int):
    raise KeyError(f"item-{item_id}")


@boom.get("/stream")
async def _stream():
    async def body():
        yield b"bir"
        raise RuntimeError("oqim uzildi")
    return StreamingResponse(body(), media_type="text/plain")


@pytest.fixture(scope="module", autouse=True)
def _test_routes():
    before = list(app.router.routes)
    app.include_router(boom)
    yield
    app.router.routes[:] = before


@pytest.fixture
async def captured():
    """Handler yoqilgan: ERROR loglar navbatga, `flush()` DB'ga yozadi."""
    monitor.start("api")
    yield monitor
    await monitor.stop()


@pytest.fixture
async def admin(client, test_user_factory):
    await test_user_factory("admin@tryjob.test", "pass", "admin")
    return await _headers(client, "admin@tryjob.test")


async def _groups(db):
    db.expire_all()
    return list((await db.execute(select(ErrorGroup).order_by(ErrorGroup.first_seen, ErrorGroup.fingerprint))).scalars())


def _event(fp="f1", source="api", at=NOW, **kw):
    return Event(source=source, level="error", title=kw.pop("title", "KeyError: x"), location="GET /x",
                 detail="tb", fingerprint=fp, at=at, **kw)


def _record(name="app.test", msg="xato %s", args=("a",), exc=None, level=logging.ERROR):
    exc_info = (type(exc), exc, exc.__traceback__) if exc else None
    return logging.LogRecord(name, level, __file__, 1, msg, args, exc_info, func="fn")


def _raise(exc):
    try:
        raise exc
    except Exception as e:  # noqa: BLE001
        return e


# ── So'rov identifikatori va access log ─────────────────────────────


async def test_request_id_header_generated_or_kept(client):
    r = await client.get("/api/v1/scenarios")
    generated = r.headers["x-request-id"]
    assert len(generated) == 32 and int(generated, 16) >= 0

    r = await client.get("/api/v1/scenarios", headers={"X-Request-ID": "lb-123.abc_x"})
    assert r.headers["x-request-id"] == "lb-123.abc_x"

    # yaroqsiz (bo'shliq, juda uzun) — yangisi beriladi, log'ga begona matn tushmaydi
    for bad in ("a b", "x" * 65, "<script>"):
        r = await client.get("/api/v1/scenarios", headers={"X-Request-ID": bad})
        assert r.headers["x-request-id"] != bad


async def test_access_log_without_query_string(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        r = await client.get("/api/v1/scenarios?token=maxfiy")
    rec = next(r_ for r_ in caplog.records if r_.name == "app.access")
    assert rec.path == "/api/v1/scenarios" and rec.status == r.status_code and rec.method == "GET"
    assert "maxfiy" not in rec.getMessage()
    assert rec.duration_ms >= 0


async def test_health_access_is_debug(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        await client.get("/api/v1/health")
    assert not [r for r in caplog.records if r.name == "app.access"]


# ── Kutilmagan xato ──────────────────────────────────────────────────


async def test_unhandled_error_returns_500_with_request_id_and_one_group(client, captured, db_session):
    r1 = await client.get("/api/v1/_test/boom/1", headers={"X-Request-ID": "req-1", "Origin": "http://localhost:5173"})
    r2 = await client.get("/api/v1/_test/boom/2", headers={"X-Request-ID": "req-2"})
    assert r1.status_code == r2.status_code == 500
    assert r1.json() == {"detail": "Internal Server Error", "request_id": "req-1"}
    assert "item-1" not in r1.text                                  # ichki tafsilot qaytmaydi
    assert r1.headers["x-request-id"] == "req-1"
    assert r1.headers["access-control-allow-origin"] == "http://localhost:5173"   # CORS ichida

    await captured.flush()
    (group,) = await _groups(db_session)
    # id farq qiladi, xato bitta — bitta guruh, route shabloni bo'yicha joy
    assert (group.source, group.count, group.status) == ("api", 2, "open")
    assert group.location == "GET /api/v1/_test/boom/{item_id}"
    assert group.title == "KeyError: 'item-2'" and group.last_request_id == "req-2"
    assert "Traceback" in group.detail and "_boom" in group.detail


async def test_error_after_response_started_is_raised_and_captured_once(client, captured, db_session, caplog):
    with pytest.raises(RuntimeError):
        await client.get("/api/v1/_test/stream")
    # server (uvicorn) shu exception'ni yana log qilsa ham ikkinchi marta yig'ilmaydi
    exc = next(r.exc_info[1] for r in caplog.records if r.name == "app.request")
    logging.getLogger("uvicorn.error").error("Exception in ASGI application", exc_info=(type(exc), exc, exc.__traceback__))
    await captured.flush()
    (group,) = await _groups(db_session)
    assert group.title == "RuntimeError: oqim uzildi" and group.count == 1


# ── Log yozuvidan hodisa ─────────────────────────────────────────────


def test_log_message_template_groups_regardless_of_args():
    a = event_from_record(_record(args=("user-1@x.uz",)), "worker")
    b = event_from_record(_record(args=("user-2@x.uz",)), "worker")
    other = event_from_record(_record(msg="boshqa %s"), "worker")
    assert a.fingerprint == b.fingerprint != other.fingerprint
    assert a.title == "xato user-1@x.uz" and a.location == "app.test:fn" and a.level == "error"
    # manba ham fingerprint'da — API va worker'dagi bir xil log alohida
    assert event_from_record(_record(args=("user-1@x.uz",)), "api").fingerprint != a.fingerprint


def test_exception_fingerprint_uses_type_and_app_frame_not_message():
    def fail(*parts):
        try:
            monitoring.fingerprint(*parts)          # app/core/monitoring.py ichida TypeError
        except TypeError as e:
            return e

    e1, e2 = fail(None), fail("a", None)
    assert str(e1) != str(e2)
    ev1 = event_from_record(_record(exc=e1), "api")
    ev2 = event_from_record(_record(exc=e2), "api")
    assert ev1.fingerprint == ev2.fingerprint
    assert ev1.title.startswith("TypeError: sequence item 0")
    # boshqa turdagi xato — boshqa guruh
    assert event_from_record(_record(exc=_raise(ValueError("x"))), "api").fingerprint != ev1.fingerprint


def test_app_frame_is_relative_to_package():
    exc = _raise(KeyError("x"))
    assert monitoring._app_frame(exc.__traceback__) == "test_monitoring.py:_raise"   # app/ tashqarisi — fayl nomi

    from app.core.monitoring import fingerprint as fp
    try:
        fp(None)                                    # app/core/monitoring.py ichida yiqiladi
    except TypeError as e:
        assert monitoring._app_frame(e.__traceback__) == "app/core/monitoring.py:fingerprint"


def test_arq_job_failure_location_is_job_name():
    exc = _raise(ZeroDivisionError("division by zero"))
    rec = _record(name="arq.worker", msg="%6.2fs ! %s failed, %s: %s",
                  args=(0.5, "cron:deliver_due_events:1760000000:deliver_due_events", "ZeroDivisionError", exc), exc=exc)
    ev = event_from_record(rec, "worker")
    assert ev.location == "deliver_due_events" and ev.title == "ZeroDivisionError: division by zero"


def test_exception_captured_once_and_own_logger_skipped():
    exc = _raise(KeyError("x"))
    assert event_from_record(_record(exc=exc), "api") is not None
    assert event_from_record(_record(name="uvicorn.error", exc=exc), "api") is None

    queue = []
    handler = monitoring.MonitorHandler("api", queue)
    logger = logging.getLogger("app.test.monitor")
    logger.addHandler(handler)
    try:
        logging.getLogger("app.core.monitoring").addHandler(handler)
        logging.getLogger("app.core.monitoring").error("yozilmadi")   # kuzatuvning o'z xatosi — aylanish yo'q
        logger.warning("ERROR'dan past")
        logger.error("haqiqiy xato")
    finally:
        logger.removeHandler(handler)
        logging.getLogger("app.core.monitoring").removeHandler(handler)
    assert [ev.title for ev in queue] == ["haqiqiy xato"]


def test_request_id_attached_and_long_detail_clipped():
    token = request_id_var.set("rid-7")
    try:
        ev = event_from_record(_record(msg="%s", args=("x" * 20_000,)), "api")
    finally:
        request_id_var.reset(token)
    assert ev.request_id == "rid-7"
    assert len(ev.title) == monitoring.TITLE_MAX and len(ev.detail) <= monitoring.DETAIL_MAX


# ── Guruhlarni yozish ────────────────────────────────────────────────


async def test_record_events_aggregates_and_reopens_resolved(db_session):
    await record_events([_event(), _event(at=NOW + timedelta(seconds=1), request_id="r2"), _event(fp="f2")])
    g1, g2 = await _groups(db_session)
    assert (g1.fingerprint, g1.count, g1.last_seen, g1.last_request_id) == ("f1", 2, NOW + timedelta(seconds=1), "r2")
    assert g2.count == 1

    g1.status, g1.resolved_at, g1.notified_at = "resolved", NOW, NOW
    g2.notified_at = NOW
    await db_session.commit()

    await record_events([_event(at=NOW + timedelta(hours=1), title="KeyError: y"), _event(fp="f2")])
    g1, g2 = await _groups(db_session)
    # regressiya: qayta ochildi va yana xabar qilinadi; request id yo'q hodisa eskisini o'chirmaydi
    assert (g1.status, g1.resolved_at, g1.notified_at, g1.count, g1.title) == ("open", None, None, 3, "KeyError: y")
    assert g1.last_request_id == "r2"
    # ochiq guruh — allaqachon xabar qilingan, qayta xabar yo'q
    assert (g2.count, g2.notified_at) == (2, NOW)


async def test_new_groups_per_hour_cap(db_session, monkeypatch):
    monkeypatch.setattr(monitoring, "NEW_GROUPS_PER_HOUR", 2)
    await record_events([_event(fp=f"f{i}", at=NOW + timedelta(seconds=i)) for i in range(3)])
    assert [g.fingerprint for g in await _groups(db_session)] == ["f0", "f1"]
    # chegara faqat yangilarga: mavjud guruh hisoblanadi, boshqa manba alohida
    await record_events([_event(fp="f0"), _event(fp="w1", source="worker")])
    groups = {g.fingerprint: g.count for g in await _groups(db_session)}
    assert groups == {"f0": 2, "f1": 1, "w1": 1}


async def test_record_events_never_raises(monkeypatch, caplog):
    def broken():
        raise RuntimeError("db yo'q")

    monkeypatch.setattr("app.database.AsyncSessionLocal", broken)
    with caplog.at_level(logging.WARNING, logger="app.core.monitoring"):
        await record_events([_event()])
    assert "xatolar yozilmadi" in caplog.text


async def test_monitor_flushes_on_stop(db_session):
    monitor.start("worker")
    logging.getLogger("app.scenario.jobs").error("navbatga qo'yilmadi: %s", "redis")
    await monitor.stop()
    (group,) = await _groups(db_session)
    assert (group.source, group.location) == ("worker", "app.scenario.jobs:test_monitor_flushes_on_stop")
    # to'xtagandan keyin yig'ilmaydi
    logging.getLogger("app.scenario.jobs").error("yana")
    assert not monitor.queue


# ── Brauzer xatolari ─────────────────────────────────────────────────


CHROME_STACK = (
    "TypeError: Cannot read properties of undefined (reading 'title')\n"
    "    at RunHeader (https://tryjob.uz/assets/index-{h}.js:41:{c})\n"
    "    at renderWithHooks (https://tryjob.uz/assets/vendor-{h}.js:1:2)"
)


async def test_client_error_recorded_and_grouped_across_deploys(client, db_session):
    for h, c, n in (("a1b2", 120, 5), ("ffee", 777, 6)):
        r = await client.post("/api/v1/client-errors", json={
            "kind": "error", "message": f"Cannot read properties of undefined (reading 'title') #{n}",
            "stack": CHROME_STACK.format(h=h, c=c), "path": "/runs/42?tab=chat#token=maxfiy",
        })
        assert r.status_code == 204 and r.content == b""
    (group,) = await _groups(db_session)
    assert (group.source, group.count, group.location) == ("frontend", 2, "/runs/42")
    assert "maxfiy" not in group.detail and "maxfiy" not in group.location
    assert "RunHeader" in group.detail and group.title.endswith("#6")


def test_first_function_chrome_and_gecko():
    from app.api.monitoring import _first_function

    assert _first_function(CHROME_STACK.format(h="x", c=1)) == "RunHeader"
    assert _first_function("    at async loadRun (https://x/a.js:1:2)") == "loadRun"
    assert _first_function("RunHeader@https://tryjob.uz/assets/index-x.js:41:12\n") == "RunHeader"
    assert _first_function("") == ""


async def test_client_error_validation_and_rate_limit(client, monkeypatch):
    assert (await client.post("/api/v1/client-errors", json={"kind": "console", "message": "x"})).status_code == 422
    assert (await client.post("/api/v1/client-errors", json={"kind": "error", "message": ""})).status_code == 422
    assert (await client.post("/api/v1/client-errors",
                              json={"kind": "error", "message": "x", "stack": "s" * 8001})).status_code == 422

    monkeypatch.setattr("app.api.monitoring.CLIENT_LIMIT", (2, 600))
    codes = [(await client.post("/api/v1/client-errors", json={"kind": "render", "message": f"m{i}"})).status_code
             for i in range(3)]
    assert codes == [204, 204, 429]


# ── Admin API ────────────────────────────────────────────────────────


async def test_admin_errors_requires_permission(client, test_user_factory):
    await test_user_factory("s@tryjob.test", "pass", "student")
    student = await _headers(client, "s@tryjob.test")
    assert (await client.get("/api/v1/admin/errors", headers=student)).status_code == 403
    assert (await client.get("/api/v1/admin/errors")).status_code == 401


async def test_admin_list_detail_resolve(client, admin, db_session):
    await record_events([
        _event(fp="a", at=NOW), _event(fp="b", at=NOW + timedelta(minutes=1), request_id="rid-b"),
        _event(fp="w", source="worker", at=NOW + timedelta(minutes=2)),
    ])
    body = (await client.get("/api/v1/admin/errors", headers=admin)).json()
    assert body["open_total"] == 3
    assert [i["source"] for i in body["items"]] == ["worker", "api", "api"]          # oxirgisi birinchi
    assert set(body["items"][0]) == {"id", "source", "level", "title", "location", "count",
                                     "first_seen", "last_seen", "status"}
    api_only = (await client.get("/api/v1/admin/errors?source=api", headers=admin)).json()["items"]
    assert len(api_only) == 2
    assert (await client.get("/api/v1/admin/errors?source=db", headers=admin)).status_code == 422

    gid = api_only[0]["id"]
    detail = (await client.get(f"/api/v1/admin/errors/{gid}", headers=admin)).json()
    assert (detail["detail"], detail["last_request_id"], detail["resolved_by_name"]) == ("tb", "rid-b", None)

    resolved = (await client.post(f"/api/v1/admin/errors/{gid}/resolve", headers=admin)).json()
    assert resolved["status"] == "resolved" and resolved["resolved_by_name"] == "Test User"
    assert resolved["resolved_at"] is not None
    assert (await client.get("/api/v1/admin/errors", headers=admin)).json()["open_total"] == 2
    done = (await client.get("/api/v1/admin/errors?status=resolved", headers=admin)).json()["items"]
    assert [i["id"] for i in done] == [gid]

    missing = "00000000-0000-0000-0000-000000000000"
    assert (await client.get(f"/api/v1/admin/errors/{missing}", headers=admin)).status_code == 404


# ── Ogohlantirish va tozalash ────────────────────────────────────────


async def test_alert_email_once_to_verified_admins(db_session, test_user_factory, monkeypatch):
    await test_user_factory("a1@tryjob.test", "pass", "admin")
    await test_user_factory("a2@tryjob.test", "pass", "admin", email_verified=False)
    await test_user_factory("s@tryjob.test", "pass", "student")
    await record_events([_event(fp=f"f{i}", title=f"Xato {i}", at=NOW + timedelta(seconds=i)) for i in range(12)])
    monkeypatch.setattr("app.notifications.mailer.enabled", lambda: True)
    sent = []

    async def fake_send(mails):
        sent.extend(mails)
        return [True] * len(mails)

    assert await monitoring.send_alerts(db_session, NOW, send=fake_send) == 12
    await db_session.commit()
    (mail,) = sent
    assert mail.to == "a1@tryjob.test" and mail.subject == "TryJob — 12 ta yangi xato"
    assert "Xato 11" in mail.body and "Xato 1\n" not in mail.body and "va yana 2 ta" in mail.body
    assert "/admin?tab=errors" in mail.body

    sent.clear()
    assert await monitoring.send_alerts(db_session, NOW, send=fake_send) == 0
    assert sent == []


async def test_alert_marks_notified_even_when_mail_off(db_session, monkeypatch):
    await record_events([_event()])
    monkeypatch.setattr("app.notifications.mailer.enabled", lambda: False)

    async def must_not_send(mails):
        raise AssertionError("email o'chiq")

    assert await monitoring.send_alerts(db_session, NOW, send=must_not_send) == 1
    await db_session.commit()
    (group,) = await _groups(db_session)
    assert group.notified_at == NOW


async def test_cleanup_old_groups(db_session):
    await record_events([
        _event(fp="old-resolved", at=NOW - timedelta(days=31)),
        _event(fp="old-open", at=NOW - timedelta(days=31)),
        _event(fp="ancient", at=NOW - timedelta(days=91)),
        _event(fp="fresh-resolved", at=NOW - timedelta(days=1)),
    ])
    for g in await _groups(db_session):
        if g.fingerprint.endswith("resolved"):
            g.status = "resolved"
    await db_session.commit()
    assert await monitoring.cleanup(db_session, NOW) == 2
    await db_session.commit()
    assert sorted(g.fingerprint for g in await _groups(db_session)) == ["fresh-resolved", "old-open"]


# ── Log formati ──────────────────────────────────────────────────────


def test_json_formatter_fields():
    rec = _record(msg="so'rov %s", args=("ok",), exc=_raise(ValueError("yomon")))
    rec.request_id, rec.source, rec.status = "rid-1", "api", 200
    out = json.loads(JsonFormatter().format(rec))
    assert out["message"] == "so'rov ok" and out["level"] == "ERROR" and out["logger"] == "app.test"
    assert (out["request_id"], out["source"], out["status"]) == ("rid-1", "api", 200)
    assert "ValueError: yomon" in out["exc"] and out["ts"].endswith("+00:00")


def test_setup_logging_idempotent_and_adopts_library_loggers():
    setup_logging("worker")
    setup_logging("api")
    ours = [h for h in logging.getLogger().handlers if isinstance(h, _Handler)]
    assert len(ours) == 1 and ours[0].stream is sys.stdout
    assert logging.getLogger("arq").handlers == [] and logging.getLogger("arq").propagate
    assert logging.getLogger("uvicorn.access").disabled
    assert logging.getLogger("httpx").level == logging.WARNING
