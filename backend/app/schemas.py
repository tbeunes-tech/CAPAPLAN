"""Schémas Pydantic.

Les listes (référentiels) sont gérées en base (table `referentials`, onglet Paramétrage) et
non plus validées en dur ici : la saisie passe par des listes déroulantes alimentées par la base,
et les valeurs legacy du classeur restent lisibles/éditables.
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


# --------------------------------------------------------------------------- #
# Champs éditables d'un projet
# --------------------------------------------------------------------------- #
class ProjectFields(BaseModel):
    entite: str | None = None
    domain_lead: str | None = None
    project_name: str | None = None
    project_leader: str | None = None
    status: str | None = None
    priorite: str | None = None
    pilier_strategique: str | None = None
    budget_item: str | None = None
    budget_owner: str | None = None
    programme: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class ProjectCreate(ProjectFields):
    project_name: str  # obligatoire à la création (§3.1)


class ProjectUpdate(ProjectFields):
    pass  # patch partiel : tous champs optionnels


class ProjectOut(ProjectFields):
    """Restitution — AUCUNE validation de référentiel (legacy lisible)."""
    model_config = ConfigDict(from_attributes=True)
    project_id: str
    in_plan: bool
    last_update: datetime | None = None
    total_project_load: float | None = None


class QC(BaseModel):
    date_error: str | None
    status_error: str | None
    obsolete_forecast: str | None
    leader_error: str | None
    has_error: bool


class ProjectWithQC(ProjectOut):
    qc: QC


# --------------------------------------------------------------------------- #
# Monthly loads — grille de saisie (§5.2)
# --------------------------------------------------------------------------- #
class LoadCell(BaseModel):
    team: str
    month: date
    days: float
    # Verrouillage optimiste : horodatage de la cellule tel que vu par le client à l'édition.
    # None = le client pensait que la cellule n'existait pas encore.
    base_updated_at: datetime | None = None


class LoadGridSave(BaseModel):
    cells: list[LoadCell]


# --------------------------------------------------------------------------- #
# Teams / Capacity
# --------------------------------------------------------------------------- #
class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    manager: str | None = None
    capacite_etp: float | None = None
    description: str | None = None


class TeamCreate(BaseModel):
    name: str
    manager: str | None = None
    capacite_etp: float | None = None
    description: str | None = None


class TeamUpdate(BaseModel):
    # `name` est la PK et la clé étrangère des charges/capacités → immuable (comme project_id).
    manager: str | None = None
    capacite_etp: float | None = None
    description: str | None = None


class CapacityUpsert(BaseModel):
    team: str
    month: date
    etp_team: float | None = None
    etp_projet: float | None = None
    jours_indispo: float | None = None


# --------------------------------------------------------------------------- #
# Référentiels génériques (Paramétrage)
# --------------------------------------------------------------------------- #
class ReferentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category: str
    value: str
    active: bool


class ReferentialCreate(BaseModel):
    category: str
    value: str
    active: bool = True


class ReferentialUpdate(BaseModel):
    value: str | None = None
    active: bool | None = None
