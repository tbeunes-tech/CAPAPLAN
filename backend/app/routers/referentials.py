"""Référentiels §4 gérés en base (table `referentials`) — onglet Paramétrage.

Lecture : tout utilisateur authentifié (listes déroulantes des formulaires).
Écriture : Admin. Renommer une valeur **se propage** aux projets qui l'utilisent (cascade).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from .. import enums, schemas
from ..deps import get_current_user, get_db, require_role
from ..models import Project, Referential
from ..security import ROLE_ADMIN

router = APIRouter(prefix="/referentials", tags=["referentials"],
                   dependencies=[Depends(get_current_user)])
admin = require_role(ROLE_ADMIN)

CATEGORIES = enums.REFERENTIAL_CATEGORIES


def _ensure_category(category: str) -> None:
    if category not in CATEGORIES:
        raise HTTPException(422, f"catégorie inconnue: {category} ({', '.join(CATEGORIES)})")


# --------------------------------------------------------------------------- #
# Lecture
# --------------------------------------------------------------------------- #
@router.get("")
def get_referentials(db: Session = Depends(get_db)) -> dict:
    """Valeurs **actives** par catégorie (pour les listes déroulantes). Forme {cat: [valeurs]}."""
    out: dict[str, list[str]] = {c: [] for c in CATEGORIES}
    rows = db.scalars(
        select(Referential).where(Referential.active.is_(True)).order_by(Referential.value)
    ).all()
    for r in rows:
        out.setdefault(r.category, []).append(r.value)
    return out


@router.get("/manage", response_model=list[schemas.ReferentialOut])
def manage_list(category: str | None = None, db: Session = Depends(get_db)):
    """Toutes les valeurs (actives et inactives) pour la gestion Admin."""
    stmt = select(Referential).order_by(Referential.category, Referential.value)
    if category:
        stmt = stmt.where(Referential.category == category)
    return db.scalars(stmt).all()


@router.get("/categories")
def categories() -> list[dict]:
    return [{"key": c, "label": enums.CATEGORY_LABELS.get(c, c)} for c in CATEGORIES]


# --------------------------------------------------------------------------- #
# Écriture (Admin)
# --------------------------------------------------------------------------- #
@router.post("", response_model=schemas.ReferentialOut, status_code=201,
             dependencies=[Depends(admin)])
def create(payload: schemas.ReferentialCreate, db: Session = Depends(get_db)):
    _ensure_category(payload.category)
    value = payload.value.strip()
    if not value:
        raise HTTPException(422, "valeur vide")
    if db.scalar(select(Referential).where(
        Referential.category == payload.category, Referential.value == value
    )):
        raise HTTPException(409, f"'{value}' existe déjà dans {payload.category}")
    r = Referential(category=payload.category, value=value, active=payload.active)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/{ref_id}", dependencies=[Depends(admin)])
def update(ref_id: int, payload: schemas.ReferentialUpdate, db: Session = Depends(get_db)):
    r = db.get(Referential, ref_id)
    if not r:
        raise HTTPException(404, "valeur introuvable")
    cascaded = 0
    if payload.value is not None and payload.value.strip() and payload.value.strip() != r.value:
        new = payload.value.strip()
        if db.scalar(select(Referential).where(
            Referential.category == r.category, Referential.value == new, Referential.id != r.id
        )):
            raise HTTPException(409, f"'{new}' existe déjà dans {r.category}")
        old = r.value
        # CASCADE : tous les projets portant l'ancienne valeur héritent de la nouvelle (audité).
        col = getattr(Project, r.category)
        for proj in db.scalars(select(Project).where(col == old)).all():
            setattr(proj, r.category, new)
            cascaded += 1
        r.value = new
    if payload.active is not None:
        r.active = payload.active
    db.commit()
    db.refresh(r)
    return {"id": r.id, "category": r.category, "value": r.value, "active": r.active,
            "projects_updated": cascaded}


@router.delete("/{ref_id}", dependencies=[Depends(admin)])
def delete(ref_id: int, db: Session = Depends(get_db)):
    r = db.get(Referential, ref_id)
    if not r:
        raise HTTPException(404, "valeur introuvable")
    col = getattr(Project, r.category)
    used = db.scalar(select(func.count()).select_from(Project).where(col == r.value))
    if used:
        raise HTTPException(
            409,
            f"'{r.value}' est utilisée par {used} projet(s). Renommez-la ou désactivez-la "
            "plutôt que de la supprimer.",
        )
    db.delete(r)
    db.commit()
    return {"deleted": ref_id}


@router.post("/seed", dependencies=[Depends(admin)])
def seed(db: Session = Depends(get_db)):
    """Amorce la table : valeurs §4 par défaut + valeurs déjà présentes sur les projets (idempotent)."""
    return {"added": _seed_referentials(db)}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _seed_referentials(db: Session) -> int:
    existing = {(r.category, r.value) for r in db.scalars(select(Referential)).all()}
    added = 0

    def add(cat: str, val: str):
        nonlocal added
        val = (val or "").strip()
        if val and (cat, val) not in existing:
            db.add(Referential(category=cat, value=val, active=True))
            existing.add((cat, val))
            added += 1

    for cat, values in enums.REFERENTIAL_DEFAULTS.items():
        for v in values:
            add(cat, v)
    for cat in CATEGORIES:
        col = getattr(Project, cat)
        for v in db.scalars(select(distinct(col)).where(col.is_not(None))).all():
            add(cat, v)
    db.commit()
    return added
