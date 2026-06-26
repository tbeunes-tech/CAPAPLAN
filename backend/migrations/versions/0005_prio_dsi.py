"""Ajout du champ projet « Prio DSI » (liste gérée).

Revision ID: 0005_prio_dsi
Revises: 0004_referentials
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_prio_dsi"
down_revision = "0004_referentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("prio_dsi", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "prio_dsi")
