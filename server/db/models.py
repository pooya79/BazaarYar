from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
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
