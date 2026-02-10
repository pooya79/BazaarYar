from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path
from typing import Awaitable, Callable

from server.features.attachments import resolve_storage_path
from server.features.agent.sandbox.sandbox_schema import (
    SandboxArtifact,
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxInputFileMapping,
    SandboxRunnerArtifact,
)
from server.core.config import get_settings

_STATUS_CALLBACK = Callable[[str, str], Awaitable[None]]
_FILENAME_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.-]+")
_STDERR_TAIL_LIMIT = 8_000


def _sandbox_runs_root() -> Path:
    root = resolve_storage_path("server/storage/sandbox_runs")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sanitize_filename(value: str) -> str:
    cleaned = _FILENAME_TOKEN_RE.sub("_", value).strip("._")
    return cleaned or "input"


def _trim_tail(value: str, *, limit: int = _STDERR_TAIL_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return f"...{value[-limit:]}"


def _docker_command(workspace_dir: Path) -> list[str]:
    settings = get_settings()
    return [
        settings.sandbox_docker_bin,
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "256",
        "--memory",
        f"{settings.sandbox_max_memory_mb}m",
        "--cpus",
        str(settings.sandbox_max_cpu),
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "-v",
        f"{workspace_dir}:/workspace:rw",
        "--workdir",
        "/workspace/output",
        settings.sandbox_docker_image,
    ]


async def _emit_status(callback: _STATUS_CALLBACK | None, stage: str, message: str) -> None:
    if callback is None:
        return
    await callback(stage, message)


def _prepare_workspace(
    request: SandboxExecutionRequest,
) -> tuple[Path, Path, Path, list[SandboxInputFileMapping]]:
    workspace_dir = _sandbox_runs_root() / request.run_id
    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)
    input_dir = workspace_dir / "input"
    output_dir = workspace_dir / "output"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Sandbox containers may run under a uid/gid that differs from host ownership.
    # Relax directory permissions so the container process can always read/write these paths.
    workspace_dir.chmod(0o777)
    input_dir.chmod(0o777)
    output_dir.chmod(0o777)

    input_files: list[SandboxInputFileMapping] = []
    for index, item in enumerate(request.files, start=1):
        source = resolve_storage_path(item.storage_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Attachment '{item.attachment_id}' file does not exist.")

        safe_name = _sanitize_filename(item.filename)
        target_name = f"{index:02d}_{safe_name}"
        target = input_dir / target_name
        shutil.copyfile(source, target)
        target.chmod(0o444)
        input_files.append(
            SandboxInputFileMapping(
                attachment_id=item.attachment_id,
                original_filename=item.filename,
                sandbox_filename=target_name,
                content_type=item.content_type,
                input_path=f"/workspace/input/{target_name}",
            )
        )

    job_payload = {
        "code": request.code,
        "files": [item.sandbox_filename for item in input_files],
        "input_files": [item.model_dump(mode="json") for item in input_files],
    }
    (workspace_dir / "job.json").write_text(json.dumps(job_payload, ensure_ascii=True), encoding="utf-8")
    return workspace_dir, input_dir, output_dir, input_files


def _validate_and_load_artifacts(
    *,
    output_dir: Path,
    artifacts_payload: list[dict[str, str]],
) -> list[SandboxArtifact]:
    settings = get_settings()
    if len(artifacts_payload) > settings.sandbox_max_artifacts:
        raise ValueError(
            f"Sandbox produced {len(artifacts_payload)} artifacts, exceeding limit {settings.sandbox_max_artifacts}."
        )

    output_dir_resolved = output_dir.resolve()
    artifacts: list[SandboxArtifact] = []
    for raw_item in artifacts_payload:
        item = SandboxRunnerArtifact.model_validate(raw_item)
        path = (output_dir / item.rel_path).resolve()
        if output_dir_resolved not in path.parents and path != output_dir_resolved:
            raise ValueError(f"Artifact path '{item.rel_path}' escapes output directory.")
        if not path.exists() or not path.is_file():
            raise ValueError(f"Artifact file '{item.rel_path}' not found.")

        size = path.stat().st_size
        if size > settings.sandbox_max_artifact_bytes:
            raise ValueError(
                f"Artifact '{item.filename}' exceeds size limit of {settings.sandbox_max_artifact_bytes} bytes."
            )

        artifacts.append(
            SandboxArtifact(
                filename=item.filename,
                content_type=item.content_type,
                size_bytes=size,
                payload=path.read_bytes(),
            )
        )

    return artifacts


async def execute_sandbox(
    request: SandboxExecutionRequest,
    *,
    on_status: _STATUS_CALLBACK | None = None,
) -> SandboxExecutionResult:
    settings = get_settings()
    workspace_dir: Path | None = None
    output_dir: Path | None = None
    input_files: list[SandboxInputFileMapping] = []

    await _emit_status(on_status, "preparing", "Preparing sandbox workspace.")
    try:
        workspace_dir, _input_dir, output_dir, input_files = _prepare_workspace(request)

        command = _docker_command(workspace_dir)
        await _emit_status(on_status, "starting", "Starting sandbox container.")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        runner_result: dict[str, object] | None = None
        runner_error_message: str | None = None
        runner_traceback_tail: str = ""
        stderr_accumulator = ""

        async def _read_stdout() -> None:
            nonlocal runner_result, runner_error_message, runner_traceback_tail
            if process.stdout is None:
                return

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if not decoded:
                    continue
                try:
                    payload = json.loads(decoded)
                except Exception:
                    continue

                event_type = payload.get("type")
                if event_type == "status":
                    stage = str(payload.get("stage") or "running")
                    message = str(payload.get("message") or "Sandbox update")
                    await _emit_status(on_status, stage, message)
                elif event_type == "error":
                    runner_error_message = str(payload.get("message") or "Sandbox execution failed.")
                    runner_traceback_tail = str(payload.get("traceback_tail") or "")
                elif event_type == "result":
                    runner_result = payload

        async def _read_stderr() -> None:
            nonlocal stderr_accumulator
            if process.stderr is None:
                return
            while True:
                chunk = await process.stderr.read(1024)
                if not chunk:
                    break
                stderr_accumulator = _trim_tail(stderr_accumulator + chunk.decode("utf-8", errors="replace"))

        stdout_task = asyncio.create_task(_read_stdout())
        stderr_task = asyncio.create_task(_read_stderr())

        timed_out = False
        try:
            await asyncio.wait_for(process.wait(), timeout=settings.sandbox_max_runtime_seconds)
        except asyncio.TimeoutError:
            timed_out = True
            process.kill()
            await process.wait()

        await stdout_task
        await stderr_task

        if timed_out:
            await _emit_status(on_status, "failed", "Sandbox execution timed out.")
            return SandboxExecutionResult(
                run_id=request.run_id,
                status="timeout",
                summary="Sandbox execution timed out.",
                stderr_tail=stderr_accumulator,
                input_files=input_files,
                error_message="Sandbox execution timed out.",
            )

        if runner_error_message is not None:
            merged_stderr = _trim_tail(
                "\n".join(item for item in [stderr_accumulator, runner_traceback_tail] if item)
            )
            await _emit_status(on_status, "failed", runner_error_message)
            return SandboxExecutionResult(
                run_id=request.run_id,
                status="failed",
                summary=runner_error_message,
                stderr_tail=merged_stderr,
                input_files=input_files,
                error_message=runner_error_message,
            )

        if process.returncode != 0:
            message = f"Sandbox process exited with code {process.returncode}."
            await _emit_status(on_status, "failed", message)
            return SandboxExecutionResult(
                run_id=request.run_id,
                status="failed",
                summary=message,
                stderr_tail=stderr_accumulator,
                input_files=input_files,
                error_message=message,
            )

        if runner_result is None:
            message = "Sandbox did not return a result payload."
            await _emit_status(on_status, "failed", message)
            return SandboxExecutionResult(
                run_id=request.run_id,
                status="failed",
                summary=message,
                stderr_tail=stderr_accumulator,
                input_files=input_files,
                error_message=message,
            )

        artifacts_payload = runner_result.get("artifacts")
        if not isinstance(artifacts_payload, list):
            artifacts_payload = []

        if output_dir is None:
            raise RuntimeError("Sandbox output directory was not initialized.")

        try:
            artifacts = _validate_and_load_artifacts(
                output_dir=output_dir,
                artifacts_payload=[item for item in artifacts_payload if isinstance(item, dict)],
            )
        except Exception as exc:
            message = str(exc)
            await _emit_status(on_status, "failed", message)
            return SandboxExecutionResult(
                run_id=request.run_id,
                status="failed",
                summary=message,
                stderr_tail=stderr_accumulator,
                input_files=input_files,
                error_message=message,
            )

        stdout_tail = str(runner_result.get("stdout_tail") or "")
        stderr_tail = _trim_tail(
            "\n".join(
                part
                for part in [
                    str(runner_result.get("stderr_tail") or ""),
                    stderr_accumulator,
                ]
                if part
            )
        )
        await _emit_status(on_status, "completed", "Sandbox execution completed.")
        return SandboxExecutionResult(
            run_id=request.run_id,
            status="succeeded",
            summary="Sandbox execution completed.",
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            input_files=input_files,
            artifacts=artifacts,
        )
    finally:
        if workspace_dir is not None:
            shutil.rmtree(workspace_dir, ignore_errors=True)
