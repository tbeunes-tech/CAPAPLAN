"""Fixtures de test — base SQLite en mémoire, isolée par test."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: F401 — enregistre les tables


@pytest.fixture()
def engine():
    from sqlalchemy.pool import StaticPool

    # StaticPool : une seule connexion partagée → la base en mémoire reste visible
    # depuis le threadpool de Starlette (sinon chaque thread ouvre une base vide).
    eng = create_engine(
        "sqlite:///:memory:", future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def session(engine):
    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(engine):
    """TestClient authentifié en **admin** via un vrai JWT (chaîne d'auth réelle).

    Un compte admin de test est créé en base et son jeton est attaché à toutes les requêtes ;
    l'audit est donc attribué à cet admin. Les tests d'auth/rôles utilisent `raw_client`.
    """
    from fastapi.testclient import TestClient

    from app.deps import get_db
    from app.main import app
    from app.models import User
    from app.security import create_access_token, hash_password

    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with Session() as s:
        s.add(User(email="admin@test", role="admin", password_hash=hash_password("x")))
        s.commit()

    def _override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    token = create_access_token("admin@test", "admin")
    with TestClient(app, headers={"Authorization": f"Bearer {token}"}) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def raw_client(engine):
    """TestClient SANS override d'auth : la vraie chaîne JWT/rôles s'applique."""
    from fastapi.testclient import TestClient

    from app.deps import get_db
    from app.main import app

    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)

    def _override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
