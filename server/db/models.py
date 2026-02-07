from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("ix_conversations_starred_updated_at", "starred", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starred: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by=lambda: (Message.created_at, Message.id),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    tokenizer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    message_kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="normal",
        server_default="normal",
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    attachment_links: Mapped[list[MessageAttachment]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageAttachment.position",
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    preview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    message_links: Mapped[list[MessageAttachment]] = relationship(
        back_populates="attachment",
        cascade="all, delete-orphan",
    )


class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    attachment_id: Mapped[UUID] = mapped_column(
        ForeignKey("attachments.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    message: Mapped[Message] = relationship(back_populates="attachment_links")
    attachment: Mapped[Attachment] = relationship(back_populates="message_links")


class ReferenceTable(Base):
    __tablename__ = "reference_tables"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(63), nullable=False, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    row_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    columns: Mapped[list[ReferenceTableColumn]] = relationship(
        back_populates="table",
        cascade="all, delete-orphan",
        order_by="ReferenceTableColumn.position",
    )
    rows: Mapped[list[ReferenceTableRow]] = relationship(
        back_populates="table",
        cascade="all, delete-orphan",
        order_by=lambda: (ReferenceTableRow.created_at, ReferenceTableRow.id),
    )
    import_jobs: Mapped[list[ReferenceTableImportJob]] = relationship(
        back_populates="table",
        cascade="all, delete-orphan",
        order_by=lambda: (ReferenceTableImportJob.created_at, ReferenceTableImportJob.id),
    )


class ReferenceTableColumn(Base):
    __tablename__ = "reference_table_columns"
    __table_args__ = (
        UniqueConstraint("table_id", "name", name="uq_reference_table_columns_table_name"),
        UniqueConstraint("table_id", "position", name="uq_reference_table_columns_table_position"),
        Index(
            "ix_reference_table_columns_table_position",
            "table_id",
            "position",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    table_id: Mapped[UUID] = mapped_column(
        ForeignKey("reference_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(63), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    nullable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    semantic_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    constraints_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    default_json: Mapped[dict | int | float | str | bool | list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    table: Mapped[ReferenceTable] = relationship(back_populates="columns")


class ReferenceTableImportJob(Base):
    __tablename__ = "reference_table_import_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    table_id: Mapped[UUID] = mapped_column(
        ForeignKey("reference_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attachment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    source_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    inserted_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    updated_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    deleted_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    errors_json: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    table: Mapped[ReferenceTable] = relationship(back_populates="import_jobs")
    attachment: Mapped[Attachment | None] = relationship()
    rows: Mapped[list[ReferenceTableRow]] = relationship(
        back_populates="import_job",
        order_by=lambda: (ReferenceTableRow.created_at, ReferenceTableRow.id),
    )


class ReferenceTableRow(Base):
    __tablename__ = "reference_table_rows"
    __table_args__ = (
        Index("ix_reference_table_rows_table_updated", "table_id", "updated_at"),
        Index("ix_reference_table_rows_table_import_job", "table_id", "import_job_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    table_id: Mapped[UUID] = mapped_column(
        ForeignKey("reference_tables.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    import_job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reference_table_import_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    values_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_actor: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="user",
        server_default="user",
    )
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    table: Mapped[ReferenceTable] = relationship(back_populates="rows")
    import_job: Mapped[ReferenceTableImportJob | None] = relationship(back_populates="rows")
