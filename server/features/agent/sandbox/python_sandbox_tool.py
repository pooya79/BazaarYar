from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from langchain.tools import tool

from server.features.attachments import (
    load_attachments_for_ids,
    store_generated_artifact,
)
from server.features.agent.sandbox.event_bus import emit_sandbox_status, get_request_context
from server.features.agent.sandbox.sandbox_executor import execute_sandbox
from server.features.agent.sandbox.sandbox_schema import SandboxExecutionRequest, SandboxInputFile
from server.core.config import get_settings
from server.db.session import AsyncSessionLocal
from server.features.chat import save_uploaded_attachments


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True)


def _normalize_attachment_ids(raw: list[str] | None) -> list[str]:
    if raw is None:
        return []

    cleaned: list[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())
    return cleaned


@tool(
    "run_python_code",
    description=(
        "Run Python code in an isolated sandbox for data analysis and plotting. "
        "Sandbox globals: INPUT_DIR=/workspace/input, OUTPUT_DIR=/workspace/output, ATTACHMENTS, AVAILABLE_FILES, load_dataframe(). "
        "The sandbox process writes artifacts from /workspace/output (its working directory). "
        "Pass attachment_ids as a list of user attachment IDs when selecting specific files. "
        "Use ATTACHMENTS entries (attachment_id/original_filename/sandbox_filename/input_path) to map IDs to files. "
        "For plots, call plt.savefig('plot.png') or save files under OUTPUT_DIR so artifacts are returned. "
        "Available libraries include pandas, matplotlib, seaborn, numpy and openpyxl. "
        "Args: code, attachment_ids (optional list of attachment IDs), description (optional)."
    )
)
async def run_python_code(
    code: str,
    attachment_ids: list[str] | None = None,
    description: str | None = None,
) -> str:
    settings = get_settings()
    if not settings.sandbox_tool_enabled:
        return _json(
            {
                "status": "failed",
                "summary": "Sandbox tool is disabled.",
                "artifact_attachment_ids": [],
                "artifacts": [],
                "input_files": [],
                "stdout_tail": "",
                "stderr_tail": "",
            }
        )

    if len(code) > settings.sandbox_max_code_chars:
        return _json(
            {
                "status": "failed",
                "summary": (
                    f"Code length exceeds max of {settings.sandbox_max_code_chars} characters."
                ),
                "artifact_attachment_ids": [],
                "artifacts": [],
                "input_files": [],
                "stdout_tail": "",
                "stderr_tail": "",
            }
        )

    attachment_ids = _normalize_attachment_ids(attachment_ids)

    context = get_request_context()
    if not attachment_ids and context is not None:
        attachment_ids = list(context.latest_user_attachment_ids)

    run_id = str(uuid4())

    async def _status_callback(stage: str, message: str) -> None:
        await emit_sandbox_status(run_id=run_id, stage=stage, message=message)

    try:
        async with AsyncSessionLocal() as session:
            attachments = await load_attachments_for_ids(
                session,
                attachment_ids,
                allow_json_fallback=False,
            )
            sandbox_request = SandboxExecutionRequest(
                run_id=run_id,
                code=code,
                files=[
                    SandboxInputFile(
                        attachment_id=item.id,
                        filename=item.filename,
                        storage_path=item.storage_path,
                        content_type=item.content_type,
                    )
                    for item in attachments
                ],
            )
            result = await execute_sandbox(sandbox_request, on_status=_status_callback)

            stored_artifacts = []
            for artifact in result.artifacts:
                stored_artifacts.append(
                    store_generated_artifact(
                        filename=artifact.filename,
                        payload=artifact.payload,
                        content_type=artifact.content_type,
                    )
                )

            if stored_artifacts:
                await save_uploaded_attachments(session, stored_artifacts)

            artifact_ids = [item.id for item in stored_artifacts]
            artifact_rows = [
                {
                    "id": item.id,
                    "filename": item.filename,
                    "content_type": item.content_type,
                    "media_type": item.media_type,
                    "size_bytes": item.size_bytes,
                }
                for item in stored_artifacts
            ]
            input_files = [item.model_dump(mode="json") for item in result.input_files]

            summary_suffix = f" ({description})" if description else ""
            summary = result.summary + summary_suffix
            return _json(
                {
                    "status": result.status,
                    "summary": summary,
                    "artifact_attachment_ids": artifact_ids,
                    "artifacts": artifact_rows,
                    "input_files": input_files,
                    "stdout_tail": result.stdout_tail,
                    "stderr_tail": result.stderr_tail,
                    "run_id": run_id,
                }
            )
    except Exception as exc:
        await emit_sandbox_status(run_id=run_id, stage="failed", message=str(exc))
        return _json(
            {
                "status": "failed",
                "summary": f"Sandbox execution failed: {exc}",
                "artifact_attachment_ids": [],
                "artifacts": [],
                "input_files": [],
                "stdout_tail": "",
                "stderr_tail": "",
                "run_id": run_id,
            }
        )


PYTHON_SANDBOX_TOOLS = [run_python_code]
