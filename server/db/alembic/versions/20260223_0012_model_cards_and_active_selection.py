"""Refactor model settings to model cards with active/default selectors.

Revision ID: 20260223_0012
Revises: 20260221_0011
Create Date: 2026-02-23 13:10:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260223_0012"
down_revision = "20260221_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_model_settings",
        sa.Column("display_name", sa.String(length=255), nullable=False, server_default="Default"),
    )
    op.add_column(
        "agent_model_settings",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "agent_model_settings",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.drop_constraint(
        "uq_agent_model_settings_singleton_key",
        "agent_model_settings",
        type_="unique",
    )
    op.drop_constraint(
        "ck_agent_model_settings_singleton_key_global",
        "agent_model_settings",
        type_="check",
    )
    op.drop_column("agent_model_settings", "singleton_key")

    op.alter_column("agent_model_settings", "display_name", server_default=None)
    op.alter_column("agent_model_settings", "is_default", server_default=sa.text("false"))
    op.alter_column("agent_model_settings", "is_active", server_default=sa.text("false"))

    op.create_index(
        "uq_agent_model_settings_default_true",
        "agent_model_settings",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_index(
        "uq_agent_model_settings_active_true",
        "agent_model_settings",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_agent_model_settings_active_true", table_name="agent_model_settings")
    op.drop_index("uq_agent_model_settings_default_true", table_name="agent_model_settings")

    op.add_column(
        "agent_model_settings",
        sa.Column(
            "singleton_key",
            sa.String(length=16),
            nullable=False,
            server_default="global",
        ),
    )

    op.execute(
        """
        DELETE FROM agent_model_settings
        WHERE id NOT IN (
            SELECT id
            FROM agent_model_settings
            ORDER BY created_at ASC, id ASC
            LIMIT 1
        )
        """
    )
    op.execute("UPDATE agent_model_settings SET singleton_key = 'global'")

    op.drop_column("agent_model_settings", "is_active")
    op.drop_column("agent_model_settings", "is_default")
    op.drop_column("agent_model_settings", "display_name")

    op.create_unique_constraint(
        "uq_agent_model_settings_singleton_key",
        "agent_model_settings",
        ["singleton_key"],
    )
    op.create_check_constraint(
        "ck_agent_model_settings_singleton_key_global",
        "agent_model_settings",
        "singleton_key = 'global'",
    )
