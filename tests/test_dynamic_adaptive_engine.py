import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def get_auth_token(email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_company_and_admin_simulation_creation():
    """HR va Adminlar uchun to'liq Simulyatsiya va Topshiriq yaratish testi"""
    hr_token = get_auth_token("hr@kapitalbank.uz", "hr123")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    test_slug = "kapitalbank-highload-test-sim"
    # Oldingisi qolib ketgan bo'lsa tozalash
    client.delete(f"/api/v1/simulations/{test_slug}", headers=hr_headers)

    # 1. Kompaniya yangi simulyatsiya yaratadi
    create_sim_payload = {
        "slug": test_slug,
        "title": "Kapitalbank Real-Time High-Load Payment Processing",
        "category": "Engineering",
        "difficulty": "Intermediate",
        "estimated_hours": 5.0,
        "description": "Kapitalbank FinTech to'lov tizimida millionlab tranzaksiyalarni qayta ishlash, poyga holatlari va anomaliyalardan himoya.",
        "learning_outcomes": ["Concurrency locking", "Anti-fraud", "High-frequency streaming"],
        "is_published": True
    }
    sim_res = client.post("/api/v1/simulations", json=create_sim_payload, headers=hr_headers)
    assert sim_res.status_code == 201
    sim_data = sim_res.json()
    assert sim_data["slug"] == test_slug
    assert sim_data["company"]["name"] == "Kapitalbank ATB"

    # 2. Kompaniya yangi topshiriq (Task) qo'shadi
    task_payload = {
        "order": 1,
        "title": "Tranzaksiyalar oqimi va ZeroDivision himoyasi",
        "briefing_text": "To'lovlar shlyuzida narxlar nisbati va o'rtacha hisoblarda xatoliklar yuzaga kelmasligini ta'minlang.",
        "instructions": "process_market_records funksiyasini yozing va nolga bo'lishdan himoyalang.",
        "rubric_criteria": [
            {"criterion": "ZeroDivision va manfiy qiymatlardan himoya", "max_score": 50},
            {"criterion": "Hisoblash aniqligi", "max_score": 50}
        ],
        "mentor_persona": "lead_engineer"
    }
    task_res = client.post(f"/api/v1/simulations/{test_slug}/tasks", json=task_payload, headers=hr_headers)
    assert task_res.status_code == 201
    task_data = task_res.json()
    assert task_data["title"] == task_payload["title"]

    # 3. Talaba simulyatsiya yaratishga urinishi (403 Forbidden tekshiruvi)
    student_token = get_auth_token("student@tryjob.uz", "student123")
    student_headers = {"Authorization": f"Bearer {student_token}"}
    forbidden_res = client.post("/api/v1/simulations", json=create_sim_payload, headers=student_headers)
    assert forbidden_res.status_code == 403

    # 4. Simulyatsiyani muvaffaqiyatli o'chirish (Delete API)
    del_res = client.delete(f"/api/v1/simulations/{test_slug}", headers=hr_headers)
    assert del_res.status_code == 200

def test_dynamic_adaptive_challenge_engine_generation():
    """Dynamic Infinite Adaptive Challenge Engine: generatsiya va sintetik datasetlar"""
    student_token = get_auth_token("student@tryjob.uz", "student123")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Adaptiv darajadagi Concurrency topshirig'ini yaratish
    concurrency_req = {
        "level": 7,
        "preferred_focus": "concurrency"
    }
    dyn_res = client.post(
        "/api/v1/simulations/kapitalbank-credit-analyst/dynamic-challenge",
        json=concurrency_req,
        headers=student_headers
    )
    assert dyn_res.status_code == 201
    dyn_data = dyn_res.json()
    assert dyn_data["level"] == 7
    assert dyn_data["challenge_type"] == "concurrency"
    assert "asyncio.Lock" in dyn_data["starter_code"]
    assert "concurrent_events" in dyn_data["synthetic_dataset"]
    assert len(dyn_data["rubric_criteria"]) >= 2
    assert dyn_data["target_elo_gain"] > 0

    # 2. Faol dinamik challenge ni so'rab olish
    active_res = client.get(
        "/api/v1/simulations/kapitalbank-credit-analyst/dynamic-challenge/active",
        headers=student_headers
    )
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["id"] == dyn_data["id"]
    assert active_data["status"] == "active"

def test_dynamic_challenge_concurrency_evaluation_and_elo_growth():
    """Concurrency kodi AST tahlili va talabaning ELO / Mastery level o'sishi"""
    student_token = get_auth_token("student@tryjob.uz", "student123")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Dinamik challenge yaratish
    dyn_res = client.post(
        "/api/v1/simulations/jpmorgan-software-engineering/dynamic-challenge",
        json={"level": 7, "preferred_focus": "concurrency"},
        headers=student_headers
    )
    assert dyn_res.status_code == 201
    challenge_id = dyn_res.json()["id"]

    # Concurrency bo'yicha mustahkam yechim kodi (asyncio.Lock va tartiblangan Deadlock prevention)
    concurrency_solution = """import asyncio
from typing import Dict

class AsyncBankLedger:
    def __init__(self, initial_balances: Dict[str, float]):
        self.balances = initial_balances.copy()
        self.locks: Dict[str, asyncio.Lock] = {}

    def _get_lock(self, account_id: str) -> asyncio.Lock:
        if account_id not in self.locks:
            self.locks[account_id] = asyncio.Lock()
        return self.locks[account_id]

    async def transfer(self, source: str, dest: str, amount: float) -> bool:
        first, second = (source, dest) if source < dest else (dest, source)
        async with self._get_lock(first):
            async with self._get_lock(second):
                if self.balances.get(source, 0.0) < amount:
                    return False
                self.balances[source] -= amount
                self.balances[dest] = self.balances.get(dest, 0.0) + amount
                return True
"""
    # Topshiriqni yuborish
    sub_res = client.post(
        "/api/v1/submissions",
        data={
            "simulation_id": dyn_res.json()["simulation_id"],
            "dynamic_challenge_id": challenge_id,
            "submitted_text": concurrency_solution
        },
        headers=student_headers
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "passed"
    assert sub_data["score"] >= 85.0
    assert sub_data["elo_change"] > 0
    assert sub_data["new_elo"] > 1000
    assert sub_data["new_mastery_level"] >= 1
    assert sub_data["ai_feedback"]["passed"] is True

def test_dynamic_challenge_anti_fraud_ast_evaluation():
    """Anti-fraud va AML qoidalarini tekshirish AST testi"""
    student_token = get_auth_token("student@tryjob.uz", "student123")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # Dinamik Anti-fraud topshirig'i
    dyn_res = client.post(
        "/api/v1/simulations/kapitalbank-credit-analyst/dynamic-challenge",
        json={"level": 5, "preferred_focus": "anti_fraud"},
        headers=student_headers
    )
    assert dyn_res.status_code == 201
    challenge_id = dyn_res.json()["id"]

    anti_fraud_solution = """class FraudEngine:
    def __init__(self):
        self.aml_lower = 9500000
        self.aml_upper = 10000000

    def evaluate_transaction(self, tx, user_history):
        flags = []
        risk_score = 10.0
        amt = tx.get("amount_uzs", 0)
        ts = tx.get("timestamp", 0)

        # Velocity check: oxirgi 5 soniyada
        recent_txs = [h for h in user_history if (ts - h.get("timestamp", 0)) <= 5]
        if len(recent_txs) >= 2:
            flags.append("FLAG_HIGH_VELOCITY")
            risk_score += 45.0

        # AML Structuring limit monitoring
        if 9500000 <= amt < 10000000:
            flags.append("FLAG_AML_STRUCTURING")
            risk_score += 40.0

        decision = "DECLINE" if risk_score >= 70 else ("REVIEW" if risk_score >= 40 else "APPROVE")
        return {
            "transaction_id": tx.get("transaction_id"),
            "risk_score": min(100.0, risk_score),
            "decision": decision,
            "triggered_flags": flags
        }
"""
    sub_res = client.post(
        "/api/v1/submissions",
        data={
            "simulation_id": dyn_res.json()["simulation_id"],
            "dynamic_challenge_id": challenge_id,
            "submitted_text": anti_fraud_solution
        },
        headers=student_headers
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "passed"
    assert sub_data["score"] >= 80.0

def test_dynamic_challenge_anomaly_detection_ast():
    """Real-Time Sliding Window va Timestamp Anomaliyalari AST baholash testi"""
    student_token = get_auth_token("student@tryjob.uz", "student123")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    dyn_res = client.post(
        "/api/v1/simulations/kapitalbank-credit-analyst/dynamic-challenge",
        json={"level": 3, "preferred_focus": "high_frequency_anomalies"},
        headers=student_headers
    )
    assert dyn_res.status_code == 201
    challenge_id = dyn_res.json()["id"]

    anomaly_solution = """import math

class AnomalyDetector:
    def __init__(self, window_size=5, threshold_multiplier=3.0):
        self.window_size = window_size
        self.threshold = threshold_multiplier
        self.history = []
        self.last_timestamp = 0

    def ingest_record(self, record):
        val = float(record.get("metric_value", 0.0))
        ts = int(record.get("timestamp", 0))
        anomaly_type = None

        if self.last_timestamp > 0 and ts < self.last_timestamp:
            anomaly_type = "OUT_OF_ORDER"

        self.last_timestamp = max(self.last_timestamp, ts)

        if len(self.history) >= self.window_size:
            avg = sum(self.history) / len(self.history)
            variance = sum((x - avg) ** 2 for x in self.history) / len(self.history)
            std = math.sqrt(variance)
            if std > 0 and abs(val - avg) > self.threshold * std:
                anomaly_type = anomaly_type or "HIGH_FREQUENCY_SPIKE"

        self.history.append(val)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        return {
            "seq_id": record.get("seq_id"),
            "metric_value": val,
            "is_anomaly": anomaly_type is not None,
            "anomaly_type": anomaly_type
        }
"""
    sub_res = client.post(
        "/api/v1/submissions",
        data={
            "simulation_id": dyn_res.json()["simulation_id"],
            "dynamic_challenge_id": challenge_id,
            "submitted_text": anomaly_solution
        },
        headers=student_headers
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "passed"
    assert sub_data["score"] >= 85.0

def test_dynamic_challenge_zero_day_security_ast():
    """SQL Injection, ReDoS va XSS sanitization AST baholash testi"""
    student_token = get_auth_token("student@tryjob.uz", "student123")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    dyn_res = client.post(
        "/api/v1/simulations/kapitalbank-credit-analyst/dynamic-challenge",
        json={"level": 9, "preferred_focus": "zero_day_bugs"},
        headers=student_headers
    )
    assert dyn_res.status_code == 201
    challenge_id = dyn_res.json()["id"]

    security_solution = r"""import re
import html

class InputSecurityGuard:
    def __init__(self, max_len=2048):
        self.max_len = max_len
        self.sql_pattern = re.compile(r"(\b(UNION|SELECT|DROP|INSERT|DELETE|UPDATE)\b|--|\bOR\b\s+['\d\w]+)", re.IGNORECASE)

    def sanitize_and_check(self, raw_input):
        if not raw_input:
            return {"is_safe": True, "clean_str": "", "threat": None}
        if len(raw_input) > self.max_len:
            return {"is_safe": False, "clean_str": raw_input[:self.max_len], "threat": "BUFFER_OVERFLOW"}
        if self.sql_pattern.search(raw_input):
            return {"is_safe": False, "clean_str": html.escape(raw_input), "threat": "SQL_INJECTION"}
        if "<script" in raw_input.lower():
            return {"is_safe": False, "clean_str": html.escape(raw_input), "threat": "XSS_PAYLOAD"}
        return {"is_safe": True, "clean_str": html.escape(raw_input), "threat": None}
"""
    sub_res = client.post(
        "/api/v1/submissions",
        data={
            "simulation_id": dyn_res.json()["simulation_id"],
            "dynamic_challenge_id": challenge_id,
            "submitted_text": security_solution
        },
        headers=student_headers
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "passed"
    assert sub_data["score"] >= 85.0

def test_infinite_adaptive_learning_progression():
    """Cheksiz adaptiv amaliyot mexanizmi: bir bosqichni topshirgach, keyingi qiyinlashgan challenge generatsiyasi"""
    student_token = get_auth_token("student@tryjob.uz", "student123")
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Talabaning joriy holatini tekshirish
    me_res = client.get("/api/v1/auth/me", headers=student_headers)
    assert me_res.status_code == 200
    initial_elo = me_res.json()["elo_rating"]
    initial_level = me_res.json()["mastery_level"]

    # 2. Avtomatik (auto) fokus bilan yangi adaptiv challenge so'rash
    dyn_res = client.post(
        "/api/v1/simulations/kapitalbank-credit-analyst/dynamic-challenge",
        json={"preferred_focus": None}, # Auto adaptiv
        headers=student_headers
    )
    assert dyn_res.status_code == 201
    dyn_data = dyn_res.json()
    assert dyn_data["level"] >= 1
    assert dyn_data["status"] == "active"
    assert dyn_data["current_elo"] >= initial_elo

