import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_case_cups_api():
    res = client.get("/api/v1/case-cups")
    assert res.status_code == 200
    cups = res.json()
    assert len(cups) >= 1
    cup_slug = cups[0]["slug"]
    
    # Leaderboard
    lb_res = client.get(f"/api/v1/case-cups/{cup_slug}/leaderboard")
    assert lb_res.status_code == 200
    lb_data = lb_res.json()
    assert "leaderboard" in lb_data
    assert len(lb_data["leaderboard"]) >= 1

def test_talent_hunt_api():
    # HR Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": "hr@kapitalbank.uz",
        "password": "hr123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    hr_headers = {"Authorization": f"Bearer {token}"}
    
    # Nomzodlarni olish
    c_res = client.get("/api/v1/talent-hunt/candidates", headers=hr_headers)
    assert c_res.status_code == 200
    candidates = c_res.json()
    assert len(candidates) >= 1
    
    # Direct Offer yuborish
    offer_payload = {
        "candidate_id": candidates[0]["user_id"],
        "position_title": "Junior Python / Quantitative Developer",
        "message": "Assalomu alaykum! Sizning TryJob platformasidagi topshiriqlaringiz bizda katta qiziqish uyg'otdi. Sizni suhbatga taklif qilamiz."
    }
    offer_res = client.post("/api/v1/talent-hunt/send-offer", json=offer_payload, headers=hr_headers)
    assert offer_res.status_code == 200
    offer_data = offer_res.json()
    assert offer_data["status"] == "sent"

def test_university_portal_api():
    # Dean Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": "dean@urdu.uz",
        "password": "dean123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    dean_headers = {"Authorization": f"Bearer {token}"}
    
    # Statistika olish
    stats_res = client.get("/api/v1/university-portal/stats", headers=dean_headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_registered_students" in stats
    assert "internship_ready_students_count" in stats

def test_billing_vip_upgrade():
    login_res = client.post("/api/v1/auth/login", json={
        "email": "student@tryjob.uz",
        "password": "student123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    vip_res = client.post("/api/v1/billing/upgrade-vip", json={"plan_type": "vip_monthly", "provider": "click"}, headers=auth_headers)
    assert vip_res.status_code == 200
    vip_data = vip_res.json()
    assert vip_data["user_vip_status"] is True
