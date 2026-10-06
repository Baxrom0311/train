import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import Simulation, User
from app.database import SessionLocal

client = TestClient(app)

def test_full_simulation_flow_e2e():
    # 0. Login to get JWT Token
    login_res = client.post("/api/v1/auth/login", json={
        "email": "student@tryjob.uz",
        "password": "student123"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Katalog tekshiruvi
    res = client.get("/api/v1/simulations")
    assert res.status_code == 200
    sims = res.json()
    assert len(sims) >= 6
    
    # 2. JPMorgan simulyatsiyasini olish
    jpm = client.get("/api/v1/simulations/jpmorgan-software-engineering")
    assert jpm.status_code == 200
    jpm_data = jpm.json()
    assert len(jpm_data["tasks"]) >= 1
    task_1 = jpm_data["tasks"][0]
    
    # 3. Python Sandbox tool orqali kodni ishlatish
    sandbox_code = """
def getDataPoint(quote):
    stock = quote['stock']
    bid_price = float(quote['top_bid']['price'])
    ask_price = float(quote['top_ask']['price'])
    price = (bid_price + ask_price) / 2
    return stock, bid_price, ask_price, price

def getRatio(price_a, price_b):
    if not price_b:
        return None
    return price_a / price_b

q1 = {'stock': 'ABC', 'top_bid': {'price': 120.0}, 'top_ask': {'price': 122.0}}
q2 = {'stock': 'DEF', 'top_bid': {'price': 100.0}, 'top_ask': {'price': 100.0}}
_, _, _, p_a = getDataPoint(q1)
_, _, _, p_b = getDataPoint(q2)
print(f"RATIO: {getRatio(p_a, p_b)}")
"""
    sb_res = client.post("/api/v1/tools/sandbox", json={"code": sandbox_code, "timeout_seconds": 5.0})
    assert sb_res.status_code == 200
    sb_data = sb_res.json()
    assert sb_data["status"] == "success"
    assert "RATIO: 1.21" in sb_data["output"]
    
    # 4. Topshiriqlarni AI Mentorga yuborish va baholatish
    task_solutions = {
        task_1["id"]: """
from typing import Tuple, Optional, Dict, Any

def getDataPoint(quote: Dict[str, Any]) -> Tuple[str, float, float, float]:
    \"\"\"Order Book kotirovkasidan aktsiya nomi, bid, ask va o'rtacha narxni hisoblaydi.\"\"\"
    stock = quote['stock']
    bid_price = float(quote['top_bid']['price'])
    ask_price = float(quote['top_ask']['price'])
    price = (bid_price + ask_price) / 2.0
    return stock, bid_price, ask_price, price

def getRatio(price_a: float, price_b: float) -> Optional[float]:
    \"\"\"Ikkita aktsiya narxlari nisbatini xavfsiz hisoblaydi (ZeroDivisionError dan himoyalangan).\"\"\"
    if not price_b or price_b == 0:
        return None
    return price_a / price_b
"""
    }

    for task in jpm_data["tasks"]:
        solution_code = task_solutions.get(task["id"], sandbox_code)
        sub_res = client.post(
            "/api/v1/submissions",
            data={
                "simulation_id": jpm_data["id"],
                "task_id": task["id"],
                "submitted_text": solution_code
            },
            headers=auth_headers
        )
        assert sub_res.status_code == 200
        sub_data = sub_res.json()
        assert sub_data["score"] >= 85.0
        assert "ai_feedback" in sub_data
        assert "rubric_breakdown" in sub_data["ai_feedback"]
    
    # 5. AI Mock Interview Tool tekshiruvi
    interview_res = client.post(
        "/api/v1/tools/mock-interview",
        json={
            "simulation_slug": "jpmorgan-software-engineering",
            "question": "JPMorgan vazifasida ZeroDivisionError xatosini qanday oldini oldingiz?",
            "student_answer": "Situation: Treyderlar terminalida 0 narx kelsa dastur qulashi xavfi bor edi. Task: Xavfsiz nisbat hisoblash. Action: if not price_b tekshiruvini qo'shdim. Result: Tizim 100% barqaror ishladi."
        }
    )
    assert interview_res.status_code == 200
    iv_data = interview_res.json()
    assert iv_data["score"] >= 70
    assert "feedback" in iv_data
    
    # 6. Sertifikat generatsiyasi va HMAC verifikatsiyasi
    cert_res = client.post(
        "/api/v1/certificates/issue",
        json={"simulation_id": jpm_data["id"]},
        headers=auth_headers
    )
    assert cert_res.status_code == 200
    cert_data = cert_res.json()
    assert "cert_uuid" in cert_data
    assert "hmac_signature" in cert_data
    
    # 7. Sertifikatni tekshirish
    verify_res = client.get(f"/api/v1/certificates/verify/{cert_data['cert_uuid']}")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["is_valid"] is True
    assert v_data["simulation_title"] == jpm_data["title"]
