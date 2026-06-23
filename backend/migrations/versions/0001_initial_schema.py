"""Lot 1 — schéma initial : 4 tables persistées (§3).

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("name", sa.String(), primary_key=True),
        sa.Column("manager", sa.String(), nullable=True),
        sa.Column("capacite_etp", sa.Numeric(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
    )

    op.create_table(
        "projects",
        sa.Column("project_id", sa.String(), primary_key=True),
        sa.Column("entite", sa.String(), nullable=True),
        sa.Column("domain_lead", sa.String(), nullable=True),
        sa.Column("project_name", sa.String(), nullable=False),
        sa.Column("project_leader", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("priorite", sa.String(), nullable=True),
        sa.Column("pilier_strategique", sa.String(), nullable=True),
        sa.Column("budget_item", sa.String(), nullable=True),
        sa.Column("budget_owner", sa.String(), nullable=True),
        sa.Column("programme", sa.String(), nullable=True),
        sa.Column("in_plan", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("last_update", sa.DateTime(), nullable=True),
        sa.Column("total_project_load", sa.Numeric(), nullable=True),
    )

    op.create_table(
        "monthly_loads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.String(), sa.ForeignKey("projects.project_id"), nullable=False),
        sa.Column("team", sa.String(), sa.ForeignKey("teams.name"), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("days", sa.Numeric(), nullable=True),
        sa.Column("in_plan", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("project_id", "team", "month", name="uq_load_project_team_month"),
    )
    op.create_index("ix_load_team_month", "monthly_loads", ["team", "month"])

    op.create_table(
        "monthly_capacity",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team", sa.String(), sa.ForeignKey("teams.name"), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("etp_team", sa.Numeric(), nullable=True),
        sa.Column("etp_projet", sa.Numeric(), nullable=True),
        sa.Column("part_projet", sa.Numeric(), nullable=True),
        sa.Column("jours_indispo", sa.Numeric(), nullable=True),
        sa.Column("capa_projet", sa.Numeric(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("team", "month", name="uq_capacity_team_month"),
    )


def downgrade() -> None:
    op.drop_table("monthly_capacity")
    op.drop_index("ix_load_team_month", table_name="monthly_loads")
    op.drop_table("monthly_loads")
    op.drop_table("projects")
    op.drop_table("teams")
