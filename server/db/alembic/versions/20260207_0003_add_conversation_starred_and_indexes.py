"""Add conversation star flag and ordering indexes.

Revision ID: 20260207_0003
Revises: 20260207_0002
Create Date: 2026-02-07 00:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260207_0003"
down_revision = "20260207_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("starred", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_conversations_starred",
        "conversations",
        ["starred"],
    )
    op.create_index(
        "ix_conversations_starred_updated_at",
        "conversations",
        ["starred", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_starred_updated_at", table_name="conversations")
    op.drop_index("ix_conversations_starred", table_name="conversations")
    op.drop_column("conversations", "starred")
