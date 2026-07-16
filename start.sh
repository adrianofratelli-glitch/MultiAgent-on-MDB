#!/bin/bash
set -e
cd "$(dirname "$0")"

if lsof -nP -iTCP:8031 -sTCP:LISTEN >/dev/null 2>&1 || lsof -nP -iTCP:5191 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "PoV já está rodando (porta 8031 e/ou 5191 ocupada). Abrindo no navegador."
  open http://127.0.0.1:5191
  exit 0
fi

source .venv/bin/activate
(cd backend && python run.py) &
BACKEND_PID=$!

(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM

sleep 3
open http://127.0.0.1:5191

wait
