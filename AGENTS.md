# TryJob — Agent yo'riqnomasi

> Haqiqat manbai: **[`docs/CONTRACT.md`](docs/CONTRACT.md)**. Shu faylga zid
> hech narsa qilmang. Noaniqlik bo'lsa — avval `CONTRACT.md`ni yangilang,
> keyin kodga tegining.

## Holat

Loyiha 2026-10-07 sanasida noldan qayta qurildi (eski kod `0e4be5e`
commitida tarixda saqlanadi). `CONTRACT.md` §6 dagi 1–6 va 8-modullar
`main`da bor (backend API, Alembic migratsiyalari, testlar, `deploy/`).
Modul 9 (ssenariy dvigateli) backend'da tayyor, kontent `backend/content/scenarios/`da
(IT, Bank, Marketing, Data, HR — `CONTRACT.md` §9.11);
frontend'da talaba "ish stoli" bor (katalog, Run sahifasi, chat, hisobot).
Talent Hunt (`CONTRACT.md` §10): kompaniya nomzodlarni Run natijalari bo'yicha
ko'radi va taklif yuboradi, talaba ko'rinishini boshqaradi va javob beradi.
Tashkilot arizasi → admin tasdiqlashi → invoice oqimi brauzerda (`CONTRACT.md` §11, `/admin`).
Universitet portali (`CONTRACT.md` §12, `/university`): o'z talabalarining Run natijalari.
Mentor (`CONTRACT.md` §9.13): talaba ishini ko'radi, har baholangan urinishdan keyin
chatda izoh yozadi, dedlayn yaqinlashsa eslatadi.
Sertifikat va portfolio (`CONTRACT.md` §13): tugagan Run'ga `TJ-XXXX-XXXX` kodli
sertifikat (ochiq tekshiruv `/c/{code}`, QR, A4 PDF), talabaning ochiq portfoliosi `/p/{slug}`.
Landing (`CONTRACT.md` §14): mehmon uchun `/` — ochiq `GET /api/v1/showcase` asosida; kirgan foydalanuvchi o'z bosh sahifasiga.
Ssenariy muharriri (`CONTRACT.md` §16, `/admin/scenarios`): admin ssenariyni brauzerda yaratadi,
tahrirlaydi (jonli tekshiruv, YAML ikki tomonlama), qoralama sifatida saqlaydi va nashr qiladi.
Bildirishnomalar (`CONTRACT.md` §15): yangi vazifa, dedlayn, mentor izohi, hisobot va takliflar —
navbar qo'ng'iroqchasi, `/notifications` va email (SMTP `.env`dan; bo'sh bo'lsa faqat sayt ichida).
Talaba analitikasi (`CONTRACT.md` §17, `/dashboard`): ball dinamikasi, kompetensiyalar o'zgarishi,
fokus kompetensiyalar, AI maslahatlari va ularni mashq qildiradigan ssenariy tavsiyalari.
Ishga tushirish (`CONTRACT.md` §18, `deploy/README.md`): `GET /api/v1/health`, HTTPS (Caddy,
`docker-compose.https.yml`), kunlik zaxira nusxa va tiklash tartibi, log rotatsiya.
Kod tekshiruvi (`CONTRACT.md` §19, `sandbox/`): talaba kodi alohida tarmoqsiz runner konteynerida;
`code` task'larida ssenariydagi yashirin testlar (`checks.tests`) baholashga qo'shiladi.
Kompaniya hisobotlari (`CONTRACT.md` §20, `/talents/report`): kompaniyaga ochiq nomzodlar bazasi kesimi,
takliflar voronkasi (oylar, lavozimlar, javob vaqti) va CSV eksport.
Platforma statistikasi (`CONTRACT.md` §21, `/admin` → Statistika): foydalanuvchilar, Run'lar, baholash navbati,
AI sarfi (`ai_usage` — har `chat()` chaqiruvi `purpose` bilan; narx `.env` `LLM_PRICES`).
Mobil PWA (`CONTRACT.md` §22): sayt telefonga o'rnatiladi (`public/manifest.webmanifest`, `public/sw.js`),
Web Push (`pywebpush`, VAPID `.env`dan, kalit: `tools/gen_vapid_keys.py`) — vazifa, dedlayn, mentor izohi;
Run ish stoli telefonda ixcham, bildirishnoma havolasi `?event=` bilan hodisani ochadi.
Kompaniya vakansiyalari (`CONTRACT.md` §23, `/company/vacancies`, `/vacancies`): kompaniya talablar (kompetensiya ≥ ball)
bilan vakansiya e'lon qiladi, mos nomzodlarni ko'radi; talaba moslik foizi, yetishmayotgan kompetensiyalar
va mashq ssenariylarini ko'radi, ariza beradi (ariza — rozilik: yopiq profil ham kompaniyaga ko'rinadi).
AI suhbat mashqi (`CONTRACT.md` §24, `/interviews`, Modul 14 `backend/app/interview/`): talaba vakansiya bo'yicha
AI suhbatdosh bilan 5 savollik sinov suhbatidan o'tadi (aniqlashtiruvchi savollar, AI'siz — `bank.py` savollari),
arq `interview_report_job` har javobga baho va izoh yozadi; natija shaxsiy, profilga ta'sir qilmaydi.
Kompaniya ssenariylari (`CONTRACT.md` §26, `/company/scenarios`): kompaniya §16 muharriri bilan shaxsiy ssenariy
yaratadi (katalogda yo'q, `company_name` — o'zi, ≤ 5 kun) va arizachiga sinov topshirig'i sifatida yuboradi
(`application_assessments`); talaba uni oddiy Run kabi o'tadi, natija faqat shu kompaniyaga, sertifikat va profilga kirmaydi.
Suhbat bosqichlari (`CONTRACT.md` §25): kompaniya arizachiga 1–3 suhbat vaqtini taklif qiladi, talaba birini
tanlaydi yoki rad etadi (`.ics` kalendar fayli), kompaniya natijani belgilaydi (o'tdi — keyingi bosqich yoki taklif,
o'tmadi/kelmadi — rad); ≤ 2 soat qolganda eslatma (`interview_reminders` cron'i).

```
backend/app/{core,models,api,ai}/   # §6 modul chegaralari CONTRACT.md'da
sandbox/                            # kod runner'i (§19), faqat stdlib
backend/{tests,alembic}/
frontend/
deploy/
tools/
docs/CONTRACT.md
```

Ssenariy dvigateli: `CONTRACT.md` §9. Eski `simulations` muzlatilgan,
o'rniga real vaqtdagi "ishdagi kun/hafta" Run'lari ishlaydi.

## Ishlash qoidalari

- Foydalanuvchi bilan o'zbekcha muloqot qiling.
- Har bir modul faqat `CONTRACT.md` §6'da o'ziga tegishli papkalarga tegadi;
  boshqa modul faylini o'zgartirish kerak bo'lsa — bu shartnoma to'liq emas
  degani, avval shartnomani yangilang.
- RBAC: `if role == "admin"` kabi inline tekshiruv taqiqlangan — faqat
  permission-based dependency (`CONTRACT.md` §4).
- Auth/JWT: `python-jose`, parol: `passlib[bcrypt]` — qo'lda crypto yozish
  taqiqlangan (statik-salt xatosi sababli eski versiya butunlay olib
  tashlangan).
- Real kompaniya nomi/brend ishlatish taqiqlangan — faqat fictional nomlar.
- Sandbox/kod bajarish endpointlari: auth + Redis rate-limit SHART, hech
  qachon autentifikatsiyasiz ochiq qoldirilmaydi.
- Click/Payme faqat kelajakdagi ixtiyoriy talaba to'lovlari uchun — B2B
  (universitet/kompaniya) to'lovi admin invoice oqimi orqali (`CONTRACT.md` §7).
- Secretlarni kodga yozmang, `.env`dan o'qing, default qiymat sifatida ham
  haqiqiy ko'rinadigan kalit yozmang.

## Lokal ishga tushirish

PostgreSQL (pgvector) va Redis kerak. Backend (`backend/` papkasidan, `.env` bilan):

```
pip install -r requirements.txt
alembic -c alembic/alembic.ini upgrade head          # rollar/ruxsatlar seed ham shu yerda
python ../tools/import_scenario.py --publish content/scenarios/*.yaml
python ../tools/bootstrap_admin.py --email admin@example.uz --password '...'   # birinchi admin
uvicorn app.main:app --port 8000
arq app.ai.worker.WorkerSettings                     # baholash, yetkazish cron'i, hisobotlar
```

Frontend (`frontend/`): `npm ci && npm run dev` — Vite `/api`ni
`http://localhost:8000`ga proksilaydi (boshqa manzil: `VITE_API_TARGET`).
Testlar: `backend/`dan `TEST_DATABASE_URL=... pytest -q`.
