"""Dépendances FastAPI partagées : session, fenêtre, et auth/rôles (§8.1)."""
from __future__ import annotations

from datetime import date

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .audit import current_user
from .database import SessionLocal
from .models import User
from .security import decode_access_token, role_at_least


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def parse_start(start: str | None) -> date | None:
    """Param `?start=YYYY-MM-DD` des dashboards ; None → mois courant."""
    if not start:
        return None
    return date.fromisoformat(start)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentification requise")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise HTTPException(401, "Jeton invalide ou expiré")
    user = db.scalar(select(User).where(User.email == payload.get("sub")))
    if not user or not user.is_active:
        raise HTTPException(401, "Utilisateur inconnu ou désactivé")
    current_user.set(user.email)  # pour le journal d'audit (§8.2)
    return user


def require_role(minimum: str):
    """Garde de rôle hiérarchique : reader < contributor < admin."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if not role_at_least(user.role, minimum):
            raise HTTPException(403, f"Rôle '{minimum}' requis (vous êtes '{user.role}')")
        return user

    return _dep
