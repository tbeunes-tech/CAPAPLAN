"""§6.5 (jours ouvrés), §6.7 (capacité projet), §6.4 (taux d'occupation).

Valeurs pivots vérifiées contre les données réellement stockées dans le classeur.
"""
from __future__ import annotations

import pytest

from app.services.rules import (
    OVERLOAD_NULL_CAPACITY, capa_projet, occupancy_rate, working_days,
)


# --- §6.5 jours ouvrés (lundi→vendredi, fériés INCLUS) ----------------------
def test_working_days_aug_2025_is_21():
    # Validé contre le classeur (Capa_Projet = 2 × 21 = 42 pour ETU- SALES & MARKET.).
    assert working_days(2025, 8) == 21


def test_working_days_includes_holidays():
    # Mai 2025 contient 2 fériés en semaine (1er, 8 mai). Ils sont INCLUS → 22 et non 20.
    assert working_days(2025, 5) == 22


def test_working_days_february_non_leap():
    assert working_days(2025, 2) == 20


# --- §6.7 capacité projet ---------------------------------------------------
def test_capa_matches_workbook_values():
    # ETU- SALES & MARKET., août 2025 : ETP_Projet=2, indispo=0 → 42.
    assert capa_projet(etp_projet=2, etp_team=2, work_days=21, jours_indispo=0) == 42
    # ETU-BI-PHX, août 2025 : ETP_Projet=0.5 → 10.5.
    assert capa_projet(etp_projet=0.5, etp_team=1, work_days=21, jours_indispo=0) == 10.5


def test_capa_weights_only_indispo_by_part_projet():
    # part = 1/2 ; brute = 1×20 = 20 ; on retranche 0.5×10 = 5 → 15.
    assert capa_projet(etp_projet=1, etp_team=2, work_days=20, jours_indispo=10) == 15


def test_capa_floored_at_zero():
    assert capa_projet(etp_projet=1, etp_team=1, work_days=0, jours_indispo=100) == 0


def test_capa_no_division_when_etp_team_zero():
    # etp_team=0 → part=0, aucune indispo déduite (pas de ZeroDivisionError).
    assert capa_projet(etp_projet=1, etp_team=0, work_days=20, jours_indispo=10) == 20


# --- §6.4 taux d'occupation -------------------------------------------------
def test_occupancy_normal():
    assert occupancy_rate(charge=10, capacite=5) == 2.0


def test_occupancy_sentinel_when_capacity_zero_and_load_positive():
    assert occupancy_rate(charge=5, capacite=0) == OVERLOAD_NULL_CAPACITY


def test_occupancy_zero_when_no_load():
    assert occupancy_rate(charge=0, capacite=0) == 0.0
