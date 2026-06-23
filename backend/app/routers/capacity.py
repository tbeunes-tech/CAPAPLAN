"""Capacité §3.4 / §5.4 — pivot (lecture) + upsert (réservé Admin au Lot 5)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_current_user, get_db, parse_start, require_role
from ..models import MonthlyCapacity, Team
from ..security import ROLE_ADMIN
from ..services.aggregations import team_capacity_pivot
from ..services.recompute import recompute_capacity_row
from ..services.window import first_of_month

router = APIRouter(prefix="/capacity", tags=["capacity"], dependencies=[Depends(get_current_user)])


@router.get("/pivot")
def capacity_pivot(start: str | None = None, db: Session = Depends(get_db)):
    return team_capacity_pivot(db, parse_start(start))


@router.get("/cell")
def capacity_cell(team: str, month: str, db: Session = Depends(get_db)):
    """Ligne de capacité d'une équipe pour un mois (entrées éditables + capa calculée).

    Renvoie des valeurs nulles si la ligne n'existe pas encore (création à la volée à la saisie).
    """
    m = first_of_month(date.fromisoformat(month))
    cap = db.scalar(
        select(MonthlyCapacity).where(MonthlyCapacity.team == team, MonthlyCapacity.month == m)
    )
    return {
        "team": team,
        "month": m.isoformat(),
        "etp_team": float(cap.etp_team) if cap and cap.etp_team is not None else None,
        "etp_projet": float(cap.etp_projet) if cap and cap.etp_projet is not None else None,
        "part_projet": float(cap.part_projet) if cap and cap.part_projet is not None else None,
        "jours_indispo": float(cap.jours_indispo) if cap and cap.jours_indispo is not None else None,
        "capa_projet": float(cap.capa_projet) if cap and cap.capa_projet is not None else None,
        "exists": cap is not None,
    }


@router.put("", dependencies=[Depends(require_role(ROLE_ADMIN))])
def upsert_capacity(payload: schemas.CapacityUpsert, db: Session = Depends(get_db)):
    if payload.team not in set(db.scalars(select(Team.name)).all()):
        raise HTTPException(422, f"équipe inconnue: {payload.team}")
    month = first_of_month(payload.month)
    cap = db.scalar(
        select(MonthlyCapacity).where(
            MonthlyCapacity.team == payload.team, MonthlyCapacity.month == month
        )
    )
    if cap is None:
        cap = MonthlyCapacity(team=payload.team, month=month)
        db.add(cap)
    cap.etp_team = payload.etp_team
    cap.etp_projet = payload.etp_projet
    cap.jours_indispo = payload.jours_indispo
    recompute_capacity_row(cap)        # part_projet + capa_projet (§6.7)
    db.commit()
    db.refresh(cap)
    return {
        "team": cap.team, "month": cap.month, "etp_team": float(cap.etp_team or 0),
        "etp_projet": float(cap.etp_projet or 0), "part_projet": float(cap.part_projet or 0),
        "jours_indispo": float(cap.jours_indispo or 0), "capa_projet": float(cap.capa_projet or 0),
    }
