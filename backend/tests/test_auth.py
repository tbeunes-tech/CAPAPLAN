"""§8.1 — authentification JWT et application des 3 rôles."""
from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from app.models import Team, User
from app.security import (
    ROLE_ADMIN, ROLE_CONTRIBUTOR, ROLE_READER,
    hash_password, role_at_least, verify_password,
)


def _seed_users(engine):
    S = sessionmaker(bind=engine, future=True)
    with S() as s:
        s.add_all([
            User(email="admin@x", role=ROLE_ADMIN, password_hash=hash_password("pw-admin")),
            User(email="contrib@x", role=ROLE_CONTRIBUTOR, password_hash=hash_password("pw-contrib")),
            User(email="reader@x", role=ROLE_READER, password_hash=hash_password("pw-reader")),
            User(email="off@x", role=ROLE_ADMIN, password_hash=hash_password("pw"), is_active=False),
        ])
        s.add(Team(name="T1", capacite_etp=1))
        s.commit()


def token(client, email, password) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


# --- hachage de mot de passe ---
def test_password_hash_roundtrip():
    h = hash_password("s3cret")
    assert h != "s3cret" and verify_password("s3cret", h)
    assert not verify_password("wrong", h)


def test_role_hierarchy():
    assert role_at_least(ROLE_ADMIN, ROLE_CONTRIBUTOR)
    assert role_at_least(ROLE_CONTRIBUTOR, ROLE_READER)
    assert not role_at_least(ROLE_READER, ROLE_CONTRIBUTOR)


# --- login ---
def test_login_ok_and_bad_password(raw_client, engine):
    _seed_users(engine)
    assert raw_client.post("/auth/login", json={"email": "admin@x", "password": "pw-admin"}).status_code == 200
    assert raw_client.post("/auth/login", json={"email": "admin@x", "password": "nope"}).status_code == 401
    assert raw_client.post("/auth/login", json={"email": "ghost@x", "password": "x"}).status_code == 401


def test_inactive_user_cannot_login(raw_client, engine):
    _seed_users(engine)
    assert raw_client.post("/auth/login", json={"email": "off@x", "password": "pw"}).status_code == 401


def test_unauthenticated_is_401(raw_client, engine):
    _seed_users(engine)
    assert raw_client.get("/projects").status_code == 401
    assert raw_client.get("/dashboards/team-load").status_code == 401


def test_reader_can_read_but_not_write(raw_client, engine):
    _seed_users(engine)
    h = auth(token(raw_client, "reader@x", "pw-reader"))
    assert raw_client.get("/projects", headers=h).status_code == 200
    assert raw_client.get("/dashboards/occupancy", headers=h).status_code == 200
    # écriture refusée (403)
    r = raw_client.post("/projects", headers=h, json={"project_name": "X", "status": "Scheduled"})
    assert r.status_code == 403


def test_contributor_can_write_projects_but_not_capacity(raw_client, engine):
    _seed_users(engine)
    h = auth(token(raw_client, "contrib@x", "pw-contrib"))
    assert raw_client.post("/projects", headers=h,
                           json={"project_name": "X", "status": "Scheduled"}).status_code == 201
    # capacité = Admin only
    r = raw_client.put("/capacity", headers=h,
                       json={"team": "T1", "month": "2026-08-01", "etp_team": 1, "etp_projet": 1, "jours_indispo": 0})
    assert r.status_code == 403


def test_admin_can_edit_capacity_and_read_audit(raw_client, engine):
    _seed_users(engine)
    h = auth(token(raw_client, "admin@x", "pw-admin"))
    assert raw_client.put("/capacity", headers=h,
                          json={"team": "T1", "month": "2026-08-01", "etp_team": 1, "etp_projet": 0.7, "jours_indispo": 5}).status_code == 200
    assert raw_client.get("/audit", headers=h).status_code == 200


def test_audit_endpoint_forbidden_for_non_admin(raw_client, engine):
    _seed_users(engine)
    h = auth(token(raw_client, "contrib@x", "pw-contrib"))
    assert raw_client.get("/audit", headers=h).status_code == 403
