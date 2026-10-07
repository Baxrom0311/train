#!/bin/sh
# Testlar uchun alohida baza (CONTRACT.md §3.1). Faqat volume birinchi marta
# yaratilganda ishga tushadi.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE DATABASE ${POSTGRES_TEST_DB:-tryjob_test} OWNER "$POSTGRES_USER";
SQL
# pgvector (§9.4) — superuser sifatida ikkala bazada ham oldindan yoqiladi.
for db in "$POSTGRES_DB" "${POSTGRES_TEST_DB:-tryjob_test}"; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$db" \
    -c "CREATE EXTENSION IF NOT EXISTS vector;"
done
