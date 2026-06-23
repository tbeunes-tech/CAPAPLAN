"""Règles de gestion §6 — **règles arrêtées**, verrouillées par les tests.

Ce module ne contient que des fonctions pures (faciles à tester). Les agrégations §6.3/§6.4/§6.8
(qui requièrent des requêtes) arriveront au Lot 2.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime

from ..enums import IN_PLAN_STATUSES

# Sentinelle §6.4 : charge > 0 mais capacité = 0 (surcharge sur capacité nulle).
OVERLOAD_NULL_CAPACITY = -1.0


# ---------------------------------------------------------------------------
# §6.2 — Flag « In Plan »
# ---------------------------------------------------------------------------
def is_in_plan(status: str | None) -> bool:
    """`true` si le statut met le projet au plan.

    `In Progress` ou `Scheduled` (+ libellés FR historiques « En cours »/« Planifié », §6.2).
    """
    if status is None:
        return False
    return status.strip() in IN_PLAN_STATUSES


# ---------------------------------------------------------------------------
# §6.1 — Génération du Project ID
# ---------------------------------------------------------------------------
def _seq_of(project_id: str) -> int | None:
    """Extrait le compteur NNNN d'un id `yymm-NNNN`. None si le format ne correspond pas."""
    if not project_id or "-" not in project_id:
        return None
    tail = project_id.rsplit("-", 1)[1]
    return int(tail) if tail.isdigit() else None


def next_project_id(existing_ids: set[str], today: date) -> str:
    """Génère le prochain `project_id` au format `yymm-NNNN`.

    - `yymm` = année (2 chiffres) + mois courant.
    - `NNNN` = compteur **global** séquentiel sur 4 chiffres (cf. données du classeur :
      2508-0004 puis 2509-0043 — le compteur ne se réinitialise pas par mois).
    - Unicité garantie : on incrémente jusqu'à trouver un id libre.
    """
    prefix = f"{today.year % 100:02d}{today.month:02d}"
    seqs = [s for s in (_seq_of(i) for i in existing_ids) if s is not None]
    n = (max(seqs) + 1) if seqs else 1
    candidate = f"{prefix}-{n:04d}"
    while candidate in existing_ids:
        n += 1
        candidate = f"{prefix}-{n:04d}"
    return candidate


# ---------------------------------------------------------------------------
# §6.5 — Jours ouvrés (lundi → vendredi, FÉRIÉS INCLUS)
# ---------------------------------------------------------------------------
def working_days(year: int, month: int) -> int:
    """Nombre de jours du lundi au vendredi dans le mois.

    Équivalent `NETWORKDAYS` **sans** liste de fériés : les jours fériés comptent comme
    travaillés (convention métier arrêtée §6.5 — ne pas réintroduire de calcul de fériés).
    """
    n_days = calendar.monthrange(year, month)[1]
    return sum(
        1
        for d in range(1, n_days + 1)
        if date(year, month, d).weekday() < 5  # 0=lundi … 4=vendredi
    )


# ---------------------------------------------------------------------------
# §6.7 — Capacité projet du mois
# ---------------------------------------------------------------------------
def capa_projet(
    etp_projet: float,
    etp_team: float,
    work_days: int,
    jours_indispo: float,
) -> float:
    """`MAX(0 ; ETP_Projet × JoursOuvrés − (ETP_Projet/ETP_Team) × Jours_Indispo)`.

    Seul le terme d'indisponibilité est pondéré par la part projet (§6.7 — le commentaire
    d'en-tête VBA est erroné, ne pas le suivre). Si `etp_team == 0`, la part projet vaut 0
    (pas de division par zéro, aucune indispo déduite).
    """
    part = (etp_projet / etp_team) if etp_team else 0.0
    brute = etp_projet * work_days
    return max(0.0, brute - part * jours_indispo)


# ---------------------------------------------------------------------------
# §6.4 — Taux d'occupation (cellule)
# ---------------------------------------------------------------------------
def occupancy_rate(charge: float, capacite: float) -> float:
    """Taux pour un couple (équipe, mois). Voir §6.4.

    - `capacite > 0` → `charge / capacite` ;
    - sinon `charge > 0` → sentinelle `OVERLOAD_NULL_CAPACITY` (-1) ;
    - sinon → 0.
    """
    if capacite > 0:
        return charge / capacite
    if charge > 0:
        return OVERLOAD_NULL_CAPACITY
    return 0.0
