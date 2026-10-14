#!/usr/bin/env bash
# E2E backend steki (CONTRACT.md §34.2): soxta LLM, toza baza, migratsiya, kontent,
# admin, arq worker va API — barchasi bitta soxta soat bilan. Playwright `webServer`
# shuni ishga tushiradi va to'xtatadi; qo'lda ham ishlaydi (Ctrl+C — hammasi to'xtaydi).
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$E2E_ROOT/backend"
mkdir -p "$E2E_STATE_DIR"
rm -rf "$UPLOAD_DIR"

pids=()
cleanup() { for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; wait 2>/dev/null || true; }
trap cleanup EXIT INT TERM

"$E2E_PYTHON" ../tools/e2e/fake_llm.py --port "$E2E_LLM_PORT" &
pids+=($!)

# Soxta "hozir" — keyingi ish kuni 09:00 Toshkent (haqiqiy soat bilan hisoblanadi)
offset="$("$E2E_PYTHON" ../tools/e2e/seed.py offset | "$E2E_PYTHON" -c 'import json,sys; print(json.load(sys.stdin)["offset_seconds"])')"
echo "+${offset}" > "$E2E_STATE_DIR/faketime"
echo "e2e: soxta soat +${offset}s → $(faked date -u +%FT%TZ)"

"$E2E_PYTHON" ../tools/e2e/seed.py reset
faked "$E2E_PYTHON" -m alembic -c alembic/alembic.ini upgrade head
faked "$E2E_PYTHON" ../tools/import_scenario.py --publish content/scenarios/*.yaml
faked "$E2E_PYTHON" ../tools/bootstrap_admin.py --email admin@e2e.tryjob.uz --password 'E2e-Admin-Parol-1' --full-name "E2E Admin"

# fon jarayonlari to'g'ridan-to'g'ri (subshell'siz) — $! haqiqiy pid, cleanup ularni to'xtatadi
LD_PRELOAD="$E2E_FAKETIME_LIB" FAKETIME="+${offset}" "$E2E_PYTHON" -m arq app.ai.worker.WorkerSettings &
pids+=($!)
LD_PRELOAD="$E2E_FAKETIME_LIB" FAKETIME="+${offset}" \
  "$E2E_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port "$E2E_API_PORT" &
pids+=($!)
wait -n "${pids[@]}"
echo "e2e: stek jarayoni to'xtadi" >&2
exit 1
