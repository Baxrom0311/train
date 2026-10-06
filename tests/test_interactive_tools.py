import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.sandbox import SafePythonSandbox

client = TestClient(app)

def test_safe_python_sandbox_execution():
    # To'g'ri va xavfsiz kod
    code = "total = sum([10, 20, 30])\nprint(f'Natija: {total}')"
    res = SafePythonSandbox.execute_code(code)
    assert res["success"] is True
    assert "Natija: 60" in res["output"]

def test_sandbox_blocks_malicious_code():
    # Xavfli kod (os moduli)
    bad_code = "import os\nos.system('ls')"
    res = SafePythonSandbox.execute_code(bad_code)
    assert res["success"] is False
    assert "taqiqlangan" in res["error"]

    # Xavfli kod: dunder injection (__class__)
    dunder_code = "x = (1).__class__.__bases__"
    res_dunder = SafePythonSandbox.execute_code(dunder_code)
    assert res_dunder["success"] is False
    assert "taqiqlangan" in res_dunder["error"]

    # Xavfli kod: getattr chaqiruvi
    getattr_code = "x = getattr(int, '__class__')"
    res_getattr = SafePythonSandbox.execute_code(getattr_code)
    assert res_getattr["success"] is False
    assert "taqiqlangan" in res_getattr["error"]

def test_sandbox_timeout_interruption():
    # Cheksiz sikl (infinite loop) timeout orqali to'xtatiladi
    loop_code = "while True:\n    pass"
    res = SafePythonSandbox.execute_code(loop_code, timeout_sec=0.2)
    assert res["success"] is False
    assert "Timeout" in res["error"]

def test_sandbox_api_endpoint():
    resp = client.post("/api/v1/tools/run-python", json={
        "code": "print('Salom TryJob!')"
    })
    assert resp.status_code == 200
    assert "Salom TryJob!" in resp.json()["output"]

def test_mock_interview_api():
    resp = client.post("/api/v1/tools/mock-interview", json={
        "category": "finance",
        "question": "DTI hisoblashda nimalarga e'tibor berish kerak?",
        "answer": "Mijozning oylik barcha kredit to'lovlarini uning soliqdan keyingi sof daromadiga nisbatini hisoblaymiz. O'zbekiston Markaziy Banki me'yori bo'yicha bu ko'rsatkich 50% dan oshmasligi shart. Agar oshsa, kredit rad etiladi yoki muddati uzaytiriladi.",
        "mentor_persona": "chief_financial_officer"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["score"] >= 80.0
    assert "Shahnoza" in data["interviewer_name"]

def test_document_audit_api():
    # To'g'ri EHF (10,000,000 + 12% QQS = 11,200,000)
    resp_ok = client.post("/api/v1/tools/document-audit", json={
        "doc_type": "ehf",
        "tin": "123456789", # 9 ta raqam
        "items_total": 10000000.0,
        "vat_rate": 0.12,
        "declared_total": 11200000.0
    })
    assert resp_ok.status_code == 200
    assert resp_ok.json()["is_valid"] is True

    # Noto'g'ri STIR (8 ta raqam) va noto'g'ri summa
    resp_bad = client.post("/api/v1/tools/document-audit", json={
        "doc_type": "ehf",
        "tin": "12345",
        "items_total": 10000000.0,
        "vat_rate": 0.12,
        "declared_total": 10000000.0
    })
    assert resp_bad.status_code == 200
    assert resp_bad.json()["is_valid"] is False
    assert len(resp_bad.json()["errors"]) >= 1
