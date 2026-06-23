"""§6.1 — génération du Project ID (`yymm-NNNN`, compteur global, immuable, unique)."""
from __future__ import annotations

import re
from datetime import date

import pytest

from app.services.rules import next_project_id

FORMAT = re.compile(r"^\d{4}-\d{4}$")


def test_format_yymm_nnnn():
    pid = next_project_id(set(), date(2025, 8, 1))
    assert FORMAT.match(pid)
    assert pid == "2508-0001"  # premier id du mois 08/2025


def test_prefix_uses_current_year_month():
    assert next_project_id(set(), date(2026, 6, 22)).startswith("2606-")
    assert next_project_id(set(), date(2025, 12, 31)).startswith("2512-")


def test_counter_is_global_not_reset_per_month():
    # Données réelles du classeur : 2508-0004 existe, l'id de septembre continue (2509-0043…),
    # le compteur NNNN ne se réinitialise PAS par mois.
    existing = {"2508-0004", "2509-0042"}
    assert next_project_id(existing, date(2025, 9, 1)) == "2509-0043"


def test_increment_from_max_existing():
    existing = {"2508-0001", "2508-0002", "2508-0007"}
    assert next_project_id(existing, date(2025, 8, 1)) == "2508-0008"


def test_retry_on_collision():
    # Le candidat « naturel » est déjà pris (id réservé manuellement) → on incrémente.
    existing = {"2508-0004", "2508-0005"}  # max=5 → candidat 0006 libre
    assert next_project_id(existing, date(2025, 8, 1)) == "2508-0006"

    existing2 = {"2508-0004", "2508-0005", "2508-0006"}  # max=6 → 0007
    assert next_project_id(existing2, date(2025, 8, 1)) == "2508-0007"


def test_ignores_malformed_existing_ids():
    existing = {"garbage", "2025", "", "2508-0003"}
    assert next_project_id(existing, date(2025, 8, 1)) == "2508-0004"


def test_uniqueness_over_a_batch():
    seen: set[str] = set()
    for _ in range(50):
        pid = next_project_id(seen, date(2025, 8, 1))
        assert pid not in seen
        seen.add(pid)
    assert len(seen) == 50
