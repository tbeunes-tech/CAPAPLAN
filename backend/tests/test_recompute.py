"""Recalculs : in_plan propagé (§6.2/§3.2), rollups projet (§6.6), capacité (§6.7)."""
from __future__ import annotations

from datetime import date, datetime

from app.models import MonthlyCapacity, MonthlyLoad, Project, Team
from app.services.recompute import (
    apply_project_status, recompute_capacity_row, recompute_project_rollups,
)


def _seed(session):
    session.add(Team(name="T1"))
    p = Project(project_id="2606-0001", project_name="P", status="In Progress")
    apply_project_status(p)
    session.add(p)
    session.flush()
    return p


def test_apply_status_propagates_in_plan_to_loads(session):
    p = _seed(session)
    session.add_all([
        MonthlyLoad(project_id=p.project_id, team="T1", month=date(2026, 6, 1),
                    days=5, in_plan=True, updated_at=datetime(2026, 6, 1)),
        MonthlyLoad(project_id=p.project_id, team="T1", month=date(2026, 7, 1),
                    days=3, in_plan=True, updated_at=datetime(2026, 6, 2)),
    ])
    session.flush()
    session.refresh(p)

    p.status = "Closed"
    apply_project_status(p)            # in_plan → False, propagé
    session.flush()
    assert p.in_plan is False
    assert all(l.in_plan is False for l in p.loads)


def test_recompute_rollups(session):
    p = _seed(session)
    session.add_all([
        MonthlyLoad(project_id=p.project_id, team="T1", month=date(2026, 6, 1),
                    days=5, in_plan=True, updated_at=datetime(2026, 6, 1, 9, 0)),
        MonthlyLoad(project_id=p.project_id, team="T1", month=date(2026, 7, 1),
                    days=3.5, in_plan=True, updated_at=datetime(2026, 6, 5, 12, 0)),
    ])
    session.flush()
    recompute_project_rollups(session, p)
    assert float(p.total_project_load) == 8.5
    assert p.last_update == datetime(2026, 6, 5, 12, 0)


def test_recompute_capacity_matches_formula(session):
    # Août 2026 : 21 jours ouvrés ; ETP_Projet=0.7, ETP_Team=1, indispo=5 → 0.7×21 − 0.7×5 = 11.2
    cap = MonthlyCapacity(team="T1", month=date(2026, 8, 1),
                          etp_team=1, etp_projet=0.7, jours_indispo=5)
    recompute_capacity_row(cap)
    assert round(float(cap.part_projet), 4) == 0.7
    assert round(float(cap.capa_projet), 4) == 11.2
