"""Add reasoning token persistence on messages.

Revision ID: 20260210_0005
Revises: 20260207_0004
Create Date: 2026-02-10 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260210_0005"
down_revision = "20260207_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "reasoning_tokens")
