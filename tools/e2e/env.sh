# E2E stek muhiti (CONTRACT.md §34.2) — `stack.sh` va `seed.sh` source qiladi.
# Faqat e2e uchun soxta qiymatlar; haqiqiy kalit/secret yo'q (AGENTS.md).
# `backend/.env`dagi qiymatlar ham shu yerda bekor qilinadi (muhit .env'dan ustun).

E2E_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export E2E_PYTHON="${E2E_PYTHON:-python3}"
export E2E_STATE_DIR="${E2E_STATE_DIR:-${TMPDIR:-/tmp}/tryjob-e2e}"
export E2E_API_PORT="${E2E_API_PORT:-8100}"
export E2E_LLM_PORT="${E2E_LLM_PORT:-8090}"

export DATABASE_URL="${E2E_DATABASE_URL:-postgresql+asyncpg://postgres:postgres@localhost:5432/tryjob_e2e}"
export REDIS_URL="${E2E_REDIS_URL:-redis://localhost:6379/5}"
export SECRET_KEY="e2e-only-not-a-secret"
export CORS_ORIGINS=""
export PUBLIC_URL="http://127.0.0.1:${E2E_WEB_PORT:-4173}"
export UPLOAD_DIR="$E2E_STATE_DIR/uploads"

# AI — faqat soxta LLM (tools/e2e/fake_llm.py)
export LLM_PROVIDERS="openai"
export OPENAI_API_KEY="e2e-fake-key"
export OPENAI_BASE_URL="http://127.0.0.1:${E2E_LLM_PORT}/v1"
export OPENAI_MODEL="fake"
export DEEPSEEK_API_KEY="" GEMINI_API_KEY="" LLM_TIMEOUT_SECONDS="5"

# Tashqi xizmatlar o'chiq: xat log'ga, push yo'q, kod lokal rejimda
export MAIL_BACKEND="console" SMTP_HOST=""
export VAPID_PUBLIC_KEY="" VAPID_PRIVATE_KEY="" VAPID_SUBJECT=""
export SANDBOX_URL="" SANDBOX_TOKEN=""
export LOG_FORMAT="text" LOG_LEVEL="INFO"

# Soxta soat (§34.1): libfaketime (`apt install faketime`) faqat Python jarayonlariga
# LD_PRELOAD bilan — jarayon pid'i o'zgarmaydi, signal to'g'ridan-to'g'ri yetadi.
# Monotonic soat haqiqiy qoladi (asyncio taymerlari buzilmaydi).
export FAKETIME_DONT_FAKE_MONOTONIC=1
if [[ -z "${E2E_FAKETIME_LIB:-}" ]]; then
  for lib in /usr/lib/*/faketime/libfaketime.so.1 /usr/local/lib/faketime/libfaketime.so.1; do
    [[ -e "$lib" ]] && E2E_FAKETIME_LIB="$lib" && break
  done
fi
export E2E_FAKETIME_LIB="${E2E_FAKETIME_LIB:?libfaketime topilmadi — apt install faketime yoki E2E_FAKETIME_LIB}"

# `faked cmd ...` — stack.sh yozgan siljish bilan (subshell + exec: pid — buyruqning o'zi)
faked() {
  local offset
  offset="$(cat "$E2E_STATE_DIR/faketime")" || { echo "soxta soat yo'q — avval stack.sh" >&2; return 1; }
  (export LD_PRELOAD="$E2E_FAKETIME_LIB" FAKETIME="$offset"; exec "$@")
}
