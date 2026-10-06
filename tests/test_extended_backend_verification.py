import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.models import User, Simulation, SimulationTask, Submission, Certificate, Company, University
from app.core.security import get_password_hash, create_access_token, generate_cert_hmac

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_unauthorized_endpoints_blocked():
    """Ruxsatsiz (token siz) himoyalangan endpointlarga kirish bloklanishi tekshiruvi"""
    # 1. /auth/me
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401

    # 2. POST /simulations
    res = client.post("/api/v1/simulations", json={"title": "Test", "category": "Engineering", "description": "Test"})
    assert res.status_code == 401

    # 3. POST /submissions
    res = client.post("/api/v1/submissions", data={"simulation_id": "test-sim"})
    assert res.status_code == 401

    # 4. POST /certificates/issue
    res = client.post("/api/v1/certificates/issue", json={"simulation_id": "test-sim"})
    assert res.status_code == 401

    # 5. POST /billing/upgrade-vip
    res = client.post("/api/v1/billing/upgrade-vip", json={"plan_type": "vip_monthly", "provider": "click"})
    assert res.status_code == 401

def test_role_based_access_control_on_simulations(db_session):
    """Student simulyatsiya yarata olmasligi (403), faqat Company HR va Admin yarata olishi"""
    # Student token
    student = db_session.query(User).filter(User.role == "student").first()
    student_token = create_access_token({"sub": student.id, "email": student.email, "role": "student"})
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Student simulyatsiya yaratishga urinsa -> 403 Forbidden
    res = client.post("/api/v1/simulations", json={
        "title": "Hacked Simulation by Student",
        "category": "Engineering",
        "description": "Unauthorized simulation"
    }, headers=student_headers)
    assert res.status_code == 403
    assert "HR yoki Admin ruxsati talab qilinadi" in res.json()["detail"]

    # Student task yaratishga urinsa -> 403 Forbidden
    res = client.post("/api/v1/simulations/jpmorgan-software-engineering/tasks", json={
        "title": "Hacked Task by Student",
        "briefing_text": "Unauthorized briefing test with long text",
        "instructions": "Unauthorized instructions test with long text"
    }, headers=student_headers)
    assert res.status_code == 403

def test_submission_idor_protection(db_session):
    """IDOR / BOLA himoyasi: Talaba A boshqa Talaba B ning topshirig'ini ko'ra olmasligi (403)"""
    students = db_session.query(User).filter(User.role == "student").all()
    assert len(students) >= 2
    student_a = students[0]
    student_b = students[1]

    # Student B nomidan submission yaratish
    sim = db_session.query(Simulation).first()
    sub_b = Submission(
        user_id=student_b.id,
        simulation_id=sim.id,
        submitted_text="Student B Maxfiy Yechimi",
        score=95.0,
        status="passed"
    )
    db_session.add(sub_b)
    db_session.commit()
    db_session.refresh(sub_b)

    # Student A tokeni bilan Student B ning topshirig'ini olishga urinish
    token_a = create_access_token({"sub": student_a.id, "email": student_a.email, "role": "student"})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    res = client.get(f"/api/v1/submissions/{sub_b.id}", headers=headers_a)
    assert res.status_code == 403
    assert "Ruxsat berilmagan resurs" in res.json()["detail"]

    # Student B o'zining topshirig'ini ko'ra olishi
    token_b = create_access_token({"sub": student_b.id, "email": student_b.email, "role": "student"})
    headers_b = {"Authorization": f"Bearer {token_b}"}
    res_b = client.get(f"/api/v1/submissions/{sub_b.id}", headers=headers_b)
    assert res_b.status_code == 200
    assert res_b.json()["submitted_text"] == "Student B Maxfiy Yechimi"

def test_certificate_issuance_and_verification_flow(db_session):
    """Sertifikat berish va HMAC orqali ommaviy tekshirish to'liq tsikli"""
    student = db_session.query(User).filter(User.role == "student").first()
    sim = db_session.query(Simulation).filter(Simulation.slug == "jpmorgan-software-engineering").first()
    assert sim is not None
    token = create_access_token({"sub": student.id, "email": student.email, "role": "student"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Tozalash (submissions & certificates)
    db_session.query(Certificate).filter(Certificate.user_id == student.id, Certificate.simulation_id == sim.id).delete()
    db_session.query(Submission).filter(Submission.user_id == student.id, Submission.simulation_id == sim.id).delete()
    db_session.commit()

    # Vazifalar to'liq topshirilmasdan turib sertifikat so'ralsa -> 400 Bad Request
    res = client.post("/api/v1/certificates/issue", json={"simulation_id": sim.id}, headers=headers)
    assert res.status_code == 400
    assert "barcha topshiriqlarni" in res.json()["detail"]

    # 2. Barcha vazifalarni 'passed' statusida topshiramiz
    for task in sim.tasks:
        sub = Submission(
            user_id=student.id,
            simulation_id=sim.id,
            task_id=task.id,
            submitted_text="def getDataPoint(): pass",
            score=92.0,
            status="passed"
        )
        db_session.add(sub)
    db_session.commit()

    # 3. Endi sertifikat so'raymiz -> 200 OK
    res = client.post("/api/v1/certificates/issue", json={"simulation_id": sim.id}, headers=headers)
    assert res.status_code == 200
    cert_data = res.json()
    assert "cert_uuid" in cert_data
    assert cert_data["user_name"] == student.full_name
    assert cert_data["average_score"] == 92.0
    assert cert_data["hmac_signature"] is not None

    cert_uuid = cert_data["cert_uuid"]

    # 4. Ochiq (public) tekshiruv endpointi
    verify_res = client.get(f"/api/v1/certificates/verify/{cert_uuid}")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["is_valid"] is True
    assert "RASMIY TASDIQLANGAN" in v_data["verification_status"]

    # 5. Mavjud bo'lmagan sertifikat tekshiruvi -> 404
    fake_res = client.get("/api/v1/certificates/verify/UZ-TRY-FAKE9999")
    assert fake_res.status_code == 404

def test_click_and_payme_webhooks(db_session):
    """Click va Payme to'lov shlyuzlari webhooklari to'liq sinovi"""
    student = db_session.query(User).filter(User.role == "student").first()
    assert student is not None
    student.is_vip = False
    student.vip_expires_at = None
    db_session.commit()

    # 1. Click Prepare (action=0)
    click_prep = client.post("/api/v1/billing/click/webhook", json={
        "click_trans_id": 99123456,
        "merchant_trans_id": student.id,
        "amount": 99000.0,
        "action": 0,
        "sign_time": "2026-10-06 12:00:00",
        "sign_string": "test_hash"
    })
    assert click_prep.status_code == 200
    assert click_prep.json()["error"] == 0
    assert click_prep.json()["merchant_prepare_id"] == student.id

    # 2. Click Complete (action=1)
    click_comp = client.post("/api/v1/billing/click/webhook", json={
        "click_trans_id": 99123456,
        "merchant_trans_id": student.id,
        "amount": 99000.0,
        "action": 1,
        "sign_time": "2026-10-06 12:00:05",
        "sign_string": "test_hash"
    })
    assert click_comp.status_code == 200
    assert click_comp.json()["error"] == 0

    db_session.refresh(student)
    assert student.is_vip is True
    assert student.vip_expires_at is not None

    # 3. Payme CheckPerformTransaction
    payme_check = client.post("/api/v1/billing/payme/webhook", json={
        "method": "CheckPerformTransaction",
        "params": {"account": {"user_id": student.id}, "amount": 9900000}
    })
    assert payme_check.status_code == 200
    assert payme_check.json()["result"]["allow"] is True

    # 4. Payme PerformTransaction
    payme_perform = client.post("/api/v1/billing/payme/webhook", json={
        "method": "PerformTransaction",
        "params": {"account": {"user_id": student.id}, "amount": 89000000}
    })
    assert payme_perform.status_code == 200
    assert payme_perform.json()["result"]["state"] == 2
