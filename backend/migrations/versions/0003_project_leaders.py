"""Paramétrage — référentiel éditable des chefs de projet.

Revision ID: 0003_project_leaders
Revises: 0002_auth_audit
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_project_leaders"
down_revision = "0002_auth_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_leaders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("name", name="uq_project_leaders_name"),
    )


def downgrade() -> None:
    op.drop_table("project_leaders")
