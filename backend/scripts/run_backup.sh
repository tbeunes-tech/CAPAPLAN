#!/bin/bash
# Wrapper de sauvegarde appelé par launchd (§8.3). Met pg_dump dans le PATH, active le venv,
# lit DATABASE_URL depuis backend/.env, écrit un dump horodaté avec rétention 30 j.
set -euo pipefail

export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
cd "/Users/theobeunes-devauze/Claude Code/portfolio-dsi/backend"
# shellcheck disable=SC1091
source .venv/bin/activate

exec python -m scripts.backup --out "$HOME/portfolio-backups" --retention-days 30
