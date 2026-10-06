# TryJob — Arxitektura Shartnomasi (v1)

> Bu hujjat — loyihani noldan qayta qurish uchun yagona haqiqat manbai.
> Har qanday AI agent / developer shu faylga zid ish qilmasligi kerak.
> O'zgartirish kerak bo'lsa — avval shu faylni yangilang, keyin kodga qo'l tegizing.

Status: **FROZEN for v1 pilot** — kelishilgan, 7 raundli arxitektura muhokamasi asosida.
Oldingi kod (`app/`, `frontend/`) `0e4be5e` commitida saqlangan, to'liq wipe qilinadi.

---

## 1. Missiya va qamrov

**Nima qiladi:** O'zbekiston talabalari uchun AI-mentor baholaydigan virtual ish
simulyatsiyalari platformasi (The Forage'ning mahalliy, chuqur integratsiyalangan
versiyasi) — B2B2C model: talaba bepul, universitet va kompaniya pul to'laydi.

**V1 pilot qamrovi:**
- Faqat **2 soha**: IT/Dasturlash va Bank/Moliya. Boshqa sohalar (Legal, Audit,
  Consulting) kod/sxema darajasida bloklanmaydi, lekin kontent yaratilmaydi.
- 4 modul **strukturaviy jihatdan** v1'da bor (quyida tartib bilan quriladi),
  lekin kontent faqat yuqoridagi 2 soha bilan cheklanadi.

**Aniq Non-goals (v1'da QILINMAYDI):**
- Click/Payme orqali B2B (universitet/kompaniya) to'lovi — faqat admin invoice.
- Real-time AI bilan topshiriq generatsiyasi (Infinite Engine v1 = katalog + AI aralashtirish).
- To'liq LinkedIn-darajasidagi maxfiylik sozlamalari (faqat sodda toggle + exclude-list).
- "Ish taklifi kafolati" — faqat "intervyu/ko'rib chiqish kafolati" (SLA).
- Real kompaniya nomi/brendi (JPMorgan, PwC, Uzum va h.k.) — barchasi fictional bo'ladi.

---

## 2. Repo tuzilishi (top-level)

Backend, frontend va deploy konfiguratsiyasi **alohida, aniq ajratilgan**
top-level papkalarda yashaydi — eski holatdagi kabi backend kodi
(`app/`) to'g'ridan-to'g'ri repo root'ida bo'lmaydi:

```
/
├── backend/
│   ├── app/
│   │   ├── core/          # auth, security, sandbox, file_validator, rbac deps
│   │   ├── models/        # SQLAlchemy models (bitta models.py emas, bo'lingan)
│   │   ├── api/           # routerlar (modul bo'yicha, §5)
│   │   └── ai/            # AI router, guardrail, personas
│   ├── alembic/
│   ├── tests/
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── deploy/
│   ├── docker-compose.yml
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   └── nginx.conf
├── tools/                  # ichki skriptlar, seed/migration CLI, dev-tooling
└── docs/
    └── CONTRACT.md         # ushbu fayl
```

Qoida: har bir yangi **platforma/qatlam** (masalan kelajakda `mobile/`
yoki `desktop/` qo'shilsa) o'z alohida top-level papkasida ochiladi —
mavjud papkalarning ichiga singdirilmaydi. **Hozir mobil/desktop rejada
umuman yo'q** — ularga placeholder/bo'sh papka ham ochilmaydi, faqat
kerak bo'lgan kunda yangi top-level papka sifatida qo'shiladi. Asosiy
skelet faqat yuqoridagi 5 papka (`backend`, `frontend`, `deploy`, `tools`,
`docs`) bilan cheklanadi.

Quyidagi §6 jadvalidagi barcha yo'llar shu tuzilishga nisbatan o'qiladi
(masalan "Core & Auth" moduli → `backend/app/core/`, `backend/app/models/user.py`).

---

## 3. Texnologik stack qarorlari

| Qatlam | Tanlov | Izoh |
|---|---|---|
| Backend | FastAPI (async), SQLAlchemy 2.0, Alembic | Saqlanadi |
| Auth/JWT | `python-jose[cryptography]` | Qo'lda yozilgan HMAC JWT olib tashlanadi |
| Parol hash | `passlib[bcrypt]` | Statik-salt PBKDF2 olib tashlanadi, per-hash random salt |
| DB (dev va prod) | **PostgreSQL — yagona**, SQLite UMUMAN ishlatilmaydi | Foydalanuvchi talabi: loyiha to'liq psql ustida, hech qanday SQLite fallback/dev-shortcut yo'q |
| Cache/Queue | Redis + `arq` | **Yangi**: rate-limiting + AI retry queue uchun real ishlatiladi |
| Frontend | React + TypeScript + shadcn/ui | Eski Jinja2 + eski React (mock-auth) butunlay o'chiriladi |
| Admin panel | Shu React ilova ichida, `role`-gated route | Alohida tool YO'Q |

### 3.1 Testlarda ham PostgreSQL (SQLite emas)

`backend/tests/conftest.py` (Modul 1 egalik qiladi) test uchun **alohida
PostgreSQL database** ishlatadi (masalan `tryjob_test`, `deploy/docker-
compose.yml`dagi `postgres` servisida), har test funksiyasidan keyin
tranzaksiya rollback qilinadi yoki test boshida schema qayta yaratiladi.
`DATABASE_URL` test uchun `.env.test` yoki muhit o'zgaruvchisi orqali
beriladi — **hech qanday joyda** `sqlite://` qatori yozilmasin
(`grep -rn "sqlite" backend/` natijasi bo'sh bo'lishi shart).

---

## 4. RBAC — Rol va ruxsatlar modeli

Oddiy `role` string tekshiruvi EMAS. To'liq permission-based:

```
roles           (id, name)                         -- "student", "company_hr", "university_admin", "admin", ...
permissions     (id, key)                           -- "manage_billing", "approve_companies", "view_candidates", ...
role_permissions(role_id, permission_id)             -- many-to-many
users.role_id   -> roles.id
```

- Yangi rol = yangi DB yozuvi, kodga tegilmaydi.
- Endpoint darajasida: `require_permission("approve_companies")` kabi dependency,
  `if current_user.role == "admin"` kabi inline tekshiruv **taqiqlangan**.
- Boshlang'ich rollar: `student`, `company_hr`, `university_admin`, `admin`.
- `Company.is_verified` va (yangi) `University.is_verified` default **`False`**
  — admin tasdiqlamaguncha pullik funksiyalar yopiq.

---

## 5. Asosiy ma'lumotlar modeli (yangi/o'zgargan)

Mavjud modeldan (eski `app/models.py`) qayta ishlatiladigan narsa: umumiy shakl
(UUID PK, FK relationship g'oyasi). Quyidagilar **yangi yoki tubdan o'zgargan**:

- `roles`, `permissions`, `role_permissions` — §3.
- `companies.is_verified` — default `False`, `verified_at`, `verified_by_admin_id`.
- `universities.is_verified` — default `False` (yangi ustun), `verified_at`.
- `invoices` (**yangi**, Click/Payme webhook'larining o'rnini bosadi B2B uchun):
  `id, payer_type(company|university), payer_id, amount, currency, status(pending|paid|cancelled), issued_by_admin_id, paid_marked_at, notes`.
- `candidate_visibility` (**yangi**, LinkedIn-sodda versiya):
  `user_id, is_open_to_work(bool, default False), hidden_from_company_ids(JSON array)`.
  — **Default: yopiq (opt-in).** Avtomatik ko'rinish YO'Q.
- `talent_offers` — saqlanadi, lekin faqat `is_open_to_work=True` bo'lgan va
  `hidden_from_company_ids`da yo'q kandidatlar ro'yxatda chiqadi.
- `submissions.ai_eval_status` (**yangi**): `completed|queued_retry|failed_permanent`
  — Cloud AI muvaffaqiyatsiz bo'lganda `queued_retry`, `arq` job orqali qayta ishlanadi.
- Sandbox/AI endpointlar uchun `rate_limit_log` jadval kerak emas — Redis'da
  key-based counter (`sandbox:{user_id}:{minute}`) sifatida, DB'ga yozilmaydi.

**Olib tashlanadi:** qo'lda JWT payload ichida token_type yuritish mantiqi
(endi `python-jose` standart claim'lari bilan), real kompaniya nomlari (seed
data fictional nomlarga almashtiriladi: masalan "Kapitalbank" → "NorthBank UZ",
"Uzum" → "Elon Market", "JPMorgan" → "Atlas Global Finance").

---

## 6. Modul chegaralari va qurish tartibi (parallel agentlar uchun)

Har bir modul **o'z fayllariga** tegadi, boshqa modulning faylini
**o'zgartirmaydi** — faqat shu shartnomada yozilgan interfeys (Pydantic
schema / endpoint shakli) orqali gaplashadi.

| # | Modul | Egalik qiladigan papkalar | Bog'liqligi |
|---|---|---|---|
| 1 | **Core & Auth & RBAC** | `backend/app/core/`, `backend/app/models/user.py`, `backend/app/models/rbac.py`, `backend/app/api/auth.py` | Yo'q (birinchi quriladi) |
| 2 | **Simulations & AI Mentor** | `backend/app/models/simulation.py`, `backend/app/api/simulations.py`, `backend/app/api/submissions.py`, `backend/app/ai/` | (1)ga bog'liq |
| 3 | **Billing & Admin approval** | `backend/app/models/billing.py`, `backend/app/api/billing.py`, `backend/app/api/admin.py` | (1)ga bog'liq |
| 4 | **Talent Hunt** | `backend/app/models/talent.py`, `backend/app/api/talent_hunt.py` | (1),(2),(3)ga bog'liq (ball/visibility kerak) |
| 5 | **Case Cup** | `backend/app/api/case_cups.py` | (1),(2)ga bog'liq |
| 6 | **University Portal** | `backend/app/api/university_portal.py` | (1),(2),(3)ga bog'liq |
| 7 | **Frontend (React+shadcn)** | `frontend/` | Har modul backend API'si tayyor bo'lgach, mos ekranlar — vertical slice, lekin alohida agent/task |
| 8 | **Deploy** | `deploy/` | Docker-compose, nginx, Dockerfile'lar — backend/frontend tuzilishi barqarorlashgach yangilanadi |

Qurish ketma-ketligi: **1 → (2,3 parallel) → (4,5,6 parallel) → 7 har
bosqichda mos ravishda**.

Har modul uchun agentga beriladigan task: shu jadvaldagi papkalar + ushbu
shartnomaning tegishli bo'limi. Boshqa modul faylini o'zgartirish kerak
bo'lib qolsa — bu "shartnoma to'liq emas" degani, avval shartnoma yangilanadi.

### 6.1 Umumiy fayllarga to'qnashuvni oldini olish

`backend/app/main.py`, `backend/app/config.py`, `backend/app/database.py`,
`backend/tests/conftest.py` — faqat **Modul 1** egalik qiladi va bir marta
yozadi. Boshqa modullar bu fayllarga **hech qachon** tegmaydi. Buning
o'rniga:

- `main.py` har bir `backend/app/api/*.py` faylidagi `router` obyektini
  **avtomatik topib** ulaydi (`pkgutil`/`importlib` orqali papkani skanerlash) —
  yangi modul `app/api/` ichiga yangi fayl qo'yadi, `main.py`ga qo'l tegmaydi.
- Har bir modul o'z Pydantic schemalarini **o'z API faylida yoki
  `app/api/<modul>_schemas.py`da** saqlaydi — umumiy `schemas.py` yo'q.
- Testlar: `conftest.py`dagi umumiy fixture'lardan (`client`, `db_session`,
  `test_user_factory`) foydalaniladi, lekin uni o'zgartirmaydi; har modul
  faqat o'zining `backend/tests/test_<modul>.py` faylini yozadi.

---

## 7. API sirtlari (yuqori darajada, implementatsiya tafsilotisiz)

```
POST   /api/v1/auth/register              student only self-serve
POST   /api/v1/auth/register-org          company_hr | university_admin -> is_verified=False
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh

GET    /api/v1/simulations
POST   /api/v1/submissions                -> AI eval, Redis/arq fallback on failure
GET    /api/v1/submissions/{id}

POST   /api/v1/admin/orgs/{id}/approve    permission: approve_companies
POST   /api/v1/admin/invoices             permission: manage_billing (create)
POST   /api/v1/admin/invoices/{id}/mark-paid

PATCH  /api/v1/users/me/visibility        { is_open_to_work, hidden_from_company_ids }
GET    /api/v1/talents                    only is_verified company + only visible candidates
POST   /api/v1/talents/offers             counts against subscription's "interview SLA" commitment
```

---

## 8. Keyingi qadam

Ushbu fayl tasdiqlangandan so'ng: eski `app/`, `frontend/`, `docker*`,
`alembic/`, `requirements.txt` kabi root-level fayllar o'chiriladi (git
tarixida — `0e4be5e` — saqlanadi) va yangi `backend/`, `frontend/`, `deploy/`
tuzilishi §2 bo'yicha yaratiladi. Shundan keyin §6 jadvaliga asoslanib
har modul uchun alohida agent task yoziladi.
