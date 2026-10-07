# TryJob — Agent yo'riqnomasi

> Haqiqat manbai: **[`docs/CONTRACT.md`](docs/CONTRACT.md)**. Shu faylga zid
> hech narsa qilmang. Noaniqlik bo'lsa — avval `CONTRACT.md`ni yangilang,
> keyin kodga tegining.

## Holat

Loyiha 2026-10-07 sanasida noldan qayta qurildi (eski kod `0e4be5e`
commitida tarixda saqlanadi). `CONTRACT.md` §6 dagi 1–6 va 8-modullar
`main`da bor (backend API, Alembic migratsiyalari, testlar, `deploy/`).
Modul 9 (ssenariy dvigateli) backend'da tayyor, kontent `backend/content/scenarios/`da;
frontend'da talaba "ish stoli" bor (katalog, Run sahifasi, chat, hisobot).
Talent Hunt (`CONTRACT.md` §10): kompaniya nomzodlarni Run natijalari bo'yicha
ko'radi va taklif yuboradi, talaba ko'rinishini boshqaradi va javob beradi.

```
backend/app/{core,models,api,ai}/   # §6 modul chegaralari CONTRACT.md'da
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
uvicorn app.main:app --port 8000
arq app.ai.worker.WorkerSettings                     # baholash, yetkazish cron'i, hisobotlar
```

Frontend (`frontend/`): `npm ci && npm run dev` — Vite `/api`ni
`http://localhost:8000`ga proksilaydi (boshqa manzil: `VITE_API_TARGET`).
Testlar: `backend/`dan `TEST_DATABASE_URL=... pytest -q`.
