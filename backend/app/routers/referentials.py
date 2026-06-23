"""Référentiels §4 (lecture). L'édition Admin arrive au Lot 5."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import enums
from ..deps import get_current_user

router = APIRouter(prefix="/referentials", tags=["referentials"],
                   dependencies=[Depends(get_current_user)])


@router.get("")
def get_referentials() -> dict:
    return enums.REFERENTIALS
