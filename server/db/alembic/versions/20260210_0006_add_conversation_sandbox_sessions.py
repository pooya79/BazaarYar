"""Add per-conversation sandbox session metadata.

Revision ID: 20260210_0006
Revises: 20260210_0005
Create Date: 2026-02-10 00:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260210_0006"
down_revision = "20260210_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_sandbox_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("container_name", sa.String(length=255), nullable=False),
        sa.Column("workspace_path", sa.Text(), nullable=False),
        sa.Column("owner_host", sa.String(length=255), nullable=False),
        sa.Column("next_request_seq", sa.BigInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("container_name"),
    )
    op.create_index(
        "ix_conversation_sandbox_sessions_conversation_id",
        "conversation_sandbox_sessions",
        ["conversation_id"],
        unique=True,
    )
    op.create_index(
        "ix_conversation_sandbox_sessions_last_used_at",
        "conversation_sandbox_sessions",
        ["last_used_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversation_sandbox_sessions_last_used_at", table_name="conversation_sandbox_sessions")
    op.drop_index("ix_conversation_sandbox_sessions_conversation_id", table_name="conversation_sandbox_sessions")
    op.drop_table("conversation_sandbox_sessions")
