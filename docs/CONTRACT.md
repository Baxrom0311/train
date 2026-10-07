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
| 4 | **Talent Hunt** | `backend/app/models/talent.py`, `backend/app/api/talent_hunt.py`, `backend/app/talent/` | (1),(3),(9)ga bog'liq — ball Run natijalaridan (§10) |
| 5 | **Case Cup** | `backend/app/api/case_cups.py` | (1),(2)ga bog'liq |
| 6 | **University Portal** | `backend/app/api/university_portal.py` | (1),(3),(9)ga bog'liq — natijalar Run'lardan (§12) |
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
# Tashkilot ariza/rad etish, invoice bekor qilish, o'z invoice'lari — §11

PATCH  /api/v1/users/me/visibility        { is_open_to_work, hidden_from_company_ids }
GET    /api/v1/talents                    only is_verified company + only visible candidates
POST   /api/v1/talents/offers             counts against subscription's "interview SLA" commitment

# Talent Hunt to'liq ro'yxati (profil, takliflarga javob) — §10.4
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
    checks: {sandbox_tests: tests/orders_refund.py}
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
                    generated bool, created_at)
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

POST   /api/v1/admin/scenarios/import            YAML; permission: manage_simulations
POST   /api/v1/admin/scenarios/{id}/versions/{v}/publish
GET    /api/v1/admin/holidays                     permission: manage_simulations
PUT    /api/v1/admin/holidays/{date}              { name } -> source=manual
DELETE /api/v1/admin/holidays/{date}
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
| 2 (AI) | `ai/llm.py`: umumiy `chat(messages, schema?) -> LLMResult` (JSON-rejim, Pydantic tekshiruv, token hisobi, provayder tartibi `LLM_PROVIDERS` va model nomlari `.env`dan); `ai/` ichida: `persona_reply(ctx, history, message) -> LLMResult`, `evaluate_rubric(task, answer, rubric) -> RubricResult`, `embed(texts) -> list[list[float]]`, `summarize_day(...)`, `final_report(...)`; `submissions` migratsiyasi (§9.7); arq cron `deliver_due_events`ni `WorkerSettings`ga ulash (funksiyaning o'zi Modul 9'da) |
| 1 (Core) | `models/enums.py`ga `Competency`, `RunStatus`, `RunEventStatus`, `NodeType`, `ChatContentType`, `ChatSender`, `ScenarioVersionStatus`, `HolidaySource`, `AIEvalStatus.PENDING`; `requirements.txt`ga `tzdata`, `holidays`, `pgvector`; `conftest.py`da `create_all`dan oldin `CREATE EXTENSION IF NOT EXISTS vector`; `file_validator`ga yangi turlar (v2) |
| 8 (Deploy) | `postgres` image → `pgvector/pgvector:pg16`; `UPLOAD_DIR` volume; nginx'da `/api/v1/runs/*/stream` uchun `proxy_buffering off` va uzun `proxy_read_timeout` |
| 7 (Frontend) | "Ish stoli": inbox, personajlar chati, task board, kalendar, soat, hisobot sahifasi |
| 4, 6 | `runs.competency_scores`ni nomzod profili va universitet statistikasiga qo'shish; Modul 6: `SubmissionSummary.task_id` → `Optional` (Run submission'ida `task_id` yo'q) |

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

**v2:** `voice`/`image`/`video`; email/push bildirishnoma; murakkab
shartlar va ko'p yakunli ssenariylar; `meeting` (jonli savol-javob) node
turi; ssenariy muharriri (admin UI).

### 9.12 Ochiq savollar (yozilgan, lekin hali hal qilinmagan)

- **Shaxsiy ma'lumotlar:** talaba matni va fayllari xorijiy AI API'larga
  ketadi — rozilik matni, saqlash muddati va O'zbekiston qonunchiligidagi
  lokalizatsiya talabi yurist bilan tekshirilsin.
- **Real vaqt va talabaning darslari:** pauza yo'q qaror qabul qilingan;
  pilotdan keyin "yonib ketgan" Run'lar ulushi kuzatilsin va kerak bo'lsa
  ssenariy dedlaynlari yumshatilsin.

---

## 10. Talent Hunt — Run natijalari asosidagi kandidat profili

Modul 4 (§6) eski `submissions` soniga emas, ssenariy dvigateli (§9)
natijalariga tayanadi. Maxfiylik qoidalari (§5, `candidate_visibility`)
o'zgarmaydi: yozuv yo'q yoki `is_open_to_work=false` — nomzod hech qayerda
ko'rinmaydi; yashirilgan kompaniya uchun "topilmadi" (404), "yashirilgan" emas.

### 10.1 Profil qanday hisoblanadi

- Faqat `status=completed` va `final_report` yozilgan Run'lar kiradi
  (sertifikatli ishlar). `expired`/`abandoned` profilga chiqmaydi — talaba
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
