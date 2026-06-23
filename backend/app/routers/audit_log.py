"""Consultation du journal d'audit §8.2 (réservé Admin)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_role
from ..models import ChangeLog
from ..security import ROLE_ADMIN

router = APIRouter(prefix="/audit", tags=["audit"],
                   dependencies=[Depends(require_role(ROLE_ADMIN))])


@router.get("")
def list_changes(
    table_name: str | None = None,
    row_pk: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """Historique des modifications, filtrable par table et clé de ligne (reconstitution §8.2)."""
    stmt = select(ChangeLog).order_by(ChangeLog.ts.desc())
    if table_name:
        stmt = stmt.where(ChangeLog.table_name == table_name)
    if row_pk:
        stmt = stmt.where(ChangeLog.row_pk == row_pk)
    rows = db.scalars(stmt.limit(min(limit, 1000))).all()
    return [
        {
            "id": r.id, "ts": r.ts, "user_email": r.user_email,
            "table_name": r.table_name, "row_pk": r.row_pk, "action": r.action,
            "before": r.before, "after": r.after,
        }
        for r in rows
    ]
