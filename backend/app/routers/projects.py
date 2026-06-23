"""CRUD projets (§5.1) + grille de saisie de charge (§5.2)."""
from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_current_user, get_db, require_role
from ..models import ChangeLog, MonthlyLoad, Project, Team
from ..security import ROLE_CONTRIBUTOR
from ..services.ids import generate_project_id
from ..services.qc import qc_for_project
from ..services.recompute import (
    apply_project_status, recompute_project_rollups,
)
from ..services.window import add_months, first_of_month

# Lecture : tout utilisateur authentifié (Lecteur+). Écritures : Contributeur+ (cf. routes).
router = APIRouter(prefix="/projects", tags=["projects"], dependencies=[Depends(get_current_user)])
contributor = require_role(ROLE_CONTRIBUTOR)


def _with_qc(project: Project) -> schemas.ProjectWithQC:
    base = schemas.ProjectOut.model_validate(project).model_dump()
    return schemas.ProjectWithQC(**base, qc=schemas.QC(**qc_for_project(project)))


@router.get("", response_model=list[schemas.ProjectWithQC])
def list_projects(db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.project_id)).all()
    return [_with_qc(p) for p in projects]


@router.get("/{project_id}", response_model=schemas.ProjectWithQC)
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "projet introuvable")
    return _with_qc(p)


@router.get("/{project_id}/history")
def project_history(project_id: str, limit: int = 200, db: Session = Depends(get_db)):
    """Historique des modifications du projet (§8.2) : ses propres changements + ceux de ses
    charges. Reconstitution « qui a changé quoi, quand, avant → après ». Lecture (Lecteur+)."""
    if not db.get(Project, project_id):
        raise HTTPException(404, "projet introuvable")
    stmt = (
        select(ChangeLog)
        .where(or_(
            and_(ChangeLog.table_name == "projects", ChangeLog.row_pk == project_id),
            and_(ChangeLog.table_name == "monthly_loads",
                 ChangeLog.row_pk.like(f"{project_id}|%")),
        ))
        .order_by(ChangeLog.ts.desc())
        .limit(min(limit, 1000))
    )
    rows = db.scalars(stmt).all()
    return [
        {
            "id": r.id, "ts": r.ts, "user_email": r.user_email,
            "table_name": r.table_name, "row_pk": r.row_pk, "action": r.action,
            "before": r.before, "after": r.after,
        }
        for r in rows
    ]


@router.post("", response_model=schemas.ProjectWithQC, status_code=201,
             dependencies=[Depends(contributor)])
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    p = Project(project_id=generate_project_id(db), **payload.model_dump())
    apply_project_status(p)            # in_plan (§6.2)
    p.total_project_load = 0.0
    db.add(p)
    db.commit()
    db.refresh(p)
    return _with_qc(p)


@router.put("/{project_id}", response_model=schemas.ProjectWithQC,
            dependencies=[Depends(contributor)])
def update_project(project_id: str, payload: schemas.ProjectUpdate, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "projet introuvable")
    data = payload.model_dump(exclude_unset=True)
    # project_id immuable (§6.1) — non modifiable, jamais exposé en écriture.
    for field, value in data.items():
        setattr(p, field, value)
    apply_project_status(p)            # recalcule in_plan + propage aux charges (§3.2/§6.2)
    db.commit()
    db.refresh(p)
    return _with_qc(p)


@router.delete("/{project_id}", status_code=204, dependencies=[Depends(contributor)])
def delete_project(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "projet introuvable")
    db.delete(p)
    db.commit()


# --------------------------------------------------------------------------- #
# §5.2 — grille de saisie équipes × mois
# --------------------------------------------------------------------------- #
def _grid_months(p: Project) -> list[date]:
    """Fenêtre du projet (§5.2) : du mois courant — ou du mois de début s'il est futur —
    jusqu'au mois de fin."""
    today_m = first_of_month(date.today())
    start_m = first_of_month(p.start_date) if p.start_date else today_m
    start = start_m if start_m > today_m else today_m
    end = first_of_month(p.end_date) if p.end_date else start
    months, m = [], start
    while m <= end:
        months.append(m)
        m = add_months(m, 1)
    return months or [start]


@router.get("/{project_id}/loads")
def get_load_grid(project_id: str, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "projet introuvable")
    months = _grid_months(p)
    existing = {
        (l.team, l.month): l
        for l in db.scalars(select(MonthlyLoad).where(MonthlyLoad.project_id == project_id)).all()
    }
    teams = db.scalars(select(Team.name).order_by(Team.name)).all()

    def cell(t, m):
        l = existing.get((t, m))
        return {
            "team": t, "month": m,
            "days": float(l.days or 0) if l else 0.0,
            # Horodatage renvoyé au client pour le verrouillage optimiste à la sauvegarde.
            "updated_at": l.updated_at.isoformat() if l and l.updated_at else None,
        }

    return {
        "project_id": project_id,
        "months": months,
        "teams": teams,
        "cells": [cell(t, m) for t in teams for m in months],
    }


@router.put("/{project_id}/loads", response_model=schemas.ProjectWithQC,
            dependencies=[Depends(contributor)])
def save_load_grid(project_id: str, payload: schemas.LoadGridSave, db: Session = Depends(get_db)):
    p = db.get(Project, project_id)
    if not p:
        raise HTTPException(404, "projet introuvable")
    now = datetime.now()
    existing = {
        (l.team, l.month): l
        for l in db.scalars(select(MonthlyLoad).where(MonthlyLoad.project_id == project_id)).all()
    }
    valid_teams = set(db.scalars(select(Team.name)).all())

    # 1) Verrouillage optimiste : on refuse en bloc si une cellule a changé côté serveur depuis
    #    que le client l'a lue (saisie concurrente). Aucune écriture si conflit (tout ou rien).
    conflicts = []
    for cell in payload.cells:
        if cell.team not in valid_teams:
            raise HTTPException(422, f"équipe inconnue: {cell.team}")
        cur = existing.get((cell.team, first_of_month(cell.month)))
        cur_ts = cur.updated_at if cur else None
        if cur_ts != cell.base_updated_at:
            conflicts.append({
                "team": cell.team,
                "month": first_of_month(cell.month).isoformat(),
                "server_days": float(cur.days or 0) if cur else 0.0,
                "server_updated_at": cur_ts.isoformat() if cur_ts else None,
                "your_days": cell.days,
            })
    if conflicts:
        raise HTTPException(409, detail={
            "message": "Des cellules ont été modifiées par un autre utilisateur depuis votre "
                       "dernière lecture. Aucune modification enregistrée.",
            "conflicts": conflicts,
        })

    # 2) Pas de conflit → on applique.
    for cell in payload.cells:
        month = first_of_month(cell.month)
        cur = existing.get((cell.team, month))
        if cur is None:
            db.add(MonthlyLoad(
                project_id=project_id, team=cell.team, month=month,
                days=cell.days, in_plan=p.in_plan, updated_at=now,
            ))
        else:
            cur.days = cell.days
            cur.in_plan = p.in_plan      # recopié du projet (§3.2)
            cur.updated_at = now
    db.flush()
    recompute_project_rollups(db, p)     # last_update (§6.6) + total_project_load
    db.commit()
    db.refresh(p)
    return _with_qc(p)
