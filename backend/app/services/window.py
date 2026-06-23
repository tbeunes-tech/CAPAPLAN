"""Fenêtre glissante de 12 mois (§6.3) et utilitaires de mois."""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def first_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def add_months(d: date, n: int) -> date:
    """Décale `d` de `n` mois, ramené au 1er du mois résultant."""
    total = (d.year * 12 + (d.month - 1)) + n
    return date(total // 12, total % 12 + 1, 1)


def month_window(start: date, length: int = 12) -> list[date]:
    """Liste des 1ers de mois `[start, start+1, …, start+length-1]`."""
    s = first_of_month(start)
    return [add_months(s, i) for i in range(length)]


def round_tenth(x: float) -> float:
    """Arrondi à 0,1 façon Excel (half-up, pas banker's) — §6.3."""
    return float(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
