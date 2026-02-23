from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PromptCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=40)
    description: str = Field(default="", max_length=180)
    prompt: str = Field(min_length=1, max_length=20_000)


class PromptUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=180)
    prompt: str | None = Field(default=None, min_length=1, max_length=20_000)


class PromptSummary(BaseModel):
    id: str
    name: str
    description: str
    prompt: str
    created_at: datetime
    updated_at: datetime


class PromptDetail(PromptSummary):
    pass

