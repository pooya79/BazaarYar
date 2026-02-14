"""Add global agent model settings table.

Revision ID: 20260214_0007
Revises: 20260210_0006
Create Date: 2026-02-14 15:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260214_0007"
down_revision = "20260210_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_model_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "singleton_key",
            sa.String(length=16),
            nullable=False,
            server_default="global",
        ),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("base_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("reasoning_effort", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("reasoning_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("singleton_key = 'global'", name="ck_agent_model_settings_singleton_key_global"),
        sa.CheckConstraint("temperature >= 0 AND temperature <= 2", name="ck_agent_model_settings_temperature"),
        sa.CheckConstraint(
            "reasoning_effort IN ('low', 'medium', 'high')",
            name="ck_agent_model_settings_reasoning_effort",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key", name="uq_agent_model_settings_singleton_key"),
    )


def downgrade() -> None:
    op.drop_table("agent_model_settings")
