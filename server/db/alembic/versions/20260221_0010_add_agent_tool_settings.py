"""Add global agent tool settings table.

Revision ID: 20260221_0010
Revises: 20260215_0009
Create Date: 2026-02-21 12:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260221_0010"
down_revision = "20260215_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_tool_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "singleton_key",
            sa.String(length=16),
            nullable=False,
            server_default="global",
        ),
        sa.Column(
            "tool_overrides_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
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
        sa.CheckConstraint("singleton_key = 'global'", name="ck_agent_tool_settings_singleton_key_global"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key", name="uq_agent_tool_settings_singleton_key"),
    )


def downgrade() -> None:
    op.drop_table("agent_tool_settings")
