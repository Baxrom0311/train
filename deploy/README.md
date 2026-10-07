# TryJob — Deploy (Modul 8)

Docker Compose bilan to'liq stek:

| Servis | Image | Vazifasi |
|---|---|---|
| `postgres` | `postgres:16-alpine` | `tryjob_dev` + testlar uchun `tryjob_test` (CONTRACT.md §3.1) |
| `redis` | `redis:7-alpine` | Rate-limit (sandbox) va arq navbati |
| `migrate` | `tryjob-backend` | Bir martalik `alembic upgrade head` (rollar/ruxsatlar seed) |
| `backend` | `tryjob-backend` | FastAPI (uvicorn), faqat ichki tarmoqda `:8000` |
| `frontend` | `tryjob-frontend` | nginx: React build + `/api/`, `/docs` → backend proxy |
| `worker` | `tryjob-backend` | arq AI-retry worker — `worker` profilida, hozircha o'chiq |

## Ishga tushirish

```bash
cp deploy/.env.example deploy/.env
# deploy/.env ni to'ldiring: POSTGRES_PASSWORD, SECRET_KEY (openssl rand -hex 32), ...

docker compose -f deploy/docker-compose.yml up -d --build
```

Ilova: `http://localhost` (yoki `HTTP_PORT`), Swagger: `http://localhost/docs`.

Birinchi admin (faqat bir marta):

```bash
docker compose -f deploy/docker-compose.yml exec backend \
  python ../tools/bootstrap_admin.py --email admin@example.uz --password '...'
```

## Testlar (konteyner ichida)

```bash
docker compose -f deploy/docker-compose.yml exec \
  -e TEST_DATABASE_URL="postgresql+asyncpg://<user>:<pass>@postgres:5432/tryjob_test" \
  backend python -m pytest -q -p no:cacheprovider
```

`tryjob_test` bazasi `postgres-init/` skripti orqali faqat `pgdata` volume
birinchi marta yaratilganda paydo bo'ladi.

## Eslatmalar

- Secretlar faqat `deploy/.env`da (`.gitignore`da) — compose majburiy
  qiymatlarsiz (`SECRET_KEY`, `POSTGRES_*`) ishga tushmaydi.
- `backend` konteyneri: root emas, `read_only`, `cap_drop: ALL`,
  `no-new-privileges`, `pids_limit`. Bu sandbox (`/tools/sandbox`) uchun
  **to'liq izolyatsiya emas** — kod hali ham backend konteyneri ichida va
  tarmoqqa chiqa oladi; alohida sandbox konteyneri keyingi qadam.
- `worker` servisi `app/ai/worker.py`da `WorkerSettings` paydo bo'lgach
  ishlaydi: `docker compose -f deploy/docker-compose.yml --profile worker up -d`.
- HTTPS: tashqi reverse proxy (Caddy/Traefik/Cloudflare) yoki `nginx.conf`ga
  sertifikat qo'shing.
