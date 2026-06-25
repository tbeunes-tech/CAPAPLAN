"""Anonymisation des données identifiantes (pour un déploiement public / démo).

Remplace de façon **déterministe** (même valeur réelle → même valeur factice) :
- noms de personnes : `projects.project_leader`, `teams.manager`, et les noms dans `teams.description`
- noms de projets   : `projects.project_name`
- entités           : `projects.entite`
- propriétaires budget : `projects.budget_owner`
- noms d'équipes    : `teams.name` (+ cascade FK sur monthly_loads / monthly_capacity)

Conserve **intactes** : toutes les charges, capacités, dates, ETP, priorités, statuts, piliers —
l'app se comporte donc à l'identique. Le référentiel (`referentials`) est resynchronisé.

⚠️ N'altère PAS les comptes utilisateurs (`users`). Réversible : ré-importer le classeur restaure
les vraies données.

Usage :
    python -m scripts.anonymize --database-url postgresql+psycopg2://.../portfolio_anon
"""
from __future__ import annotations

import argparse
import string

from sqlalchemy import create_engine, distinct, select, update
from sqlalchemy.orm import Session

from app.audit import audit_disabled
from app.config import settings
from app.models import MonthlyCapacity, MonthlyLoad, Project, Referential, Team

# --- Pools de valeurs factices ------------------------------------------------
_FIRST = [
    "Camille", "Lucas", "Emma", "Hugo", "Léa", "Nathan", "Chloé", "Louis", "Manon", "Jules",
    "Sarah", "Adam", "Inès", "Tom", "Jade", "Paul", "Lina", "Noah", "Zoé", "Gabriel",
    "Alice", "Raphaël", "Anna", "Arthur", "Rose", "Maël", "Eva", "Sacha", "Mila", "Liam",
]
_CODENAMES = [
    "Atlas", "Borée", "Cosmos", "Delta", "Éole", "Fjord", "Galaxie", "Horizon", "Iris", "Jade",
    "Kepler", "Lagon", "Mistral", "Nova", "Onyx", "Phénix", "Quartz", "Récif", "Sirius", "Tornade",
    "Ulysse", "Vega", "Wasabi", "Xénon", "Yucca", "Zéphyr", "Alizé", "Brume", "Cyclone", "Dune",
    "Écho", "Flux", "Givre", "Halo", "Ibis", "Jet", "Karst", "Lyre", "Maelström", "Nimbus",
]
_NATO = [
    "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliett",
    "Kilo", "Lima", "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo", "Sierra", "Tango",
]


def _people(n: int) -> list[str]:
    out = []
    for letter in string.ascii_uppercase:
        for first in _FIRST:
            out.append(f"{first} {letter}.")
            if len(out) >= n:
                return out
    return out


def _projects(n: int) -> list[str]:
    out, rnd = [], 0
    while len(out) < n:
        rnd += 1
        for c in _CODENAMES:
            out.append(f"Projet {c}" if rnd == 1 else f"Projet {c} {rnd}")
            if len(out) >= n:
                return out
    return out


def _entities(n: int) -> list[str]:
    return [f"Entité {_NATO[i % len(_NATO)]}" for i in range(n)]


def _owners(n: int) -> list[str]:
    letters = string.ascii_uppercase
    return [f"{letters[i // 26 % 26]}{letters[i % 26]}" for i in range(n)]


def _teams(n: int) -> list[str]:
    return [f"Équipe {i + 1:02d}" for i in range(n)]


def _make_map(values, pool_fn) -> dict[str, str]:
    vals = sorted({v for v in values if v})
    pool = pool_fn(len(vals))
    return {v: pool[i] for i, v in enumerate(vals)}


def anonymize(session: Session) -> dict:
    audit_disabled.set(True)  # ne pas journaliser l'anonymisation
    scol = session.scalars

    leaders = scol(select(distinct(Project.project_leader))).all()
    managers = scol(select(distinct(Team.manager))).all()
    people_map = _make_map(list(leaders) + list(managers), _people)

    proj_map = _make_map(scol(select(distinct(Project.project_name))).all(), _projects)
    ent_map = _make_map(scol(select(distinct(Project.entite))).all(), _entities)
    owner_map = _make_map(scol(select(distinct(Project.budget_owner))).all(), _owners)
    team_map = _make_map(scol(select(distinct(Team.name))).all(), _teams)

    # 1) Projets
    for p in session.scalars(select(Project)).all():
        if p.project_name in proj_map:
            p.project_name = proj_map[p.project_name]
        if p.project_leader in people_map:
            p.project_leader = people_map[p.project_leader]
        if p.entite in ent_map:
            p.entite = ent_map[p.entite]
        if p.budget_owner in owner_map:
            p.budget_owner = owner_map[p.budget_owner]
    session.flush()

    # 2) Équipes : renommage de la PK → on crée la nouvelle, on repointe les FK, on supprime l'ancienne.
    for old, new in team_map.items():
        old_team = session.get(Team, old)
        session.add(Team(
            name=new,
            manager=people_map.get(old_team.manager, old_team.manager) if old_team.manager else None,
            capacite_etp=old_team.capacite_etp,
            description="(équipe anonymisée)",
        ))
    session.flush()
    for old, new in team_map.items():
        session.execute(update(MonthlyLoad).where(MonthlyLoad.team == old).values(team=new))
        session.execute(update(MonthlyCapacity).where(MonthlyCapacity.team == old).values(team=new))
    session.flush()
    for old in team_map:
        session.delete(session.get(Team, old))
    session.flush()

    # 3) Référentiel : on resynchronise entite + project_leader sur les valeurs anonymisées.
    for cat in ("entite", "project_leader"):
        for r in session.scalars(select(Referential).where(Referential.category == cat)).all():
            session.delete(r)
    session.flush()
    for cat, col in (("entite", Project.entite), ("project_leader", Project.project_leader)):
        for v in session.scalars(select(distinct(col)).where(col.is_not(None))).all():
            session.add(Referential(category=cat, value=v, active=True))

    session.commit()
    return {
        "projects": len(proj_map), "people": len(people_map),
        "entities": len(ent_map), "teams": len(team_map), "owners": len(owner_map),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Anonymise les données identifiantes.")
    p.add_argument("--database-url", default=settings.database_url)
    args = p.parse_args(argv)
    engine = create_engine(args.database_url, future=True)
    with Session(engine) as session:
        stats = anonymize(session)
    print("Anonymisation terminée :", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
