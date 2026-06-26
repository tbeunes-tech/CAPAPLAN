"""Initialisation cloud (one-shot) — peuple la base depuis le seed embarqué.

Nécessaire parce que le réseau local ne peut pas joindre la base cloud (port Postgres bloqué) :
on déclenche le chargement **depuis le serveur déployé** (réseau ouvert) via cet endpoint, une
seule fois, protégé par un jeton. Idempotent : ne fait rien si la base contient déjà des projets.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import audit_disabled
from ..database import Base, engine
from ..deps import get_db
from ..models import MonthlyCapacity, MonthlyLoad, Project, Referential, Team, User
from ..security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])

SEED_PATH = Path(__file__).resolve().parent.parent.parent / "seed_data.json"
_DATE = {"month", "start_date", "end_date"}
_DT = {"updated_at", "last_update"}


def _coerce(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if v is None:
            out[k] = None
        elif k in _DATE:
            out[k] = date.fromisoformat(v)
        elif k in _DT:
            out[k] = datetime.fromisoformat(v)
        else:
            out[k] = v
    return out


def run_seed(db: Session) -> dict:
    """Crée le schéma, charge le seed et l'admin (depuis l'environnement). Idempotent."""
    Base.metadata.create_all(engine)  # crée les tables si absentes

    already = db.scalar(select(func.count()).select_from(Project))
    if already:
        return {"status": "already-initialized", "projects": already}

    audit_disabled.set(True)  # ne pas journaliser le chargement initial
    if SEED_PATH.exists():
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        for t in data.get("teams", []):
            db.add(Team(**_coerce(t)))
        db.flush()
        for p in data.get("projects", []):
            db.add(Project(**_coerce(p)))
        for r in data.get("referentials", []):
            db.add(Referential(**_coerce(r)))
        db.flush()
        for l in data.get("monthly_loads", []):
            db.add(MonthlyLoad(**_coerce(l)))
        for c in data.get("monthly_capacity", []):
            db.add(MonthlyCapacity(**_coerce(c)))

    # Compte admin créé depuis l'environnement (jamais committé).
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if email and password and not db.scalar(select(User).where(User.email == email)):
        db.add(User(email=email, role="admin", password_hash=hash_password(password),
                    full_name="Admin"))

    db.commit()
    return {
        "status": "initialized",
        "teams": db.scalar(select(func.count()).select_from(Team)),
        "projects": db.scalar(select(func.count()).select_from(Project)),
        "monthly_loads": db.scalar(select(func.count()).select_from(MonthlyLoad)),
    }


@router.post("/init")
def init_db(x_init_token: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Endpoint manuel d'initialisation, protégé par jeton."""
    expected = os.environ.get("INIT_TOKEN")
    if not expected or x_init_token != expected:
        raise HTTPException(403, "jeton d'initialisation invalide")
    return run_seed(db)
