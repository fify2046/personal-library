#!/usr/bin/env bash
# Per-boot startup: bring up PostgreSQL and ensure the ebook database, role and
# schema exist. Idempotent and safe to run on every boot.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[start] Ensuring PostgreSQL cluster is running"
if ! sudo pg_lsclusters -h 2>/dev/null | grep -q "online"; then
  sudo pg_ctlcluster 16 main start || true
fi

echo "[start] Waiting for PostgreSQL to accept connections"
for i in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then
    break
  fi
  sleep 1
done

echo "[start] Ensuring role and database exist"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='ebook') THEN
    CREATE ROLE ebook LOGIN PASSWORD 'asdfgh' SUPERUSER;
  END IF;
END $$;
SQL
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='ebook_db'" | grep -q 1; then
  sudo -u postgres createdb -O ebook ebook_db
fi

echo "[start] Ensuring schema (idempotent)"
PGPASSWORD=asdfgh psql -h localhost -U ebook -d ebook_db -v ON_ERROR_STOP=1 \
  -f "$REPO_ROOT/InitBookData/sql/init_database.sql" >/dev/null

echo "[start] PostgreSQL ready"
