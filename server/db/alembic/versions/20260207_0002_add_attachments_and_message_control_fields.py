"""Add attachments/message_attachments and message control fields.

Revision ID: 20260207_0002
Revises: 20260203_0001
Create Date: 2026-02-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260207_0002"
down_revision = "20260203_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("extraction_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "message_attachments",
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["attachment_id"],
            ["attachments.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("message_id", "attachment_id"),
    )
    op.create_index(
        "ix_message_attachments_attachment_id",
        "message_attachments",
        ["attachment_id"],
    )

    op.add_column(
        "messages",
        sa.Column("token_estimate", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "messages",
        sa.Column("tokenizer_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("message_kind", sa.String(length=32), nullable=True, server_default="normal"),
    )
    op.add_column(
        "messages",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("usage_json", sa.JSON(), nullable=True),
    )

    # Backfill token/message-kind defaults for existing rows.
    op.execute(
        """
        UPDATE messages
        SET
            token_estimate = GREATEST(1, CEIL(char_length(content) / 4.0)::int),
            tokenizer_name = COALESCE(tokenizer_name, 'char4_approx_v1'),
            message_kind = COALESCE(message_kind, 'normal')
        """
    )
    op.alter_column("messages", "token_estimate", nullable=False, server_default="0")
    op.alter_column("messages", "message_kind", nullable=False, server_default="normal")


def downgrade() -> None:
    op.drop_column("messages", "usage_json")
    op.drop_column("messages", "archived_at")
    op.drop_column("messages", "message_kind")
    op.drop_column("messages", "tokenizer_name")
    op.drop_column("messages", "token_estimate")

    op.drop_index("ix_message_attachments_attachment_id", table_name="message_attachments")
    op.drop_table("message_attachments")
    op.drop_table("attachments")
