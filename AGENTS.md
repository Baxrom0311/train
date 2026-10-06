# TryJob loyiha yo‘riqnomasi

## Loyiha xaritasi

- Mahsulot: talabalar uchun virtual ish simulyatsiyalari, AI baholash, sertifikatlar, Case Cup, HR Talent Hunt va universitet statistikasi.
- Backend: Python, FastAPI, SQLAlchemy sync Session, Pydantic. API prefiksi `/api/v1`.
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, React Router, Axios; manbalar `frontend/src/` ichida.
- `app/main.py`: ilova, routerlar, static/upload mount va eski Jinja sahifalari.
- `app/api/`: auth, simulations, submissions, certificates, tools, billing, case_cups, talent_hunt, university_portal.
- `app/models.py`, `app/schemas.py`: ORM va API shartnomalari.
- `app/ai/`: provider routeri, lokal baholash, adaptiv topshiriqlar, mentorlar, intervyu, prompt filtri.
- `app/core/`: parol/token/sertifikat, fayl tekshiruvi, Python bajarish.
- `alembic/`: DB migratsiyalari. `app/seed_data.py`: demo ma’lumotlar.
- `tests/`: backend pytest testlari. Brauzer E2E testlari hozir mavjud emas; `test_e2e_platform.py` FastAPI TestClient bilan ishlaydi.
- `Dockerfile`, `docker-compose.yml`, `docker/nginx.conf`, `scripts/start.sh`: deploy konfiguratsiyasi.
- `scratch/skills_source/`: yuklab olingan tashqi materiallar; mahsulot kodi hisoblanmaydi.

## Ishlash qoidalari

- Foydalanuvchi bilan odatda o‘zbekcha muloqot qiling.
- Avval tegishli backend schema, endpoint va frontend chaqiruvini birgalikda tekshiring. TypeScript generic API javobini runtime’da validatsiya qilmaydi.
- Haqiqiy API xatosini soxta muvaffaqiyat yoki yashirin demo ma’lumot bilan almashtirmang. Demo rejimini alohida va aniq qiling.
- Auth va role/ownership nazoratini backendda bajaring. Frontend role qiymati ruxsat manbai emas.
- Schema o‘zgartirish bilan Alembic migratsiyasini ham yangilang.
- Testlar va tekshiruvlarda vaqtinchalik DB va upload katalogidan foydalaning; AI kalitlarini bo‘shating. Mavjud `tryjob.db`, `train.db`, `uploads/` foydalanuvchi ma’lumotlaridir.
- `app.main` importi SQLite holatida seed bajaradi. Hozirgi seed topshiriqlarni o‘chirib qayta yaratadi: mavjud bazada oddiy import ham ma’lumot bog‘lanishlarini buzishi mumkin.
- Sandboxning AST filtri izolyatsiya emas. Ishonchsiz kodni asosiy server muhiti ichida xavfsiz deb hisoblamang.
- Secretlarni chiqarmang, kodga yangi production kalit yoki demo administrator paroli kiritmang.
- `/init` audit natijalari `CODE_REVIEW.md` ichida. Undagi topilmalar joriy kod tuzatilganda qayta tekshirilishi kerak.

## Lokal ishga tushirish

- Python muhiti: `.venv`; bog‘liqliklar `requirements.txt` ichida.
- Backend: `.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`.
- Frontend: `cd frontend` va `npm run dev`; port 3000. Vite `/api`, `/static`, `/uploads` so‘rovlarini port 8000 ga uzatadi.
- Backendni boshlashdan oldin `DATABASE_URL` va `UPLOAD_DIR` ni tekshiring; yuqoridagi seed ogohlantirishi amal qiladi.
- Frontend build: `cd frontend && npm run build`.
- Backend HTML root hozir React ilovasini bermaydi; frontendni alohida ishga tushirish kerak.

## Izolyatsiyalangan backend testlari

Loyiha ildizidan:

```bash
.venv/bin/python - <<'PY'
import os
import subprocess
import tempfile

with tempfile.TemporaryDirectory(prefix="tryjob-test-") as tmp:
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite:///" + tmp + "/test.db",
        "UPLOAD_DIR": tmp + "/uploads",
        "ENVIRONMENT": "testing",
        "DEEPSEEK_API_KEY": "",
        "GEMINI_API_KEY": "",
        "OPENAI_API_KEY": "",
    }
    result = subprocess.run(
        [".venv/bin/python", "-m", "pytest", "tests/", "-q"], env=env
    )
    raise SystemExit(result.returncode)
PY
```

Migratsiyalarni alohida yangi vaqtinchalik DB bilan, `app.main` ni import qilmasdan tekshiring: avval `.venv/bin/python -m alembic upgrade head`, keyin `.venv/bin/python -m alembic check`. Oddiy pytest migratsiyalarni tekshirmaydi, chunki ilova `create_all()` ishlatadi.

## Audit bazaviy holati — 2026-10-07

- Backend: 34 test o‘tgan; 1 TestClient deprecation ogohlantirishi.
- Frontend: TypeScript + Vite build o‘tgan; JS bundle 602.85 kB, gzip 165.69 kB.
- SQLite migratsiyasi o‘tgan; `alembic check` 18 ta yetishmayotgan indeks topgan.
- Tekshirish paytida loyiha ildizi Git repository emas edi.
- Production PostgreSQL/Docker va haqiqiy AI/payment providerlari auditda ishga tushirilmagan.
