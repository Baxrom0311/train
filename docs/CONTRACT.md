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
| 2 | **Simulations & AI Mentor** | `backend/app/models/simulation.py`, `backend/app/models/ai_usage.py`, `backend/app/api/simulations.py`, `backend/app/api/submissions.py`, `backend/app/ai/` | (1)ga bog'liq |
| 3 | **Billing & Admin approval** | `backend/app/models/billing.py`, `backend/app/api/billing.py`, `backend/app/api/admin.py` | (1)ga bog'liq |
| 4 | **Talent Hunt** | `backend/app/models/talent.py`, `backend/app/api/talent_hunt.py`, `backend/app/talent/` | (1),(3),(9)ga bog'liq — ball Run natijalaridan (§10) |
| 5 | **Case Cup** | `backend/app/api/case_cups.py` | (1),(2)ga bog'liq |
| 6 | **University Portal** | `backend/app/api/university_portal.py` | (1),(3),(9)ga bog'liq — natijalar Run'lardan (§12) |
| 7 | **Frontend (React+shadcn)** | `frontend/` | Har modul backend API'si tayyor bo'lgach, mos ekranlar — vertical slice, lekin alohida agent/task |
| 8 | **Deploy** | `deploy/` | Docker-compose, nginx, Dockerfile'lar — backend/frontend tuzilishi barqarorlashgach yangilanadi |
| 9 | **Scenario Engine** | §9.10 ro'yxati (`backend/app/scenario/`, `models/scenario.py`, `api/scenarios.py`, `api/runs.py`, `api/files.py`, `backend/content/scenarios/`, `tools/import_scenario.py`) | (1),(2) interfeyslari — §9.10 |
| 10 | **Credentials** | `backend/app/models/credential.py`, `backend/app/api/credentials.py`, `backend/app/credentials/` | (1),(6),(9)ga bog'liq — sertifikat Run'dan, portfolio §10.1 profilidan (§13) |
| 11 | **Notifications** | `backend/app/models/notification.py`, `backend/app/api/notifications.py`, `backend/app/notifications/`, `tools/gen_vapid_keys.py` | (1),(4),(9),(10)ga bog'liq — manbalar §15.2 |
| 12 | **Analytics** | `backend/app/api/analytics.py`, `backend/app/analytics/` | (9),(10)ga bog'liq — Run natijalarini faqat o'qiydi (§17); platforma statistikasi hisobi `analytics/platform.py` (§21), endpointi Modul 3 `api/admin.py`da |
| 13 | **Sandbox runner** | `sandbox/`, `deploy/sandbox.Dockerfile` | Tashqi bog'liqliksiz (faqat stdlib); backend `core/sandbox.py` orqali chaqiradi (§19) |

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
# Tashkilot ariza/rad etish, invoice bekor qilish, o'z invoice'lari — §11

PATCH  /api/v1/users/me/visibility        { is_open_to_work, hidden_from_company_ids }
GET    /api/v1/talents                    only is_verified company + only visible candidates
POST   /api/v1/talents/offers             counts against subscription's "interview SLA" commitment

# Talent Hunt to'liq ro'yxati (profil, takliflarga javob) — §10.4
# Kompaniya hisobotlari (nomzodlar bazasi, takliflar voronkasi, CSV) — §20
# Platforma statistikasi va AI sarfi (admin) — §21
# Push obunalari va PWA — §22
# Universitet portali (talabalar natijalari, bog'lanish) — §12.2
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
| Q8 | Bayramlar | O'zbekiston rasmiy bayramlari **ish kuni emas**. `work_holidays` jadvali avtomatik to'ldiriladi (`holidays` paketi), admin qo'lda tuzata oladi (§9.2) |
| Q9 | Tushlik | **13:00–14:00 ish vaqtiga kirmaydi.** Ish kuni = 09:00–13:00 + 14:00–18:00 = 480 ish daqiqasi |
| Q10 | Boshlanish | **Istalgan payt**, shu jumladan "hozir". Kech boshlansa ogohlantirish beriladi, ssenariy vaqt jadvali boshlanish nuqtasidan siljiydi (§9.2) |
| Q11 | Qayta topshirish | **Ruxsat.** Bir task'ga ko'pi bilan `max_attempts` (standart 3) urinish, hisobga **oxirgisi** olinadi, urinish uchun jarima yo'q |
| Q12 | Embedding | Gemini `gemini-embedding-001`, o'lcham **768**. Provayder bitta modulda; almashtirish = qayta indekslash |

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

- Vaqt zonasi: **`Asia/Tashkent`** (`zoneinfo`, qattiq `+05:00` emas; slim
  image uchun `tzdata` paketi). DB'da barcha vaqtlar UTC `timestamptz`.
- **Ish vaqti** (Q8, Q9): dushanba–juma, ikki bo'lak — 09:00–13:00 va
  14:00–18:00 (kuniga 480 ish daqiqasi). `work_holidays` jadvalidagi sanalar
  ish kuni emas. Bo'laklar va bayramlar bitta `WorkCalendar` obyektida
  (`scenario/clock.py`), barcha vaqt matematikasi faqat shu yerda.
- **Bayramlar:** haftalik arq job `holidays` paketining O'zbekiston
  kalendaridan joriy va keyingi yil sanalarini `work_holidays`ga yozadi
  (`source=auto`). Admin yozuvi (`source=manual`) avtomatik yozuvdan ustun:
  hayit sanalari va ko'chirilgan dam olish kunlari har yili qaror bilan
  e'lon qilinadi. Sinxronizatsiya faqat hali bitta ham `auto` yozuvi yo'q
  yilni to'ldiradi — admin o'chirgan taxminiy sana qaytib kelmaydi.
- **Ish daqiqasi qo'shish:** `add_work_minutes(t, m)` — `t` ish vaqtidan
  tashqarida bo'lsa keyingi bo'lak boshiga suriladi, so'ng bo'laklar bo'yicha
  hisoblanadi; tushlik, kechqurun, dam olish va bayram kunlari o'tkazib
  yuboriladi. Bo'lak oxiriga aynan tushgan natija (13:00, 18:00) o'sha
  vaqtda qoladi. Misollar: 17:30 + 60 = ertasi 09:30; juma 17:30 + 60 =
  dushanba 09:30; 12:30 + 60 = 14:30.
- **Boshlanish** (Q10): talaba "hozir" yoki kelajakdagi vaqtni tanlaydi;
  `runs.start_at = normalize(tanlangan)` (ish vaqtidan tashqarida bo'lsa
  keyingi bo'lak boshi). `start_at` kelajakda bo'lsa `status=scheduled`,
  aks holda darhol `active`.
- **Node vaqti:** `day` (1..`duration_days`) + `at` (`"HH:MM"`, ish
  bo'laklari ichida) ssenariyning **ish-daqiqa siljishi**ga aylantiriladi:
  `offset = (day-1)·480 + work_minutes(09:00 → at)`, va
  `scheduled_at = normalize(add_work_minutes(start_at, offset))` — hodisa
  boshlanishi bo'lak oxiriga (13:00, 18:00) tushmaydi, keyingi bo'lak
  boshiga suriladi (`WorkCalendar.start_after`). Run 09:00 da
  boshlansa bu aynan ssenariydagi soatlar; 15:00 da boshlansa butun jadval
  5 ish soatiga siljiydi (1-kun ertasi 15:00 da tugaydi). Bunday holatda
  `POST /runs` javobida `warning` va 1-kunning haqiqiy tugash vaqti qaytadi.
- **Nisbiy node:** `after: {node, event: delivered|submitted, minutes}` →
  `scheduled_at = start_after(trigger_vaqti, minutes)` (yuqoridagidek normallashtiriladi).
- **Dedlayn:** `due_at = add_work_minutes(delivered_at, due_in_minutes)` —
  `scheduled_at`dan emas, cron kechiksa talaba vaqt yo'qotmaydi
  (`delivered_at` = haqiqiy yetkazilgan payt). `due_in_minutes` berilmagan
  `decision` — 60, `day_end` — 30 ish daqiqasi; `message`da dedlayn yo'q.
- **Pauza yo'q.** `compression_ratio` ham yo'q (v1'dan olib tashlandi) — 1
  simulyatsiya soati = 1 real soat.
- Ssenariy darajasidagi parametr: `duration_days` (1 = kunlik, 5 = haftalik).
- **Tugash (`completed`):** oxirgi kunning `day_end` hodisasi `submitted`
  yoki `missed` bo'lsa, `pending` hodisa qolmagan bo'lsa va dedlayni hali
  o'tmagan (`delivered`) baholanadigan hodisa qolmagan bo'lsa — talaba
  ochiq task'ini tugatishga ulguradi.
- **Muddat tugashi (`expired`):**
  - `last_activity_at`dan 7 kalendar kun o'tsa, yoki
  - `ends_at`dan o'tsa: `ends_at` = eng kech fixed node'ning `scheduled_at`
    kunidan keyingi 2-ish kunining 18:00 i.
  Expire paytida avval yonish vaqtigacha bo'lgan hodisalar tartib bilan
  bajariladi, keyin `pending` → `skipped`, baholanadigan `delivered` →
  `missed` (`message` `delivered` qoladi). `abandoned` ham shunday yopiladi. Yongan Run
  uchun bajarilgan qism bo'yicha yakuniy hisobot "tugallanmagan" belgisi
  bilan yoziladi, sertifikat berilmaydi. Talaba yangi Run ochishi mumkin.
- `last_activity_at` — Run egasining har qanday `runs/*` so'rovida yangilanadi.
- Dedlayni o'tgan task → `missed`. Bu ballga (vaqtni boshqarish) ta'sir
  qiladi va branching sharti bo'la oladi. Run `active` ekan, `missed`
  task'ga kech topshirish ruxsat etiladi (`late=true`), jarima standart
  **−20%** (node'da `late_penalty`).

### 9.3 Ssenariy formati (daraxt)

#### 9.3.1 Manba va hayot sikli

- Manba: `backend/content/scenarios/<slug>.yaml` (gitda, review qilinadi).
- `tools/import_scenario.py` YAML'ni **Pydantic sxema** bilan validatsiya
  qiladi (sikl yo'qligi, mavjud bo'lmagan node/persona'ga havola yo'qligi,
  `at` ish bo'laklari ichida — 13:00–14:00 tushlik rad etiladi, `day`
  1..`duration_days` ichida) va `scenario_versions`ga `draft` sifatida yozadi.
  `missed: X` sharti X'ning eng erta mumkin bo'lgan `due_at`idan oldin
  tekshirilsa — ogohlantirish.
- `publish` → versiya o'zgarmas bo'ladi. Tahrir = yangi versiya.

#### 9.3.2 Node turlari (v1)

| `type` | Vazifasi | Baholanadimi |
|---|---|---|
| `message` | Personajdan skript xabar (chat yoki inbox) | Yo'q |
| `task` | Topshiriq: brief, ilovalar, dedlayn, javob turi, rubrika | Ha |
| `incident` | Yuqori ustuvorlikdagi task, qisqa dedlayn, odatda boshqa ishni bo'lib kiradi | Ha |
| `decision` | Variantli tanlov (A/B/C); natija `flag` qo'yadi | Ha (rubrikada `correct`/`acceptable` variantlar) |
| `day_end` | Kun yakuni: talaba qisqa hisobot yozadi → kunlik AI hisobot | Ha (muloqot) |

`task`/`incident` maydonlari: `brief`, `attachments` (ssenariy `documents`
kalitlari — talaba hodisa yetkazilgandan keyin shu hujjatlarni o'qiy oladi;
qolgan hujjatlarni faqat personajlar "biladi" va chatda aytadi),
`answer_types` (`text|file|link|code`), `due_in_minutes`, `weight`,
`competencies` (§9.6), `rubric` (faqat baholovchi ko'radi), `checks`
(deterministik: sandbox testlari, sonli javob ± tolerance), `hints` (mentor uchun),
`reference_answer` (faqat baholovchi va anti-spoiler tekshiruvi uchun),
`max_attempts` (standart 3), `late_penalty` (standart 0.2), `hint_penalty`
(standart 0.1).

#### 9.3.3 Shartlar (v1 cheklangan DSL)

Node'da ixtiyoriy `when`. Faqat quyidagi predikatlar (`all`/`any` bilan
birlashtiriladi), ixtiyoriy kod/ifoda **taqiqlangan**:

```
score_lt: {node, value}      score_gte: {node, value}
missed: node                 submitted: node
chose: {node, option}        flag: name
```

Shart node'ning vaqti kelganda tekshiriladi: `false` bo'lsa → `skipped`.
`score_*` predikatlari o'sha paytdagi **oxirgi baholangan** urinish ballini
ko'radi. Ball hali tayyor bo'lmasa (AI baholash `pending`/`queued_retry`),
yetkazish har daqiqada qayta tekshiriladi, ko'pi bilan 15 daqiqa; keyin
ball `None` deb olinadi va `score_*` predikatlari `false` bo'ladi.
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
    checks:                       # §19.3 — yashirin testlar
      tests: |
        from solution import total_amount
        def test_refund_has_no_amount():
            assert total_amount([{"amount": None, "status": "refunded"}]) == 0
    competencies: [technical]
  - id: incident_payments
    type: incident
    day: 1
    at: "14:00"
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

- **Skript xabarlar** — `from` va `brief`i bor har bir node yetkazilganda
  shu personaj chatiga ham yoziladi (o'zgarmas, `generated=false`).
- **AI javoblar** — talaba personajga yozganda. Kontekst: personaj
  tavsifi + chat tarixi + **RAG** natijalari + Run holati (qaysi task'lar
  kelgan, dedlaynlar).
- **RAG:** ssenariy hujjatlari (kompaniya wiki'si, siyosatlar, ma'lumotlar)
  bo'laklanib, **pgvector** orqali PostgreSQL'da saqlanadi (§3: Postgres
  yagona DB qoidasi saqlanadi). Qidiruv faqat shu `scenario_version` va
  shu personajning `knows` ro'yxati bilan cheklanadi.
  - Import paytida hujjatlar ~1200 belgilik bo'laklarga bo'linadi (150
    belgi overlap); embedding'larni har 5 daqiqada arq cron
    (`embed_document_chunks_job`) to'ldiradi — import tashqi API'ga bog'liq emas.
  - Personaj biladigan hujjatlar jami 6000 belgidan kam bo'lsa — qidirilmaydi,
    butunligicha beriladi (v1 ssenariylarining aksariyati shunday).
  - Aks holda **gibrid**: pgvector cosine (top 20) + full-text
    (`to_tsquery('simple', so'z1 | so'z2 ...)`, top 20) → Reciprocal Rank
    Fusion (k=60) → top 4. Embedding yo'q bo'lsa (Gemini kaliti/API ishlamasa)
    faqat full-text.
- **Javobni oshkor qilmaslik (anti-spoiler), 4 qavat:**
  1. **Ma'lumot izolyatsiyasi:** rubrika, namunaviy javob, `checks` testlari
     va `hints` RAG indeksiga **hech qachon** kirmaydi — faqat baholovchi/mentor oladi.
  2. `secrets` faqat talaba aniq so'raganda aytiladi (system prompt qoidasi).
     Namunaviy javoblar tekshiruvga ssenariyning **barcha** node'laridan olinadi.
  3. **Chiqish tekshiruvi** (`ai/spoiler.py`): namunaviy javobning so'z
     5-gramlaridan ≥30% i AI javobida bo'lsa **yoki** embedding cosine ≥ 0.85
     bo'lsa → javob tashlanadi, ssenariyda yozilgan zaxira javob
     (personajning `deflect_reply` maydoni) yuboriladi. n-gram tekshiruvi
     embedding'siz ham ishlaydi.
  4. Talaba matni mavjud `ai/guardrail.py`dan o'tadi.
- **AI chat Run holatini o'zgartirmaydi.** Branching faqat strukturaviy
  harakatlardan (task topshirish, decision, missed) kelib chiqadi —
  dvigatel deterministik va test qilinadigan bo'lib qoladi.
- **Mentor** — alohida personaj (YAML'da `kind: mentor`; `role` — erkin matnli lavozim). Javobni aytmaydi,
  yo'naltiradi. Har bir `hint` shu task'ning maksimal balini kamaytiradi
  (standart −10%, node'da sozlanadi).
- **Limitlar:** Redis rate-limit (personaj chatiga daqiqasiga 10 xabar),
  har Run uchun kunlik AI xabar limiti (standart 60) va token byudjeti
  (`runs.ai_tokens_used`, standart 200 000). Limit tugasa yoki AI ishlamasa —
  personajning `busy_reply` skript javobi. LLM chaqiruvi Run qulfidan
  tashqarida: talaba xabari yozilib commit qilinadi, keyin javob yaratiladi.
- **Mentor** talabaning ishini ko'radi, har baholangan urinishdan keyin o'zi
  izoh yozadi va dedlayn yaqinlashsa eslatadi — §9.13.
- **Hint:** `POST .../hint` navbatdagi `hints[i]`ni qaytaradi, `hints_used`
  oshadi (keyingi baholashlarda `hint_penalty` qo'llanadi); ssenariyda
  `kind: mentor` personaj bo'lsa, hint uning chatiga ham yoziladi.

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

- **Kirish:** fayl egasi yoki `manage_simulations` ruxsati (admin); boshqalarga 404.
  Fayl Run'ga bog'lansa (`run_id`), faqat shu Run javobi/chatida ishlatiladi.
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
   - keyin **rubrika bo'yicha LLM** (`ai/evaluator.py: evaluate_rubric`) →
     tuzilgan JSON `{criteria: [{id, score, evidence}], short_feedback}`;
     mezon id'lari rubrikadagidan farq qilsa javob yaroqsiz (keyingi
     provayder). Umumiy ball kodda: mezon ballarining og'irlikli o'rtachasi.
     Rubrikasiz node — bitta `overall` mezoni. `submissions.rubric_scores` =
     `{criteria, raw_score, penalty_factor, provider, model}`;
   - `short_feedback` (2–3 gap) talabaga darhol SSE orqali ko'rsatiladi.
   - Jarimalar: `late`, ishlatilgan `hints` — hammasi kodda, LLM'ning
     umumiy ballidan emas, mezon og'irliklaridan hisoblanadi.
   - Qayta topshirish (Q11): har urinish alohida baholanadi, task balli =
     oxirgi urinish. Hisobotda urinishlar bo'yicha o'sish ko'rsatiladi.
   - Yakuniy task balli `submissions.ai_score`ga ham yoziladi — Universitet
     portali statistikasi o'zgarishsiz ishlaydi.
2. **Jarayon signallari:** dedlaynga ulgurish, incident'ga birinchi
   reaksiya vaqti, personajga aniqlashtiruvchi savol berganmi (kun oxirida
   chat transkriptidan baholovchi aniqlaydi).
3. **Kunlik hisobot** (`day_end` topshirilganda yoki o'tkazib yuborilganda):
   shu kun task'lari natijasi, o'rtacha ball, o'z vaqtida topshirish ulushi +
   AI xulosasi (kuchli/zaif tomonlar, ertangi kun uchun maslahat) →
   `run_events.result.report`.
4. **Yakuniy hisobot** (Run `completed` yoki `expired`): kompetensiyalar
   bo'yicha 0–100 ballar → `runs.competency_scores`, to'liq hisobot →
   `runs.final_report` (`expired` — `incomplete: true`, `certificate: false`).
   Bu **Talent Hunt** (kandidat profili) va **Universitet portali**
   statistikasiga beriladi.
   - Task balli = oxirgi baholangan urinish (jarimalar bilan); topshirilmay
     o'tkazib yuborilgan — 0; baholanmagan (AI ishlamagan) — hisobga kirmaydi.
   - Kompetensiya = shu kompetensiya belgilangan task'lar ballining
     og'irlikli o'rtachasi; `day_end` → `communication`; `time_management`
     — o'z vaqtida topshirish ulushi bilan o'rtacha; `initiative` — AI'ning
     chat transkripti bahosi bilan o'rtacha. Ma'lumot yo'q kompetensiya
     hisobotga kirmaydi.
   - Ballar faqat kodda; AI faqat matn va `initiative`ni beradi. AI ishlamasa
     hisobot matnsiz yoziladi.
   - Hisobotlar baholash tugashini kutadi (oxirgi javobdan 15 daqiqagacha).
     Yozilishi kerak bo'lganlarni har daqiqalik cron topib, arq job'larini
     (`day_report_job`, `final_report_job`) navbatga qo'yadi.
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
document_chunks    (id, document_id, chunk_index, text, embedding vector(768),
                    embedding_model, tsv tsvector)  -- HNSW + GIN indeks
runs               (id, user_id, scenario_version_id,
                    status scheduled|active|completed|expired|abandoned,
                    start_at, ends_at, last_activity_at, flags JSONB (ro'yxat),  -- INDEX(status, ends_at)
                    ai_tokens_used, competency_scores JSONB, final_report JSONB)
run_events         (id, run_id, node_id, scheduled_at, delivered_at, due_at,
                    status pending|delivered|submitted|missed|skipped,
                    first_opened_at, choice, hints_used, result JSONB,
                    UNIQUE(run_id, node_id))  -- INDEX(status, scheduled_at), INDEX(status, due_at)
chat_messages      (id, run_id, persona_key, sender student|persona|system,
                    content_type, body, file_id NULL, link_url NULL,
                    generated bool, created_at,
                    purpose NULL review|nudge, node_id NULL,        -- mentor xabarlari (§9.13)
                    submission_id NULL FK UNIQUE)                   -- bitta urinishga bitta izoh
uploaded_files     (id, owner_user_id, run_id NULL, stored_path, original_name, mime,
                    size_bytes, sha256, created_at)
work_holidays      (date PK, name, source auto|manual)
```

Bir foydalanuvchida bir ssenariy versiyasi uchun bir vaqtda bitta faol Run:
qisman UNIQUE `(user_id, scenario_version_id) WHERE status IN ('scheduled','active')`.

`submissions` (Modul 2) kengaytiriladi:
`run_id`, `run_event_id` (nullable FK), `rubric_scores JSONB`, `late bool`,
`attempt smallint` (standart 1), `file_id` (nullable FK → `uploaded_files`),
`link_url`; `task_id` nullable bo'ladi; CHECK: `task_id` va `run_event_id`dan
**aynan bittasi** to'ldirilgan; UNIQUE `(run_event_id, attempt)` (qisman,
`run_event_id IS NOT NULL`). `AIEvalStatus`ga `pending` qo'shiladi — Run
submission'i har doim arq job orqali baholanadi. Talent Hunt/Universitet portali so'rovlari
`submissions` orqali ishlashda davom etadi.

### 9.8 Dvigatel mexanikasi

- Run yaratilganda vaqti aniq (`day`+`at`) barcha node'lar uchun
  `run_events` (`pending`, `scheduled_at` hisoblangan) yoziladi. Nisbiy
  (`after`) node'lar trigger sodir bo'lganda yaratiladi.
- **Yetkazish:** arq cron (`deliver_due_events`) har daqiqada ishi bor
  ochiq Run'larni **Run qatori bo'yicha** qulflaydi (`SELECT ... FOR UPDATE
  SKIP LOCKED`; API o'sha Run'ni kutib qulflaydi), `pending` va
  `scheduled_at <= now` hodisalarda `when`ni tekshiradi → `delivered` yoki
  `skipped`, `due_at` o'tganlarni `missed` qiladi, `scheduled` Run'ni
  `active`, tugaganini `completed`, muddati o'tganini `expired` qiladi.
  Yetkazish va dedlaynlar **xronologik** tartibda bajariladi: cron kechiksa
  ham 13:00 dagi shart 13:30 dagi dedlayndan oldin tekshiriladi.
- **Baholash navbati:** javob `pending` holatda yoziladi va arq job
  (`evaluate_run_submission_job`, `_job_id=run-eval:{id}`) navbatga
  qo'yiladi. 5 daqiqadan ko'p `pending` turgan javobni cron qayta navbatga
  qo'yadi. `decision` AI'siz, darhol baholanadi (`correct` 100,
  `acceptable` 60, `wrong` 0; kech bo'lsa `late_penalty`).
- **Idempotent:** `UNIQUE(run_id, node_id)` + holat o'tishlari faqat bir
  yo'nalishda. `GET /runs/{id}` ham "kechikkan" hodisalarni shu funksiya
  bilan yetkazadi (cron kechiksa ham talaba to'g'ri holatni ko'radi).
- Barcha o'tishlar bitta modulda: `scenario/engine.py: advance(db, now,
  run_id=None)` (va talaba harakatlari `submit_answer`, `decide`,
  `abandon`); `now` parametr, testlar aniq vaqtlar bilan yoziladi.
- **Bildirishnoma:** frontend'ga SSE oqimi. Worker va API alohida
  jarayonlar, shuning uchun hodisalar **Redis pub/sub** (`run:{id}` kanali)
  orqali uzatiladi; SSE endpoint shu kanalga obuna bo'ladi (`event: <type>`,
  har 15 soniyada `: ping`). Auth — `Authorization` header, shuning uchun
  frontend `EventSource` emas, `fetch` asosidagi SSE mijozini ishlatadi. Talaba sahifada
  bo'lmasa — keyingi kirishda inbox'da ko'radi (v1). Email/push — v2.
- **Bayram sinxronizatsiyasi:** haftalik arq cron `sync_work_holidays` (§9.2).

### 9.9 API (Modul 9)

```
GET    /api/v1/scenarios                         katalog (published, is_active)
GET    /api/v1/scenarios/{id}
GET    /api/v1/showcase                          ochiq (login'siz) — landing uchun, §14.1
POST   /api/v1/runs                              { scenario_id, start_at? } -> scheduled|active (+warning, day1_ends_at)
GET    /api/v1/runs/my
GET    /api/v1/runs/{id}                         holat: soat, hodisalar, dedlaynlar
GET    /api/v1/runs/{id}/stream                  SSE: yangi hodisa, feedback
POST   /api/v1/runs/{id}/events/{node_id}/submit { text?, file_id?, link_url?, code? }  (<= max_attempts)
POST   /api/v1/runs/{id}/events/{node_id}/decide { option }
POST   /api/v1/runs/{id}/events/{node_id}/hint
GET    /api/v1/runs/{id}/chat/{persona_key}
POST   /api/v1/runs/{id}/chat/{persona_key}      AI javob; rate-limit
POST   /api/v1/runs/{id}/abandon
GET    /api/v1/runs/{id}/report                  kunlik + yakuniy hisobot
GET    /api/v1/runs/{id}/documents/{key}         ilova hujjat (faqat yetkazilgan hodisaga biriktirilgan bo'lsa)
POST   /api/v1/files                             multipart; auth + rate-limit
GET    /api/v1/files/{id}                        faqat egasi / baholovchi / admin

# Ssenariy muharriri (admin, manage_simulations) — to'liq ro'yxat §16.2
GET    /api/v1/admin/holidays                     permission: manage_simulations
PUT    /api/v1/admin/holidays/{date}              { name } -> source=manual
DELETE /api/v1/admin/holidays/{date}
```

Barcha `runs/*` endpointlari: faqat Run egasi (boshqa foydalanuvchiga 404).

### 9.10 Modul chegaralari (§6 bilan bog'liq)

**Modul 9 — Scenario Engine** egaligi:
`backend/app/scenario/` (engine, clock, conditions, schema, rag),
`backend/app/models/scenario.py`, `backend/app/api/scenarios.py`,
`backend/app/api/runs.py`, `backend/app/api/files.py`, `backend/app/api/scenario_admin.py`,
`backend/content/scenarios/`, `tools/import_scenario.py`,
`backend/tests/test_scenario_*.py`, `backend/tests/test_runs_*.py`.

Boshqa modullardan talab qilinadigan interfeyslar (Modul 9 ularning
fayliga **tegmaydi**):

| Modul | Nima qo'shadi |
|---|---|
| 2 (AI) | `ai/llm.py`: umumiy `chat(messages, schema?) -> LLMResult` (JSON-rejim, Pydantic tekshiruv, token hisobi, provayder tartibi `LLM_PROVIDERS` va model nomlari `.env`dan); `ai/` ichida: `persona_reply(ctx, history, message) -> LLMResult`, `evaluate_rubric(task, answer, rubric) -> RubricResult`, `embed(texts) -> list[list[float]]`, `summarize_day(...)`, `final_report(...)`, `mentor_review(ctx) -> LLMResult` (§9.13); `submissions` migratsiyasi (§9.7); arq cron `deliver_due_events`ni `WorkerSettings`ga ulash (funksiyaning o'zi Modul 9'da) |
| 1 (Core) | `models/enums.py`ga `Competency`, `RunStatus`, `RunEventStatus`, `NodeType`, `ChatContentType`, `ChatSender`, `ScenarioVersionStatus`, `HolidaySource`, `AIEvalStatus.PENDING`; `requirements.txt`ga `tzdata`, `holidays`, `pgvector`; `conftest.py`da `create_all`dan oldin `CREATE EXTENSION IF NOT EXISTS vector`; `file_validator`ga yangi turlar (v2) |
| 8 (Deploy) | `postgres` image → `pgvector/pgvector:pg16`; `UPLOAD_DIR` volume; nginx'da `/api/v1/runs/*/stream` uchun `proxy_buffering off` va uzun `proxy_read_timeout` |
| 7 (Frontend) | "Ish stoli": inbox, personajlar chati, task board, kalendar, soat, hisobot sahifasi |
| 4, 6 | `runs.competency_scores`ni nomzod profili va universitet statistikasiga qo'shish; Modul 6: `SubmissionSummary.task_id` → `Optional` (Run submission'ida `task_id` yo'q) |
| 10 (Credentials) | `credentials/issue.py`: `issue_for_run(db, run)` — `write_final_report` uni yakuniy hisobot bilan bir tranzaksiyada chaqiradi (§13.1) |

### 9.11 v1 qamrovi va v2

**v1:** real vaqt; kunlik va haftalik; `text`/`file`/`link`; skript + AI
personaj (RAG, anti-spoiler); cheklangan shartlar DSL; task feedback +
kunlik + yakuniy hisobot; kontent: **1 ta IT (1 kun) + 1 ta Bank (1 kun)**,
keyin 1 ta haftalik. Kontent `backend/content/scenarios/`da: `lazurit-go-backend-day1`
(IT, Junior Backend), `oqsaroy-bank-credit-day1` (Bank, Junior kredit tahlilchisi),
`lazurit-go-backend-week1` (IT, 5 kun: tanishuv → dizayn → kod va review →
incident va postmortem → demo va retro; 4-kun incident'i 3-kun kodi baliga bog'liq).
Barcha kompaniya, mijoz va raqamlar o'ylab topilgan; bank chegaralari
(DSCR, ta'minot, AML) o'quv maqsadidagi ichki siyosat, real normativ emas.

**Sohalar (v1.1):** `Sector` = `IT | Banking | Marketing | Data | HR`
(`scenarios.sector`, 20 belgigacha — yangi soha migratsiyasiz qo'shilmaydi:
enum + baholovchi persona + frontend `SECTORS`). Har sohada kamida bitta
1 kunlik ssenariy, hammasi bir xil kun skeleti bo'yicha (09:00 standup →
09:30 asosiy task → 11:30 axloqiy/kasbiy tuzoqli decision → 14:00 mentor
eslatmasi va ikkinchi task → 15:00/15:30 30 daqiqalik incident → 17:30 day_end):

- `oydinbarg-marketing-day1` (Marketing, Junior digital marketolog):
  kampaniya metrikalari va budjet taqsimoti, tasdiqlanmagan tibbiy da'vo
  bosimi, brendbukka mos aksiya matni va A/B sarlavhalar, xato narxli post.
- `sabzazor-data-day1` (Data, Junior data analyst): SQL haftalik hisobot
  (dublikat, refund, UTC → Toshkent hafta chegarasi), kengash grafigini
  "chiroyli" qilish bosimi, Simpson paradoksli A/B test, JOIN'dan 3× oshgan dashboard.
- `qaldirgoch-qadoq-hr-day1` (HR, Junior HR/rekruter): profil va ball
  jadvali bo'yicha CV saralash, kamsituvchi filtr va tanish nomzod bosimi,
  ta'til kunlari va ta'til puli hisobi, noto'g'ri adresatga ketgan taklif xati.

Marketing/HR qoidalari ham o'quv maqsadidagi ichki siyosat, real qonunchilik
emas. Baholovchi soha bo'yicha tanlanadi (`app/ai/personas.for_sector`);
noma'lum soha — IT. Hujjat va brief matnida ketma-ket `a | b | c` qatorlar
jadval, ``` bloklari kod sifatida, chekinishli qatorlar alohida qator bo'lib ko'rsatiladi;
`A) Sarlavha. Izoh` bilan boshlanib, qolgan qatorlari chekinishli abzas — kartochka
(CV, profil: `YYYY-MM – YYYY-MM|hozir: ...` qatorlari vaqt chizig'i, `Kalit: qiymat` — maydon).

**v2:** `voice`/`image`/`video`; email/push bildirishnoma; murakkab
shartlar va ko'p yakunli ssenariylar; `meeting` (jonli savol-javob) node
turi. Ssenariy muharriri (admin UI) — §16.

### 9.12 Ochiq savollar (yozilgan, lekin hali hal qilinmagan)

- **Shaxsiy ma'lumotlar:** talaba matni va fayllari xorijiy AI API'larga
  ketadi — rozilik matni, saqlash muddati va O'zbekiston qonunchiligidagi
  lokalizatsiya talabi yurist bilan tekshirilsin.
- **Real vaqt va talabaning darslari:** pauza yo'q qaror qabul qilingan;
  pilotdan keyin "yonib ketgan" Run'lar ulushi kuzatilsin va kerak bo'lsa
  ssenariy dedlaynlari yumshatilsin.

### 9.13 Mentor (Modul 2 + 9)

Ssenariydagi `kind: mentor` personaj — talabaning ish joyidagi ustozi. U
oddiy hamkasbdan uchta narsa bilan farq qiladi; hammasi faqat ssenariyda
mentor bo'lsa ishlaydi (bo'lmasa — hech narsa yuborilmaydi).

1. **Talabaning ishini ko'radi.** Mentor chatining kontekstiga har
   yetkazilgan task/incident bo'yicha oxirgi urinish qo'shiladi: urinish
   raqami va qolgani, ball (jarimalar bilan), baholovchi izohi, eng past
   mezon va dalili, talaba javobining boshi (≤ 600 belgi, `<data>` ichida).
   Namunaviy javob va rubrikaning `reference_answer`i **kirmaydi**. Talaba
   "nega 60 oldim?" desa — mentor aynan shu ish asosida tushuntiradi.
2. **Har baholangan urinishdan keyin izoh** (`purpose=review`): baholash
   job'i (`evaluate_run_submission_job`) `completed` bo'lgach shu job ichida
   `scenario/mentor.py: post_review` chaqiriladi. Mentor chatiga 3–5 gaplik
   xabar: bitta aniq kuchli tomon → eng zaif mezon va real ishda nimaga
   olib kelishi → bitta yo'naltiruvchi savol; urinish qolgan va ball < 80
   bo'lsa — qayta topshirishga taklif. Ball raqami yozilmaydi (u task
   kartasida bor). Promptga brief, mezonlar (ball + dalil), talaba javobi
   (`<data>`), task'ning `hints`lari (yo'nalish uchun, so'zma-so'z emas)
   beriladi; namunaviy javob berilmaydi, chiqish baribir anti-spoiler
   (§9.4, 3-qavat) tekshiruvidan o'tadi.
   - Idempotent: `chat_messages.submission_id` UNIQUE — job qayta ishlasa
     ikkinchi izoh yozilmaydi. `day_end` va `decision` uchun izoh yo'q
     (ular kunlik hisobotda).
   - AI ishlamasa, token byudjeti (§9.4) tugagan bo'lsa yoki anti-spoiler
     bloklasa — skript izoh: baholovchining `short_feedback`i + (urinish
     qolgan bo'lsa) qayta topshirish taklifi. Izoh har doim yoziladi.
   - Tokenlar `runs.ai_tokens_used`ga qo'shiladi; kunlik AI xabar limitiga
     kirmaydi (talaba boshlamagan).
3. **Dedlayn eslatmasi** (`purpose=nudge`, LLM'siz, skript): task/incident
   yetkazilganda, dedlayn oynasi ≥ 45 ish daqiqasi bo'lsa,
   `run_events.result.nudge_at` = yetkazilgan payt + (oyna − min(30,
   oyna/3)) ish daqiqasi. Shu vaqt kelganda (`advance`, cron) hodisa hali
   `delivered` (topshirilmagan) va talaba yetkazilgandan beri **hech bir**
   personajga yozmagan bo'lsa — mentor chatiga eslatma (personajning
   `nudge_reply` shabloni, `{task}` va `{time}` bilan; standart matn bor).
   Har hodisaga ko'pi bilan bitta: `nudge_at` o'chirilib, `nudged_at` yoki
   `nudge_skipped` yoziladi.
4. SSE: ikkala xabar ham `chat_message` (`persona_key` bilan) — frontend
   o'qilmaganlar sonini oshiradi. Chat API `purpose` va `node_id`ni qaytaradi;
   frontend izohni "Task bo'yicha izoh", eslatmani "Eslatma" yorlig'i bilan
   ko'rsatadi, task kartasidagi baho ostida "Mentor bilan muhokama qilish"
   tugmasi mentor chatini ochadi.

---

## 10. Talent Hunt — Run natijalari asosidagi kandidat profili

Modul 4 (§6) eski `submissions` soniga emas, ssenariy dvigateli (§9)
natijalariga tayanadi. Maxfiylik qoidalari (§5, `candidate_visibility`)
o'zgarmaydi: yozuv yo'q yoki `is_open_to_work=false` — nomzod hech qayerda
ko'rinmaydi; yashirilgan kompaniya uchun "topilmadi" (404), "yashirilgan" emas.

### 10.1 Profil qanday hisoblanadi

- Faqat `status=completed` va `final_report` yozilgan Run'lar kiradi
  (sertifikatli ishlar; sertifikati bekor qilingani — yo'q, §13.1).
  `expired`/`abandoned` profilga chiqmaydi — talaba
  ochgan narsa uning portfoliosi, xatolar jurnali emas.
- Bir ssenariy bir necha marta o'tilgan bo'lsa — eng yuqori
  `overall_score`li Run olinadi.
- `overall_score` — tanlangan Run'lar `overall_score`ining o'rtachasi;
  `competencies` — har kompetensiya bo'yicha shu Run'lardagi ballar
  o'rtachasi (ma'lumot yo'q kompetensiya chiqmaydi); `sectors` — ssenariy
  sohalari.
- Kompaniyaga talabaning javoblari, chat va fayllari **ko'rsatilmaydi** —
  faqat ssenariy nomi, soha, sana, ball, kompetensiyalar va yakuniy
  hisobotdagi AI xulosasi (kuchli tomonlar).
- Modul 4 `runs`/`scenario_*` jadvallarini **faqat o'qiydi** (§9.10
  interfeysi); dvigatel kodiga tegmaydi.

### 10.2 Takliflar (`talent_offers`)

- Qo'shimcha ustunlar: `response` (`accepted|declined`, nullable),
  `response_note` (≤ 500 belgi), `responded_at`.
- Holat: `sent` → (talaba ochdi) `viewed` → (javob berdi) `responded`.
- `respond_due_at` = yuborilgan vaqt + **5 ish kuni** (§9.2 ish kalendari).
- Bir kompaniya bir nomzodga javob kutilayotgan (`sent|viewed`) taklif
  turganida yana yubora olmaydi — 409.
- Kontakt (email) kompaniyaga **faqat talaba `accepted` qilgandan keyin**
  ochiladi. Talaba taklifni rad etib, shu kompaniyadan yashirinishi mumkin
  (`hidden_from_company_ids`ga qo'shiladi) — shundan keyin u kompaniya
  nomzodni ro'yxatda ham, profilda ham ko'rmaydi.

### 10.3 Ruxsatlar

- `view_candidates` (`company_hr`): nomzodlar ro'yxati/profili, taklif
  yuborish, yuborilgan takliflar. Qo'shimcha shart: foydalanuvchi
  `org_type=company` va kompaniya `is_verified=true` (aks holda 403).
- `receive_offers` (**yangi**, `student`): o'z ko'rinish sozlamasi, o'z
  profili ko'rinishi, kelgan takliflar va ularga javob.
- `GET /users/me` javobiga `permissions: [key]` qo'shiladi — frontend
  menyuni shu ro'yxat bo'yicha quradi (rol nomi bo'yicha emas).

### 10.4 API

```
GET   /api/v1/users/me/visibility          receive_offers → {is_open_to_work, hidden_from_company_ids}
PATCH /api/v1/users/me/visibility          receive_offers
GET   /api/v1/users/me/talent-profile      receive_offers → o'z CandidateProfile'i (ko'rinishdan qat'i nazar)

GET   /api/v1/talents                      view_candidates
      ?sector=&competency=&min_score=&sort=score|recent&limit=&offset=
      → {items: [CandidateCard], total}
GET   /api/v1/talents/{user_id}            view_candidates → CandidateProfile | 404
POST  /api/v1/talents/offers               view_candidates; 404 ko'rinmasa; 409 javob kutilayotgan bo'lsa
GET   /api/v1/talents/offers/sent          view_candidates → kompaniya takliflari (+ email faqat accepted'da)

GET   /api/v1/talents/offers/my            receive_offers → kelgan takliflar (+ kompaniya nomi, sohasi)
POST  /api/v1/talents/offers/{id}/view     receive_offers; sent → viewed
POST  /api/v1/talents/offers/{id}/respond  receive_offers; {decision: accepted|declined, note?, hide_company?}
```

`CandidateCard`: `id, full_name, overall_score, runs_completed, sectors,
top_competencies (3 ta), last_completed_at`. `CandidateProfile`: kartadagi
hamma narsa + `competencies` (to'liq) + `runs: [{scenario_title,
company_name, sector, completed_at, overall_score, competency_scores,
strengths}]`. Ro'yxatda faqat kamida bitta tugallangan Run'i bor nomzodlar
chiqadi.

---

## 11. Tashkilotlar va admin panel (Modul 1, 3)

Talent Hunt (§10) va Universitet portali faqat **tasdiqlangan** tashkilotga
ochiladi. Bu bo'lim tashkilot ro'yxatdan o'tishidan to admin tasdiqlashi va
invoice'gacha bo'lgan oqimni brauzerda to'liq qiladi.

### 11.1 Ro'yxatdan o'tish

- `POST /auth/register-org` → **202** `{status: "pending", org_type, org_name}`;
  token **qaytarilmaydi** (foydalanuvchi `is_active=false`, token baribir
  ishlamasdi). Login 403 bilan "admin tasdiqlashini kutmoqda" deydi.
- Tashkilot nomi katta-kichik harfga qaramay takrorlanmaydi → 409.
- Talaba `/auth/register`da ixtiyoriy ravishda tasdiqlangan universitetni
  tanlaydi (`GET /university/list` — ochiq ro'yxat).

### 11.2 Admin: tashkilotlar

- `approve_companies` ruxsati kompaniya **va** universitetlarni boshqaradi
  (alohida `approve_universities` yaratilmaydi — bitta admin roli).
- `GET /admin/orgs?status=pending|verified` → `{companies, universities}`;
  har tashkilotda arizachi (`owner_name`, `owner_email`) bor.
- `POST /admin/orgs/{id}/approve {org_type}` — tasdiqlaydi, kutayotgan
  xodimlarini faollashtiradi.
- `POST /admin/orgs/{id}/reject {org_type}` — faqat tasdiqlanmagan ariza:
  tashkilot va uning hech qachon faollashmagan akkauntlari o'chiriladi
  (ular tizimda hech narsa qilmagan). Tasdiqlanganini rad etib bo'lmaydi → 409.
- `GET /admin/stats` (`approve_companies` yoki `manage_billing`): kutilayotgan
  arizalar, tasdiqlangan tashkilotlar, to'lanmagan invoice'lar soni.

### 11.3 Invoice'lar

- Faqat **tasdiqlangan** tashkilotga yoziladi (aks holda 400). Valyuta:
  `UZS` yoki `USD`; summa > 0, 2 xonagacha.
- Holatlar: `pending` → `paid` (mark-paid) yoki `pending` → `cancelled`
  (cancel). `paid`/`cancelled` qaytmaydi → 409 (paid'ni qayta mark-paid —
  o'zgarishsiz qaytariladi).
- `GET /admin/invoices?status=&payer_type=` — to'lovchi nomi bilan, yangilari
  tepada.
- `GET /billing/invoices` — **`view_org_invoices`** (yangi; `company_hr`,
  `university_admin`): faqat o'z tashkilotining invoice'lari.

### 11.4 Frontend

- `/register`: talaba | kompaniya | universitet; tashkilot arizasidan keyin
  "tasdiqlash kutilmoqda" ekrani.
- `/admin` (`approve_companies`): statistika, arizalar (tasdiqlash/rad etish),
  tasdiqlangan tashkilotlar, invoice'lar (yaratish, to'landi, bekor qilish).
- `/billing` (`view_org_invoices`): tashkilotning o'z invoice'lari.
- Kirishdan keyingi sahifa va menyu ruxsatga qarab: admin → `/admin`,
  kompaniya → `/talents`, universitet → `/university` (§12), talaba → `/simulations`.

---

## 12. Universitet portali (Modul 6)

Universitet o'z talabalarining ssenariy dvigateli (§9) natijalarini ko'radi:
kim qancha ish o'tdi, qanday ball oldi, qaysi kompetensiyalar kuchli. Eski
`submissions` asosidagi `/students/{id}/progress` va `/stats` olib tashlanadi
(`simulations` muzlatilgan, §9).

### 12.1 Kirish va bog'lanish

- Portal: `manage_universities` (`university_admin`) + `org_type=university`
  + universitet `is_verified=true` (aks holda 403).
- "Talaba" = `users.university_id = org_id` va `org_id IS NULL` (tashkilot
  xodimi emas). Bog'lanishni talaba o'zi qiladi: ro'yxatdan o'tishda yoki
  keyin `PATCH /users/me/university` orqali (**`join_university`** — yangi,
  `student`). Faqat tasdiqlangan universitetni tanlash mumkin (aks holda 404).
  Talaba bu yerda universiteti natijalarini ko'rishini ogohlantiriladi.
- Universitet noto'g'ri bog'langan talabani ajratadi
  (`DELETE /university/students/{id}` → `university_id=NULL`); akkaunt va
  natijalar o'chmaydi.
- `candidate_visibility` (§10) bu yerga ta'sir qilmaydi — u kompaniyalar
  uchun. Universitet ham javoblar, chat va fayllarni **ko'rmaydi**: faqat
  §10.1 profili (ssenariy, soha, sana, ball, kompetensiyalar, kuchli
  tomonlar), hozir ketayotgan ishlar (ssenariy nomi, holat, tugash vaqti)
  va kontakt (ism, email).
- Modul 6 `runs`/`scenario_*` jadvallarini faqat o'qiydi va profilni
  `app.talent.profile.build_profiles` orqali oladi (§10.1 bilan bir xil hisob).

### 12.2 API

```
GET    /api/v1/university/list               ochiq → tasdiqlangan universitetlar
GET    /api/v1/university/overview           manage_universities
       → {university, students_total, students_with_results, runs_completed,
          runs_in_progress, avg_score, sectors: [{sector, students, avg_score}],
          competencies: {key: avg}, top_students: [StudentRow] (5 ta)}
GET    /api/v1/university/students           manage_universities
       ?q=&sector=&has_results=&sort=score|recent|name&limit=&offset=
       → {items: [StudentRow], total}
GET    /api/v1/university/students/{id}      manage_universities → StudentDetail | 404
DELETE /api/v1/university/students/{id}      manage_universities → 204 | 404

GET    /api/v1/users/me/university           join_university → {university: University | null}
PATCH  /api/v1/users/me/university           join_university; {university_id: uuid | null}
```

`StudentRow`: `id, full_name, email, joined_at, overall_score,
runs_completed, runs_in_progress, sectors, top_competencies,
last_completed_at`. `StudentDetail`: qator + `competencies` (to'liq) +
`runs` (§10.4 `RunSummary`) + `in_progress: [{scenario_title, sector,
status, ends_at}]`. `avg_score` va `competencies` — natijasi bor talabalar
profillari o'rtachasi; natija yo'q bo'lsa `null` / `{}`.

### 12.3 Frontend

- `/university` (`manage_universities`): statistika, sohalar va
  kompetensiyalar kesimi, talabalar jadvali (qidiruv, soha, saralash),
  talaba profili dialogi va ajratish.
- Universitet xodimi kirgach `/university`ga tushadi; menyuda
  "Talabalar" va "To'lovlar".
- Talaba `/dashboard`da universitetini ko'radi va o'zgartiradi.

---

## 13. Sertifikat va portfolio (Modul 10)

Talaba tugatgan ishini platformadan tashqarida ko'rsata olishi kerak:
CV'ga, LinkedIn'ga yoki ish beruvchiga havola beradi, ular esa
sertifikat haqiqiyligini login'siz tekshiradi.

### 13.1 Sertifikat

- Har `status=completed` va `final_report.certificate=true` bo'lgan Run
  uchun **bitta** sertifikat (`certificates.run_id` UNIQUE). Dvigatel
  (Modul 9) yakuniy hisobotni yozgan tranzaksiyada
  `app.credentials.issue.issue_for_run(db, run)`ni chaqiradi; avval
  tugagan Run'lar migratsiyada to'ldiriladi. `expired`/`abandoned` —
  sertifikat yo'q.
- Kod: `TJ-XXXX-XXXX`, 8 belgi `23456789ABCDEFGHJKMNPQRSTUVWXYZ`
  alifbosidan (`secrets`, adashtiradigan 0/O/1/I/L yo'q), UNIQUE. Qidiruvda
  katta-kichik harf va bo'shliq farq qilmaydi.
- Sertifikat — **berilgan paytdagi surat** (snapshot): egasining ismi,
  ssenariy nomi, kompaniya (fictional), soha, daraja, davomiyligi,
  tugallangan sana, `overall_score`, `competency_scores`. Keyin ssenariy
  yoki ism o'zgarsa ham sertifikat o'zgarmaydi.
- Ochiq tekshiruv (`GET /certificates/{code}`) faqat shu suratni va holatni
  qaytaradi: email, javoblar, chat, fayllar, hisobot matni **yo'q**.
- Bekor qilish: admin (`manage_certificates` — yangi, `admin`) sabab bilan
  bekor qiladi (masalan, ko'chirmachilik). Tekshiruvda "bekor qilingan" va
  sabab ko'rinadi. Bunday Run §10.1 profiliga (kompaniya, universitet,
  portfolio) kirmaydi. Qayta tiklash yo'q.

### 13.2 Portfolio

- Talabaning ochiq sahifasi `/p/{slug}` — **default yopiq (opt-in)**,
  `candidate_visibility` (§10) dan alohida: portfolio ochiqligi kompaniyalar
  ro'yxatiga ta'sir qilmaydi va aksincha.
- `portfolios`: `user_id` (PK), `slug` (UNIQUE, `^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$`),
  `is_public` (default false), `headline` (≤ 120), `about` (≤ 1000),
  `links` (≤ 3 ta `{label ≤ 40, url}`; faqat `https://`), `updated_at`.
  Band slug — 409.
- Ochiq sahifada: ism, headline, about, havolalar, universitet (bog'langan va
  tasdiqlangan bo'lsa), §10.1 profili (umumiy ball, kompetensiyalar,
  sohalar) va bekor qilinmagan sertifikatlar (yangisi birinchi). Email va
  javoblar **yo'q**. Yopiq yoki mavjud bo'lmagan slug — bir xil 404.
- Ruxsat: `manage_portfolio` (**yangi**, `student`) — o'z sertifikatlari va
  portfolio sozlamalari.

### 13.3 API

```
GET  /api/v1/certificates/{code}                 ochiq → CertificatePublic | 404
GET  /api/v1/portfolios/{slug}                   ochiq → PortfolioPublic | 404

GET  /api/v1/users/me/certificates               manage_portfolio → [Certificate] (bekor qilinganlar ham)
GET  /api/v1/users/me/portfolio                  manage_portfolio → PortfolioSettings
     (yozuv yo'q bo'lsa: is_public=false va ismdan taklif qilingan slug)
PUT  /api/v1/users/me/portfolio                  manage_portfolio; {slug, is_public, headline, about, links} → 409 band slug

POST /api/v1/admin/certificates/{code}/revoke    manage_certificates; {reason ≤ 300} → Certificate | 404 | 409 allaqachon
```

`CertificatePublic`: `code, status (valid|revoked), holder_name,
scenario_title, company_name, sector, difficulty, duration_days,
completed_at, issued_at, overall_score, competency_scores, revoked_at,
revoked_reason`. `Certificate` (talabaga): shu + `run_id`.
`PortfolioPublic`: `slug, full_name, headline, about, links, university,
overall_score, competencies, sectors, certificates: [CertificatePublic]`.

### 13.4 Frontend

- `/c/{code}` (ochiq): sertifikat varag'i — chop etish/PDF (`window.print`,
  A4 albom), shu sahifaga olib boradigan QR, holat belgisi, havolani
  nusxalash; kod bo'yicha qidirish formasi (topilmasa).
- `/p/{slug}` (ochiq): portfolio sahifasi.
- `/portfolio` (`manage_portfolio`): sertifikatlarim (ochish, havolani
  nusxalash, LinkedIn'ga "Add to profile" — faqat egasiga, ochiq sahifada
  emas) va portfolio sozlamalari; menyuda "Portfolio".
- Run hisobotida (`/runs/{id}/report`) sertifikat bo'lsa — unga havola va
  LinkedIn tugmasi.

---

## 14. Landing sahifa (Modul 7 + 9)

Kirmagan mehmon uchun `/` — platformaning ochiq bosh sahifasi. Kirgan
foydalanuvchi `/`dan o'z bosh sahifasiga yo'naltiriladi (talaba — `/dashboard`,
qolganlar — §11.4 `homeFor`); `/dashboard` faqat kirganlar uchun.

### 14.1 `GET /api/v1/showcase` (ochiq)

Faqat nashr qilingan (`published`, `is_active`) ssenariylar va umumiy
sonlar; shaxsiy ma'lumot yo'q. `Cache-Control: public, max-age=300`.

```
Showcase: {
  stats: { scenarios, sectors, completed_runs },
  scenarios: [ShowcaseScenario]           # sarlavha bo'yicha
}
ShowcaseScenario: { slug, title, sector, company_name, difficulty,
  duration_days, tasks,                   # task + incident + decision soni
  mentor: { name, role } | null,
  day1: [{ at: "HH:MM", type, title }] }  # 1-kunning `day`+`at` node'lari, vaqt bo'yicha
```

`day1[].title` — faqat `message` va `task` uchun `short_title(brief)`;
`incident` va `decision` uchun `null` (kutilmagan vaziyat oldindan
oshkor qilinmaydi, frontend "Kutilmagan vaziyat" / "Qaror" deb yozadi).
`after` bilan keladigan node'lar ro'yxatga kirmaydi. Rubrika, hint,
namunaviy javob, hujjat va personaj `knows`/`secrets` hech qachon chiqmaydi.

### 14.2 Bo'limlar

1. **Hero**: sarlavha, qisqa izoh, "Bepul boshlash" (`/register`) va
   "Kompaniyalar uchun" (pastdagi bo'limga); yonida tanlangan ssenariyning
   1-kun jadvali "ish stoli" ko'rinishida (Toshkent vaqti bilan joriy payt
   belgisi).
2. **Raqamlar**: ssenariylar, sohalar, ish kuni 09:00–18:00, AI mentor.
   `completed_runs` 100 dan kam bo'lsa ko'rsatilmaydi.
3. **Sohalar**: har soha kartasi va undagi ssenariylar (showcase'dan).
4. **Qanday ishlaydi**: ssenariy tanlash → real vaqtda ish kuni → AI baholash
   va mentor izohi → sertifikat va portfolio → kompaniya takliflari.
5. **Sertifikat**: namuna varaq (`CertificateSheet`, "Namuna" belgisi bilan,
   fictional ism) va kod bo'yicha tekshirish formasi (§13.4).
6. **Kimlar uchun**: talaba (bepul, §1), kompaniya (Talent Hunt §10,
   `/register?as=company`), universitet (portal §12, `/register?as=university`).
7. **Savol-javob** va footer.

Barcha matn uz/ru/en; kompaniya nomlari faqat ssenariylardagi fictional nomlar.

---

## 15. Bildirishnomalar (Modul 11)

Run'lar real vaqtda ketadi va pauza yo'q (§9.2) — talaba saytda bo'lmasa
ham muhim narsadan xabar topishi kerak. Ikki kanal: ilova ichida
(qo'ng'iroqcha) va email. SSE (§9.8) o'zgarmaydi — u faqat ochiq Run
sahifasi uchun.

### 15.1 Ma'lumot

`notifications`: `id, user_id (FK, index), kind, params JSONB, link,
dedupe_key, created_at, read_at, email_status (null | sent | skipped |
failed), emailed_at`; `UNIQUE(user_id, dedupe_key)` — bitta hodisa uchun
bitta bildirishnoma (job qayta ishlasa ham). Matn saqlanmaydi: frontend
`kind` + `params`dan interfeys tilida yozadi, email o'zbekcha.

`notification_settings`: `user_id (PK), email_enabled (default true),
email_kinds JSONB` — qator yo'q bo'lsa default'lar.

### 15.2 Turlar va manbalar

| kind | Kimga | Qachon | params | Email default |
|---|---|---|---|---|
| `task_delivered` | talaba | task/incident/decision yetkazildi (`event_delivered`) | run_id, node_id, type, title, due_at | yo'q |
| `deadline_soon` | talaba | yetkazilgan, topshirilmagan hodisa dedlayniga ≤ 30 daqiqa qoldi (cron) | run_id, node_id, title, due_at | ha |
| `mentor_review` | talaba | mentor baholangan urinishga izoh yozdi (§9.13) | run_id, node_id, title, mentor | yo'q |
| `report_ready` | talaba | yakuniy hisobot yozildi | run_id, scenario_title, certificate, code | ha |
| `offer_received` | talaba | kompaniya taklif yubordi (§10.2) | offer_id, company, position | ha |
| `offer_responded` | kompaniyaning faol xodimlari (taklifni kim yuborgani saqlanmaydi) | talaba javob berdi | offer_id, candidate, position, accepted | ha |

`dedupe_key`: `event:{run_id}:{node_id}:delivered`, `event:{run_id}:{node_id}:deadline`,
`review:{submission_id}`, `final:{run_id}`, `offer:{id}`, `offer:{id}:response`.
`title` — `short_title(brief)`; incident/decision nomi bildirishnomada
ko'rsatiladi (u allaqachon yetkazilgan). `task_delivered` faqat cron yetkazgan
hodisalar uchun: talaba Run sahifasida turganda (API `advance`) yetkazilgani
uning ko'z oldida — bildirishnoma yozilmaydi.

Yozish: `app/notifications/service.py: notify(db, user_id, kind, params,
link, key)` — `INSERT … ON CONFLICT DO NOTHING`, chaqiruvchining
tranzaksiyasida. Chaqiruvchilar: `scenario/jobs.py` (yetkazish cron'i,
mentor izohi, yakuniy hisobot), `api/talent_hunt.py` (taklif, javob),
`notifications/jobs.py: deadline_reminders` (har daqiqa).

### 15.3 Email

SMTP `.env`dan: `SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD,
SMTP_FROM, SMTP_STARTTLS (true)`, havolalar uchun `PUBLIC_URL`. `SMTP_HOST`
bo'sh — email o'chirilgan (faqat ilova ichida). Cron `send_notification_emails`
(har daqiqa): `email_status IS NULL` va 1 soatdan yangi bildirishnomalar,
50 tadan; foydalanuvchi email'ni o'chirgan yoki tur yoqilmagan — `skipped`,
yuborildi — `sent`, xato — `failed` (qayta urinilmaydi, log). Stdlib
`smtplib` (`asyncio.to_thread`), yangi kutubxona yo'q.
Modul 8: `deploy/docker-compose.yml` va `.env.example`ga `SMTP_*`, `PUBLIC_URL`.

### 15.4 API (kirgan foydalanuvchi, faqat o'ziniki)

```
GET  /api/v1/users/me/notifications?limit=20&before={iso}  → {items, unread}
GET  /api/v1/users/me/notifications/unread                 → {unread}
POST /api/v1/users/me/notifications/read   {ids: [uuid]} | {all: true} → {unread}
GET  /api/v1/users/me/notification-settings               → {email_enabled, email_kinds, available}
PUT  /api/v1/users/me/notification-settings               {email_enabled, email_kinds} → shu
```

`available` — foydalanuvchiga tegishli turlar (talaba: birinchi 5 ta,
`view_candidates`: `offer_responded`); boshqa tur yuborilsa 422.

### 15.5 Frontend

Navbar'da qo'ng'iroqcha (kirganlar uchun): o'qilmaganlar soni, ochilganda
oxirgi 10 ta; bosilsa `link`ga o'tadi va o'qilgan bo'ladi; "Hammasini
o'qildi". Soni har 60 soniyada va oyna fokusga qaytganda yangilanadi.
`/notifications`: to'liq ro'yxat va email sozlamalari.

---

## 16. Ssenariy muharriri (Modul 9 + 7)

Admin (`manage_simulations`) ssenariyni brauzerda yaratadi va tahrirlaydi —
YAML fayl va `tools/import_scenario.py` ixtiyoriy bo'lib qoladi. Manba va
qoidalar o'zgarmaydi: ta'rif — §9.3 sxemasi (`ScenarioDefinition`),
tekshiruv — o'sha validatorlar, versiyalash — §9.3.1.

### 16.1 Versiyalar

- `published` va `archived` versiya o'zgarmas (unga Run'lar bog'langan).
- Tahrir **qoralama**ga yoziladi: oxirgi versiya `draft` bo'lsa — o'sha
  joyida yangilanadi (ta'rif, hujjatlar va bo'laklar qayta yoziladi),
  aks holda yangi `draft` versiya ochiladi. Qoralamaga Run bog'lanmaydi
  (katalogda faqat `published`).
- Mavjud ssenariyning `slug`i o'zgarmaydi (boshqa slug — 422); yangi
  ssenariy band slug bilan — 409.
- Nashr — §9.3.1 `publish_version` (avvalgi `published` → `archived`).
- `is_active=false` — ssenariy katalog va landingdan yashiriladi, boshlangan
  Run'lar davom etadi.

### 16.2 API (`manage_simulations`)

```
GET    /api/v1/admin/scenarios                          ro'yxat: versiyalar, Run'lar soni
POST   /api/v1/admin/scenarios                          {definition} → yangi ssenariy, v1 draft; 409 slug band
GET    /api/v1/admin/scenarios/{id}/versions/{v}        {version, status, definition, warnings}
PUT    /api/v1/admin/scenarios/{id}/draft               {definition} → qoralama (16.1)
POST   /api/v1/admin/scenarios/{id}/versions/{v}/publish   409 — arxivlangan
PATCH  /api/v1/admin/scenarios/{id}                     {is_active}
POST   /api/v1/admin/scenarios/validate                 {definition} → {ok, errors, warnings, summary} (DB'ga yozmaydi)
POST   /api/v1/admin/scenarios/yaml                     {text} → {definition | null, errors} (YAML → ta'rif)
POST   /api/v1/admin/scenarios/to-yaml                  {definition} → {text} (saqlanmagan holat ham; noto'g'ri ta'rif — xom holicha)
GET    /api/v1/admin/scenarios/{id}/versions/{v}/yaml   text/yaml — content/ uchun eksport
```

`errors[]`: `{path: [str|int], message}` — Pydantic `loc` (masalan
`["nodes", 3, "due_in_minutes"]`); ta'rif darajasidagi xatoda `path` bo'sh,
xabar node id bilan boshlanadi (`"bug_orders: ..."`). Saqlash va nashr
noto'g'ri ta'rifni 422 bilan rad etadi (xuddi shu `errors` bilan).
`summary`: `{days, nodes, graded, personas, documents, mentor}`.

### 16.3 Frontend

`/admin/scenarios` — ro'yxat (holat, versiyalar, faollik, tahrirlash, yangi).
`/admin/scenarios/new`, `/admin/scenarios/{id}/edit` — muharrir:
- bo'limlar: umumiy ma'lumot, personajlar, hujjatlar, node'lar (kunlar
  bo'yicha vaqt chizig'i), YAML (to'liq matn, ikki tomonlama);
- har o'zgarishdan keyin (debounce) `validate`: xatolar ro'yxati, bosilsa
  tegishli bo'lim/node ochiladi; node ro'yxatida xatoli node belgilanadi;
- node formasi turga qarab: vaqt (`day`+`at` yoki `after`), kimdan, brief
  (talabaga qanday ko'rinishi — `RichText` oldindan ko'rinishi), ilovalar,
  javob turlari, dedlayn, vazn, kompetensiyalar, rubrika, hintlar, namunaviy
  javob, decision variantlari, `when` sharti (oddiy shartlar uchun
  konstruktor, murakkabi — JSON); `checks` faqat YAML bo'limida;
- "Qoralamani saqlash" va "Nashr qilish" (tasdiq bilan); nashr qilingan
  versiyani ochganda tahrir yangi qoralama bo'lib saqlanadi.

---

## 17. Talaba analitikasi (Modul 12 + 7)

Talaba o'z o'sishini ko'radi: ball va kompetensiyalar Run'dan Run'ga qanday
o'zgargan, qaysi kompetensiya eng zaif va uni qaysi ssenariy mashq qildiradi.
Hisob §10.1 bilan bir xil manbadan, lekin **barcha** tugallangan Run'lar
olinadi (profil kabi "eng yaxshisi" emas) — o'sish aynan qayta urinishlarda
ko'rinadi.

### 17.1 Manba

- Faqat o'z Run'lari, `status=completed`, `final_report` yozilgan,
  sertifikati bekor qilinmagan (§13.1). `expired`/`abandoned` hisobga
  kirmaydi; joriy (`scheduled`/`active`) Run'lar faqat soni bilan.
- Vaqt o'qi — `completed_at` (`last_activity_at`), o'sish tartibida.
- Kompetensiya: har Run'ning `competency_scores`i. `first` — birinchi
  qiymat (boshlang'ich nuqta); `current` — undan **keyingi** oxirgi 3 ta
  qiymat o'rtachasi (bitta qiymat bo'lsa — o'sha qiymat); `delta = current −
  first` (kamida 2 qiymat bo'lsa, aks holda `null`). Birinchi qiymat
  `current`ga kirmaydi — aks holda 60 → 80 o'sishi "+10" ko'rinardi.
  `trend` shu `delta`dan: ±3 ichida `flat`, katta — `up`, kichik — `down`,
  bitta qiymat — `new`.
- **Fokus**: `current` bo'yicha eng past 2 ta kompetensiya (ma'lumot bor
  bo'lsa), har birida `trend`.
- **Maslahatlar**: oxirgi Run yakuniy hisobotidagi AI `improvements`
  (≤ 4 ta, o'zgartirilmagan holda).
- **Tavsiya**: nashr qilingan, faol ssenariylardan talaba hali
  tugatmaganlari; har biri fokus kompetensiyalarini baholanadigan
  node'larida necha marta mashq qildirishi bo'yicha saralanadi (teng
  bo'lsa — sarlavha), ko'pi bilan 3 ta; birorta fokus kompetensiyasi
  yo'q ssenariy tavsiya qilinmaydi. Fokus bo'lmasa (hali Run yo'q) —
  tavsiya ham yo'q, frontend katalogga yuboradi.

### 17.2 API

```
GET /api/v1/users/me/analytics          kirgan foydalanuvchi, faqat o'ziniki
→ {
    summary: { completed, in_progress, avg_score, best_score, on_time_rate, certificates },
    timeline: [{ run_id, scenario_title, sector, completed_at, overall_score,
                 on_time_rate, competency_scores }],          # eskidan yangiga
    competencies: [{ key, current, first, delta, trend, values: [number] }],   # current bo'yicha kamayish
    sectors: [{ sector, runs, avg_score }],
    focus: [{ key, current, trend }],
    improvements: [string],
    recommendations: [{ scenario_id, title, sector, company_name, duration_days,
                        difficulty, practices: { competency: count } }]
  }
```

`avg_score`, `on_time_rate` — Run'lar o'rtachasi (ma'lumot yo'q — `null`);
`on_time_rate` — foiz (0–100), §9.6 hisobotidagi kabi.

### 17.3 Frontend

`/dashboard` (talaba) — "Mening o'sishim": umumiy raqamlar, ball chizig'i
(har nuqta — Run, bosilsa hisobot), kompetensiyalar (joriy qiymat, o'zgarish,
mini-chiziq), fokus va AI maslahatlari, tavsiya qilingan ssenariylar
("Boshlash" — `POST /runs`, ochiq Run bo'lsa 409 xabari), sohalar,
oxirgi ishlar va universitet kartasi. Grafiklar SVG, kutubxonasiz.

## 18. Ishga tushirish (Modul 8 + 1)

Pilot uchun bitta server (Docker Compose). Maqsad: HTTPS, kunlik zaxira
nusxa, holatni kuzatish va takrorlanadigan yangilash tartibi —
qo'shimcha xizmat (Kubernetes, tashqi monitoring) talab qilinmaydi.

### 18.1 Holat (`GET /api/v1/health`, ochiq)

`{status: "ok" | "degraded", db, redis, worker}` — har biri `bool`.
`db`: `SELECT 1`; `redis`: `PING`; `worker`: arq worker'ning health-check
kaliti Redis'da bor (worker o'lsa real vaqtdagi hodisalar yetkazilmaydi,
§9.2 — shuning uchun u ham majburiy). Hammasi `true` — 200, aks holda 503.
Ichki tafsilot (xato matni, versiya) qaytarilmaydi. Compose healthcheck va
tashqi uptime monitor shu manzilni tekshiradi.

`DOCS_ENABLED` (default `true`): `false` bo'lsa `/docs`, `/redoc`,
`/openapi.json` o'chiriladi (production `.env.example`da `false`).

### 18.2 HTTPS

`deploy/docker-compose.https.yml` (qo'shimcha fayl): Caddy `DOMAIN` uchun
Let's Encrypt sertifikatini o'zi oladi va yangilaydi, `frontend` (nginx)ga
proksilaydi; `frontend` tashqi portni ochmaydi. SSE uchun `flush_interval -1`.
HSTS Caddy'da.

### 18.3 Zaxira nusxa

`backup` servisi (Postgres image, `deploy/backup.sh`): har kuni
`BACKUP_HOUR` (Toshkent vaqti, default 03) da `pg_dump -Fc` va `uploads`
volume'ining `tar.gz`i `deploy/backups/`ga; `BACKUP_KEEP_DAYS` (default 14)
dan eskilari o'chiriladi. Fayl avval `.partial` bo'lib yoziladi — yarim
qolgan nusxa hech qachon to'liqdek ko'rinmaydi. Qo'lda: `backup.sh now`.
Tiklash tartibi `deploy/README.md`da. Serverdan tashqariga ko'chirish
(off-site) — operator vazifasi, README'da tavsiya.

### 18.4 Boshqa

- Barcha servislarda log rotatsiya (`json-file`, 10 MB × 5).
- `worker` healthcheck: `arq --check`.
- Ssenariy kontenti birinchi ishga tushirishda `import_scenario.py --publish`
  bilan yuklanadi; keyin ssenariylar muharrirda (§16) o'zgartiriladi —
  qayta import muharrirdagi nashrni fayldagisi bilan almashtiradi, shuning
  uchun avtomatik import yo'q.
- `definition_for` keshi kaliti `(versiya id, created_at)`: bir nechta API
  jarayoni va worker bo'lsa ham qoralama tahriridan keyin eski ta'rif
  ishlatilmaydi (§16.1).

---

## 19. Kod tekshiruvi va sandbox (Modul 13 + 9 + 1)

Talaba kodi backend jarayonida emas, alohida **runner** konteynerida
bajariladi. `code` javobli task'larda ssenariy muallifi yozgan yashirin
testlar ishlaydi va natija baholashga qo'shiladi (§9.6 "avval
deterministik `checks`").

### 19.1 Runner (`sandbox/runner.py`, `deploy/sandbox.Dockerfile`)

- Runner kodi faqat stdlib (Python 3.13), `ThreadingHTTPServer`, port 8100;
  image'da talaba kodi uchun `pytest` bor (o'z testlarini import qilsa yiqilmasin).
  `POST /run`, `Authorization: Bearer <SANDBOX_TOKEN>` (`hmac.compare_digest`);
  token bo'sh bo'lsa runner ishga tushmaydi. `GET /health` — ochiq, `{ok}`.
- So'rov: `{code, tests?, module?, timeout?}` (tana ≤ 256 KB). `tests` yo'q —
  **skript rejimi** (`code` bajariladi); bor — **test rejimi**: `code`
  `{module}.py` (standart `solution`) bo'lib yoziladi, `tests` ichidagi
  `test_*` funksiyalari e'lon tartibida chaqiriladi.
- Javob: `{status, stdout, stderr, passed, total, tests: [{name, ok, message}]}`;
  `status`: `ok` (kod/testlar ishga tushdi; testlar yiqilgan bo'lishi
  mumkin) `| error` (import/sintaksis xatosi — barcha testlar yiqilgan
  hisoblanadi) `| timeout`. stdout ≤ 4 KB, stderr ≤ 2 KB, `message` ≤ 300 belgi.
- Har so'rov: yangi vaqtinchalik papka (`/tmp`, tmpfs), alohida `python -I`
  jarayoni, bo'sh muhit o'zgaruvchilari, rlimit: CPU = timeout, xotira
  256 MB, fayl 1 MB, yangi jarayon 0, fayl deskriptor 32. Timeout: skript
  ≤ 3 s, test ≤ 10 s (server cheklaydi). Bir vaqtda ≤ 2 bajarish, ortig'i —
  503 `busy`.
- Konteyner: `read_only`, `/tmp` tmpfs (64 MB), root emas (uid 10002),
  `cap_drop: ALL`, `no-new-privileges`, `pids_limit`, xotira va CPU limiti,
  volume va secret yo'q (faqat `SANDBOX_TOKEN`).
- Tarmoq: runner faqat `sandbox` ichki tarmog'ida (`internal: true`) —
  internetga, Postgres va Redis'ga chiqa olmaydi. `backend` va `worker`
  ikkala tarmoqda. **Qolgan xavf:** runner ichidagi kod `backend:8000` API'ga
  ulana oladi (internetdagi har kim kabi, auth va rate-limit amal qiladi).
- Test natijasi xavfsizlik chegarasi emas: talaba kodi test bilan bitta
  jarayonda ishlaydi va natijani soxtalashtirishga urinishi mumkin. Natija
  satri tasodifiy nonce bilan belgilanadi (oddiy `print` bilan
  soxtalashtirib bo'lmaydi); baribir test balli rubrika bahosi bilan
  birga ishlatiladi va kod LLM baholovchiga to'liq ko'rinadi.

### 19.2 Backend mijozi (`app/core/sandbox.py`)

- `SANDBOX_URL` (masalan `http://sandbox:8100`) va `SANDBOX_TOKEN` `.env`dan.
  Compose ikkalasini majburiy qiladi.
- `SANDBOX_URL` bo'sh — **faqat lokal ishlab chiqish va testlar uchun**:
  skript rejimi shu jarayonda subprocess (AST filtri + rlimit,
  izolyatsiyasiz, `asyncio.to_thread` orqali — event loop to'xtamaydi);
  test rejimi o'chiq (`checks` o'tkazib yuboriladi, `status: "disabled"`).
  Lokal testlar kerak bo'lsa runner'ni o'zi ishga tushiriladi:
  `SANDBOX_TOKEN=dev python sandbox/runner.py`.
- Runner javob bermasa/503 — `SandboxUnavailable`.
- `POST /api/v1/tools/sandbox` (auth + Redis rate-limit, o'zgarishsiz) skript
  rejimida shu mijozdan foydalanadi; AST filtri runner oldidan ham qo'llanadi
  (qo'shimcha qatlam). Test rejimida AST filtri yo'q — talaba kodi oddiy
  importlarni ishlatadi, himoya — konteyner.

### 19.3 Ssenariy: `checks`

```yaml
checks:
  module: solution        # talaba kodi fayl nomi (standart)
  weight: 0.5             # task ballidagi ulushi (0 < w ≤ 1, standart 0.5)
  tests: |
    from solution import calculate_total, Item, Promo
    def test_percent_not_on_delivery():
        assert calculate_total([Item(80000, 1)], 15000, Promo("S", "percent", 20, 0)) == 79000
```

`checks` faqat `answer_types`da `code` bo'lgan `task`/`incident`da; `tests`da
kamida bitta `test_*` funksiya (import paytida AST bilan tekshiriladi).
`checks` testlari talabaga, RAG'ga, mentorga va API'ga **hech qachon**
berilmaydi (§9.4 anti-spoiler) — faqat test **nomlari** va o'tdi/yiqildi.

### 19.4 Baholash

- `submissions.code` (yangi ustun): talabaning `code` javobi alohida
  saqlanadi (`content`da ham avvalgidek).
- `checks` bor node'da baholash oldidan runner chaqiriladi →
  `submissions.check_results = {status, passed, total, failed: [nom]}`.
  Kod topshirilmagan bo'lsa — `{status: "no_code", passed: 0, total: N}`.
- Runner ishlamasa — AI xatosi kabi `queued_retry`; oxirgi urinishda ham
  ishlamasa testlarsiz (faqat rubrika) baholanadi,
  `check_results.status = "unavailable"`. Runner sozlanmagan
  (`SANDBOX_URL` bo'sh) — darhol `"disabled"`, faqat rubrika.
- Test natijasi LLM baholovchiga javob oxirida qisqa satr bo'lib beriladi
  (`[Avtomatik testlar: 5/7 o'tdi; yiqilgan: …]`); mentor (§9.13) talaba
  ishi xulosasida xuddi shu satrni oladi.
- Xom ball = `(1 − w) × rubrika + w × 100 × passed/total`; jarimalar
  (§9.6) shundan keyin. `unavailable`/`disabled` — faqat rubrika.
- `submission_evaluated` hodisasi va `EventOut.last_checks`:
  `{status, passed, total, failed}` (`unavailable`/`disabled` — `null`);
  hisobotdagi task natijasida `checks` (oxirgi baholangan urinishniki).

### 19.5 Frontend

Run sahifasida task tafsilotida va hisobotda: "Avtomatik testlar: 5/7" va
yiqilgan test nomlari.


## 20. Kompaniya hisobotlari (Modul 4 + 7)

Kompaniya Talent Hunt (§10) natijasini bir sahifada ko'radi: unga ochiq
nomzodlar bazasi qanday (soha, ball, kompetensiyalar) va yuborgan
takliflari qayerga yetib bordi (ko'rildi, javob, qabul). Ssenariylar
platformaniki (§9), kompaniyaga tegishli emas — shuning uchun hisobot
"kompaniya ssenariylari" emas, **nomzodlar bazasi + takliflar voronkasi**.

### 20.1 Manba va maxfiylik

- Ruxsat va shart §10.3 bilan bir xil: `view_candidates` + tasdiqlangan
  kompaniya (aks holda 403). Yangi ruxsat yo'q.
- **Baza** — faqat shu kompaniyaga hozir ko'rinadigan nomzodlar (§10:
  `is_open_to_work`, yashirmagan, faol), profil §10.1 hisobidan
  (`build_profiles`). Ko'rinmaydigan nomzod hech qaysi songa kirmaydi —
  aks holda yashiringan talabalar soni "oqib" chiqardi.
- **Takliflar** — faqat shu kompaniyaning `talent_offers` yozuvlari.
  Nomzod keyin yashiringan bo'lsa ham taklif statistikasi saqlanadi
  (bu kompaniyaning o'z harakati), lekin ism va email §10.2 qoidasida:
  email faqat `accepted`da.
- Davr (`days`): takliflar `created_at` bo'yicha oxirgi N kunda; baza —
  joriy holat, davr unga faqat `active_in_period` (shu davrda Run tugatgan
  nomzodlar) soni orqali ta'sir qiladi. `days` berilmasa — butun tarix.

### 20.2 Ko'rsatkichlar

- `pool`: `candidates`, `active_in_period`, `avg_score` (profillar
  `overall_score` o'rtachasi), `score_bands` — `0–49`, `50–69`, `70–84`,
  `85–100` oraliqlarida nomzodlar soni (balli yo'q nomzod kirmaydi),
  `sectors: [{sector, candidates, avg_score}]` (nomzod har sohasida
  sanaladi), `competencies: {key: avg}`.
- `offers` (davr ichida): `sent` (hammasi), `viewed` (`viewed` yoki
  `responded`), `responded`, `accepted`, `declined`, `pending`
  (`sent|viewed`), `overdue` (pending va `respond_due_at` o'tgan),
  `response_rate = responded / sent`, `acceptance_rate = accepted /
  responded` (foiz, 0–100, maxraj 0 bo'lsa `null`),
  `median_response_hours` — `responded_at − created_at` medianasi
  (kalendar soatlari, 1 xona; javob bo'lmasa `null`).
- `by_position: [{position_title, sent, accepted, declined, pending}]` —
  lavozim nomi bo'yicha (katta-kichik harf va chetdagi bo'sh joy
  farqlanmaydi, ko'rsatishda eng ko'p yozilgani), `sent` kamayishi bo'yicha.
- `by_month: [{month: "YYYY-MM", sent, accepted, declined}]` — Toshkent
  vaqti bo'yicha oy, eskidan yangiga, bo'sh oylar ham (0) kiradi.

### 20.3 API

```
GET /api/v1/talents/report                 view_candidates; ?days=1..3650
    → {company, generated_at, days, pool, offers, by_position, by_month}
GET /api/v1/talents/report/offers.csv      view_candidates; ?days=
    created_at, position_title, candidate_name, status, response,
    respond_due_at, responded_at, response_hours, candidate_email (faqat accepted)
GET /api/v1/talents/report/candidates.csv  view_candidates
    full_name, overall_score, runs_completed, sectors, <har kompetensiya>, last_completed_at
```

CSV: UTF-8 BOM bilan (Excel kirill/o'zbek harflarini to'g'ri ochadi),
`Content-Disposition: attachment`, vaqtlar Toshkent vaqtida. `= + - @`
(va tab/CR) bilan boshlanadigan matn katakchasi oldiga `'` qo'yiladi —
CSV/formula injection'ga qarshi (ism va lavozim foydalanuvchi matni).
Nomzodlar CSV'sida email yo'q (§10.2).

### 20.4 Frontend

`/talents/report` (`view_candidates`), menyuda "Hisobot": davr tanlovi
(30 / 90 / 365 kun / hammasi), takliflar voronkasi va asosiy raqamlar,
oylar bo'yicha takliflar, lavozimlar jadvali, baza kesimi (ball
oraliqlari, sohalar, kompetensiyalar) va ikkala CSV yuklab olish tugmasi.
Grafiklar SVG/CSS, kutubxonasiz.

## 21. Platforma statistikasi (Modul 2 + 12 + 3 + 7)

Admin pilotni bitta sahifadan kuzatadi: kim keldi, Run'lar qanday tugayapti,
baholash navbati tiqilmaganmi va AI qancha token/pul sarflayapti. Mavjud
`GET /admin/stats` (§11.2, arizalar va invoice'lar) o'zgarmaydi.

### 21.1 AI sarfi hisobi (Modul 2)

- Yangi jadval `ai_usage`: `day` (DATE, Toshkent kuni), `provider`, `model`,
  `purpose`, `calls`, `failures`, `tokens_in`, `tokens_out`; PK
  `(day, provider, model, purpose)`. Bir kun-provayder-model-maqsad uchun bitta
  qator, `INSERT … ON CONFLICT DO UPDATE` bilan oshiriladi.
- `ai/llm.py` `chat(..., purpose=)`: `evaluation` (rubrika), `persona`
  (personaj javobi), `mentor`, `day_report`, `final_report`; berilmasa
  `other`. Muvaffaqiyatli javob — `calls + 1` va tokenlar; provayder xatosi
  yoki yaroqsiz javob — shu provayderga `failures + 1` (keyingi provayderga
  o'tiladi, §9.10).
- Yozuv alohida qisqa sessiyada; yozib bo'lmasa — log, `chat` natijasi
  o'zgarmaydi (hisob AI ishini hech qachon to'xtatmaydi). Xabar matni,
  foydalanuvchi yoki Run id **saqlanmaydi** — faqat yig'indi sonlar.
- Narx: `.env` `LLM_PRICES` — `provider=kirish/chiqish` (1M token uchun USD),
  vergul bilan, masalan `deepseek=0.27/1.10,gemini=0.10/0.40`. Narxi yo'q
  provayder qatorida `cost_usd = null`. Yig'indilarda (`ai.cost_usd`,
  maqsadlar, kunlar) — narxi ma'lum qismlar yig'indisi (birortasi ham
  ma'lum bo'lmasa `null`); `cost_complete=false` — tokenlarning bir qismi
  narxsiz qolganini bildiradi. Narx 4 xonagacha yaxlitlanadi.

### 21.2 Ruxsat

`view_platform_stats` (**yangi**, `admin`; migratsiya `0020`). Inline rol
tekshiruvi yo'q (§4).

### 21.3 API

```
GET /api/v1/admin/platform?days=7|30|90      view_platform_stats (standart 30)
→ {
    generated_at, days,
    users:  { students, companies, universities, new_students, active_students },
    runs:   { in_progress, started, completed, expired, abandoned, completion_rate, avg_score },
    evaluation: { pending, queued_retry, failed, oldest_pending_minutes, queue_jobs },
    ai:     { calls, failures, tokens_in, tokens_out, cost_usd, cost_complete,
              by_purpose: [{purpose, calls, tokens, cost_usd}],
              by_provider: [{provider, model, calls, failures, tokens_in, tokens_out, cost_usd}] },
    daily:  [{ day, new_students, runs_started, runs_completed, ai_tokens, ai_cost_usd }],
    scenarios: [{ scenario_id, title, sector, started, completed, completion_rate, avg_score }]
  }
```

- Davr — oxirgi `days` Toshkent kuni, bugun ham kiradi; `daily`da har kun
  bor (bo'sh kun — 0), eskidan yangiga.
- `students`/`companies`/`universities` — jami (faol talabalar, tasdiqlangan
  tashkilotlar). `new_students` — davrda ro'yxatdan o'tgan talabalar;
  `active_students` — davrda Run faolligi (`last_activity_at`) bo'lgan
  talabalar.
- `runs`: `in_progress` — hozir `scheduled|active`; qolganlari davrda
  **boshlangan** (`created_at`) Run'lar bo'yicha. `completion_rate =
  completed / (completed + expired + abandoned)` (foiz, tugamaganlar
  kirmaydi; maxraj 0 — `null`). `avg_score` — `final_report.overall_score`
  o'rtachasi.
- `evaluation`: hozirgi `submissions` holati (Run javoblari): `pending`,
  `queued_retry`, davrda `failed_permanent` bo'lganlar, eng eski kutayotgan
  javob yoshi (daqiqa). `queue_jobs` — arq navbatidagi ishlar soni (Redis
  ishlamasa `null`).
- `scenarios` — davrda eng ko'p boshlangan 10 ta ssenariy (teng bo'lsa nom
  bo'yicha).
- Hisob `app/analytics/platform.py`da (faqat o'qiydi), endpoint `api/admin.py`da.

### 21.4 Frontend

`/admin` sahifasida yangi "Statistika" bo'limi (`view_platform_stats`):
davr tanlovi (7 / 30 / 90 kun), asosiy raqamlar, kunlik faollik grafigi
(yangi talabalar, boshlangan va tugagan Run'lar), AI sarfi (kunlik tokenlar,
maqsad va provayder kesimi, narx — ma'lum bo'lsa), baholash navbati holati
(tiqilib qolsa ogohlantirish: `failed > 0` yoki eng eskisi > 30 daqiqa) va
ssenariylar jadvali. Grafiklar SVG/CSS, kutubxonasiz.

## 22. Mobil PWA va push bildirishnomalar (Modul 7 + 11 + 8)

Run real vaqtda ketadi (§9.2), talabalar esa ko'pincha telefondan kiradi.
Sayt telefonga ilova kabi o'rnatiladi, vazifa va dedlayn haqida push xabar
keladi, ish stoli telefonda qulay ishlaydi. Alohida mobil ilova yo'q — shu
React ilova.

### 22.1 PWA (frontend)

- `public/manifest.webmanifest`: nom `TryJob`, `display: standalone`,
  `start_url: /`, rang — brend; ikonlar 192/512 (oddiy va `maskable`),
  `apple-touch-icon` 180. `index.html`: `theme-color`, `viewport-fit=cover`.
- `public/sw.js` (qo'lda, kutubxonasiz; ilova yuklanganda ro'yxatdan o'tadi):
  - `/api/*` va boshqa domen so'rovlari **hech qachon keshlanmaydi** (shaxsiy ma'lumot);
  - `/assets/*` (Vite hash'li fayllar) — cache-first;
  - sahifa navigatsiyasi — network-first, tarmoq yo'q bo'lsa keshdagi
    `index.html` (ilova ochiladi va "internet yo'q" deydi);
  - yangi versiya o'rnatilganda eski keshlar o'chiriladi.
- "Ilovani o'rnatish": brauzer `beforeinstallprompt` bersa — navbar'da va
  `/notifications` push kartasida tugma; iOS Safari'da — "Ulashish → Bosh ekranga" ko'rsatmasi
  (`/notifications` sahifasida). O'rnatilgan (standalone) holatda ko'rsatilmaydi.
- Tarmoq uzilsa — sahifa tepasida "Internet yo'q" yo'lagi.

### 22.2 Push (Modul 11)

- Web Push + VAPID, `pywebpush` kutubxonasi (shifrlash qo'lda yozilmaydi).
  `.env`: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`
  (`mailto:…`). Bo'sh — push o'chirilgan (faqat sayt va email).
  Kalit juftligi: `python tools/gen_vapid_keys.py`.
- `push_subscriptions`: `id, user_id (FK, CASCADE), endpoint (UNIQUE, ≤ 1000),
  p256dh, auth, user_agent (≤ 200), created_at, last_used_at`. Bitta
  foydalanuvchida ko'pi bilan **10** ta obuna (eskisi o'chiriladi). Shu
  endpoint boshqa foydalanuvchida bo'lsa — yangi egaga o'tadi (bitta brauzer,
  boshqa akkaunt). `endpoint` faqat `https://`.
- `notifications.push_status` (`null | sent | skipped | failed`),
  `notification_settings.push_enabled` (default `true`; turlar bo'yicha
  ajratilmaydi — push hamma tegishli turlarga).
- Cron `send_push_notifications` (har daqiqa): `push_status IS NULL`,
  **10 daqiqadan** yangi (eskisi `skipped` — kech push foydasiz), 50 tadan.
  O'qilgan, foydalanuvchi faol emas, push o'chirilgan yoki obuna yo'q —
  `skipped`. Har obunaga yuboriladi (`asyncio.to_thread`); bittasiga yetsa
  `sent`, hammasi xato — `failed`. 404/410 javobi — obuna o'chiriladi.
  Qayta urinish yo'q.
- Payload (JSON, ≤ 2 KB): `{title, body, link, tag}` — matn email bilan bir
  xil o'zbekcha (§15.3 `render`), `tag = notification id` (takror ko'rsatilmaydi).
  Push bosilsa — `link` ochiladi (ochiq oyna bo'lsa o'sha fokuslanadi).
- Chiqishda (logout) frontend shu brauzer obunasini `DELETE` qiladi va
  `unsubscribe()` — boshqa akkaunt kirsa avvalgisining xabarlari kelmaydi.
  Qurilma obunasi va `push_enabled` alohida: `push_enabled=false` — hech bir
  qurilmaga yuborilmaydi; qurilmani ulash `push_enabled`ni ham yoqadi.
- Run hodisalari havolasi `/runs/{id}?event={node_id}` (`task_delivered`,
  `deadline_soon`, `mentor_review`) — Run sahifasi shu hodisani ochadi
  (telefonda "Vazifa" bo'limida).

### 22.3 API

```
GET    /api/v1/push/config                          ochiq → {enabled, public_key | null}
POST   /api/v1/users/me/push-subscriptions          kirgan; {endpoint, keys: {p256dh, auth}} → 204
DELETE /api/v1/users/me/push-subscriptions          kirgan; {endpoint} → 204 (o'ziniki bo'lmasa ham 204)
GET/PUT /api/v1/users/me/notification-settings      + push_enabled (§15.4)
```

Push o'chirilgan (`enabled=false`) bo'lsa POST — 409.

### 22.4 Ish stoli telefonda

- Run sarlavhasi ixcham (kompaniya nomi va "To'xtatish" kichik ekranda
  qisqaroq), bo'limlar yo'lagida "Chat" o'qilmagan xabarlar soni bilan.
- Xavfsiz hudud (`env(safe-area-inset-*)`) — o'rnatilgan ilovada pastki va
  yuqori chetlar kesilmaydi.
- `/notifications`: "Push bildirishnomalar" kartasi — holat (qo'llab-quvvatlanmaydi,
  ruxsat berilmagan, yoqilgan), yoqish/o'chirish, iOS uchun o'rnatish ko'rsatmasi.
  Server push'siz (`enabled=false`) bo'lsa karta ko'rsatilmaydi.
