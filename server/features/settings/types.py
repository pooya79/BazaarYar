from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReasoningEffort = Literal["low", "medium", "high"]
ModelSettingsSource = Literal["database", "environment_defaults"]
CompanyProfileSource = Literal["database", "defaults"]
ToolSettingsSource = Literal["database", "defaults"]


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


@dataclass(frozen=True)
class ToolSettingsResolved:
    tool_overrides: dict[str, bool]
    source: ToolSettingsSource


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


class ToolCatalogTool(BaseModel):
    key: str
    label: str
    description: str
    default_enabled: bool
    available: bool
    unavailable_reason: str | None = None
    enabled: bool


class ToolCatalogGroup(BaseModel):
    key: str
    label: str
    enabled: bool
    tools: list[ToolCatalogTool]


class ToolSettingsResponse(BaseModel):
    groups: list[ToolCatalogGroup]
    tool_overrides: dict[str, bool]
    source: ToolSettingsSource


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


class ToolSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_overrides: dict[str, bool] = Field(default_factory=dict)
