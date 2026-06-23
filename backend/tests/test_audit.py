"""§8.2 — historisation : chaque écriture produit une ligne change_log (avant → après)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models import ChangeLog, Team


def _changes(engine, **filters):
    S = sessionmaker(bind=engine, future=True)
    with S() as s:
        stmt = select(ChangeLog).order_by(ChangeLog.id)
        for k, v in filters.items():
            stmt = stmt.where(getattr(ChangeLog, k) == v)
        return s.scalars(stmt).all()


def test_insert_update_delete_are_logged(client, engine):
    # CREATE projet → log insert
    pid = client.post("/projects", json={"project_name": "Audit", "status": "Scheduled"}).json()["project_id"]
    inserts = _changes(engine, table_name="projects", action="insert", row_pk=pid)
    assert len(inserts) == 1
    assert inserts[0].user_email == "admin@test"          # qui (§8.2)
    assert inserts[0].after["project_name"] == "Audit"     # après

    # UPDATE statut → log update avec avant/après
    client.put(f"/projects/{pid}", json={"status": "In Progress"})
    updates = _changes(engine, table_name="projects", action="update", row_pk=pid)
    assert updates, "aucun update journalisé"
    last = updates[-1]
    assert last.before.get("status") == "Scheduled"
    assert last.after.get("status") == "In Progress"

    # DELETE → log delete avec snapshot avant
    client.delete(f"/projects/{pid}")
    deletes = _changes(engine, table_name="projects", action="delete", row_pk=pid)
    assert len(deletes) == 1
    assert deletes[0].before["project_id"] == pid


def test_load_save_is_logged(client, engine):
    S = sessionmaker(bind=engine, future=True)
    with S() as s:
        s.add(Team(name="T1", capacite_etp=1))
        s.commit()
    pid = client.post("/projects", json={"project_name": "Charge", "status": "In Progress",
                                         "project_leader": "A", "start_date": "2026-06-01",
                                         "end_date": "2026-07-31"}).json()["project_id"]
    month = client.get(f"/projects/{pid}/loads").json()["months"][0]
    client.put(f"/projects/{pid}/loads", json={"cells": [{"team": "T1", "month": month, "days": 3}]})
    logs = _changes(engine, table_name="monthly_loads")
    assert any(l.action == "insert" for l in logs)


def test_no_log_without_changes_is_fine(client, engine):
    # Un GET ne journalise rien.
    client.get("/projects")
    assert _changes(engine) == []
