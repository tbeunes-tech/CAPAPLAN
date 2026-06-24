"""Paramétrage généralisé — table unique `referentials` (remplace `project_leaders`).

Revision ID: 0004_referentials
Revises: 0003_project_leaders
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_referentials"
down_revision = "0003_project_leaders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("category", "value", name="uq_referentials_category_value"),
    )
    op.create_index("ix_referentials_category", "referentials", ["category"])
    # Reprise des chefs de projet déjà saisis (table dédiée → table générique).
    op.execute(
        "INSERT INTO referentials (category, value, active) "
        "SELECT 'project_leader', name, active FROM project_leaders"
    )
    op.drop_table("project_leaders")


def downgrade() -> None:
    op.create_table(
        "project_leaders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("name", name="uq_project_leaders_name"),
    )
    op.execute(
        "INSERT INTO project_leaders (name, active) "
        "SELECT value, active FROM referentials WHERE category = 'project_leader'"
    )
    op.drop_index("ix_referentials_category", table_name="referentials")
    op.drop_table("referentials")
