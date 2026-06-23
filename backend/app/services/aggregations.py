"""Restitutions calculées à la volée (§5.3–5.8 / §6.3, §6.4, §6.8).

Toutes ces fonctions sont en **lecture seule** : elles dérivent les 4 tables, ne stockent rien.
Chacune prend un `start` (1er mois de la fenêtre) ; défaut = mois courant.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import MonthlyCapacity, MonthlyLoad, Project, Team
from .rules import OVERLOAD_NULL_CAPACITY, occupancy_rate
from .window import first_of_month, month_window, round_tenth


def _today() -> date:
    return date.today()


# --------------------------------------------------------------------------- #
# §6.3 — Charge équipe (pivot équipe × 12 mois, somme des jours in_plan)
# --------------------------------------------------------------------------- #
def team_load_pivot(db: Session, start: date | None = None) -> dict:
    months = month_window(start or first_of_month(_today()))
    mset = set(months)
    rows = db.execute(
        select(MonthlyLoad.team, MonthlyLoad.month, func.sum(MonthlyLoad.days))
        .where(MonthlyLoad.in_plan.is_(True), MonthlyLoad.month.in_(months))
        .group_by(MonthlyLoad.team, MonthlyLoad.month)
    ).all()
    acc: dict[str, dict[date, float]] = defaultdict(lambda: {m: 0.0 for m in months})
    for team, month, total in rows:
        if month in mset:
            acc[team][month] = round_tenth(float(total or 0))
    teams = db.scalars(select(Team.name).order_by(Team.name)).all()
    return {
        "months": months,
        "rows": [{"team": t, "values": [acc[t][m] for m in months]} for t in teams],
    }


def team_load_detail(db: Session, team: str, start: date | None = None) -> dict:
    """Détail de la charge d'une équipe (§5.3 drill-down) : ventilation par projet × mois.

    Ce sont les lignes `monthly_loads` (in_plan) qui composent la cellule agrégée du pivot.
    """
    months = month_window(start or first_of_month(_today()))
    mset = set(months)
    rows = db.execute(
        select(MonthlyLoad.project_id, Project.project_name, MonthlyLoad.month,
               func.sum(MonthlyLoad.days))
        .join(Project, Project.project_id == MonthlyLoad.project_id)
        .where(MonthlyLoad.team == team, MonthlyLoad.in_plan.is_(True),
               MonthlyLoad.month.in_(months))
        .group_by(MonthlyLoad.project_id, Project.project_name, MonthlyLoad.month)
    ).all()
    acc: dict[str, dict] = {}
    for pid, pname, month, total in rows:
        if month not in mset:
            continue
        entry = acc.setdefault(pid, {"project_id": pid, "project_name": pname,
                                     "vals": {m: 0.0 for m in months}})
        entry["vals"][month] = round_tenth(float(total or 0))
    out = [
        {"project_id": e["project_id"], "project_name": e["project_name"],
         "values": [e["vals"][m] for m in months]}
        for e in acc.values()
    ]
    out.sort(key=lambda r: -sum(r["values"]))  # projets les plus chargés en tête
    return {"team": team, "months": months, "rows": out}


# --------------------------------------------------------------------------- #
# §5.4 — Capacité équipe (pivot capa_projet)
# --------------------------------------------------------------------------- #
def team_capacity_pivot(db: Session, start: date | None = None) -> dict:
    months = month_window(start or first_of_month(_today()))
    mset = set(months)
    rows = db.execute(
        select(MonthlyCapacity.team, MonthlyCapacity.month, MonthlyCapacity.capa_projet)
        .where(MonthlyCapacity.month.in_(months))
    ).all()
    # Capacité = valeur précise de capa_projet (l'arrondi à 0,1 du §6.3 ne concerne que la charge).
    acc: dict[str, dict[date, float]] = defaultdict(lambda: {m: 0.0 for m in months})
    for team, month, capa in rows:
        if month in mset:
            acc[team][month] = float(capa or 0)
    teams = db.scalars(select(Team.name).order_by(Team.name)).all()
    return {
        "months": months,
        "rows": [{"team": t, "values": [acc[t][m] for m in months]} for t in teams],
    }


# --------------------------------------------------------------------------- #
# §5.5 / §6.4 — Taux d'occupation (charge / capacité) + code couleur
# --------------------------------------------------------------------------- #
def occupancy_color(rate: float) -> str:
    """Code couleur §5.5 (seuils paramétrables)."""
    if rate == OVERLOAD_NULL_CAPACITY:
        return "overload_null_capacity"  # marqueur distinct : charge>0, capacité=0
    if rate < settings.occupancy_green_below:
        return "green"
    if rate <= settings.occupancy_amber_below:
        return "amber"
    return "red"


def team_occupancy_pivot(db: Session, start: date | None = None) -> dict:
    months = month_window(start or first_of_month(_today()))
    load = {(r["team"]): r["values"] for r in team_load_pivot(db, start)["rows"]}
    capa = {(r["team"]): r["values"] for r in team_capacity_pivot(db, start)["rows"]}
    teams = db.scalars(select(Team.name).order_by(Team.name)).all()
    rows = []
    for t in teams:
        cells = []
        for i in range(len(months)):
            charge = load.get(t, [0] * len(months))[i]
            capacite = capa.get(t, [0] * len(months))[i]
            rate = occupancy_rate(charge, capacite)
            cells.append({"rate": rate, "color": occupancy_color(rate)})
        rows.append({"team": t, "cells": cells})
    return {"months": months, "rows": rows}


# --------------------------------------------------------------------------- #
# §5.6 — Analyse des surcharges (couples équipe, mois où taux > 100 %)
# --------------------------------------------------------------------------- #
def overload_list(db: Session, start: date | None = None) -> list[dict]:
    months = month_window(start or first_of_month(_today()))
    load = {r["team"]: r["values"] for r in team_load_pivot(db, start)["rows"]}
    capa = {r["team"]: r["values"] for r in team_capacity_pivot(db, start)["rows"]}
    out = []
    for t in load:
        for i, m in enumerate(months):
            charge = load[t][i]
            capacite = capa.get(t, [0] * len(months))[i]
            rate = occupancy_rate(charge, capacite)
            # Surcharge : taux > 100 % OU capacité nulle avec charge (sentinelle).
            if rate == OVERLOAD_NULL_CAPACITY:
                out.append({"team": t, "month": m, "charge": charge, "capacite": capacite,
                            "rate": rate, "ecart_jours": round_tenth(charge),
                            "color": "overload_null_capacity"})
            elif rate > settings.occupancy_amber_below:
                out.append({"team": t, "month": m, "charge": charge, "capacite": capacite,
                            "rate": rate, "ecart_jours": round_tenth(charge - capacite),
                            "color": "red"})
    out.sort(key=lambda r: (-(r["ecart_jours"]), r["team"], r["month"]))
    return out


# --------------------------------------------------------------------------- #
# §5.7 — Roadmap (Gantt) : projets in_plan sur start_date → end_date
# --------------------------------------------------------------------------- #
def roadmap(db: Session) -> list[dict]:
    projs = db.scalars(
        select(Project).where(Project.in_plan.is_(True)).order_by(Project.start_date)
    ).all()
    return [
        {
            "project_id": p.project_id,
            "project_name": p.project_name,
            "pilier_strategique": p.pilier_strategique,
            "start_date": p.start_date,
            "end_date": p.end_date,
        }
        for p in projs
    ]


# --------------------------------------------------------------------------- #
# §5.8 / §6.8 — Plan de priorisation (4 scénarios cumulatifs)
# --------------------------------------------------------------------------- #
SCENARIOS = [
    ("P0", "P0"),
    ("P0 + P1 Renforcement SI", "P0_P1_RENFSI"),
    ("P0 + P1", "P0_P1"),
    ("Plan intégral", "FULL"),
]


def _scenario_project_ids(projects: list[Project]) -> dict[str, list[str]]:
    p0 = [p for p in projects if p.priorite == "P0"]
    p1 = [p for p in projects if p.priorite == "P1"]
    p1_renfsi = [p for p in p1 if p.pilier_strategique == "Renforcement SI"]
    return {
        "P0": [p.project_id for p in p0],
        "P0_P1_RENFSI": [p.project_id for p in p0 + p1_renfsi],
        "P0_P1": [p.project_id for p in p0 + p1],
        "FULL": [p.project_id for p in projects],
    }


def prioritization_plan(db: Session, start: date | None = None) -> dict:
    months = month_window(start or first_of_month(_today()))
    mset = set(months)
    in_plan_projects = db.scalars(select(Project).where(Project.in_plan.is_(True))).all()
    by_scenario = _scenario_project_ids(in_plan_projects)
    total_load = {p.project_id: float(p.total_project_load or 0) for p in in_plan_projects}

    # Charge mensuelle par projet (in_plan), sur la fenêtre.
    load_rows = db.execute(
        select(MonthlyLoad.project_id, MonthlyLoad.month, func.sum(MonthlyLoad.days))
        .where(MonthlyLoad.in_plan.is_(True), MonthlyLoad.month.in_(months))
        .group_by(MonthlyLoad.project_id, MonthlyLoad.month)
    ).all()
    proj_month_load: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    for pid, month, total in load_rows:
        if month in mset:
            proj_month_load[pid][month] += float(total or 0)

    # Capacité totale par mois = somme des capa_projet de toutes les équipes.
    capa_rows = db.execute(
        select(MonthlyCapacity.month, func.sum(MonthlyCapacity.capa_projet))
        .where(MonthlyCapacity.month.in_(months))
        .group_by(MonthlyCapacity.month)
    ).all()
    capa_total = {m: 0.0 for m in months}
    for month, total in capa_rows:
        if month in mset:
            capa_total[month] = float(total or 0)

    scenarios = []
    for label, key in SCENARIOS:
        pids = by_scenario[key]
        monthly_charge = {m: 0.0 for m in months}
        for pid in pids:
            for m, d in proj_month_load.get(pid, {}).items():
                monthly_charge[m] += d
        monthly = []
        for m in months:
            charge = round_tenth(monthly_charge[m])
            capacite = round_tenth(capa_total[m])
            rate = occupancy_rate(charge, capacite)
            monthly.append({"month": m, "charge": charge, "capacite": capacite,
                            "rate": rate, "color": occupancy_color(rate)})
        sum_charge = sum(monthly_charge.values())
        sum_capa = sum(capa_total.values())
        global_rate = occupancy_rate(sum_charge, sum_capa)
        scenarios.append({
            "scenario": label,
            "project_count": len(pids),
            "project_ids": pids,
            "charge_cumulee": round_tenth(sum(total_load.get(p, 0.0) for p in pids)),
            "global_rate": global_rate,
            "global_color": occupancy_color(global_rate),
            "monthly": monthly,
        })
    return {"months": months, "scenarios": scenarios}
