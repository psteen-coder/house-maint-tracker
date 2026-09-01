#!/usr/bin/env bash
# Desktop helper: venv + uvicorn serving the built UI on :8000
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
