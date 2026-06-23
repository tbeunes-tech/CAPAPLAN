"""Recalculs des colonnes dérivées (§6.2, §6.6, §6.7, total_project_load).

Appelés à chaque écriture. Jamais saisis à la main.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import MonthlyCapacity, MonthlyLoad, Project
from .rules import capa_projet, is_in_plan, working_days


def apply_project_status(project: Project) -> None:
    """Recalcule `in_plan` depuis le statut (§6.2) et le propage aux charges du projet (§3.2)."""
    project.in_plan = is_in_plan(project.status)
    for load in project.loads:
        load.in_plan = project.in_plan


def recompute_project_rollups(db: Session, project: Project) -> None:
    """Recalcule `total_project_load` (somme des jours) et `last_update` (§6.6).

    §6.6 privilégie les lignes in_plan ; on retombe sur l'ensemble des lignes sinon.
    """
    total = db.scalar(
        select(func.coalesce(func.sum(MonthlyLoad.days), 0)).where(
            MonthlyLoad.project_id == project.project_id
        )
    )
    project.total_project_load = round(float(total or 0), 1)

    last_inplan = db.scalar(
        select(func.max(MonthlyLoad.updated_at)).where(
            MonthlyLoad.project_id == project.project_id, MonthlyLoad.in_plan.is_(True)
        )
    )
    last_any = db.scalar(
        select(func.max(MonthlyLoad.updated_at)).where(
            MonthlyLoad.project_id == project.project_id
        )
    )
    project.last_update = last_inplan or last_any


def recompute_capacity_row(cap: MonthlyCapacity) -> None:
    """Recalcule `part_projet` et `capa_projet` (§6.7) pour une ligne de capacité."""
    etp_team = float(cap.etp_team or 0)
    etp_projet = float(cap.etp_projet or 0)
    indispo = float(cap.jours_indispo or 0)
    cap.part_projet = (etp_projet / etp_team) if etp_team else 0.0
    wd = working_days(cap.month.year, cap.month.month)
    cap.capa_projet = capa_projet(etp_projet, etp_team, wd, indispo)
