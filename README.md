# 🚀 Train — O'zbekiston Talabalari Uchun Virtual Ish Simulyatsiyalari Platformasi

> **The Forage platformasining O'zbekiston bozori uchun to'liq milliy alternativi.**  
> Talabalar ishga kirishdan oldin O'zbekistonning yetakchi banklari, IT kompaniyalari va konsalting agentliklarining real korporativ vazifalarini bajarib, tajriba orttiradi, AI mentorlardan tahliliy baho oladi va kriptografik QR-sertifikatga ega bo'ladi.

---

## 🌟 Asosiy Imkoniyatlar

1. **🏢 Haqiqiy Korporativ Simulyatsiyalar:**
   - **Kapitalbank ATB:** Kredit scoring, mijoz qarz yuklamasi (DTI) hisob-kitobi va bank kredit qo'mitasi uchun xulosa tayyorlash.
   - **Uzum Technologies:** Savatdagi chegirmalar biznes mantig'ini tuzatish, SQL injection himoyasi va xavfsiz REST API.
   - **Toshkent Audit & Legal:** Korporativ shartnomalar auditi va elektron hisob-fakturalar (Didox) bilan ishlash.

2. **🧠 Multi-Model Cloud AI Mentorlik:**
   - **DeepSeek (R1/V3) & Gemini:** Talabaning kod va hisobotlarini chuqur mantiqiy tahlil qilish (Reasoning).
   - **4 ta Ixtisoslashgan Mentor:** Bosh Dasturchi (Tech Lead), Bosh Moliyachi (CFO), Yurist (Legal) va HR Direktor.
   - **Strukturaviy Baholash:** 0-100% rubrika, yutuqlar, xatolar va «Kompaniya standarti (Best Practice)» maslahatlari.

3. **📜 Kriptografik Tasdiqlangan QR Sertifikat:**
   - Har bir bitiruvchiga `HMAC-SHA256` orqali imzolangan unikal sertifikat (`UZ-TRN-XXXXXX`).
   - HR va ish beruvchilar uchun ochiq tekshiruv havolasi: `/verify/{cert_uuid}`.

4. **🔒 Qat'iy Xavfsizlik va Anti-Hallucination:**
   - Prompt Injection ga qarshi `AI Guardrail` filtri.
   - Magic bytes va MIME-type asosidagi xavfsiz fayl yuklash tizimi (`SafeFileValidator`).
   - IDOR / BOLA himoyasi va UUIDv4 identifikatorlar.

---

## 🛠 Texnologik Stack

- **Backend:** FastAPI (Python 3.10+ async), SQLAlchemy 2.0 ORM, SQLite / PostgreSQL.
- **Xavfsizlik:** PBKDF2 Hashing, HS256 JWT Tokens, HMAC-SHA256 Signatures, HTML Sanitizer.
- **AI Integratsiya:** DeepSeek API, Google Gemini API, OpenAI API, Smart Rule Engine.
- **Frontend:** Responsive SPA (Tailwind CSS, Jinja2, Lucide Icons, Vanilla JS).
- **Testlash:** Pytest, TestClient, AST Code Validator.

---

## 🚀 Ishga Tushirish

### 1. Bog'liqliklarni o'rnatish:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Serverni ishga tushirish:
```bash
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Brauzerda oching: **`http://127.0.0.1:8000`**

### 3. API Hujjatlari (Swagger / OpenAPI):
- **Interactive API Docs:** `http://127.0.0.1:8000/docs`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

### 4. Testlarni ishga tushirish:
```bash
pytest tests/ -v
```

---

## 🏛️ Kengash (Council) & Definition of Done

- **DoD Mezonlari:**
  - ✅ Bosh Arxitektor tasdiqi (RFC-002: Modular Clean Architecture)
  - ✅ Xavfsizlik Auditi (MIME magic bytes, Prompt injection guardrail, HMAC certs)
  - ✅ Biznes va Bozor validatsiyasi (O'zbekiston bank/IT/Legal simulyatsiyalari)
  - ✅ 100% Sintaktik va Unit testlar muvaffaqiyati
  - ✅ Zero Critical Vulnerabilities
