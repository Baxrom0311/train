#!/usr/bin/env bash
# Playwright fixture'lari uchun: `seed.sh student --email … [--completed slug]` (CONTRACT.md §34.2)
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$E2E_ROOT/backend"
faked "$E2E_PYTHON" ../tools/e2e/seed.py "$@"
