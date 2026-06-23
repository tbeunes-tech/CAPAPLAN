"""Authentification §8.1 — login (email/mot de passe → JWT) et profil courant."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import User
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str


class MeOut(BaseModel):
    email: str
    role: str
    full_name: str | None = None


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Identifiants invalides")
    return TokenOut(
        access_token=create_access_token(user.email, user.role),
        email=user.email,
        role=user.role,
    )


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return MeOut(email=user.email, role=user.role, full_name=user.full_name)
