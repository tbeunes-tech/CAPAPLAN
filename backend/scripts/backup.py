"""Sauvegarde quotidienne automatique (§8.3).

Génère un dump PostgreSQL horodaté via `pg_dump`, applique une rétention glissante (30 j par
défaut), journalise succès/échec et sort en code ≠ 0 en cas d'échec (pour qu'un cron/superviseur
puisse alerter).

    python -m scripts.backup --out /var/backups/portfolio --retention-days 30

`DATABASE_URL` (ou --database-url) doit pointer une base PostgreSQL. Pour la planification, voir
le README (cron / systemd timer). Le dossier de sortie doit être sur un **volume distinct** du
serveur applicatif.
"""
from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.config import settings

log = logging.getLogger("backup")


def _ts() -> str:
    # Horodatage UTC déterministe (pas de dépendance à la locale).
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def run_backup(database_url: str, out_dir: Path, retention_days: int) -> Path:
    if not database_url.startswith("postgresql"):
        raise SystemExit(
            f"backup.py cible PostgreSQL via pg_dump ; DATABASE_URL={database_url!r}. "
            "En SQLite (dev), copiez simplement le fichier .db."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"portfolio-{_ts()}.dump"

    # pg_dump attend une URI libpq « postgresql://… » : on retire le suffixe de driver
    # SQLAlchemy (« +psycopg2 ») le cas échéant.
    pg_url = re.sub(r"^(postgresql)\+\w+://", r"\1://", database_url)

    # Format custom (-Fc) : compressé et restaurable sélectivement via pg_restore.
    cmd = ["pg_dump", "--format=custom", "--no-owner", "--file", str(target), pg_url]
    log.info("pg_dump → %s", target)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        log.error("ÉCHEC pg_dump (code %s): %s", res.returncode, res.stderr.strip())
        target.unlink(missing_ok=True)  # ne pas laisser un dump vide/partiel
        raise SystemExit(2)
    size = target.stat().st_size
    if size == 0:
        log.error("ÉCHEC : dump vide")
        raise SystemExit(2)
    log.info("OK dump %.1f Mo", size / 1e6)

    _prune(out_dir, retention_days)
    return target


def _prune(out_dir: Path, retention_days: int) -> None:
    cutoff = time.time() - retention_days * 86_400
    removed = 0
    for f in out_dir.glob("portfolio-*.dump"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    if removed:
        log.info("rétention : %s dump(s) > %s j supprimé(s)", removed, retention_days)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [backup] %(message)s")
    p = argparse.ArgumentParser(description="Sauvegarde quotidienne (§8.3).")
    p.add_argument("--database-url", default=os.environ.get("DATABASE_URL", settings.database_url))
    p.add_argument("--out", default="./backups", type=Path)
    p.add_argument("--retention-days", default=30, type=int)
    args = p.parse_args(argv)
    try:
        run_backup(args.database_url, args.out, args.retention_days)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — on veut alerter sur tout échec
        log.exception("ÉCHEC inattendu : %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
