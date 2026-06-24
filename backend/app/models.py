"""Modèle de données §3 — 4 tables persistées.

Les restitutions §5.3–5.8 sont calculées à la volée et ne sont jamais stockées.
Les colonnes marquées « calculé » dans la spec (`in_plan`, `last_update`,
`total_project_load`, `part_projet`, `capa_projet`) sont matérialisées ici pour
performance/fidélité, mais recalculées par l'app à chaque écriture — jamais saisies à la main.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String,
    UniqueConstraint, Index, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Team(Base):
    """§3.3 — équipes."""
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    manager: Mapped[str | None] = mapped_column(String)
    capacite_etp: Mapped[float | None] = mapped_column(Numeric)  # ETP de référence
    description: Mapped[str | None] = mapped_column(String)

    loads: Mapped[list["MonthlyLoad"]] = relationship(back_populates="team_ref")
    capacities: Mapped[list["MonthlyCapacity"]] = relationship(back_populates="team_ref")


class User(Base):
    """§8.1 — comptes et rôles. role ∈ {admin, contributor, reader}."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="reader")
    full_name: Mapped[str | None] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Referential(Base):
    """Référentiel générique éditable (onglet Paramétrage, Admin).

    Une ligne = une valeur d'une liste. `category` ∈ les colonnes de projet à liste gérée
    (entite, domain_lead, status, priorite, pilier_strategique, programme, project_leader).
    Remplace les listes en dur de `enums.py`. Renommer une valeur se propage aux projets.
    """
    __tablename__ = "referentials"
    __table_args__ = (
        UniqueConstraint("category", "value", name="uq_referentials_category_value"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ChangeLog(Base):
    """§8.2 — journal d'audit : une ligne par écriture (qui, quand, quoi, avant → après)."""
    __tablename__ = "change_log"
    __table_args__ = (Index("ix_changelog_target", "table_name", "row_pk"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    user_email: Mapped[str] = mapped_column(String, default="system")
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    row_pk: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)  # insert | update | delete
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)


class Project(Base):
    """§3.1 — portefeuille projets."""
    __tablename__ = "projects"

    # PK immuable, généré par le système (§6.1).
    project_id: Mapped[str] = mapped_column(String, primary_key=True)

    entite: Mapped[str | None] = mapped_column(String)
    domain_lead: Mapped[str | None] = mapped_column(String)
    project_name: Mapped[str] = mapped_column(String, nullable=False)
    project_leader: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    priorite: Mapped[str | None] = mapped_column(String)
    pilier_strategique: Mapped[str | None] = mapped_column(String)
    budget_item: Mapped[str | None] = mapped_column(String)
    budget_owner: Mapped[str | None] = mapped_column(String)
    programme: Mapped[str | None] = mapped_column(String)

    # Calculés (§6.2 / §6.6) — jamais saisis.
    in_plan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    last_update: Mapped[datetime | None] = mapped_column(DateTime)
    total_project_load: Mapped[float | None] = mapped_column(Numeric)

    loads: Mapped[list["MonthlyLoad"]] = relationship(
        back_populates="project", cascade="all, delete-orphan",
    )


class MonthlyLoad(Base):
    """§3.2 — charge mensuelle (table de faits). Une ligne = (projet, équipe, mois)."""
    __tablename__ = "monthly_loads"
    __table_args__ = (
        UniqueConstraint("project_id", "team", "month", name="uq_load_project_team_month"),
        Index("ix_load_team_month", "team", "month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), nullable=False)
    team: Mapped[str] = mapped_column(ForeignKey("teams.name"), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)  # toujours le 1er du mois
    days: Mapped[float] = mapped_column(Numeric, default=0)     # charge en jours-homme
    in_plan: Mapped[bool] = mapped_column(Boolean, default=False)  # recopié du projet (§3.2)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    project: Mapped["Project"] = relationship(back_populates="loads")
    team_ref: Mapped["Team"] = relationship(back_populates="loads")


class MonthlyCapacity(Base):
    """§3.4 — capacité mensuelle par équipe."""
    __tablename__ = "monthly_capacity"
    __table_args__ = (
        UniqueConstraint("team", "month", name="uq_capacity_team_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    team: Mapped[str] = mapped_column(ForeignKey("teams.name"), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)  # 1er du mois
    etp_team: Mapped[float | None] = mapped_column(Numeric)
    etp_projet: Mapped[float | None] = mapped_column(Numeric)
    part_projet: Mapped[float | None] = mapped_column(Numeric)   # etp_projet / etp_team
    jours_indispo: Mapped[float | None] = mapped_column(Numeric)
    capa_projet: Mapped[float | None] = mapped_column(Numeric)   # §6.7
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    team_ref: Mapped["Team"] = relationship(back_populates="capacities")
