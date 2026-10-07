# TryJob — Deploy (Modul 8)

Docker Compose bilan to'liq stek:

| Servis | Image | Vazifasi |
|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | `tryjob_dev` + testlar uchun `tryjob_test` (CONTRACT.md §3.1), `vector` extension (§9.4) |
| `redis` | `redis:7-alpine` | Rate-limit (sandbox) va arq navbati |
| `migrate` | `tryjob-backend` | Bir martalik `alembic upgrade head` (rollar/ruxsatlar seed) |
| `backend` | `tryjob-backend` | FastAPI (uvicorn), faqat ichki tarmoqda `:8000` |
| `frontend` | `tryjob-frontend` | nginx: React build + `/api/`, `/docs` → backend proxy |
| `worker` | `tryjob-backend` | arq worker: baholash, hodisalar yetkazish cron'i, hisobotlar |
| `sandbox` | `tryjob-sandbox` | Talaba kodi va yashirin testlar (§19): faqat ichki `sandbox` tarmog'ida, internet/DB/Redis'siz |
| `backup` | `pgvector/pgvector:pg16` | Kunlik `pg_dump` + `uploads` arxivi `deploy/backups/`ga |
| `caddy` | `caddy:2-alpine` | Faqat `docker-compose.https.yml` bilan: HTTPS (Let's Encrypt) |

## Ishga tushirish

```bash
cp deploy/.env.example deploy/.env
# deploy/.env ni to'ldiring: POSTGRES_PASSWORD, SECRET_KEY va SANDBOX_TOKEN (openssl rand -hex 32), ...

docker compose -f deploy/docker-compose.yml up -d --build
```

Ilova: `http://localhost` (yoki `HTTP_PORT`). Swagger (`/docs`) faqat
`DOCS_ENABLED=true` bo'lsa ochiq — `.env.example`da production uchun `false`.

Ssenariylar (faqat birinchi marta — keyin muharrirda, `/admin/scenarios`;
qayta import muharrirdagi nashrni fayldagisi bilan almashtiradi):

```bash
docker compose -f deploy/docker-compose.yml exec backend \
  sh -c 'python ../tools/import_scenario.py --publish content/scenarios/*.yaml'
```

Birinchi admin (faqat bir marta):

```bash
docker compose -f deploy/docker-compose.yml exec backend \
  python ../tools/bootstrap_admin.py --email admin@example.uz --password '...'
```

## HTTPS

DNS'da `DOMAIN` serverga qaragan, 80 va 443 portlar ochiq bo'lsin;
`deploy/.env`da `DOMAIN`, `ACME_EMAIL`, `CORS_ORIGINS=https://<domen>`,
`PUBLIC_URL=https://<domen>`. Keyin har buyruqqa ikkinchi fayl qo'shiladi:

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.https.yml up -d --build
```

Caddy sertifikatni o'zi oladi va yangilaydi (`caddy_data` volume'ida),
HSTS qo'yadi; `frontend` tashqi portni ochmaydi.

### Telefon ilovasi va push (§22)

Sayt telefonga ilova sifatida o'rnatiladi va push xabar yuboradi — ikkalasi
ham faqat HTTPS'da ishlaydi (brauzer talabi; `localhost` bundan mustasno).
Push uchun bir marta kalit juftligi yarating va `deploy/.env`ga qo'ying:

```bash
docker compose -f deploy/docker-compose.yml exec backend python ../tools/gen_vapid_keys.py
# VAPID_PUBLIC_KEY=..., VAPID_PRIVATE_KEY=... → deploy/.env, VAPID_SUBJECT=mailto:admin@<domen>
docker compose -f deploy/docker-compose.yml up -d backend worker
```

Yuborishni `worker` bajaradi (har daqiqa). Kalitni almashtirsangiz eski
obunalar ishlamay qoladi — foydalanuvchilar `/notifications`da qayta ulaydi.

## Holat

`GET /api/v1/health` → `{status, db, redis, worker}`; hammasi ishlasa 200,
aks holda 503 (ichki xato matni qaytmaydi). Tashqi uptime monitorni
(masalan, har daqiqada) shu manzilga ulang — worker o'lsa real vaqtdagi
hodisalar yetkazilmaydi, buni faqat shu yerda ko'rasiz.
Compose ichida: `backend` — DB va Redis, `worker` — `arq --check`.

```bash
docker compose -f deploy/docker-compose.yml ps        # healthy / unhealthy
docker compose -f deploy/docker-compose.yml logs -f --tail=100 worker
```

Loglar `json-file`, har servisga 10 MB × 5 fayl.

## Zaxira nusxa va tiklash

`backup` servisi har kuni `BACKUP_HOUR`da (Toshkent) `deploy/backups/`ga
`tryjob_<sana>.dump` va `uploads_<sana>.tar.gz` yozadi, `BACKUP_KEEP_DAYS`dan
eskilarini o'chiradi. Yozilayotgan fayl `.partial` bilan tugaydi — u tayyor
nusxa emas. Qo'lda (masalan, yangilashdan oldin):

```bash
docker compose -f deploy/docker-compose.yml exec backup sh /backup.sh now
```

Nusxalar shu serverda turadi — disk yo'qolsa ular ham yo'qoladi.
`deploy/backups/`ni muntazam boshqa joyga ko'chiring (masalan, `rclone`
yoki `rsync` bilan obyekt xotiraga).

Tiklash (yangi yoki bo'sh serverda):

```bash
C="docker compose -f deploy/docker-compose.yml"
$C up -d postgres
$C stop backend worker                      # ishlayotgan bo'lsa
$C exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' \
  < deploy/backups/tryjob_<sana>.dump
docker run --rm -v tryjob_uploads:/data/uploads -v "$PWD/deploy/backups:/b:ro" alpine \
  sh -c 'rm -rf /data/uploads/* && tar -xzf /b/uploads_<sana>.tar.gz -C /data'
$C up -d
```

`tryjob_uploads` — compose loyihasi (`name: tryjob`) yaratgan volume nomi
(`docker volume ls`).

## Yangilash

```bash
git pull
docker compose -f deploy/docker-compose.yml exec backup sh /backup.sh now   # avval nusxa
docker compose -f deploy/docker-compose.yml up -d --build                   # migrate o'zi yuradi
docker compose -f deploy/docker-compose.yml ps
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

- `postgres` image `postgres:16-alpine`dan `pgvector/pgvector:pg16`ga
  almashgan (bir xil Postgres 16, lekin Alpine/musl emas, Debian/glibc).
  Collation farqi sababli eski `pgdata` volume'ni to'g'ridan-to'g'ri
  ishlatmang: ma'lumot bo'lsa `pg_dump` → yangi volume → `pg_restore`.
  Yangi volume'da `vector` extension'ni `postgres-init/` yoqadi; managed
  Postgres'da extension oldindan yoqilishi kerak.
- Run chat fayllari `uploads` volume'ida (`/data/uploads`), faqat auth'li
  `/api/v1/files/{id}` orqali beriladi.

- Secretlar faqat `deploy/.env`da (`.gitignore`da) — compose majburiy
  qiymatlarsiz (`SECRET_KEY`, `POSTGRES_*`) ishga tushmaydi.
- Talaba kodi `backend`da emas, `sandbox` konteynerida bajariladi (§19):
  `internal: true` tarmoq (internet, Postgres, Redis yo'q), `read_only`,
  root emas, `cap_drop: ALL`, xotira/CPU/jarayon limitlari, secret faqat
  `SANDBOX_TOKEN`. Qolgan xavf: runner ichidagi kod `backend:8000` API'ga
  ulana oladi (internetdagi har kim kabi — auth va rate-limit amal qiladi).
  Tekshirish: `docker compose -f deploy/docker-compose.yml exec sandbox
  python -c "import urllib.request; urllib.request.urlopen('https://example.com', timeout=3)"`
  — xato bilan tugashi kerak.
- `worker` servisi `app/ai/worker.py`dagi `WorkerSettings` bilan standart
  profilda ishlaydi (`up -d` shartidan ortiq hech narsa kerak emas) —
  Cloud AI zanjiri muvaffaqiyatsiz bo'lganda submission'larni qayta
  baholaydi; bu servis ishlamasa, "queued_retry" holatidagi topshiriqlar
  abadiy shu holatda qolib ketadi.
- HTTPS: yuqoridagi "HTTPS" bo'limi (Caddy). Tashqi proxy (Cloudflare va
  h.k.) ishlatilsa, `docker-compose.https.yml` shart emas.
