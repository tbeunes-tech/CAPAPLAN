"""Schémas Pydantic.

Important : la validation des référentiels §4 s'applique à la **saisie** (create/update),
**pas** à la restitution. Les données migrées du classeur peuvent contenir des valeurs hors
référentiel (ex. `programme = 'Modern BI'`) ; on doit pouvoir les **lire** sans les rejeter
(et un Admin pourra étendre les référentiels au Lot 5).
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from . import enums


def _check(value: str | None, allowed: list[str], field: str) -> str | None:
    if value is None:
        return None
    if value not in allowed:
        raise ValueError(f"{field}: valeur '{value}' hors référentiel §4 ({', '.join(allowed)})")
    return value


# --------------------------------------------------------------------------- #
# Champs éditables d'un projet (sans validation — base commune)
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


class _ReferentialValidators:
    """Mixin : valide les champs à liste fermée contre le référentiel §4 (saisie uniquement)."""

    @field_validator("entite", check_fields=False)
    @classmethod
    def _v_entite(cls, v): return _check(v, enums.ENTITE, "entite")

    @field_validator("domain_lead", check_fields=False)
    @classmethod
    def _v_domain(cls, v): return _check(v, enums.DOMAIN_LEAD, "domain_lead")

    @field_validator("status", check_fields=False)
    @classmethod
    def _v_status(cls, v): return _check(v, enums.STATUT, "status")

    @field_validator("priorite", check_fields=False)
    @classmethod
    def _v_prio(cls, v): return _check(v, enums.PRIORITE, "priorite")

    @field_validator("pilier_strategique", check_fields=False)
    @classmethod
    def _v_pilier(cls, v): return _check(v, enums.PILIER_STRATEGIQUE, "pilier_strategique")

    # programme : texte libre (cf. enums.PROGRAMME_IS_FREE_TEXT) — pas de validation fermée.


class ProjectCreate(ProjectFields, _ReferentialValidators):
    project_name: str  # obligatoire à la création (§3.1)


class ProjectUpdate(ProjectFields, _ReferentialValidators):
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
# Référentiel chefs de projet (Paramétrage)
# --------------------------------------------------------------------------- #
class ProjectLeaderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    active: bool


class ProjectLeaderCreate(BaseModel):
    name: str
    active: bool = True


class ProjectLeaderUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None
