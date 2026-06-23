"""Connexion DB et session SQLAlchemy 2.0 (§2).

Écritures concurrentes et transactionnelles — pas de verrou global de fichier (objectif n°1).
"""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _make_engine(url: str):
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(url, future=True, connect_args=connect_args)

    if url.startswith("sqlite"):
        # SQLite n'applique pas les FK par défaut : on les active pour rester fidèle au schéma.
        @event.listens_for(engine, "connect")
        def _fk_pragma(dbapi_conn, _rec):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_session():
    """Dépendance FastAPI / context manager simple."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
