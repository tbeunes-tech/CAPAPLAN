"""Génération du Project ID côté base (§6.1)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ChangeLog, Project
from .rules import next_project_id


def generate_project_id(db: Session, today: date | None = None) -> str:
    """Génère le prochain id en évitant **toute réutilisation**, y compris d'un id déjà supprimé.

    On considère « pris » : les projets existants ET tous les project_id jamais apparus dans le
    journal d'audit (`change_log`). Sinon, supprimer le dernier projet libérerait son id, et un
    nouveau projet hériterait de l'historique de l'ancien (§8.2).
    """
    used = set(db.scalars(select(Project.project_id)).all())
    used |= set(
        db.scalars(select(ChangeLog.row_pk).where(ChangeLog.table_name == "projects")).all()
    )
    return next_project_id(used, today or date.today())
