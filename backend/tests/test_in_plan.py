"""§6.2 — flag « In Plan »."""
from __future__ import annotations

import pytest

from app.services.rules import is_in_plan


@pytest.mark.parametrize("status", ["In Progress", "Scheduled"])
def test_in_plan_true_for_active_statuses(status):
    assert is_in_plan(status) is True


@pytest.mark.parametrize("status", ["En cours", "Planifié"])
def test_in_plan_true_for_legacy_french_labels(status):
    # Compatibilité import d'anciennes données (§6.2).
    assert is_in_plan(status) is True


@pytest.mark.parametrize(
    "status", ["Closed", "Not Scheduled", "Canceled", "On Hold", "", None, "in progress"],
)
def test_in_plan_false_otherwise(status):
    # NB : la comparaison est sensible à la casse (libellés repris à l'identique du référentiel §4).
    assert is_in_plan(status) is False


def test_in_plan_trims_whitespace():
    assert is_in_plan("  In Progress  ") is True
