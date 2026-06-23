"""Migration §9 — fumée + non-régression métier (skip si le classeur n'est pas présent).

Définir `PORTFOLIO_XLSM` pour pointer vers le classeur, sinon on tente le chemin Downloads.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.models import MonthlyCapacity, MonthlyLoad, Project, Team
from scripts.migrate_from_xlsm import migrate

_DEFAULT = Path.home() / "Downloads" / "PORTFOLIO PROJETS DSI V_4_02.xlsm"
_XLSM = Path(os.environ.get("PORTFOLIO_XLSM", _DEFAULT))

pytestmark = pytest.mark.skipif(not _XLSM.exists(), reason=f"classeur introuvable: {_XLSM}")


@pytest.fixture()
def populated(session):
    migrate(str(_XLSM), session)
    return session


def test_tables_are_populated_and_queryable(populated):
    s = populated
    assert s.scalar(select(func.count()).select_from(Project)) >= 120
    assert s.scalar(select(func.count()).select_from(Team)) >= 60
    assert s.scalar(select(func.count()).select_from(MonthlyLoad)) >= 2000
    assert s.scalar(select(func.count()).select_from(MonthlyCapacity)) >= 1000


def test_no_orphan_foreign_keys(populated):
    s = populated
    team_names = set(s.scalars(select(Team.name)).all())
    load_teams = set(s.scalars(select(MonthlyLoad.team).distinct()).all())
    capa_teams = set(s.scalars(select(MonthlyCapacity.team).distinct()).all())
    assert load_teams <= team_names
    assert capa_teams <= team_names
    load_pids = set(s.scalars(select(MonthlyLoad.project_id).distinct()).all())
    proj_ids = set(s.scalars(select(Project.project_id).distinct()).all())
    assert load_pids <= proj_ids


def test_in_plan_recomputed_from_status(populated):
    # in_plan projet = recalculé depuis le statut (§6.2), jamais la colonne « IN PLAN ? ».
    for proj in populated.scalars(select(Project)).all():
        expected = proj.status in {"In Progress", "Scheduled", "En cours", "Planifié"}
        assert proj.in_plan is expected, proj.project_id


def test_total_project_load_equals_sum_of_loads(populated):
    s = populated
    for proj in s.scalars(select(Project)).all():
        summed = s.scalar(
            select(func.coalesce(func.sum(MonthlyLoad.days), 0)).where(
                MonthlyLoad.project_id == proj.project_id
            )
        )
        assert round(float(proj.total_project_load or 0), 1) == round(float(summed), 1)


def test_months_normalized_to_first_of_month(populated):
    for load in populated.scalars(select(MonthlyLoad)).all():
        assert load.month.day == 1
    for capa in populated.scalars(select(MonthlyCapacity)).all():
        assert capa.month.day == 1


def test_migration_is_idempotent(populated):
    # Rejouer ne doit pas dupliquer (upsert par clé) — on relance sur la même session/db.
    before = populated.scalar(select(func.count()).select_from(MonthlyLoad))
    migrate(str(_XLSM), populated)
    after = populated.scalar(select(func.count()).select_from(MonthlyLoad))
    assert after == before


# --- Non-régression métier §9 : dashboards recalculés == onglets du classeur --------
import openpyxl  # noqa: E402
from datetime import date  # noqa: E402

from app.services.aggregations import team_capacity_pivot, team_load_pivot  # noqa: E402

# Mois courant du classeur lors de sa dernière recalc (cf. en-têtes des onglets).
WORKBOOK_START = date(2026, 5, 1)


def _read_pivot_tab(sheet: str) -> dict:
    """Lit un onglet pivot (équipe en col A, 12 mois en en-tête) → {team: [12 valeurs]}."""
    wb = openpyxl.load_workbook(_XLSM, data_only=True, read_only=True)
    ws = wb[sheet]
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        out[str(row[0]).strip()] = [float(c or 0) for c in row[1:13]]
    return out


def _compare_pivot(got: dict, expected: dict, tol: float) -> list[str]:
    mismatches = []
    for team, exp_vals in expected.items():
        got_vals = got.get(team)
        if got_vals is None:
            continue  # équipes purement « affichage » du classeur, ignorées
        for i, (a, b) in enumerate(zip(got_vals, exp_vals)):
            if abs(a - b) > tol:
                mismatches.append(f"{team}[{i}] got={a} exp={b}")
    return mismatches


def test_team_load_matches_workbook(populated):
    """§5.3/§6.3 — Charge équipe recalculée == onglet « Charge Equipe »."""
    expected = _read_pivot_tab("Charge Equipe")
    got = {r["team"]: r["values"] for r in team_load_pivot(populated, WORKBOOK_START)["rows"]}
    assert not _compare_pivot(got, expected, tol=0.05)[:20]


def test_team_capacity_matches_workbook(populated):
    """§5.4/§6.7 — Capacité équipe recalculée == onglet « Capa Equipe » (capa_projet stocké)."""
    expected = _read_pivot_tab("Capa Equipe")
    got = {r["team"]: r["values"] for r in team_capacity_pivot(populated, WORKBOOK_START)["rows"]}
    assert not _compare_pivot(got, expected, tol=0.05)[:20]
