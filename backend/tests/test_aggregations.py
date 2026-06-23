"""§6.3 (charge), §6.4/§5.5 (taux + couleur), §5.6 (surcharges), §6.8 (priorisation)."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models import MonthlyCapacity, MonthlyLoad, Project, Team
from app.services.aggregations import (
    occupancy_color, overload_list, prioritization_plan,
    team_load_detail, team_load_pivot, team_occupancy_pivot,
)
from app.services.rules import OVERLOAD_NULL_CAPACITY

START = date(2026, 6, 1)


@pytest.fixture()
def data(session):
    session.add_all([Team(name="A"), Team(name="B")])
    # Capacité juin : A=10, B=0
    session.add_all([
        MonthlyCapacity(team="A", month=START, etp_team=1, etp_projet=1,
                        part_projet=1, jours_indispo=0, capa_projet=10),
        MonthlyCapacity(team="B", month=START, etp_team=1, etp_projet=0,
                        part_projet=0, jours_indispo=0, capa_projet=0),
    ])
    session.add_all([
        Project(project_id="2606-0001", project_name="P1", status="In Progress",
                in_plan=True, priorite="P0", total_project_load=13),
        # Projet hors plan : ses charges ne doivent PAS compter (§6.3).
        Project(project_id="2606-0002", project_name="P2", status="Closed",
                in_plan=False, priorite="P1", total_project_load=99),
    ])
    session.add_all([
        # in_plan : comptés
        MonthlyLoad(project_id="2606-0001", team="A", month=START, days=8,
                    in_plan=True, updated_at=datetime(2026, 6, 1)),
        MonthlyLoad(project_id="2606-0001", team="B", month=START, days=5,
                    in_plan=True, updated_at=datetime(2026, 6, 1)),
        # hors plan (projet fermé) sur l'équipe A : ignoré dans la charge
        MonthlyLoad(project_id="2606-0002", team="A", month=START, days=99,
                    in_plan=False, updated_at=datetime(2026, 6, 1)),
    ])
    session.flush()
    return session


def test_team_load_excludes_out_of_plan(data):
    piv = team_load_pivot(data, START)
    by_team = {r["team"]: r["values"][0] for r in piv["rows"]}  # 1re colonne = juin
    assert by_team["A"] == 8.0      # 99 (hors plan) exclu
    assert by_team["B"] == 5.0
    assert len(piv["months"]) == 12


def test_occupancy_rate_and_colors(data):
    occ = team_occupancy_pivot(data, START)
    cell = {r["team"]: r["cells"][0] for r in occ["rows"]}
    assert cell["A"]["rate"] == 0.8                 # 8/10
    assert cell["A"]["color"] == "amber"            # 80–100 %
    assert cell["B"]["rate"] == OVERLOAD_NULL_CAPACITY   # 5 jours, capa 0
    assert cell["B"]["color"] == "overload_null_capacity"


def test_color_thresholds():
    assert occupancy_color(0.5) == "green"
    assert occupancy_color(0.79) == "green"
    assert occupancy_color(0.8) == "amber"
    assert occupancy_color(1.0) == "amber"
    assert occupancy_color(1.01) == "red"
    assert occupancy_color(OVERLOAD_NULL_CAPACITY) == "overload_null_capacity"


def test_team_load_detail_breaks_down_by_project(data):
    # L'équipe A (8 j in plan en juin) provient du projet 2606-0001 ; le 99 hors plan est exclu.
    detail = team_load_detail(data, "A", START)
    assert detail["team"] == "A"
    assert len(detail["rows"]) == 1
    row = detail["rows"][0]
    assert row["project_id"] == "2606-0001"
    assert row["values"][0] == 8.0
    # La somme du détail = la cellule agrégée du pivot.
    agg = next(r["values"][0] for r in team_load_pivot(data, START)["rows"] if r["team"] == "A")
    assert sum(r["values"][0] for r in detail["rows"]) == agg


def test_overload_list(data):
    ov = overload_list(data, START)
    teams = {r["team"] for r in ov}
    assert "B" in teams                              # sentinelle capa nulle
    b = next(r for r in ov if r["team"] == "B")
    assert b["ecart_jours"] == 5.0


def test_prioritization_scenarios(session):
    session.add_all([Team(name="A")])
    session.add(MonthlyCapacity(team="A", month=START, etp_team=1, etp_projet=1,
                                part_projet=1, jours_indispo=0, capa_projet=20))
    projs = [
        ("2606-0001", "P0", None, 10),
        ("2606-0002", "P1", "Renforcement SI", 5),
        ("2606-0003", "P1", "Supply Chain efficiente", 7),
        ("2606-0004", "P2", None, 3),
    ]
    for pid, prio, pilier, load in projs:
        session.add(Project(project_id=pid, project_name=pid, status="In Progress",
                            in_plan=True, priorite=prio, pilier_strategique=pilier,
                            total_project_load=load))
        session.add(MonthlyLoad(project_id=pid, team="A", month=START, days=load,
                                in_plan=True, updated_at=datetime(2026, 6, 1)))
    session.flush()

    plan = prioritization_plan(session, START)
    by_label = {s["scenario"]: s for s in plan["scenarios"]}
    assert by_label["P0"]["project_count"] == 1
    assert by_label["P0 + P1 Renforcement SI"]["project_count"] == 2
    assert by_label["P0 + P1"]["project_count"] == 3
    assert by_label["Plan intégral"]["project_count"] == 4
    # charge cumulée = somme total_project_load des projets inclus
    assert by_label["P0"]["charge_cumulee"] == 10
    assert by_label["P0 + P1 Renforcement SI"]["charge_cumulee"] == 15
    assert by_label["Plan intégral"]["charge_cumulee"] == 25
    # taux juin scénario complet = 25 / 20
    assert by_label["Plan intégral"]["monthly"][0]["rate"] == pytest.approx(25 / 20)
