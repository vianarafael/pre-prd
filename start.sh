#!/usr/bin/env bash
set -euo pipefail
export UVICORN_RELOAD=${UVICORN_RELOAD:-1}
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 ${UVICORN_RELOAD:+--reload}
