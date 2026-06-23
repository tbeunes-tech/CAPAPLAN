"""Historisation §8.2 — journal d'audit automatique sur les 4 tables métier.

Implémenté via des écouteurs d'événements SQLAlchemy : à chaque flush, on capture les
insert/update/delete sur `projects`, `monthly_loads`, `teams`, `monthly_capacity` et on
écrit une ligne `change_log` (qui, quand, table, clé, avant → après) au commit.

- L'utilisateur courant est lu dans un `ContextVar` posé par la couche auth (→ `system` sinon).
- Désactivable via `audit_disabled` (utilisé par l'import massif `migrate_from_xlsm`).
"""
from __future__ import annotations

from contextvars import ContextVar
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from .models import ChangeLog, MonthlyCapacity, MonthlyLoad, Project, Team

current_user: ContextVar[str] = ContextVar("current_user", default="system")
audit_disabled: ContextVar[bool] = ContextVar("audit_disabled", default=False)

_AUDITED = {Project, MonthlyLoad, Team, MonthlyCapacity}


def _json_safe(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def _audit_key(obj) -> str:
    """Clé métier de la ligne (disponible avant flush, contrairement aux PK auto-incrément)."""
    if isinstance(obj, Project):
        return str(obj.project_id)
    if isinstance(obj, Team):
        return str(obj.name)
    if isinstance(obj, MonthlyLoad):
        return f"{obj.project_id}|{obj.team}|{obj.month}"
    if isinstance(obj, MonthlyCapacity):
        return f"{obj.team}|{obj.month}"
    return "|".join(str(getattr(obj, c.name)) for c in inspect(obj.__class__).primary_key)


def _full_row(obj) -> dict:
    return {c.key: _json_safe(getattr(obj, c.key)) for c in inspect(obj.__class__).columns}


def _changed(obj) -> tuple[dict, dict]:
    """Colonnes modifiées : (avant, après)."""
    before, after = {}, {}
    state = inspect(obj)
    for attr in state.attrs:
        hist = attr.load_history()
        if hist.has_changes():
            before[attr.key] = _json_safe(hist.deleted[0]) if hist.deleted else None
            after[attr.key] = _json_safe(hist.added[0]) if hist.added else None
    return before, after


def _before_flush(session: Session, _ctx, _instances):
    """Capture insert/update/delete et ajoute les `ChangeLog` au sein du même flush.

    On agit dans `before_flush` (et non `before_commit`, qui s'exécute *avant* le flush) :
    les historiques d'attributs y sont encore disponibles, et les objets `ChangeLog`
    ajoutés ici sont persistés dans le flush courant (modèle recommandé par SQLAlchemy).
    """
    if audit_disabled.get():
        return
    logs = []
    user = current_user.get()
    for obj in session.new:
        if type(obj) in _AUDITED:
            logs.append(ChangeLog(user_email=user, table_name=type(obj).__tablename__,
                                  row_pk=_audit_key(obj), action="insert",
                                  before=None, after=_full_row(obj)))
    for obj in session.dirty:
        if type(obj) in _AUDITED and session.is_modified(obj, include_collections=False):
            before, after = _changed(obj)
            if after:  # au moins une colonne réellement modifiée
                logs.append(ChangeLog(user_email=user, table_name=type(obj).__tablename__,
                                      row_pk=_audit_key(obj), action="update",
                                      before=before, after=after))
    for obj in session.deleted:
        if type(obj) in _AUDITED:
            logs.append(ChangeLog(user_email=user, table_name=type(obj).__tablename__,
                                  row_pk=_audit_key(obj), action="delete",
                                  before=_full_row(obj), after=None))
    if logs:
        session.add_all(logs)


_REGISTERED = False


def register_audit() -> None:
    """Branche l'écouteur globalement (idempotent)."""
    global _REGISTERED
    if _REGISTERED:
        return
    event.listen(Session, "before_flush", _before_flush)
    _REGISTERED = True
