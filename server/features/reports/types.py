from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1, max_length=20_000)
    preview_text: str | None = Field(default=None, max_length=180)
    enabled_for_agent: bool = True
    source_conversation_id: str | None = None


class ReportUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1, max_length=20_000)
    preview_text: str | None = Field(default=None, max_length=180)
    enabled_for_agent: bool | None = None


class ReportSummary(BaseModel):
    id: str
    title: str
    preview_text: str
    source_conversation_id: str | None
    enabled_for_agent: bool
    created_at: datetime
    updated_at: datetime


class ReportDetail(ReportSummary):
    content: str
