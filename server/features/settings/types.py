from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReasoningEffort = Literal["low", "medium", "high"]
ModelSettingsSource = Literal["database", "environment_defaults"]
CompanyProfileSource = Literal["database", "defaults"]


@dataclass(frozen=True)
class ModelSettingsResolved:
    model_name: str
    api_key: str
    base_url: str
    temperature: float
    reasoning_effort: ReasoningEffort
    reasoning_enabled: bool
    source: ModelSettingsSource


@dataclass(frozen=True)
class CompanyProfileResolved:
    name: str
    description: str
    enabled: bool
    source: CompanyProfileSource


class ModelSettingsResponse(BaseModel):
    model_name: str
    base_url: str
    temperature: float
    reasoning_effort: ReasoningEffort
    reasoning_enabled: bool
    has_api_key: bool
    api_key_preview: str | None
    source: ModelSettingsSource


class CompanyProfileResponse(BaseModel):
    name: str
    description: str
    enabled: bool
    source: CompanyProfileSource


class ModelSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    reasoning_effort: ReasoningEffort | None = None
    reasoning_enabled: bool | None = None


class CompanyProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    enabled: bool | None = None
