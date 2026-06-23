"""Référentiel des chefs de projet (onglet Paramétrage).

Lecture : tout utilisateur authentifié (pour la liste de suggestions du formulaire).
Écriture : Admin uniquement (§8.1).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from .. import schemas
from ..deps import get_current_user, get_db, require_role
from ..models import Project, ProjectLeader
from ..security import ROLE_ADMIN

router = APIRouter(prefix="/project-leaders", tags=["project-leaders"],
                   dependencies=[Depends(get_current_user)])
admin = require_role(ROLE_ADMIN)


@router.get("", response_model=list[schemas.ProjectLeaderOut])
def list_leaders(db: Session = Depends(get_db)):
    return db.scalars(select(ProjectLeader).order_by(ProjectLeader.name)).all()


@router.post("", response_model=schemas.ProjectLeaderOut, status_code=201,
             dependencies=[Depends(admin)])
def create_leader(payload: schemas.ProjectLeaderCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(422, "nom vide")
    if db.scalar(select(ProjectLeader).where(ProjectLeader.name == name)):
        raise HTTPException(409, f"chef de projet '{name}' déjà présent")
    leader = ProjectLeader(name=name, active=payload.active)
    db.add(leader)
    db.commit()
    db.refresh(leader)
    return leader


@router.put("/{leader_id}", response_model=schemas.ProjectLeaderOut,
            dependencies=[Depends(admin)])
def update_leader(leader_id: int, payload: schemas.ProjectLeaderUpdate, db: Session = Depends(get_db)):
    leader = db.get(ProjectLeader, leader_id)
    if not leader:
        raise HTTPException(404, "chef de projet introuvable")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        leader.name = data["name"].strip()
    if "active" in data and data["active"] is not None:
        leader.active = data["active"]
    db.commit()
    db.refresh(leader)
    return leader


@router.delete("/{leader_id}", status_code=204, dependencies=[Depends(admin)])
def delete_leader(leader_id: int, db: Session = Depends(get_db)):
    leader = db.get(ProjectLeader, leader_id)
    if not leader:
        raise HTTPException(404, "chef de projet introuvable")
    db.delete(leader)
    db.commit()


@router.post("/import-from-projects", dependencies=[Depends(admin)])
def import_from_projects(db: Session = Depends(get_db)):
    """Alimente la liste à partir des chefs de projet déjà saisis sur les projets (idempotent)."""
    existing = {l.name for l in db.scalars(select(ProjectLeader)).all()}
    names = db.scalars(
        select(distinct(Project.project_leader)).where(Project.project_leader.is_not(None))
    ).all()
    added = 0
    for n in names:
        n = (n or "").strip()
        if n and n not in existing:
            db.add(ProjectLeader(name=n, active=True))
            existing.add(n)
            added += 1
    db.commit()
    return {"added": added, "total": len(existing)}
