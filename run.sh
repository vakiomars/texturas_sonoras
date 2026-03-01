#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv || echo "⚠️ Could not create .venv; will try venv/ if present."
fi

PY=""
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
else
  echo "No virtualenv found. Create one with: python3 -m venv .venv" >&2
  exit 1
fi

"$PY" -m pip install -r requirements-lite.txt
exec "$PY" -m streamlit run src/app.py
