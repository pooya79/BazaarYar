"""Add conversation reports table.

Revision ID: 20260215_0009
Revises: 20260215_0008
Create Date: 2026-02-15 13:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260215_0009"
down_revision = "20260215_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("preview_text", sa.String(length=180), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_conversation_id", sa.Uuid(), nullable=True),
        sa.Column(
            "enabled_for_agent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.ForeignKeyConstraint(
            ["source_conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_reports_created_at",
        "conversation_reports",
        ["created_at"],
    )
    op.create_index(
        "ix_conversation_reports_updated_at",
        "conversation_reports",
        ["updated_at"],
    )
    op.create_index(
        "ix_conversation_reports_enabled_for_agent",
        "conversation_reports",
        ["enabled_for_agent"],
    )
    op.create_index(
        "ix_conversation_reports_source_conversation_id",
        "conversation_reports",
        ["source_conversation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_reports_source_conversation_id",
        table_name="conversation_reports",
    )
    op.drop_index(
        "ix_conversation_reports_enabled_for_agent",
        table_name="conversation_reports",
    )
    op.drop_index(
        "ix_conversation_reports_updated_at",
        table_name="conversation_reports",
    )
    op.drop_index(
        "ix_conversation_reports_created_at",
        table_name="conversation_reports",
    )
    op.drop_table("conversation_reports")
