"""Contrôle qualité §7 — 4 indicateurs d'erreur, sur projets `in_plan = true`.

Fonctions pures : prennent les champs du projet + la date du jour, renvoient les libellés
d'erreur (ou None). `qc_for_project` agrège les 4 et indique si la ligne est en erreur.
"""
from __future__ import annotations

from datetime import date, datetime

OBSOLETE_DAYS = 31


def date_error(start_date: date | None, end_date: date | None) -> str | None:
    """§7.1 — `Missing Start` puis `Missing End`."""
    if start_date is None:
        return "Missing Start"
    if end_date is None:
        return "Missing End"
    return None


def status_error(status: str | None, start_date: date | None,
                 end_date: date | None, today: date) -> str | None:
    """§7.2 — incohérence statut / dates."""
    if status == "Scheduled" and start_date is not None and start_date < today:
        return "Scheduled but started"
    if status == "In Progress" and end_date is not None and end_date < today:
        return "In Progress but ended"
    return None


def obsolete_forecast(status: str | None, last_update: datetime | None,
                      today: date) -> str | None:
    """§7.3 — In Progress et last_update absent ou ≥ 31 jours."""
    if status != "In Progress":
        return None
    if last_update is None:
        return "Obsolete forecast"
    age = (today - last_update.date()).days
    return "Obsolete forecast" if age >= OBSOLETE_DAYS else None


def leader_error(status: str | None, project_leader: str | None) -> str | None:
    """§7.4 — In Progress et project_leader vide."""
    if status == "In Progress" and not (project_leader or "").strip():
        return "Leader Error"
    return None


def qc_for_project(project, today: date | None = None) -> dict:
    """Calcule les 4 indicateurs. Ne s'applique qu'aux projets in_plan (§7) ;
    pour un projet hors plan, renvoie tout à None et `has_error=False`."""
    today = today or date.today()
    if not project.in_plan:
        return {"date_error": None, "status_error": None, "obsolete_forecast": None,
                "leader_error": None, "has_error": False}
    de = date_error(project.start_date, project.end_date)
    se = status_error(project.status, project.start_date, project.end_date, today)
    of = obsolete_forecast(project.status, project.last_update, today)
    le = leader_error(project.status, project.project_leader)
    return {
        "date_error": de,
        "status_error": se,
        "obsolete_forecast": of,
        "leader_error": le,
        "has_error": any([de, se, of, le]),
    }
