"""Sécurité §8.1 — hachage de mot de passe (PBKDF2-HMAC-SHA256) et JWT.

Pas de dépendance native : PBKDF2 est dans la stdlib (`hashlib`). Format stocké :
``pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>``.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from .config import settings

_ITERATIONS = 600_000
_ALGO = "pbkdf2_sha256"

# Rôles (§8.1) et hiérarchie de privilèges.
ROLE_ADMIN = "admin"
ROLE_CONTRIBUTOR = "contributor"
ROLE_READER = "reader"
ROLES = {ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_READER}
_RANK = {ROLE_READER: 0, ROLE_CONTRIBUTOR: 1, ROLE_ADMIN: 2}


def role_at_least(role: str, required: str) -> bool:
    return _RANK.get(role, -1) >= _RANK.get(required, 99)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{_ALGO}${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != _ALGO:
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(email: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Lève `jwt.PyJWTError` si invalide/expiré."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
