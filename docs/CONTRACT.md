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
- Simulyatsiyalar — **real vaqtdagi "ishdagi kun/hafta" ssenariylari**
  (§9), oddiy topshiriqlar ro'yxati emas.

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
| Vektor qidiruv (RAG) | `pgvector` (PostgreSQL extension) | §9.4 — alohida vektor DB YO'Q, Postgres yagona DB qoidasi saqlanadi |
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
| 9 | **Scenario Engine** | §9.10 ro'yxati (`backend/app/scenario/`, `models/scenario.py`, `api/scenarios.py`, `api/runs.py`, `api/files.py`, `backend/content/scenarios/`, `tools/import_scenario.py`) | (1),(2) interfeyslari — §9.10 |

Qurish ketma-ketligi: **1 → (2,3 parallel) → (4,5,6 parallel) → 7 har
bosqichda mos ravishda**. Modul 9: avval (1),(2),(8)dagi §9.10
interfeyslari qo'shiladi, keyin dvigatelning o'zi.

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

GET    /api/v1/simulations                (LEGACY — muzlatilgan, §9)
POST   /api/v1/submissions                (LEGACY) -> AI eval, Redis/arq fallback on failure
GET    /api/v1/submissions/{id}

# Ssenariy dvigateli (scenarios, runs, chat, files) — to'liq ro'yxat §9.9

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

---

## 9. Ssenariy dvigateli — "ishdagi kun/hafta" simulyatsiyasi

> Holat: **kelishilgan (2026-10-07), Modul 9 uchun asos.** Eski
> "topshiriqlar ro'yxati" (`simulations` → `simulation_tasks`) o'rnini
> egallaydi. Talaba real kompaniyadagidek ishlaydi: ertalab 09:00 da
> boshlaydi, kun davomida task, xabar, muammoli holat va o'zgarishlar
> real vaqtda kelib turadi.

### 9.0 Qabul qilingan qarorlar

| # | Savol | Qaror |
|---|---|---|
| Q1 | Vaqt | **Real vaqt, pauza YO'Q.** Talaba sahifani yopsa ham soat yuradi, hodisalar inbox'da to'planadi, dedlaynlar o'tib ketaveradi — real ishdagidek |
| Q2 | Eski `simulations` | **Almashtiriladi.** `simulations`/`simulation_tasks` muzlatiladi (yangi kontent yo'q), `submissions` umumiy javob jadvali bo'lib qoladi (§9.7) |
| Q3 | Personaj xabarlari | **Aralash:** ssenariyda yozilgan (skript) xabarlar + talaba yozganda AI javobi, **RAG** bilan, javobni oshkor qilmaydigan qilib (§9.4) |
| Q4 | Chat media | v1: `text`, `file`, `link`. v2: `voice`, `image`, `video` (§9.5) |
| Q5 | Davomiylik / uzilish | Kunlik (1 kun) va haftalik (5 ish kuni). 7 kun faollik bo'lmasa yoki muddat tugasa — Run **yonadi** (`expired`) |
| Q6 | Baholash vaqti | Har task'dan keyin **qisqa feedback** + har kun oxirida **kunlik hisobot** + Run oxirida **yakuniy hisobot** |
| Q7 | Branching | Sxema **daraxt** (shartli tugunlar), lekin v1 dvigateli faqat cheklangan shartlar to'plamini qo'llaydi (§9.3.3) |

### 9.1 Asosiy tushunchalar

- **Scenario** — "Elon Market'da Junior Backend, 1 kun" kabi katalog yozuvi.
- **ScenarioVersion** — ssenariyning e'lon qilingan (published) **o'zgarmas**
  nusxasi. Run har doim aniq versiyaga bog'lanadi — kontent tahriri
  yurib turgan Run'larni buzmaydi.
- **Node** — ssenariy daraxtidagi tugun (xabar, task, qaror, incident, kun
  yakuni). Vaqti va (ixtiyoriy) sharti bor.
- **Persona** — ssenariy ichidagi o'ylab topilgan shaxs (rahbar, hamkasb,
  mijoz, mentor). Real odam emas, real brend emas.
- **Run** — talabaning bitta ssenariyni o'tishi.
- **RunEvent** — Run ichida aniq bir Node'ning taqdiri: qachon yetkazildi,
  dedlayn, holat, natija.

### 9.2 Vaqt modeli — real vaqt

- Vaqt zonasi: **`Asia/Tashkent`**. Ish vaqti: dushanba–juma, 09:00–18:00.
- Talaba Run yaratganda **boshlanish sanasini** tanlaydi; Run shu ish
  kunining **09:00** da boshlanadi (`status=scheduled` → `active`).
- Node vaqti: `day` (1..`duration_days`, ish kunlari bo'yicha; dam olish
  kunlari o'tkazib yuboriladi) + `at` (`"HH:MM"`). Yoki nisbiy:
  `after: {node, event: delivered|submitted, minutes}`.
- Dedlayn: `due_in_minutes` — **ish daqiqalarida**. 18:00 dan oshsa,
  keyingi ish kuni 09:00 dan davom etadi (masalan 17:30 + 60 daq = ertasi 09:30).
- **Pauza yo'q.** `compression_ratio` ham yo'q (v1'dan olib tashlandi) — 1
  simulyatsiya soati = 1 real soat.
- Ssenariy darajasidagi parametr: `duration_days` (1 = kunlik, 5 = haftalik).
- **Muddat tugashi (`expired`):**
  - `last_activity_at`dan 7 kalendar kun o'tsa, yoki
  - oxirgi ish kuni + 2 ish kuni o'tsa.
  Yongan Run uchun bajarilgan qism bo'yicha yakuniy hisobot "tugallanmagan"
  belgisi bilan yoziladi, sertifikat berilmaydi. Talaba yangi Run ochishi mumkin.
- Dedlayni o'tgan task → `missed`. Bu ballga (vaqtni boshqarish) ta'sir
  qiladi va branching sharti bo'la oladi. `missed` task'ga kech topshirish
  ruxsat etiladi (`late=true`), lekin jarima bilan.

### 9.3 Ssenariy formati (daraxt)

#### 9.3.1 Manba va hayot sikli

- Manba: `backend/content/scenarios/<slug>.yaml` (gitda, review qilinadi).
- `tools/import_scenario.py` YAML'ni **Pydantic sxema** bilan validatsiya
  qiladi (sikl yo'qligi, mavjud bo'lmagan node/persona'ga havola yo'qligi,
  vaqtlar ish soatlari ichida) va `scenario_versions`ga `draft` sifatida yozadi.
- `publish` → versiya o'zgarmas bo'ladi. Tahrir = yangi versiya.

#### 9.3.2 Node turlari (v1)

| `type` | Vazifasi | Baholanadimi |
|---|---|---|
| `message` | Personajdan skript xabar (chat yoki inbox) | Yo'q |
| `task` | Topshiriq: brief, ilovalar, dedlayn, javob turi, rubrika | Ha |
| `incident` | Yuqori ustuvorlikdagi task, qisqa dedlayn, odatda boshqa ishni bo'lib kiradi | Ha |
| `decision` | Variantli tanlov (A/B/C); natija `flag` qo'yadi | Ha (rubrikada `correct`/`acceptable` variantlar) |
| `day_end` | Kun yakuni: talaba qisqa hisobot yozadi → kunlik AI hisobot | Ha (muloqot) |

`task`/`incident` maydonlari: `brief`, `attachments` (ssenariy fayllari),
`answer_types` (`text|file|link|code`), `due_in_minutes`, `weight`,
`competencies` (§9.6), `rubric` (faqat baholovchi ko'radi), `checks`
(deterministik: sandbox testlari, sonli javob ± tolerance), `hints` (mentor uchun).

#### 9.3.3 Shartlar (v1 cheklangan DSL)

Node'da ixtiyoriy `when`. Faqat quyidagi predikatlar (`all`/`any` bilan
birlashtiriladi), ixtiyoriy kod/ifoda **taqiqlangan**:

```
score_lt: {node, value}      score_gte: {node, value}
missed: node                 submitted: node
chose: {node, option}        flag: name
```

Shart node'ning vaqti kelganda tekshiriladi: `false` bo'lsa → `skipped`.
Daraxt chuqurligi va yakunlar soni sxemada cheklanmaydi, lekin v1
kontentida har ssenariyda **ko'pi bilan 2–3 tarmoqlanish** tavsiya qilinadi.

#### 9.3.4 Misol (qisqartirilgan)

```yaml
slug: elon-market-backend-day1
title: "Elon Market — Junior Backend, 1 kun"
sector: IT
company_name: "Elon Market"        # fictional
duration_days: 1
personas:
  - key: dilnoza
    name: "Dilnoza"
    role: "Team Lead"
    tone: "talabchan, lekin adolatli"
    knows: [doc_onboarding, doc_orders_api]
    secrets: ["Buyurtma bug'i faqat qaytarilgan (refund) buyurtmalarda chiqadi"]
nodes:
  - id: standup
    type: task
    day: 1
    at: "09:00"
    from: dilnoza
    brief: "Standup: bugungi rejangizni 3–5 qatorda yozing."
    answer_types: [text]
    due_in_minutes: 20
    competencies: [communication]
  - id: bug_orders
    type: task
    day: 1
    at: "09:30"
    from: dilnoza
    brief: "Ticket ORD-142: /orders ba'zan 500 qaytaryapti."
    answer_types: [code, text]
    due_in_minutes: 120
    checks: {sandbox_tests: tests/orders_refund.py}
    competencies: [technical]
  - id: incident_payments
    type: incident
    day: 1
    at: "13:00"
    when: {any: [{missed: bug_orders}, {score_lt: {node: bug_orders, value: 60}}]}
    brief: "Prod: to'lov xizmati 500. Mijozlar shikoyat qilyapti!"
    due_in_minutes: 30
    competencies: [stress_handling, technical]
  - id: day1_end
    type: day_end
    day: 1
    at: "17:30"
```

### 9.4 Personajlar, AI chat va RAG

- **Skript xabarlar** (`message` node) — o'zgarmas, `generated=false`.
- **AI javoblar** — talaba personajga yozganda. Kontekst: personaj
  tavsifi + chat tarixi + **RAG** natijalari + Run holati (qaysi task'lar
  kelgan, dedlaynlar).
- **RAG:** ssenariy hujjatlari (kompaniya wiki'si, siyosatlar, ma'lumotlar)
  bo'laklanib, **pgvector** orqali PostgreSQL'da saqlanadi (§3: Postgres
  yagona DB qoidasi saqlanadi). Qidiruv faqat shu `scenario_version` va
  shu personajning `knows` ro'yxati bilan cheklanadi.
- **Javobni oshkor qilmaslik (anti-spoiler), 4 qavat:**
  1. **Ma'lumot izolyatsiyasi:** rubrika, namunaviy javob, `checks` testlari
     va `hints` RAG indeksiga **hech qachon** kirmaydi — faqat baholovchi/mentor oladi.
  2. `secrets` faqat talaba aniq so'raganda aytiladi (system prompt qoidasi).
  3. **Chiqish tekshiruvi:** AI javobi namunaviy javobga o'xshashligi
     (embedding cosine) chegaradan oshsa → javob tashlanadi, ssenariyda
     yozilgan zaxira javob ("Buni o'zingiz hal qiling, lekin ... ga qarang") yuboriladi.
  4. Talaba matni mavjud `ai/guardrail.py`dan o'tadi.
- **AI chat Run holatini o'zgartirmaydi.** Branching faqat strukturaviy
  harakatlardan (task topshirish, decision, missed) kelib chiqadi —
  dvigatel deterministik va test qilinadigan bo'lib qoladi.
- **Mentor** — alohida personaj (`role: mentor`). Javobni aytmaydi,
  yo'naltiradi. Har bir `hint` shu task'ning maksimal balini kamaytiradi
  (standart −10%, node'da sozlanadi).
- **Limitlar:** Redis rate-limit (personaj chatiga daqiqasiga 10 xabar),
  har Run uchun kunlik AI xabar limiti (standart 60) va token byudjeti
  (`runs.ai_tokens_used`). Limit tugasa — personaj "band" skript javobini beradi.

### 9.5 Chat va fayllar

`chat_messages.content_type`:

| Tur | v1 | Tafsilot |
|---|---|---|
| `text` | ✅ | Oddiy matn, guardrail'dan o'tadi |
| `file` | ✅ | `core/file_validator.py` orqali (magic bytes, UUID prefiks, 10MB). pdf/docx/xlsx/png/jpg/zip |
| `link` | ✅ | Faqat `http(s)://`, backend **fetch qilmaydi** (SSRF yo'q). Link bilan birga qisqa matnli izoh majburiy; AI izohni baholaydi, task `manual_review=true` bo'lishi mumkin |
| `voice` | v2 | STT (o'zbek tili sifati oldin sinaladi), audio magic bytes (mp3 `ID3`/`FF Fx`, wav `RIFF..WAVE`, m4a `ftyp` **4-baytda**) |
| `image` | v2 | Vision model; rasm ichidagi matn ham guardrail'dan o'tishi shart |
| `video` | v2 | Kadrlash (ffmpeg), alohida hajm limiti |

v2 turlari uchun oldindan kelishilgan tafsilotlar:
- `voice` — STT (Whisper API yoki Gemini audio input) → matn AI zanjiriga
  `text` kabi beriladi; original audio playback uchun saqlanadi.
- `image` — ikki yo'nalishli (ssenariy brief'ida beradi, talaba screenshot
  yuklaydi); vision kerak, shuning uchun matn-only DeepSeek avtomatik
  o'tkazib yuboriladi → Gemini/OpenAI.
- `video` — vision'dan oldin kadrlash (masalan har 2 soniyada 1 kadr),
  hajm limiti alohida (50–100MB oralig'ida tanlanadi).
- `link` — agar kelajakda backend linkni o'zi fetch qilsa, SSRF himoyasi
  (ichki IP/localhost bloklash) shart.

- **Saqlash joyi:** `UPLOAD_DIR` — doimiy Docker volume (backend konteyneri
  `read_only`, shuning uchun alohida yoziladigan mount; Modul 8). Fayllar
  nginx orqali to'g'ridan-to'g'ri **berilmaydi** — faqat egasi/baholovchi/
  admin uchun auth'li endpoint orqali.
- Bu chat **faqat Run ichida**; `TalentOffer` (kompaniya ↔ real talaba)
  xabarlashuvi bilan aralashmaydi.

### 9.6 Baholash va hisobotlar

Kompetensiyalar (sobit ro'yxat, `enums.py`):
`technical`, `communication`, `prioritization`, `time_management`,
`stress_handling`, `initiative` (aniqlashtiruvchi savol berish).

1. **Task baholash** (arq job, topshirgandan keyin):
   - avval **deterministik** `checks` (sandbox testlari, sonli tekshiruv);
   - keyin **rubrika bo'yicha LLM** → tuzilgan JSON:
     `{criteria: [{id, score, evidence}], score, short_feedback}`;
   - `short_feedback` (2–3 gap) talabaga darhol SSE orqali ko'rsatiladi.
   - Jarimalar: `late`, ishlatilgan `hints`.
2. **Jarayon signallari:** dedlaynga ulgurish, incident'ga birinchi
   reaksiya vaqti, personajga aniqlashtiruvchi savol berganmi (kun oxirida
   chat transkriptidan baholovchi aniqlaydi).
3. **Kunlik hisobot** (`day_end`): kun bo'yicha kuchli va zaif tomonlar,
   ertangi kun uchun maslahat.
4. **Yakuniy hisobot** (Run `completed`): kompetensiyalar bo'yicha 0–100
   ballar → `runs.competency_scores`. Bu **Talent Hunt** (kandidat profili) va
   **Universitet portali** statistikasiga beriladi.
- Baholovchi model personaj modelidan **alohida chaqiruv**, personaj
  prompt'larini ko'rmaydi. AI ishlamasa — mavjud `queued_retry` →
  `failed_permanent` oqimi (§5).

### 9.7 Ma'lumotlar modeli

```
scenarios          (id, slug UNIQUE, title, sector, company_name, difficulty,
                    duration_days, is_active, created_at)
scenario_versions  (id, scenario_id, version, status draft|published|archived,
                    definition JSONB  -- validatsiyadan o'tgan to'liq daraxt,
                    published_at, UNIQUE(scenario_id, version))
scenario_documents (id, scenario_version_id, key, title, content,
                    visible_to_personas JSONB)
document_chunks    (id, document_id, chunk_index, text, embedding vector(N))
runs               (id, user_id, scenario_version_id,
                    status scheduled|active|completed|expired|abandoned,
                    start_at, ends_at, last_activity_at, flags JSONB,
                    ai_tokens_used, competency_scores JSONB, final_report JSONB)
run_events         (id, run_id, node_id, scheduled_at, delivered_at, due_at,
                    status pending|delivered|submitted|missed|skipped,
                    choice, hints_used, result JSONB, UNIQUE(run_id, node_id))
chat_messages      (id, run_id, persona_key, sender student|persona|system,
                    content_type, body, file_id NULL, link_url NULL,
                    generated bool, created_at)
uploaded_files     (id, owner_user_id, run_id NULL, stored_path, mime,
                    size_bytes, sha256, created_at)
```

`submissions` (Modul 2) kengaytiriladi:
`run_id`, `run_event_id` (nullable FK), `rubric_scores JSONB`, `late bool`;
`task_id` nullable bo'ladi; CHECK: `task_id` va `run_event_id`dan
**aynan bittasi** to'ldirilgan. Talent Hunt/Universitet portali so'rovlari
`submissions` orqali ishlashda davom etadi.

### 9.8 Dvigatel mexanikasi

- Run yaratilganda vaqti aniq (`day`+`at`) barcha node'lar uchun
  `run_events` (`pending`, `scheduled_at` hisoblangan) yoziladi. Nisbiy
  (`after`) node'lar trigger sodir bo'lganda yaratiladi.
- **Yetkazish:** arq cron har daqiqada `pending` va `scheduled_at <= now`
  hodisalarni oladi (`SELECT ... FOR UPDATE SKIP LOCKED`), `when`ni
  tekshiradi → `delivered` yoki `skipped`. Shu cron `due_at` o'tganlarni
  `missed` qiladi va `expired` Run'larni yopadi.
- **Idempotent:** `UNIQUE(run_id, node_id)` + holat o'tishlari faqat bir
  yo'nalishda. `GET /runs/{id}` ham "kechikkan" hodisalarni shu funksiya
  bilan yetkazadi (cron kechiksa ham talaba to'g'ri holatni ko'radi).
- **Bildirishnoma:** frontend'ga SSE oqimi. Talaba sahifada bo'lmasa —
  keyingi kirishda inbox'da ko'radi (v1). Email/push — v2.

### 9.9 API (Modul 9)

```
GET    /api/v1/scenarios                         katalog (published, is_active)
GET    /api/v1/scenarios/{id}
POST   /api/v1/runs                              { scenario_id, start_date } -> scheduled
GET    /api/v1/runs/my
GET    /api/v1/runs/{id}                         holat: soat, hodisalar, dedlaynlar
GET    /api/v1/runs/{id}/stream                  SSE: yangi hodisa, feedback
POST   /api/v1/runs/{id}/events/{node_id}/submit { text?, file_id?, link_url?, code? }
POST   /api/v1/runs/{id}/events/{node_id}/decide { option }
POST   /api/v1/runs/{id}/events/{node_id}/hint
GET    /api/v1/runs/{id}/chat/{persona_key}
POST   /api/v1/runs/{id}/chat/{persona_key}      AI javob; rate-limit
POST   /api/v1/runs/{id}/abandon
GET    /api/v1/runs/{id}/report                  kunlik + yakuniy hisobot
POST   /api/v1/files                             multipart; auth + rate-limit
GET    /api/v1/files/{id}                        faqat egasi / baholovchi / admin

POST   /api/v1/admin/scenarios/import            YAML; permission: manage_simulations
POST   /api/v1/admin/scenarios/{id}/versions/{v}/publish
```

Barcha `runs/*` endpointlari: faqat Run egasi (boshqa foydalanuvchiga 404).

### 9.10 Modul chegaralari (§6 bilan bog'liq)

**Modul 9 — Scenario Engine** egaligi:
`backend/app/scenario/` (engine, clock, conditions, schema, rag),
`backend/app/models/scenario.py`, `backend/app/api/scenarios.py`,
`backend/app/api/runs.py`, `backend/app/api/files.py`,
`backend/content/scenarios/`, `tools/import_scenario.py`,
`backend/tests/test_scenario_*.py`, `backend/tests/test_runs_*.py`.

Boshqa modullardan talab qilinadigan interfeyslar (Modul 9 ularning
fayliga **tegmaydi**):

| Modul | Nima qo'shadi |
|---|---|
| 2 (AI) | `ai/` ichida: `persona_reply(ctx, history) -> str`, `evaluate_rubric(task, answer, rubric) -> RubricResult`, `embed(texts) -> list[list[float]]`, `summarize_day(...)`, `final_report(...)`; `submissions` migratsiyasi (§9.7); arq cron `deliver_due_events`ni `WorkerSettings`ga ulash (funksiyaning o'zi Modul 9'da) |
| 1 (Core) | `models/enums.py`ga `Competency`, `RunStatus`, `RunEventStatus`, `NodeType`, `ChatContentType`; `file_validator`ga yangi turlar (v2) |
| 8 (Deploy) | `postgres` image → `pgvector/pgvector:pg16`; `UPLOAD_DIR` volume; nginx'da `/api/v1/runs/*/stream` uchun `proxy_buffering off` va uzun `proxy_read_timeout` |
| 7 (Frontend) | "Ish stoli": inbox, personajlar chati, task board, kalendar, soat, hisobot sahifasi |
| 4, 6 | `runs.competency_scores`ni nomzod profili va universitet statistikasiga qo'shish |

### 9.11 v1 qamrovi va v2

**v1:** real vaqt; kunlik va haftalik; `text`/`file`/`link`; skript + AI
personaj (RAG, anti-spoiler); cheklangan shartlar DSL; task feedback +
kunlik + yakuniy hisobot; kontent: **1 ta IT (1 kun) + 1 ta Bank (1 kun)**,
keyin 1 ta haftalik.

**v2:** `voice`/`image`/`video`; email/push bildirishnoma; murakkab
shartlar va ko'p yakunli ssenariylar; `meeting` (jonli savol-javob) node
turi; ssenariy muharriri (admin UI).

### 9.12 Ochiq savollar (yozilgan, lekin hali hal qilinmagan)

- **Embedding provayderi** (DeepSeek embedding bermaydi → Gemini/OpenAI)
  va vektor o'lchami `N`.
- **Shaxsiy ma'lumotlar:** talaba matni va fayllari xorijiy AI API'larga
  ketadi — rozilik matni, saqlash muddati va O'zbekiston qonunchiligidagi
  lokalizatsiya talabi yurist bilan tekshirilsin.
- **Real vaqt va talabaning darslari:** pauza yo'q qaror qabul qilingan;
  pilotdan keyin "yonib ketgan" Run'lar ulushi kuzatilsin va kerak bo'lsa
  ssenariy dedlaynlari yumshatilsin.
