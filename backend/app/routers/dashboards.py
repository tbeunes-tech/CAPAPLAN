"""Dashboards lecture seule §5.3 / §5.5 / §5.6 / §5.7 / §5.8."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db, parse_start
from ..services.aggregations import (
    overload_list, prioritization_plan, roadmap,
    team_load_detail, team_load_pivot, team_occupancy_pivot,
)

# Dashboards = lecture seule, accessibles à tout utilisateur authentifié (Lecteur+).
router = APIRouter(prefix="/dashboards", tags=["dashboards"], dependencies=[Depends(get_current_user)])


@router.get("/team-load")          # §5.3
def team_load(start: str | None = None, db: Session = Depends(get_db)):
    return team_load_pivot(db, parse_start(start))


@router.get("/team-load/detail")   # §5.3 — drill-down par projet
def team_load_detail_route(team: str, start: str | None = None, db: Session = Depends(get_db)):
    return team_load_detail(db, team, parse_start(start))


@router.get("/occupancy")          # §5.5
def occupancy(start: str | None = None, db: Session = Depends(get_db)):
    return team_occupancy_pivot(db, parse_start(start))


@router.get("/overloads")          # §5.6
def overloads(start: str | None = None, db: Session = Depends(get_db)):
    return overload_list(db, parse_start(start))


@router.get("/roadmap")            # §5.7
def roadmap_view(db: Session = Depends(get_db)):
    return roadmap(db)


@router.get("/prioritization")     # §5.8
def prioritization(start: str | None = None, db: Session = Depends(get_db)):
    return prioritization_plan(db, parse_start(start))
