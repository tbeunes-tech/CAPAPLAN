"""API §5.1/§5.2 + dashboards, via TestClient sur base SQLite isolée."""
from __future__ import annotations

from sqlalchemy.orm import sessionmaker

from app.models import Team


def _add_team(engine, name="T1"):
    Session = sessionmaker(bind=engine, future=True)
    with Session() as s:
        s.add(Team(name=name, manager="M", capacite_etp=1))
        s.commit()


def test_referentials_endpoint(client):
    r = client.get("/referentials")
    assert r.status_code == 200
    assert "In Progress" in r.json()["status"]


def test_project_create_validates_referential(client):
    r = client.post("/projects", json={"project_name": "X", "status": "BOGUS"})
    assert r.status_code == 422


def test_full_project_lifecycle_and_in_plan(client):
    # Projet Scheduled à démarrage futur : in_plan true, aucune erreur QC.
    r = client.post("/projects", json={
        "project_name": "Refonte SI", "status": "Scheduled",
        "priorite": "P0", "project_leader": "Alice",
        "start_date": "2099-01-01", "end_date": "2099-12-31",
    })
    assert r.status_code == 201, r.text
    body = r.json()
    pid = body["project_id"]
    assert body["in_plan"] is True
    assert len(pid) == 9 and pid[4] == "-"           # yymm-NNNN
    assert body["qc"]["has_error"] is False

    r = client.put(f"/projects/{pid}", json={"status": "Closed"})
    assert r.status_code == 200 and r.json()["in_plan"] is False

    assert any(p["project_id"] == pid for p in client.get("/projects").json())
    assert client.delete(f"/projects/{pid}").status_code == 204
    assert client.get(f"/projects/{pid}").status_code == 404


def test_in_progress_without_loads_is_obsolete(client):
    # Comportement §7.3 attendu : In Progress sans charge saisie → last_update absent
    # → « Obsolete forecast » (le projet n'a pas encore de prévision de charge).
    r = client.post("/projects", json={
        "project_name": "Neuf", "status": "In Progress", "project_leader": "Alice",
        "start_date": "2026-01-01", "end_date": "2026-12-31",
    })
    qc = r.json()["qc"]
    assert qc["obsolete_forecast"] == "Obsolete forecast"


def test_two_projects_get_distinct_ids(client):
    a = client.post("/projects", json={"project_name": "A", "status": "Scheduled"}).json()
    b = client.post("/projects", json={"project_name": "B", "status": "Scheduled"}).json()
    assert a["project_id"] != b["project_id"]


def test_deleted_project_id_is_not_reused(client):
    # Un id supprimé ne doit jamais être réattribué (sinon l'historique d'audit serait confondu).
    a = client.post("/projects", json={"project_name": "A", "status": "Scheduled"}).json()["project_id"]
    assert client.delete(f"/projects/{a}").status_code == 204
    b = client.post("/projects", json={"project_name": "B", "status": "Scheduled"}).json()["project_id"]
    assert b != a


def test_qc_flags_in_progress_without_leader(client):
    r = client.post("/projects", json={
        "project_name": "Sans chef", "status": "In Progress",
        "start_date": "2026-01-01", "end_date": "2026-12-31",
    })
    qc = r.json()["qc"]
    assert qc["leader_error"] == "Leader Error" and qc["has_error"] is True


def test_load_grid_save_updates_rollups(client, engine):
    _add_team(engine, "T1")
    pid = client.post("/projects", json={
        "project_name": "Charge", "status": "In Progress", "project_leader": "Bob",
        "start_date": "2026-06-01", "end_date": "2026-08-31",
    }).json()["project_id"]

    grid = client.get(f"/projects/{pid}/loads").json()
    assert "T1" in grid["teams"] and len(grid["months"]) >= 1
    month0 = grid["months"][0]

    r = client.put(f"/projects/{pid}/loads", json={
        "cells": [{"team": "T1", "month": month0, "days": 4.5}]
    })
    assert r.status_code == 200
    body = r.json()
    assert float(body["total_project_load"]) == 4.5
    assert body["last_update"] is not None          # §6.6 recalculé

    # La charge in_plan remonte dans le dashboard.
    occ = client.get("/dashboards/team-load").json()
    row = next(r for r in occ["rows"] if r["team"] == "T1")
    assert 4.5 in row["values"]


def test_load_save_optimistic_conflict(client, engine):
    _add_team(engine, "T1")
    pid = client.post("/projects", json={
        "project_name": "Concurrence", "status": "In Progress", "project_leader": "A",
        "start_date": "2026-06-01", "end_date": "2026-07-31",
    }).json()["project_id"]
    m = client.get(f"/projects/{pid}/loads").json()["months"][0]

    # 1) Création d'une cellule (n'existait pas → base_updated_at None) : OK
    assert client.put(f"/projects/{pid}/loads", json={
        "cells": [{"team": "T1", "month": m, "days": 4, "base_updated_at": None}]
    }).status_code == 200

    # On relit l'horodatage serveur de la cellule.
    cells = client.get(f"/projects/{pid}/loads").json()["cells"]
    ts = next(c["updated_at"] for c in cells if c["team"] == "T1" and c["month"] == m)
    assert ts is not None

    # 2) Utilisateur A enregistre avec le bon horodatage de base → OK (et l'horodatage change).
    assert client.put(f"/projects/{pid}/loads", json={
        "cells": [{"team": "T1", "month": m, "days": 5, "base_updated_at": ts}]
    }).status_code == 200

    # 3) Utilisateur B enregistre avec le MÊME horodatage (désormais périmé) → 409, rien écrit.
    r = client.put(f"/projects/{pid}/loads", json={
        "cells": [{"team": "T1", "month": m, "days": 9, "base_updated_at": ts}]
    })
    assert r.status_code == 409
    conflicts = r.json()["detail"]["conflicts"]
    assert conflicts[0]["server_days"] == 5 and conflicts[0]["your_days"] == 9
    # La valeur en base reste celle d'A (5), pas celle de B (9).
    cells = client.get(f"/projects/{pid}/loads").json()["cells"]
    assert next(c["days"] for c in cells if c["team"] == "T1" and c["month"] == m) == 5


def test_capacity_upsert_recomputes_capa(client, engine):
    _add_team(engine, "T1")
    r = client.put("/capacity", json={
        "team": "T1", "month": "2026-08-01",
        "etp_team": 1, "etp_projet": 0.7, "jours_indispo": 5,
    })
    assert r.status_code == 200
    assert round(r.json()["capa_projet"], 2) == 11.2     # §6.7, août 2026 = 21 j ouvrés


def test_project_history(client, engine):
    _add_team(engine, "T1")
    pid = client.post("/projects", json={"project_name": "Hist", "status": "Scheduled"}).json()["project_id"]
    client.put(f"/projects/{pid}", json={"status": "In Progress", "project_leader": "A"})
    m = client.get(f"/projects/{pid}/loads").json()["months"][0]
    client.put(f"/projects/{pid}/loads", json={"cells": [{"team": "T1", "month": m, "days": 3, "base_updated_at": None}]})

    hist = client.get(f"/projects/{pid}/history").json()
    actions = [(h["table_name"], h["action"]) for h in hist]
    assert ("projects", "insert") in actions
    assert ("projects", "update") in actions
    assert ("monthly_loads", "insert") in actions
    # le changement de statut est traçable avant → après
    upd = next(h for h in hist if h["table_name"] == "projects" and h["action"] == "update")
    assert upd["before"].get("status") == "Scheduled" and upd["after"].get("status") == "In Progress"
    assert upd["user_email"] == "admin@test"


def test_capacity_cell_get_reflects_edit(client, engine):
    _add_team(engine, "T1")
    # Cellule inexistante → valeurs nulles
    empty = client.get("/capacity/cell?team=T1&month=2026-08-01").json()
    assert empty["exists"] is False and empty["capa_projet"] is None
    # Après édition, la cellule reflète les entrées + capa recalculée
    client.put("/capacity", json={"team": "T1", "month": "2026-08-01",
                                  "etp_team": 1, "etp_projet": 0.7, "jours_indispo": 5})
    cell = client.get("/capacity/cell?team=T1&month=2026-08-01").json()
    assert cell["exists"] is True
    assert cell["etp_projet"] == 0.7 and round(cell["capa_projet"], 2) == 11.2
    assert round(cell["part_projet"], 2) == 0.7


def test_team_crud_and_delete_guard(client, engine):
    # Création
    r = client.post("/teams", json={"name": "ETU-NEW", "manager": "Zoé", "capacite_etp": 2,
                                    "description": "nouvelle équipe"})
    assert r.status_code == 201 and r.json()["manager"] == "Zoé"
    # Doublon → 409
    assert client.post("/teams", json={"name": "ETU-NEW"}).status_code == 409
    # Mise à jour (nom immuable, on change le reste)
    r = client.put("/teams/ETU-NEW", json={"manager": "Léo", "capacite_etp": 3})
    assert r.status_code == 200 and r.json()["manager"] == "Léo" and r.json()["capacite_etp"] == 3
    # Suppression d'une équipe libre → 204
    assert client.delete("/teams/ETU-NEW").status_code == 204

    # Garde d'intégrité : équipe référencée par une charge → 409
    _add_team(engine, "ETU-USED")
    pid = client.post("/projects", json={"project_name": "P", "status": "In Progress",
                                         "project_leader": "A", "start_date": "2026-06-01",
                                         "end_date": "2026-07-31"}).json()["project_id"]
    month = client.get(f"/projects/{pid}/loads").json()["months"][0]
    client.put(f"/projects/{pid}/loads", json={"cells": [{"team": "ETU-USED", "month": month, "days": 2}]})
    assert client.delete("/teams/ETU-USED").status_code == 409


def test_team_write_forbidden_for_non_admin(raw_client, engine):
    from app.models import User
    from app.security import ROLE_CONTRIBUTOR, create_access_token, hash_password
    from sqlalchemy.orm import sessionmaker
    S = sessionmaker(bind=engine, future=True)
    with S() as s:
        s.add(User(email="c@x", role=ROLE_CONTRIBUTOR, password_hash=hash_password("x")))
        s.commit()
    h = {"Authorization": f"Bearer {create_access_token('c@x', ROLE_CONTRIBUTOR)}"}
    assert raw_client.post("/teams", headers=h, json={"name": "X"}).status_code == 403


def test_dashboards_endpoints_smoke(client):
    for path in ["/dashboards/team-load", "/dashboards/occupancy",
                 "/dashboards/overloads", "/dashboards/roadmap",
                 "/dashboards/prioritization", "/capacity/pivot", "/teams"]:
        assert client.get(path).status_code == 200, path
