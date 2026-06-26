"""Exporte les données (anonymisées) de la base locale vers un JSON embarquable.

Ce fichier (`backend/seed_data.json`) sert à peupler la base cloud **depuis le cloud**
(le réseau local bloque l'accès Postgres). Les données étant anonymisées, il est sans risque
de le committer. N'exporte PAS les utilisateurs (l'admin est recréé depuis l'environnement).

    python -m scripts.export_seed --database-url postgresql+psycopg2://.../portfolio --out seed_data.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import MonthlyCapacity, MonthlyLoad, Project, Referential, Team

TABLES = {
    "teams": (Team, ["name", "manager", "capacite_etp", "description"]),
    "projects": (Project, [
        "project_id", "entite", "domain_lead", "project_name", "project_leader", "status",
        "priorite", "pilier_strategique", "budget_item", "budget_owner", "programme",
        "prio_dsi", "in_plan", "start_date", "end_date", "last_update", "total_project_load",
    ]),
    "monthly_loads": (MonthlyLoad, ["project_id", "team", "month", "days", "in_plan", "updated_at"]),
    "monthly_capacity": (MonthlyCapacity, [
        "team", "month", "etp_team", "etp_projet", "part_projet", "jours_indispo",
        "capa_projet", "updated_at",
    ]),
    "referentials": (Referential, ["category", "value", "active"]),
}


def _val(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--database-url", default=settings.database_url)
    p.add_argument("--out", default="seed_data.json")
    args = p.parse_args(argv)

    engine = create_engine(args.database_url, future=True)
    data: dict[str, list[dict]] = {}
    with Session(engine) as s:
        for name, (model, cols) in TABLES.items():
            rows = s.scalars(select(model)).all()
            data[name] = [{c: _val(getattr(r, c)) for c in cols} for r in rows]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print({k: len(v) for k, v in data.items()}, "→", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
