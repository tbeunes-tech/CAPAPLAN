"""Référentiels §4 — repris **à l'identique** du classeur.

Stockés en base comme colonnes texte (pas d'ENUM SQL figé), validés contre ces listes
au niveau service/Pydantic. Un Admin pourra les éditer en Lot 5 sans migration de schéma.
"""
from __future__ import annotations

ENTITE = [
    "CPM", "DEPOTRADE", "IVRYLAB", "OCP FORMATION", "OCP RETAIL", "PHV", "PHR",
    "PHX FR GLOBAL", "PHX FR RETAIL", "PHX GROUP", "PHOENIX OCP",
]

DOMAIN_LEAD = [
    "ETU-BI", "ETU-LEG", "ETU-CUST EXP", "ETU-GAIN", "ETU-SAP", "CYBER SEC",
    "TP", "TP-OPE", "TP-PM", "ETU-PPF", "AUTRE",
]

PILIER_STRATEGIQUE = [
    "Supply Chain efficiente", "Push ==> Pull", "Vite ==> Pas Cher",
    "Renforcement SI", "Autres projets business stratégiques", "Projets groupe",
]

PRIORITE = ["P0", "P1", "P2", "P3"]

STATUT = ["In Progress", "Scheduled", "Closed", "Not Scheduled", "Canceled", "On Hold"]

# PROGRAMME : la colonne réelle est en **texte libre** (sous-programmes : ARCHI, MFT, Modern BI,
# NETWORK…). Les 5 valeurs ci-dessous ne sont que des suggestions, PAS une liste fermée — la
# saisie n'est donc pas validée contre cette liste (décision « données réelles font foi »).
PROGRAMME = ["LOCAL", "GLOBAL", "Chronique", "MB", "ORSEC"]
PROGRAMME_IS_FREE_TEXT = True

# Statuts qui mettent un projet « in plan » (§6.2). Inclut les libellés FR historiques
# (compatibilité import d'anciennes données — cf. §6.2).
IN_PLAN_STATUSES = {"In Progress", "Scheduled", "En cours", "Planifié"}

REFERENTIALS = {
    "entite": ENTITE,
    "domain_lead": DOMAIN_LEAD,
    "pilier_strategique": PILIER_STRATEGIQUE,
    "priorite": PRIORITE,
    "status": STATUT,
    "programme": PROGRAMME,
}

# Catégories gérées en base (table `referentials`). La clé de catégorie == nom de la colonne
# de `projects` correspondante → renommer une valeur peut se propager (cascade) à cette colonne.
REFERENTIAL_CATEGORIES = [
    "entite", "domain_lead", "status", "priorite", "pilier_strategique",
    "programme", "project_leader",
]

# Valeurs par défaut servant à amorcer la table (§4). project_leader n'a pas de défaut
# (alimenté depuis les données). Programme : la liste §4 + valeurs réelles importées.
REFERENTIAL_DEFAULTS = {
    "entite": ENTITE,
    "domain_lead": DOMAIN_LEAD,
    "status": STATUT,
    "priorite": PRIORITE,
    "pilier_strategique": PILIER_STRATEGIQUE,
    "programme": PROGRAMME,
    "project_leader": [],
}

# Libellés d'affichage des catégories (UI Paramétrage).
CATEGORY_LABELS = {
    "entite": "Entité",
    "domain_lead": "Domain lead",
    "status": "Statut",
    "priorite": "Priorité",
    "pilier_strategique": "Pilier stratégique",
    "programme": "Programme",
    "project_leader": "Chef de projet",
}
