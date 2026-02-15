"""Add global agent company profile table.

Revision ID: 20260215_0008
Revises: 20260214_0007
Create Date: 2026-02-15 12:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260215_0008"
down_revision = "20260214_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_company_profile",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "singleton_key",
            sa.String(length=16),
            nullable=False,
            server_default="global",
        ),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.CheckConstraint("singleton_key = 'global'", name="ck_agent_company_profile_singleton_key_global"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key", name="uq_agent_company_profile_singleton_key"),
    )


def downgrade() -> None:
    op.drop_table("agent_company_profile")
