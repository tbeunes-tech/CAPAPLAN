"""Équipes §3.3 — lecture (tout authentifié) + CRUD réservé Admin (§8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_current_user, get_db, require_role
from ..models import MonthlyCapacity, MonthlyLoad, Team
from ..security import ROLE_ADMIN

router = APIRouter(prefix="/teams", tags=["teams"], dependencies=[Depends(get_current_user)])
admin = require_role(ROLE_ADMIN)


@router.get("", response_model=list[schemas.TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.scalars(select(Team).order_by(Team.name)).all()


@router.post("", response_model=schemas.TeamOut, status_code=201, dependencies=[Depends(admin)])
def create_team(payload: schemas.TeamCreate, db: Session = Depends(get_db)):
    if db.get(Team, payload.name):
        raise HTTPException(409, f"équipe '{payload.name}' déjà existante")
    team = Team(**payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.put("/{name}", response_model=schemas.TeamOut, dependencies=[Depends(admin)])
def update_team(name: str, payload: schemas.TeamUpdate, db: Session = Depends(get_db)):
    team = db.get(Team, name)
    if not team:
        raise HTTPException(404, "équipe introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(team, field, value)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{name}", status_code=204, dependencies=[Depends(admin)])
def delete_team(name: str, db: Session = Depends(get_db)):
    team = db.get(Team, name)
    if not team:
        raise HTTPException(404, "équipe introuvable")
    # Garde d'intégrité : on refuse la suppression d'une équipe encore référencée (FK).
    loads = db.scalar(select(func.count()).select_from(MonthlyLoad).where(MonthlyLoad.team == name))
    caps = db.scalar(select(func.count()).select_from(MonthlyCapacity).where(MonthlyCapacity.team == name))
    if loads or caps:
        raise HTTPException(
            409,
            f"équipe '{name}' référencée par {loads} charge(s) et {caps} capacité(s) — "
            "réaffectez ou supprimez ces lignes avant de supprimer l'équipe.",
        )
    db.delete(team)
    db.commit()
