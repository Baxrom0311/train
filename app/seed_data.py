import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import (
    Company,
    Simulation,
    SimulationTask,
    User,
    University,
    CaseCupLeaderboard,
    TalentOffer,
    Transaction,
    Submission,
    Certificate
)
from app.core.security import get_password_hash

def seed_database(db: Session):
    # ── 1. Universitetlar (O'zbekiston Yetakchi OTMlari) ───────────────────────
    universities_data = [
        {
            "name": "Urganch davlat universiteti (UrDU)",
            "city": "Urganch",
            "official_code": "UrDU-01",
            "total_students": 22400
        },
        {
            "name": "Westminster International University in Tashkent (WIUT)",
            "city": "Toshkent",
            "official_code": "WIUT-01",
            "total_students": 4800
        },
        {
            "name": "Inha University in Tashkent (IUT)",
            "city": "Toshkent",
            "official_code": "IUT-01",
            "total_students": 3200
        },
        {
            "name": "Toshkent Davlat Iqtisodiyot Universiteti (TDIU)",
            "city": "Toshkent",
            "official_code": "TDIU-01",
            "total_students": 18000
        }
    ]

    unis_map = {}
    for u_data in universities_data:
        uni = db.query(University).filter_by(name=u_data["name"]).first()
        if not uni:
            uni = University(**u_data)
            db.add(uni)
            db.flush()
        unis_map[u_data["name"]] = uni

    # ── 2. Kompaniyalar (Global & O'zbekiston Yetakchilari) ────────────────────
    companies_data = [
        {
            "name": "JPMorgan Chase & Co.",
            "industry": "Global Investment Banking & Tech",
            "logo_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=120&auto=format&fit=crop&q=80",
            "description": "Dunyoning 1-raqamli investitsiya banki va kvantitativ moliya texnologiyalari markazi.",
            "website": "https://jpmorgan.com"
        },
        {
            "name": "Goldman Sachs",
            "industry": "Investment Banking & Cybersecurity",
            "logo_url": "https://images.unsplash.com/photo-1554224155-8d04cb21cd6c?w=120&auto=format&fit=crop&q=80",
            "description": "Global moliyaviy xizmatlar va kiberxavfsizlik sohasida yetakchi xalqaro korporatsiya.",
            "website": "https://goldmansachs.com"
        },
        {
            "name": "Accenture",
            "industry": "Data Analytics & IT Consulting",
            "logo_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?w=120&auto=format&fit=crop&q=80",
            "description": "Raqamli transformatsiya, Data Analytics va AI integratsiyasi bo'yicha dunyo yetakchisi.",
            "website": "https://accenture.com"
        },
        {
            "name": "BCG (Boston Consulting Group)",
            "industry": "Strategy Consulting",
            "logo_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=120&auto=format&fit=crop&q=80",
            "description": "Bozor strategiyasi, korporativ boshqaruv va biznes transformatsiyasi bo'yicha global konsalting kompaniyasi.",
            "website": "https://bcg.com"
        },
        {
            "name": "PwC (PricewaterhouseCoopers)",
            "industry": "Audit, Tax & Advisory",
            "logo_url": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=120&auto=format&fit=crop&q=80",
            "description": "Katta to'rtlik (Big 4) xalqaro audit va biznes tahlil giganti.",
            "website": "https://pwc.com"
        },
        {
            "name": "Kapitalbank ATB",
            "industry": "Banking & FinTech (Uzbekistan)",
            "logo_url": "https://images.unsplash.com/photo-1541354329998-f4d9a9f9297f?w=120&auto=format&fit=crop&q=80",
            "description": "O'zbekistondagi yetakchi xususiy tijorat banki va FinTech innovatsiyalari markazi.",
            "website": "https://kapitalbank.uz"
        },
        {
            "name": "Uzum Technologies",
            "industry": "E-Commerce & IT Ecosystem (Uzbekistan)",
            "logo_url": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=120&auto=format&fit=crop&q=80",
            "description": "O'zbekistonning birinchi IT-unikorni, elektron tijorat, to'lovlar va bank xizmatlari ekotizimi.",
            "website": "https://uzum.uz"
        },
        {
            "name": "Toshkent Audit & Legal",
            "industry": "Legal & Tax Advisory (Uzbekistan)",
            "logo_url": "https://images.unsplash.com/photo-1450133064473-71024230f91b?w=120&auto=format&fit=crop&q=80",
            "description": "O'zbekiston korporativ sektori uchun soliq, audit va Didox elektron hujjatlar ekspertizasi.",
            "website": "https://audit-legal.uz"
        }
    ]

    companies_map = {}
    for c_data in companies_data:
        comp = db.query(Company).filter_by(name=c_data["name"]).first()
        if not comp:
            comp = Company(**c_data)
            db.add(comp)
            db.flush()
        companies_map[c_data["name"]] = comp

    # ── 3. Foydalanuvchilar (Student, HR, Dean, Admin) ──────────────────────────
    users_data = [
        {
            "email": "student@tryjob.uz",
            "full_name": "Bahrom Reyimberganov",
            "password": "student123",
            "role": "student",
            "university": "Urganch davlat universiteti (UrDU)",
            "university_id": unis_map["Urganch davlat universiteti (UrDU)"].id,
            "is_vip": True,
            "vip_expires_at": datetime.now(timezone.utc) + timedelta(days=90),
            "mastery_level": 3,
            "elo_rating": 1350,
            "xp_points": 1450,
            "adaptive_skill_profile": {
                "algorithms": 1350,
                "edge_cases": 1380,
                "high_frequency_anomalies": 1320,
                "anti_fraud": 1290,
                "concurrency": 1250,
                "zero_day_bugs": 1200
            }
        },
        {
            "email": "aziza@wiut.uz",
            "full_name": "Aziza Rahimova",
            "password": "student123",
            "role": "student",
            "university": "Westminster International University in Tashkent (WIUT)",
            "university_id": unis_map["Westminster International University in Tashkent (WIUT)"].id,
            "is_vip": True,
            "vip_expires_at": datetime.now(timezone.utc) + timedelta(days=60),
            "mastery_level": 2,
            "elo_rating": 1200,
            "xp_points": 950,
            "adaptive_skill_profile": {
                "algorithms": 1200,
                "edge_cases": 1250,
                "anti_fraud": 1150
            }
        },
        {
            "email": "jasur@iut.uz",
            "full_name": "Jasur Abdullayev",
            "password": "student123",
            "role": "student",
            "university": "Inha University in Tashkent (IUT)",
            "university_id": unis_map["Inha University in Tashkent (IUT)"].id,
            "is_vip": False,
            "vip_expires_at": None,
            "mastery_level": 1,
            "elo_rating": 1050,
            "xp_points": 450,
            "adaptive_skill_profile": {
                "algorithms": 1050,
                "edge_cases": 1050
            }
        },
        {
            "email": "hr@kapitalbank.uz",
            "full_name": "Kamola Rustamova (Kapitalbank HR Head)",
            "password": "hr123",
            "role": "company_hr",
            "company_id": companies_map["Kapitalbank ATB"].id
        },
        {
            "email": "dean@urdu.uz",
            "full_name": "Prof. Otabek Shukurov (UrDU Dekani)",
            "password": "dean123",
            "role": "university_dean",
            "university_id": unis_map["Urganch davlat universiteti (UrDU)"].id
        },
        {
            "email": "admin@tryjob.uz",
            "full_name": "TryJob Platform Admin",
            "password": "admin123",
            "role": "admin"
        }
    ]

    users_map = {}
    for u_data in users_data:
        user = db.query(User).filter_by(email=u_data["email"]).first()
        if not user:
            user = User(
                email=u_data["email"],
                full_name=u_data["full_name"],
                hashed_password=get_password_hash(u_data["password"]),
                role=u_data["role"],
                university=u_data.get("university"),
                university_id=u_data.get("university_id"),
                company_id=u_data.get("company_id"),
                is_vip=u_data.get("is_vip", False),
                vip_expires_at=u_data.get("vip_expires_at"),
                mastery_level=u_data.get("mastery_level", 1),
                elo_rating=u_data.get("elo_rating", 1000),
                xp_points=u_data.get("xp_points", 0),
                adaptive_skill_profile=u_data.get("adaptive_skill_profile", {})
            )
            db.add(user)
            db.flush()
        else:
            user.role = u_data["role"]
            user.university = u_data.get("university", user.university)
            user.university_id = u_data.get("university_id", user.university_id)
            user.company_id = u_data.get("company_id", user.company_id)
            user.is_vip = u_data.get("is_vip", user.is_vip)
            user.vip_expires_at = u_data.get("vip_expires_at", user.vip_expires_at)
            if "mastery_level" in u_data:
                user.mastery_level = u_data["mastery_level"]
            if "elo_rating" in u_data:
                user.elo_rating = u_data["elo_rating"]
            if "xp_points" in u_data:
                user.xp_points = u_data["xp_points"]
            if "adaptive_skill_profile" in u_data:
                user.adaptive_skill_profile = u_data["adaptive_skill_profile"]
            db.flush()
        users_map[u_data["email"]] = user

    # ── 4. The Forage Standartidagi Haqiqiy Ko'p Bosqichli Simulyatsiyalar ───────
    simulations_data = [
        # 1. JPMorgan Chase — Software Engineering & Quantitative Technology
        {
            "slug": "jpmorgan-software-engineering",
            "title": "JPMorgan Chase — Software Engineering & Quantitative Technology",
            "company": companies_map["JPMorgan Chase & Co."],
            "category": "Engineering",
            "difficulty": "Intermediate",
            "estimated_hours": 5.0,
            "is_case_cup": False,
            "prize_pool": None,
            "deadline": None,
            "description": "JPMorgan investitsiya va treyding tizimlarida real dasturlash amaliyoti. Siz real-vaqt rejimida aktsiyalar narxlari oqimini (Stock Price Feed) tahlil qilasiz, narxlar nisbatini hisoblash algoritmini ishlab chiqasiz, unittests yozasiz va Perspective chart vizualizatsiyasi bilan integratsiya qilasiz.",
            "learning_outcomes": [
                "Moliyaviy ma'lumotlar oqimini (Order Book Data Stream) qayta ishlash",
                "Aktsiyalar narxlari o'rtasidagi nisbatni (Stock Ratio) nolga bo'lish xavfisiz hisoblash",
                "Python Unittest kutubxonasi yordamida avtomatlashtirilgan testlar yozish",
                "Perspective realtime grafiklari bilan treyderlar terminalini qurish"
            ],
            "tasks": [
                {
                    "order": 1,
                    "title": "1-Bosqich: Order Book Narxlar Oqimini Qayta Ishlash va Unittest Yozish",
                    "briefing": "Xush kelibsiz! Men Alexandre Duboisman, JPMorgan Quantitative Technology jamoasi Tech Leadiman. Treyderlarimiz har millisekundda millionlab kotirovkalarni solishtirib korrelyatsiya xatolarini topishadi. Sizning birinchi vazifangiz — Order Book oqimidan eng yaxshi Bid va Ask narxlarini olib, o'rtacha narx (Mid-Price) hamda ikkita aktsiya narxlari nisbatini (Ratio = Price_A / Price_B) hisoblash. Agar Price_B 0 ga teng bo'lsa yoki bo'sh ma'lumot kelsa, tizim qulamasligi va xavfsiz None qaytarishi lozim.",
                    "instructions": "1. `getDataPoint(quote)` funksiyasini yozing: quote lug'atidan `stock`, `top_bid_price`, `top_ask_price` va `price = (bid + ask) / 2` qiymatlarini qaytarsin.\n2. `getRatio(price_a, price_b)` funksiyasini yozing: `price_a / price_b` nisbatini hisoblasin. Agar `price_b == 0` yoki None bo'lsa, xavfsiz `None` qaytarsin.\n3. Funksiyalarni test qiling va Sandbox orqali ishga tushiring.",
                    "template": "from typing import Tuple, Optional, Dict, Any\n\ndef getDataPoint(quote: Dict[str, Any]) -> Tuple[str, float, float, float]:\n    \"\"\"Order Book kotirovkasidan aktsiya nomi, bid, ask va o'rtacha narxni hisoblaydi.\"\"\"\n    stock = quote['stock']\n    bid_price = float(quote['top_bid']['price'])\n    ask_price = float(quote['top_ask']['price'])\n    price = (bid_price + ask_price) / 2.0\n    return stock, bid_price, ask_price, price\n\ndef getRatio(price_a: float, price_b: float) -> Optional[float]:\n    \"\"\"Ikkita aktsiya narxlari nisbatini xavfsiz hisoblaydi (ZeroDivisionError dan himoyalangan).\"\"\"\n    if not price_b or price_b == 0:\n        return None\n    return price_a / price_b\n\n# ── REAL JPMORGAN FEED TESTLARI ───────────────────────────────────────────\nquotes = [\n    {'stock': 'ABC', 'top_bid': {'price': 120.48}, 'top_ask': {'price': 121.52}},\n    {'stock': 'DEF', 'top_bid': {'price': 118.20}, 'top_ask': {'price': 119.80}},\n    {'stock': 'GHI', 'top_bid': {'price': 0.00}, 'top_ask': {'price': 0.00}}\n]\n\nprices = {}\nfor q in quotes:\n    stock, bid, ask, price = getDataPoint(q)\n    prices[stock] = price\n    print(f'[{stock}] Bid: {bid:.2f} | Ask: {ask:.2f} | O\\'rtacha: {price:.2f}')\n\nratio_normal = getRatio(prices['ABC'], prices['DEF'])\nratio_zero = getRatio(prices['ABC'], prices['GHI'])\nprint(f'\\nHisoblangan ABC/DEF Ratio: {ratio_normal:.4f}')\nprint(f'Hisoblangan ABC/GHI Zero-Safe Ratio: {ratio_zero}')",
                    "mentor": "lead_engineer",
                    "rubric": [
                        {"criterion": "Nolga bo'lishdan (ZeroDivisionError) xavfsizlik va None tekshiruvi", "max_score": 50},
                        {"criterion": "O'rtacha narx (Mid-Price) arifmetik aniqligi", "max_score": 50}
                    ],
                    "model_answer": "from typing import Tuple, Optional, Dict, Any\n\ndef getDataPoint(quote: Dict[str, Any]) -> Tuple[str, float, float, float]:\n    stock = quote['stock']\n    bid_price = float(quote['top_bid']['price'])\n    ask_price = float(quote['top_ask']['price'])\n    price = (bid_price + ask_price) / 2.0\n    return stock, bid_price, ask_price, price\n\ndef getRatio(price_a: float, price_b: float) -> Optional[float]:\n    if not price_b or price_b == 0:\n        return None\n    return price_a / price_b",
                    "resources": {
                        "task_type": "code",
                        "supervisor": {
                            "name": "Alexandre Dubois",
                            "role": "Managing Director, Quantitative Technology",
                            "department": "JPMorgan Global Markets",
                            "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
                            "audio_duration": "1:45"
                        }
                    }
                }
            ]
        },

        # 2. Kapitalbank FinTech Cup 2026 (CASE CUP)
        {
            "slug": "kapitalbank-fintech-cup-2026",
            "title": "Kapitalbank FinTech Cup 2026 — 50,000,000 so'm sovrin jamg'armasi",
            "company": companies_map["Kapitalbank ATB"],
            "category": "Finance",
            "difficulty": "Intermediate",
            "estimated_hours": 6.0,
            "is_case_cup": True,
            "prize_pool": "50,000,000 UZS",
            "deadline": datetime(2026, 11, 30, 23, 59, 59),
            "description": "Kapitalbank ATB va O'zbekiston Markaziy Banki hamkorligidagi 1-Raqamli Respublika FinTech Case Cup chempionati! Talabalar real vaqtda Humo/Uzcard to'lov tranzaksiyalari tahlili, antiftod (firibgarlikni aniqlash) modellari va Open Banking API integratsiyasi bo'yicha kuch sinashadilar.",
            "learning_outcomes": [
                "Humo va Uzcard to'lov tizimlari oqimini real-vaqtda tahlil qilish",
                "Machine Learning asosida shubhali tranzaksiyalarni (Anti-Fraud) aniqlash",
                "O'zbekiston Markaziy Banki Open Banking API me'yorlari",
                "Bank Boshqaruvi va Investorlar oldida himoya qilish (Pitching)"
            ],
            "tasks": [
                {
                    "order": 1,
                    "title": "1-Bosqich: Shubhali Tranzaksiyalarni Aniqlash (Anti-Fraud Risk Engine)",
                    "briefing": "Kapitalbank FinTech Cup 1-bosqichiga xush kelibsiz! Har kuni bankimiz orqali 3 milliondan ortiq tranzaksiyalar o'tadi. Sizning vazifangiz — 3 ta xavf indikatori asosida shubhali to'lovlarni bloklash yoki qo'shimcha SMS-tasdiqqa yo'naltirish (2FA Trigger) algoritmik mantiqini ishlab chiqish.",
                    "instructions": "1. Bir daqiqada 3 dan ortiq to'lov qilingan bo'lsa: 'FLAG_VELOCITY_SUSPECT'.\n2. To'lov summasi mijozning o'rtacha tranzaksiyasidan 5 barobar yuqori bo'lsa: 'FLAG_AMOUNT_ANOMALY'.\n3. Xorijiy IP-manzil orqali kutilmagan kirish: 'FLAG_GEO_RISK'.\n4. Risk skoringi 70 dan oshsa: 'BLOCK_AND_ALERT'.",
                    "template": "from typing import Dict, Any\n\ndef evaluate_fraud_risk(transaction: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:\n    risk_score = 0\n    reasons = []\n    \n    amount = transaction.get('amount', 0)\n    avg_amount = user_profile.get('avg_amount', 100000)\n    if amount > avg_amount * 5:\n        risk_score += 40\n        reasons.append('High Amount Spike')\n        \n    if transaction.get('velocity_1min', 0) > 3:\n        risk_score += 35\n        reasons.append('Velocity Limit Exceeded')\n        \n    if transaction.get('country') != user_profile.get('home_country', 'UZ'):\n        risk_score += 30\n        reasons.append('Geo Location Mismatch')\n        \n    decision = 'ALLOW'\n    if risk_score >= 70:\n        decision = 'BLOCK_AND_ALERT'\n    elif risk_score >= 35:\n        decision = 'REQUIRE_SMS_OTP'\n        \n    return {'risk_score': risk_score, 'decision': decision, 'reasons': reasons}\n\n# Test Case\nsample_tx = {'amount': 15000000, 'velocity_1min': 4, 'country': 'TR'}\nsample_user = {'avg_amount': 200000, 'home_country': 'UZ'}\nprint(evaluate_fraud_risk(sample_tx, sample_user))",
                    "mentor": "chief_financial_officer",
                    "rubric": [
                        {"criterion": "Anti-fraud risk hisoblash mantig'i va to'liqligi", "max_score": 50},
                        {"criterion": "Edge-cases va noto'g'ri bloklanishlarning (False Positive) oldini olish", "max_score": 50}
                    ],
                    "model_answer": "Fraud baholash algoritmi 3 ta muhim parametrni (Spike, Velocity, Geo) hisobga oladi va xavfsizlik qarorini chiqaradi.",
                    "resources": {
                        "task_type": "code",
                        "supervisor": {
                            "name": "Kamola Rustamova",
                            "role": "Head of FinTech & Digital Products",
                            "department": "Kapitalbank FinTech Lab",
                            "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
                            "audio_duration": "2:15"
                        }
                    }
                },
                {
                    "order": 2,
                    "title": "2-Bosqich: FinTech Cup Bosh sovrini uchun Pitch Deck va Mahsulot Strategiyasi",
                    "briefing": "Final bosqichi! Kapitalbank Boshqaruvi va Hakamlar Hay'atiga yangi avlod FinTech mahsuloti (masalan, Talabalar uchun AI moliyaviy yordamchi yoki Kichik Biznes uchun avtomatik kassa) loyihasini taqdim eting.",
                    "instructions": "1. Muammo va Taklif etilayotgan yechimni yoriting.\n2. Bozor sig'imi (O'zbekiston yoshlari va KOB segmenti) va Monetizatsiya modelini tuzing.\n3. 1 yillik rivojlanish Roadmapini shakllantiring.",
                    "template": "KAPITALBANK FINTECH CUP 2026 PITCH PROPOSAL:\n1. Mahsulot Nomi: Kapital AI Junior Wallet\n2. Asosiy Qiymat: Talabalar uchun xarajatlarni avtomatik optimallashtiruvchi va cashback beruvchi aqlli hamyon.\n3. O'zbekiston Bozori: 3.5M talaba va o'quvchilar, yillik to'lov aylanmasi $1.2B.\n4. Monetizatsiya: Hamkor do'konlar komissiyasi (B2B) va Premium obunalar.\n5. Xavfsizlik: Markaziy Bank 2026 axborot xavfsizligi standartlariga 100% muvofiq.",
                    "mentor": "chief_financial_officer",
                    "rubric": [
                        {"criterion": "Mahsulotning bozorga mosligi (Product-Market Fit)", "max_score": 50},
                        {"criterion": "Moliyaviy rentabellik va innovatsion yondashuv", "max_score": 50}
                    ],
                    "model_answer": "Loyiha talabalar moliyaviy savodxonligini oshiradi va Kapitalbank uchun yosh sadoqatli mijozlar oqimini jalb qiladi.",
                    "resources": {
                        "task_type": "report",
                        "supervisor": {
                            "name": "Kamola Rustamova",
                            "role": "Head of FinTech",
                            "department": "Kapitalbank FinTech Lab",
                            "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
                            "audio_duration": "1:50"
                        }
                    }
                }
            ]
        },

        # 3. Uzum E-Commerce AI Challenge 2026 (CASE CUP)
        {
            "slug": "uzum-ecommerce-ai-cup-2026",
            "title": "Uzum E-Commerce AI Challenge 2026 — 30,000,000 so'm sovrin",
            "company": companies_map["Uzum Technologies"],
            "category": "Engineering",
            "difficulty": "Advanced",
            "estimated_hours": 6.0,
            "is_case_cup": True,
            "prize_pool": "30,000,000 UZS",
            "deadline": datetime(2026, 12, 15, 23, 59, 59),
            "description": "Uzum Technologies milliy AI chempionati! Siz Uzum Market uchun shaxsiy tavsiya algoritmi (Personalized Recommendation System), tovarlar talabini oldindan bashorat qilish (Demand Forecasting) va ombor logistikasini optimallashtirish masalalarini yechasiz.",
            "learning_outcomes": [
                "Katta hajmdagi elektron tijorat ma'lumotlarini tahlil qilish",
                "Collaborative Filtering va Embedding asosida tavsiya modellari",
                "1 kunda yetkazib berish (Next-Day Delivery) logistika optimallashtirish"
            ],
            "tasks": [
                {
                    "order": 1,
                    "title": "1-Bosqich: Uzum Market Tovarlar Tavsiya Qidiruv Algoritmi",
                    "briefing": "Uzum AI Challenge 1-bosqichiga xush kelibsiz! Xaridorning so'nggi 5 ta ko'rgan mahsulotlari asosida unga eng mos keluvchi 3 ta mahsulotni tavsiya qiluvchi kosinus o'xshashlik (Cosine Similarity) hisoblash funksiyasini yozing.",
                    "instructions": "1. Mahsulotlarning xususiyat vektorlarini solishtiring.\n2. Cosine similarity formulasini qo'llang.\n3. Eng yuqori ballga ega tovarlar ro'yxatini qaytaring.",
                    "template": "import math\nfrom typing import List, Tuple\n\ndef cosine_similarity(v1: List[float], v2: List[float]) -> float:\n    dot = sum(a * b for a, b in zip(v1, v2))\n    norm1 = math.sqrt(sum(a * a for a in v1))\n    norm2 = math.sqrt(sum(b * b for b in v2))\n    if norm1 == 0 or norm2 == 0:\n        return 0.0\n    return dot / (norm1 * norm2)\n\nprint('Vector Similarity:', cosine_similarity([1.0, 0.5, 0.2], [0.9, 0.4, 0.3]))",
                    "mentor": "lead_engineer",
                    "rubric": [
                        {"criterion": "Matematik va algoritmik to'g'rilik", "max_score": 50},
                        {"criterion": "Hisoblash tezligi va xotira samaradorligi", "max_score": 50}
                    ],
                    "model_answer": "Vektorlar o'xshashligi kosinus burchagi orqali aniq hisoblandi va tavsiyalar chiqarildi.",
                    "resources": {
                        "task_type": "code",
                        "supervisor": {
                            "name": "Jamshid Qodirov",
                            "role": "Staff AI Engineer",
                            "department": "Uzum AI Research Lab",
                            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
                            "audio_duration": "2:00"
                        }
                    }
                }
            ]
        },

        # 4. Kapitalbank ATB — Chakana Kredit Tahlili va Risk Skoringi
        {
            "slug": "kapitalbank-credit-analyst",
            "title": "Kapitalbank ATB — Chakana Kredit Tahlili va Risk Skoringi",
            "company": companies_map["Kapitalbank ATB"],
            "category": "Finance",
            "difficulty": "Beginner",
            "estimated_hours": 3.5,
            "is_case_cup": False,
            "prize_pool": None,
            "deadline": None,
            "description": "Kapitalbank Kredit departamentida amaliy ish simulyatsiyasi. Siz mijozlarning moliyaviy holatini tekshirasiz, O'zbekiston Markaziy Banki 3205-sonli nizomi asosida DTI (qarz yuki) ko'rsatkichini hisoblaysiz, garov ta'minotini (LTV) baholaysiz va Kredit Qo'mitasi uchun rasmiy qaror loyihasini tayyorlaysiz.",
            "learning_outcomes": [
                "Kredit arizalarini tahlil qilish va skoring tekshiruvi (KATM skoring)",
                "DTI (Debt-to-Income) va qarz yuklamasi hisob-kitobi (Markaziy Bank 50% chegarasi)",
                "Garov ta'minoti likvidligi va LTV (Loan-to-Value) tahlili",
                "Kredit qo'mitasi Boshqaruvi uchun rasmiy bayonnoma (Protocol) tuzish"
            ],
            "tasks": [
                {
                    "order": 1,
                    "title": "1-Bosqich: Mijozning Daromad va Qarz Yukini (DTI) Hisoblash",
                    "briefing": "Assalomu alaykum! Men Sardor Rahimov, Kapitalbank Chakana Kreditlash Departamenti Boshqaruvchisi. Mijoz Akromov Rustam 50,000,000 so'm kredit so'ramoqda. Oylik rasmiy daromadi: 8,000,000 so'm. Boshqa bankdagi mavjud avtokredit to'lovi: 2,100,000 so'm. Yangi kredit oylik to'lovi: 1,850,000 so'm. Markaziy Bankning 3205-sonli nizomiga ko'ra DTI ko'rsatkichini hisoblang va xulosa bering.",
                    "instructions": "1. Jami oylik to'lov: 2,100,000 + 1,850,000 = 3,950,000 so'm\n2. DTI = (3,950,000 / 8,000,000) * 100%\n3. Markaziy Bankning 50% lik maksimal chegarasiga muvofiqligini baholang va xulosa bering.",
                    "template": "KREDIT SKORING XULOSASI (Kapitalbank ATB):\n1. Mijoz: Akromov Rustam (STIR/JSHSHIR: 31204910020019)\n2. Rasmiy oylik daromad: 8,000,000 UZS\n3. Mavjud majburiyatlar: 2,100,000 UZS\n4. Yangi kredit to'lovi: 1,850,000 UZS\n5. Jami oylik yuklama: 3,950,000 UZS\n6. Hisoblangan DTI: 49.38%\n7. Markaziy Bank talabiga moslik: To'liq mos (50% dan past)\n8. Yakuniy Xulosa: Kredit ajratish tavsiya etiladi.",
                    "mentor": "chief_financial_officer",
                    "rubric": [
                        {"criterion": "DTI hisob-kitobining to'g'riligi (49.38%)", "max_score": 50},
                        {"criterion": "O'zbekiston Markaziy Banki me'yorlariga rioya qilish va xulosa", "max_score": 50}
                    ],
                    "model_answer": "Jami oylik kredit to'lovlari: 3,950,000 so'm. Rasmiy daromad: 8,000,000 so'm. DTI = (3,950,000 / 8,000,000) * 100 = 49.38%. Ko'rsatkich 50% chegarasidan oshmagan, mijozning to'lov qobiliyati yetarli.",
                    "resources": {
                        "task_type": "report",
                        "supervisor": {
                            "name": "Sardor Rahimov",
                            "role": "Head of Retail Lending & Risk Underwriting",
                            "department": "Kapitalbank ATB Bosh Ofisi",
                            "avatar": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=150&auto=format&fit=crop&q=80",
                            "audio_duration": "1:35"
                        }
                    }
                }
            ]
        },

        # 5. Goldman Sachs — Kiberxavfsizlik va Kriptografiya
        {
            "slug": "goldman-sachs-cybersecurity",
            "title": "Goldman Sachs — Kiberxavfsizlik va Kriptografiya",
            "company": companies_map["Goldman Sachs"],
            "category": "Engineering",
            "difficulty": "Advanced",
            "estimated_hours": 4.5,
            "is_case_cup": False,
            "prize_pool": None,
            "deadline": None,
            "description": "Goldman Sachs axborot xavfsizligi jamoasida amaliyot. Siz parollar bazasidagi sizib chiqishlarni tahlil qilasiz, Rainbow Table hujumlariga qarshi xesh algoritmlarini kuchaytirasiz va korporativ autentifikatsiya xavfsizligi bo'yicha tavsiyalar berasiz.",
            "learning_outcomes": [
                "Kriptografik xeshlash algoritmlari (SHA-256, Bcrypt, Argon2)",
                "Rainbow Table va Dictionary hujumlarining oldini olish",
                "Bank darajasidagi xavfsiz parollar arxitekturasi"
            ],
            "tasks": [
                {
                    "order": 1,
                    "title": "1-Bosqich: Sizib Chiqqan MD5 Parollar Tahlili va Xavf Hisoboti",
                    "briefing": "Xush kelibsiz! Men Marcus Vance, Goldman Sachs Cyber Defense Operations Leadiman. Eski ichki tizimlarning birida MD5 xeshlash ishlatilgani aniqlandi. Boshqaruv va xavfsizlik qo'mitasiga Rainbow Table xavflari hamda Argon2id/PBKDF2 ga o'tish bo'yicha professional hisobot tayyorlang.",
                    "instructions": "1. MD5 to'qnashuvlari (collisions) va Rainbow Table hujumi haqida tushuntiring.\n2. Parollarga Salt va Pepper qo'shish mexanizmini yoriting.\n3. PBKDF2 / Argon2id ga o'tish bo'yicha 3 ta amaliy qadam taklif qiling.",
                    "template": "XAVFSIZLIK HISOBOTI (Goldman Sachs Cyber Defense):\n1. Zaiflik Tahlili: MD5 kriptografik jihatdan butkul eskirgan va to'qnashuvlarga moyil.\n2. Hujum Xatarlari: Rainbow Table va GPU brute-force orqali 8-10 belgili parollar soniyalar ichida ochiladi.\n3. Himoya Strategiyasi:\n   - Har bir parol uchun 16-baytli tasodifiy Salt generatsiya qilish;\n   - Argon2id yoki PBKDF2 (kamida 100,000 iteratsiya) standartiga o'tish;\n   - Ikki bosqichli autentifikatsiya (MFA/FIDO2) talabini kiritish.",
                    "mentor": "lead_engineer",
                    "rubric": [
                        {"criterion": "Kriptografik zaifliklarni aniq tushuntirish", "max_score": 50},
                        {"criterion": "Salt va Peppering arxitekturasi", "max_score": 50}
                    ],
                    "model_answer": "MD5 va oddiy SHA-1 banklarda mutlaqo taqiqlangan. Chunki zamonaviy GPU klasterlar soniyasiga milliardlab MD5 xeshlarini hisoblash quvvatiga ega.",
                    "resources": {
                        "task_type": "report",
                        "supervisor": {
                            "name": "Marcus Vance",
                            "role": "Vice President, Information Security",
                            "department": "Goldman Sachs Global Cyber Defense",
                            "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
                            "audio_duration": "2:05"
                        }
                    }
                }
            ]
        },

        # 6. BCG — Bozor Strategiyasi va Unit-Ekonomika
        {
            "slug": "bcg-strategy-consulting",
            "title": "BCG (Boston Consulting Group) — Bozor Strategiyasi va Unit-Ekonomika",
            "company": companies_map["BCG (Boston Consulting Group)"],
            "category": "Analytics",
            "difficulty": "Advanced",
            "estimated_hours": 4.5,
            "is_case_cup": False,
            "prize_pool": None,
            "deadline": None,
            "description": "BCG strategik loyihasida Management Consultant sifatida amaliyot. Siz Markaziy Osiyo elektron tijorat bozorini tahlil qilasiz, yangi bozorga kirish strategiyasini (Market Entry) tuzasiz va Unit Economics hisobini amalga oshirasiz.",
            "learning_outcomes": [
                "Bozor hajmini baholash (TAM, SAM, SOM tahlili)",
                "Unit Economics (CAC, LTV, Payback period) hisob-kitobi",
                "Boshqaruv va investorlar uchun strategik Memorandum tayyorlash"
            ],
            "tasks": [
                {
                    "order": 1,
                    "title": "1-Bosqich: O'zbekiston E-Commerce Bozoriga Kirish Memorandumi",
                    "briefing": "Assalomu alaykum! Men Kamilla Xasanova, BCG Toshkent ofisi Project Leaderiman. Xalqaro riteyler O'zbekiston bozoriga kirishni rejalashtirmoqda. Bozor sig'imi (TAM $1.8B, SAM $650M), raqobatchilar tahlili va eng optimal kirish modelini o'z ichiga olgan strategik memorandum tayyorlang.",
                    "instructions": "1. Bozor hajmi va yillik o'sish sur'atini (CAGR 35%) tahlil qiling.\n2. 3 ta kirish yo'lini solishtiring (Mustaqil qurish, M&A - sotib olish, Franchayzing).\n3. BCG tavsiyasini shakllantiring.",
                    "template": "STRATEGIC MARKET ENTRY MEMO (BCG Central Asia):\n1. Bozor Sig'imi: O'zbekiston E-Commerce TAM = $1.8B, SAM = $650M, SOM = $90M.\n2. Raqobat Muhiti: Uzum Market, Express yetkazib berish xizmatlari.\n3. Tavsiya Etilayotgan Model: Mahalliy logistika operatori bilan qo'shma korxona (Joint Venture) tuzish.\n4. Moliyaviy Prognoz: 2-yilda operatsion rentabellik (Break-even).",
                    "mentor": "chief_financial_officer",
                    "rubric": [
                        {"criterion": "Bozor tahlili va raqobat ustunliklari", "max_score": 50},
                        {"criterion": "Strategik asos va konsalting xulosasi", "max_score": 50}
                    ],
                    "model_answer": "BCG tahlili ko'rsatadiki, O'zbekiston elektron tijorati yiliga 35% dan ortiq o'smoqda.",
                    "resources": {
                        "task_type": "report",
                        "supervisor": {
                            "name": "Kamilla Xasanova",
                            "role": "Project Leader",
                            "department": "BCG Central Asia",
                            "avatar": "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150&auto=format&fit=crop&q=80",
                            "audio_duration": "2:30"
                        }
                    }
                }
            ]
        }
    ]

    # Simulyatsiyalarni bazada yangilash
    sim_objects = {}
    for s_info in simulations_data:
        sim = db.query(Simulation).filter_by(slug=s_info["slug"]).first()
        if not sim:
            sim = Simulation(
                slug=s_info["slug"],
                title=s_info["title"],
                company_id=s_info["company"].id,
                category=s_info["category"],
                difficulty=s_info["difficulty"],
                estimated_hours=s_info["estimated_hours"],
                description=s_info["description"],
                learning_outcomes=s_info["learning_outcomes"],
                is_case_cup=s_info.get("is_case_cup", False),
                prize_pool=s_info.get("prize_pool"),
                deadline=s_info.get("deadline")
            )
            db.add(sim)
            db.flush()
        else:
            sim.title = s_info["title"]
            sim.description = s_info["description"]
            sim.learning_outcomes = s_info["learning_outcomes"]
            sim.category = s_info["category"]
            sim.difficulty = s_info["difficulty"]
            sim.estimated_hours = s_info["estimated_hours"]
            sim.is_case_cup = s_info.get("is_case_cup", False)
            sim.prize_pool = s_info.get("prize_pool")
            sim.deadline = s_info.get("deadline")
            db.flush()

        sim_objects[s_info["slug"]] = sim

        # Eski tasklarni tozalab, yangi The Forage tasklarini qo'shish
        db.query(SimulationTask).filter_by(simulation_id=sim.id).delete()
        for t_info in s_info["tasks"]:
            task = SimulationTask(
                simulation_id=sim.id,
                order=t_info["order"],
                title=t_info["title"],
                briefing_text=t_info["briefing"],
                instructions=t_info["instructions"],
                template_data=t_info["template"],
                mentor_persona=t_info["mentor"],
                rubric_criteria=t_info["rubric"],
                model_answer=t_info["model_answer"],
                resource_files=t_info.get("resources", {})
            )
            db.add(task)

    # ── 5. Case Cup Leaderboard Initial Records ────────────────────────────────
    kapital_cup = sim_objects.get("kapitalbank-fintech-cup-2026")
    if kapital_cup:
        db.query(CaseCupLeaderboard).filter_by(simulation_id=kapital_cup.id).delete()
        
        baxrom = users_map.get("student@tryjob.uz")
        aziza = users_map.get("aziza@wiut.uz")
        jasur = users_map.get("jasur@iut.uz")

        if baxrom:
            db.add(CaseCupLeaderboard(
                simulation_id=kapital_cup.id,
                user_id=baxrom.id,
                total_score=96.5,
                rank=1,
                submitted_at=datetime.now(timezone.utc) - timedelta(hours=3)
            ))
        if aziza:
            db.add(CaseCupLeaderboard(
                simulation_id=kapital_cup.id,
                user_id=aziza.id,
                total_score=94.0,
                rank=2,
                submitted_at=datetime.now(timezone.utc) - timedelta(hours=5)
            ))
        if jasur:
            db.add(CaseCupLeaderboard(
                simulation_id=kapital_cup.id,
                user_id=jasur.id,
                total_score=89.5,
                rank=3,
                submitted_at=datetime.now(timezone.utc) - timedelta(hours=10)
            ))

    # ── 6. Talent Offers (HR Direct Sourcing) ──────────────────────────────────
    kapital_comp = companies_map.get("Kapitalbank ATB")
    baxrom = users_map.get("student@tryjob.uz")
    if kapital_comp and baxrom:
        existing_offer = db.query(TalentOffer).filter_by(candidate_id=baxrom.id, company_id=kapital_comp.id).first()
        if not existing_offer:
            offer = TalentOffer(
                company_id=kapital_comp.id,
                candidate_id=baxrom.id,
                simulation_id=kapital_cup.id if kapital_cup else None,
                position_title="Junior FinTech Analyst / Quant Developer",
                message="Tabriklaymiz! Sizning FinTech simulyatsiyasidagi 96.5% natijangiz Kapitalbank Risk Management departamenti tomonidan yuqori baholandi. Sizni to'g'ridan-to'g'ri yakuniy intervyuga taklif etamiz.",
                status="sent"
            )
            db.add(offer)

    # ── 7. Transactions (VIP obunalar) ─────────────────────────────────────────
    if baxrom:
        existing_tx = db.query(Transaction).filter_by(user_id=baxrom.id).first()
        if not existing_tx:
            tx = Transaction(
                user_id=baxrom.id,
                amount=99000.0,
                provider="click",
                status="completed",
                plan_type="vip_monthly"
            )
            db.add(tx)

    # ── 8. Demo Submissions va Certificates (Dean va Talent Hunt uchun) ─────────
    if baxrom and kapital_cup:
        # Submission
        first_task = db.query(SimulationTask).filter_by(simulation_id=kapital_cup.id, order=1).first()
        if first_task:
            sub = db.query(Submission).filter_by(user_id=baxrom.id, task_id=first_task.id).first()
            if not sub:
                sub = Submission(
                    user_id=baxrom.id,
                    simulation_id=kapital_cup.id,
                    task_id=first_task.id,
                    submitted_text="Anti-fraud risk baholash algoritmi to'liq ishlab chiqildi va test qilindi.",
                    status="passed",
                    score=96.5,
                    ai_feedback={
                        "total_score": 96.5,
                        "passed": True,
                        "mentor_name": "Kamola Rustamova",
                        "mentor_role": "Head of FinTech & Digital Products",
                        "executive_summary": "Mukammal kod arxitekturasi va risk baholash mantig'i!"
                    }
                )
                db.add(sub)

    db.commit()
    print("✅ TryJob platformasi (Universitetlar, Case Cup, Talent Hunt, Billing va VIP) ma'lumotlari bazaga 100% muvaffaqiyatli yuklandi!")
