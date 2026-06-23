"""§7 — contrôle qualité (4 indicateurs, sur projets in_plan)."""
from __future__ import annotations

from datetime import date, datetime

from app.models import Project
from app.services.qc import qc_for_project

TODAY = date(2026, 6, 22)


def _p(**kw) -> Project:
    base = dict(project_id="2606-0001", project_name="X", in_plan=True,
                status="In Progress", project_leader="Alice",
                start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
                last_update=datetime(2026, 6, 20))
    base.update(kw)
    return Project(**base)


def test_clean_project_has_no_error():
    assert qc_for_project(_p(), TODAY)["has_error"] is False


def test_out_of_plan_project_is_never_flagged():
    p = _p(in_plan=False, start_date=None, project_leader=None, last_update=None)
    assert qc_for_project(p, TODAY)["has_error"] is False


def test_missing_start_then_missing_end():
    assert qc_for_project(_p(start_date=None), TODAY)["date_error"] == "Missing Start"
    assert qc_for_project(_p(end_date=None), TODAY)["date_error"] == "Missing End"


def test_scheduled_but_started():
    p = _p(status="Scheduled", start_date=date(2026, 1, 1))
    assert qc_for_project(p, TODAY)["status_error"] == "Scheduled but started"


def test_in_progress_but_ended():
    p = _p(status="In Progress", end_date=date(2026, 5, 1))
    assert qc_for_project(p, TODAY)["status_error"] == "In Progress but ended"


def test_obsolete_forecast_when_last_update_old():
    p = _p(last_update=datetime(2026, 5, 1))  # > 31 jours avant le 22/06
    assert qc_for_project(p, TODAY)["obsolete_forecast"] == "Obsolete forecast"


def test_obsolete_forecast_when_last_update_missing():
    assert qc_for_project(_p(last_update=None), TODAY)["obsolete_forecast"] == "Obsolete forecast"


def test_obsolete_forecast_boundary_30_days_ok():
    p = _p(last_update=datetime(2026, 5, 23))  # 30 jours → pas obsolète (seuil 31)
    assert qc_for_project(p, TODAY)["obsolete_forecast"] is None


def test_leader_error():
    assert qc_for_project(_p(project_leader=""), TODAY)["leader_error"] == "Leader Error"
    assert qc_for_project(_p(project_leader=None), TODAY)["leader_error"] == "Leader Error"


def test_has_error_aggregates():
    p = _p(start_date=None, project_leader="")
    res = qc_for_project(p, TODAY)
    assert res["has_error"] is True
