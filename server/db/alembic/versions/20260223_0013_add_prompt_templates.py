"""Add prompt templates table.

Revision ID: 20260223_0013
Revises: 20260223_0012
Create Date: 2026-02-23 15:40:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260223_0013"
down_revision = "20260223_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=180), nullable=False, server_default=""),
        sa.Column("prompt", sa.Text(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_templates_created_at",
        "prompt_templates",
        ["created_at"],
    )
    op.create_index(
        "ix_prompt_templates_updated_at",
        "prompt_templates",
        ["updated_at"],
    )
    op.create_index(
        "uq_prompt_templates_name_lower",
        "prompt_templates",
        [sa.text("lower(name)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_prompt_templates_name_lower", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_updated_at", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_created_at", table_name="prompt_templates")
    op.drop_table("prompt_templates")

