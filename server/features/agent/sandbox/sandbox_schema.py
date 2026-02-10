from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SandboxRunStatus = Literal["succeeded", "failed", "timeout"]


class SandboxInputFile(BaseModel):
    attachment_id: str
    filename: str
    storage_path: str
    content_type: str


class SandboxInputFileMapping(BaseModel):
    attachment_id: str
    original_filename: str
    sandbox_filename: str
    content_type: str
    input_path: str


class SandboxRunnerArtifact(BaseModel):
    filename: str
    rel_path: str
    content_type: str


class SandboxArtifact(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    payload: bytes


class SandboxStatusEventPayload(BaseModel):
    run_id: str
    stage: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SandboxExecutionRequest(BaseModel):
    run_id: str
    code: str
    files: list[SandboxInputFile]


class SandboxExecutionResult(BaseModel):
    run_id: str
    status: SandboxRunStatus
    summary: str
    stdout_tail: str = ""
    stderr_tail: str = ""
    input_files: list[SandboxInputFileMapping] = Field(default_factory=list)
    artifacts: list[SandboxArtifact] = Field(default_factory=list)
    error_message: str | None = None
