from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from server.db.base import Base


class AgentModelSettings(Base):
    __tablename__ = "agent_model_settings"
    __table_args__ = (
        UniqueConstraint("singleton_key", name="uq_agent_model_settings_singleton_key"),
        CheckConstraint("singleton_key = 'global'", name="ck_agent_model_settings_singleton_key_global"),
        CheckConstraint("temperature >= 0 AND temperature <= 2", name="ck_agent_model_settings_temperature"),
        CheckConstraint(
            "reasoning_effort IN ('low', 'medium', 'high')",
            name="ck_agent_model_settings_reasoning_effort",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    singleton_key: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="global",
        server_default="global",
    )
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    base_url: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    reasoning_effort: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="medium",
        server_default="medium",
    )
    reasoning_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AgentCompanyProfile(Base):
    __tablename__ = "agent_company_profile"
    __table_args__ = (
        UniqueConstraint("singleton_key", name="uq_agent_company_profile_singleton_key"),
        CheckConstraint("singleton_key = 'global'", name="ck_agent_company_profile_singleton_key_global"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    singleton_key: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="global",
        server_default="global",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="", server_default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
