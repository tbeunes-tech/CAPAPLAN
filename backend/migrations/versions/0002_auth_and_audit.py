"""Lot 5 — auth (users) + historisation (change_log).

Revision ID: 0002_auth_audit
Revises: 0001_initial
Create Date: 2026-06-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_auth_audit"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="reader"),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "change_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("user_email", sa.String(), nullable=False, server_default="system"),
        sa.Column("table_name", sa.String(), nullable=False),
        sa.Column("row_pk", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
    )
    op.create_index("ix_changelog_target", "change_log", ["table_name", "row_pk"])
    op.create_index("ix_change_log_ts", "change_log", ["ts"])


def downgrade() -> None:
    op.drop_index("ix_change_log_ts", table_name="change_log")
    op.drop_index("ix_changelog_target", table_name="change_log")
    op.drop_table("change_log")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
