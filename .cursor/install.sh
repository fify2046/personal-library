#!/usr/bin/env bash
# Idempotent repository bootstrap for the EBook Reader & Manager.
# Installs backend (Python) and frontend (Node) dependencies and prepares the
# backend .env. PostgreSQL itself is provided by the base environment snapshot.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "[install] Setting up Python virtualenv and backend dependencies"
if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r backend/requirements.txt

echo "[install] Preparing backend/.env"
if [ ! -f backend/.env ]; then
  cat > backend/.env <<'ENV'
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ebook_db
DB_USER=ebook
DB_PASSWORD=asdfgh
IMAGES_DIR=../images
ENV
fi

echo "[install] Installing frontend dependencies"
cd frontend
npm install

echo "[install] Done"
