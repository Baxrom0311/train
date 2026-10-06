#!/usr/bin/env bash
set -e

echo "🚀 TryJob Backend Production Server ishga tushmoqda..."

# PostgreSQL ulanishini tekshirish (agar Postgres ishlatilsa)
if [ "$USE_POSTGRES" = "true" ] || [ "$ENVIRONMENT" = "production" ]; then
    echo "⏳ PostgreSQL ma'lumotlar bazasi kutilmoqda ($POSTGRES_SERVER:$POSTGRES_PORT)..."
    python -c "
import time, os, psycopg2
host = os.getenv('POSTGRES_SERVER', 'postgres')
port = int(os.getenv('POSTGRES_PORT', 5432))
user = os.getenv('POSTGRES_USER', 'postgres')
password = os.getenv('POSTGRES_PASSWORD', 'postgres')
dbname = os.getenv('POSTGRES_DB', 'tryjob_db')

for i in range(30):
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
        conn.close()
        print('✅ PostgreSQL tayyor!')
        break
    except Exception as e:
        print(f'Baza hali tayyor emas ({i+1}/30)... kutilmoqda')
        time.sleep(1)
else:
    import sys
    print('❌ Xatolik: PostgreSQL bilan ulanish vaqti tugadi (Timeout: 30s)!')
    sys.exit(1)
"
fi

# 1. Alembic Migratsiyalarini avtomatik yurgizish
echo "📦 Alembic migratsiyalari tekshirilmoqda va qo'llanilmoqda (alembic upgrade head)..."
alembic upgrade head

# 2. Boshlang'ich seed ma'lumotlarini yuklash (agar baza yangi bo'lsa)
echo "🌱 Boshlang'ich ma'lumotlar (Universitetlar, Case Cup, Simulyatsiyalar) tekshirilmoqda..."
python -c "
from app.database import SessionLocal
from app.seed_data import seed_database
with SessionLocal() as db:
    seed_database(db)
print('✅ Seed tekshiruvi muvaffaqiyatli yakunlandi.')
"

# 3. Gunicorn + Uvicorn Workers orqali Production Serverni ishga tushirish
WORKERS=${GUNICORN_WORKERS:-4}
PORT=${PORT:-8000}
TIMEOUT=${GUNICORN_TIMEOUT:-120}

echo "🔥 Server ishga tushdi: Gunicorn ($WORKERS workers) on 0.0.0.0:$PORT"
exec gunicorn app.main:app \
    --workers "$WORKERS" \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:$PORT" \
    --timeout "$TIMEOUT" \
    --keep-alive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
