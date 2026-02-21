"""Drop deprecated reference table storage entities.

Revision ID: 20260221_0011
Revises: 20260221_0010
Create Date: 2026-02-21 16:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260221_0011"
down_revision = "20260221_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_reference_table_rows_table_import_job", table_name="reference_table_rows")
    op.drop_index("ix_reference_table_rows_table_updated", table_name="reference_table_rows")
    op.drop_index("ix_reference_table_rows_import_job_id", table_name="reference_table_rows")
    op.drop_index("ix_reference_table_rows_table_id", table_name="reference_table_rows")
    op.drop_table("reference_table_rows")

    op.drop_index(
        "ix_reference_table_import_jobs_table_id",
        table_name="reference_table_import_jobs",
    )
    op.drop_table("reference_table_import_jobs")

    op.drop_index(
        "ix_reference_table_columns_table_position",
        table_name="reference_table_columns",
    )
    op.drop_index("ix_reference_table_columns_table_id", table_name="reference_table_columns")
    op.drop_table("reference_table_columns")

    op.drop_index("ix_reference_tables_name", table_name="reference_tables")
    op.drop_table("reference_tables")


def downgrade() -> None:
    op.create_table(
        "reference_tables",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(length=63), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
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
    )
    op.create_index("ix_reference_tables_name", "reference_tables", ["name"], unique=True)

    op.create_table(
        "reference_table_columns",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=63), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("data_type", sa.String(length=32), nullable=False),
        sa.Column("nullable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("semantic_hint", sa.String(length=128), nullable=True),
        sa.Column("constraints_json", sa.JSON(), nullable=True),
        sa.Column("default_json", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["table_id"], ["reference_tables.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("table_id", "name", name="uq_reference_table_columns_table_name"),
        sa.UniqueConstraint("table_id", "position", name="uq_reference_table_columns_table_position"),
    )
    op.create_index("ix_reference_table_columns_table_id", "reference_table_columns", ["table_id"])
    op.create_index(
        "ix_reference_table_columns_table_position",
        "reference_table_columns",
        ["table_id", "position"],
    )

    op.create_table(
        "reference_table_import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("attachment_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("source_filename", sa.String(length=512), nullable=True),
        sa.Column("source_format", sa.String(length=16), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inserted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("created_by", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(["table_id"], ["reference_tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attachment_id"], ["attachments.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_reference_table_import_jobs_table_id",
        "reference_table_import_jobs",
        ["table_id"],
    )

    op.create_table(
        "reference_table_rows",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("table_id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("values_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_actor", sa.String(length=16), nullable=False, server_default="user"),
        sa.Column("source_ref", sa.String(length=255), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("updated_by", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(["table_id"], ["reference_tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["import_job_id"],
            ["reference_table_import_jobs.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_reference_table_rows_table_id", "reference_table_rows", ["table_id"])
    op.create_index(
        "ix_reference_table_rows_import_job_id",
        "reference_table_rows",
        ["import_job_id"],
    )
    op.create_index(
        "ix_reference_table_rows_table_updated",
        "reference_table_rows",
        ["table_id", "updated_at"],
    )
    op.create_index(
        "ix_reference_table_rows_table_import_job",
        "reference_table_rows",
        ["table_id", "import_job_id"],
    )
