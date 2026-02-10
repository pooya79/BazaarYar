from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from server.features.agent.sandbox.sandbox_executor import execute_sandbox
from server.features.agent.sandbox.sandbox_schema import SandboxExecutionRequest, SandboxInputFile
from server.core.config import get_settings


class _FakeStdout:
    def __init__(self, lines: list[str]):
        self._lines = [f"{line}\n".encode("utf-8") for line in lines]

    async def readline(self) -> bytes:
        await asyncio.sleep(0)
        if not self._lines:
            return b""
        return self._lines.pop(0)


class _FakeStderr:
    def __init__(self, chunks: list[bytes]):
        self._chunks = chunks

    async def read(self, _size: int) -> bytes:
        await asyncio.sleep(0)
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _FakeProcess:
    def __init__(
        self,
        *,
        stdout_lines: list[str],
        stderr_chunks: list[bytes],
        returncode: int,
        wait_delay: float = 0,
    ):
        self.stdout = _FakeStdout(stdout_lines)
        self.stderr = _FakeStderr(stderr_chunks)
        self.returncode = returncode
        self._wait_delay = wait_delay
        self.killed = False

    async def wait(self) -> int:
        if self.killed:
            return self.returncode
        if self._wait_delay:
            await asyncio.sleep(self._wait_delay)
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9


@pytest.mark.asyncio
async def test_execute_sandbox_builds_secure_docker_command_and_reads_artifacts(
    monkeypatch,
    tmp_path: Path,
):
    source_file = tmp_path / "input.csv"
    source_file.write_text("a,b\n1,2\n", encoding="utf-8")

    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_docker_bin", "docker")
    monkeypatch.setattr(settings, "sandbox_docker_image", "sandbox:test")
    monkeypatch.setattr(settings, "sandbox_max_runtime_seconds", 30)
    monkeypatch.setattr(settings, "sandbox_max_memory_mb", 512)
    monkeypatch.setattr(settings, "sandbox_max_cpu", 0.5)
    monkeypatch.setattr(settings, "sandbox_max_artifacts", 8)
    monkeypatch.setattr(settings, "sandbox_max_artifact_bytes", 10_000)

    captured_cmd: list[str] = []
    captured_job_payload: dict[str, object] | None = None

    async def _fake_create_subprocess_exec(*cmd, **_kwargs):
        nonlocal captured_cmd, captured_job_payload
        captured_cmd = [str(item) for item in cmd]

        mount = captured_cmd[captured_cmd.index("-v") + 1]
        workspace = Path(mount.split(":", 1)[0])
        captured_job_payload = json.loads((workspace / "job.json").read_text(encoding="utf-8"))
        output_file = workspace / "output" / "plot.png"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(b"PNG")

        lines = [
            json.dumps(
                {
                    "type": "status",
                    "stage": "executing",
                    "message": "running",
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "stdout_tail": "done",
                    "stderr_tail": "",
                    "artifacts": [
                        {
                            "filename": "plot.png",
                            "rel_path": "plot.png",
                            "content_type": "image/png",
                        }
                    ],
                }
            ),
        ]
        return _FakeProcess(stdout_lines=lines, stderr_chunks=[], returncode=0)

    monkeypatch.setattr(
        "server.features.agent.sandbox.sandbox_executor.asyncio.create_subprocess_exec",
        _fake_create_subprocess_exec,
    )

    request = SandboxExecutionRequest(
        run_id="run-secure",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="a-1",
                filename="input.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            )
        ],
    )

    result = await execute_sandbox(request)

    assert result.status == "succeeded"
    assert len(result.artifacts) == 1
    assert result.artifacts[0].filename == "plot.png"
    assert result.stdout_tail == "done"
    assert result.input_files[0].attachment_id == "a-1"
    assert result.input_files[0].sandbox_filename == "01_input.csv"
    assert result.input_files[0].input_path == "/workspace/input/01_input.csv"

    assert captured_job_payload is not None
    input_files = captured_job_payload["input_files"]
    assert isinstance(input_files, list)
    assert input_files[0]["attachment_id"] == "a-1"
    assert input_files[0]["original_filename"] == "input.csv"
    assert input_files[0]["sandbox_filename"] == "01_input.csv"
    assert input_files[0]["content_type"] == "text/csv"
    assert input_files[0]["input_path"] == "/workspace/input/01_input.csv"

    assert "--network" in captured_cmd
    assert captured_cmd[captured_cmd.index("--network") + 1] == "none"
    assert "--read-only" in captured_cmd
    assert "--cap-drop" in captured_cmd
    assert captured_cmd[captured_cmd.index("--cap-drop") + 1] == "ALL"
    assert "--security-opt" in captured_cmd
    assert "no-new-privileges" in captured_cmd
    assert "--memory" in captured_cmd
    assert captured_cmd[captured_cmd.index("--memory") + 1] == "512m"
    assert "--cpus" in captured_cmd
    assert captured_cmd[captured_cmd.index("--cpus") + 1] == "0.5"


@pytest.mark.asyncio
async def test_execute_sandbox_times_out_and_kills_process(monkeypatch, tmp_path: Path):
    source_file = tmp_path / "input.csv"
    source_file.write_text("a\n1\n", encoding="utf-8")

    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_max_runtime_seconds", 1)
    monkeypatch.setattr(settings, "sandbox_max_memory_mb", 256)
    monkeypatch.setattr(settings, "sandbox_max_cpu", 1.0)

    process_ref: _FakeProcess | None = None

    async def _fake_create_subprocess_exec(*_cmd, **_kwargs):
        nonlocal process_ref
        process_ref = _FakeProcess(
            stdout_lines=[],
            stderr_chunks=[],
            returncode=0,
            wait_delay=60,
        )
        return process_ref

    monkeypatch.setattr(
        "server.features.agent.sandbox.sandbox_executor.asyncio.create_subprocess_exec",
        _fake_create_subprocess_exec,
    )

    request = SandboxExecutionRequest(
        run_id="run-timeout",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="a-1",
                filename="input.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            )
        ],
    )

    result = await execute_sandbox(request)

    assert result.status == "timeout"
    assert process_ref is not None and process_ref.killed is True


@pytest.mark.asyncio
async def test_execute_sandbox_rejects_oversized_artifact(monkeypatch, tmp_path: Path):
    source_file = tmp_path / "input.csv"
    source_file.write_text("a\n1\n", encoding="utf-8")

    settings = get_settings()
    monkeypatch.setattr(settings, "sandbox_max_runtime_seconds", 30)
    monkeypatch.setattr(settings, "sandbox_max_artifact_bytes", 2)

    async def _fake_create_subprocess_exec(*cmd, **_kwargs):
        mount = str(cmd[cmd.index("-v") + 1])
        workspace = Path(mount.split(":", 1)[0])
        output_file = workspace / "output" / "plot.png"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(b"TOO_BIG")

        lines = [
            json.dumps(
                {
                    "type": "result",
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "artifacts": [
                        {
                            "filename": "plot.png",
                            "rel_path": "plot.png",
                            "content_type": "image/png",
                        }
                    ],
                }
            )
        ]
        return _FakeProcess(stdout_lines=lines, stderr_chunks=[], returncode=0)

    monkeypatch.setattr(
        "server.features.agent.sandbox.sandbox_executor.asyncio.create_subprocess_exec",
        _fake_create_subprocess_exec,
    )

    request = SandboxExecutionRequest(
        run_id="run-limit",
        code="print('ok')",
        files=[
            SandboxInputFile(
                attachment_id="a-1",
                filename="input.csv",
                storage_path=str(source_file),
                content_type="text/csv",
            )
        ],
    )

    result = await execute_sandbox(request)

    assert result.status == "failed"
    assert "exceeds size limit" in (result.summary or "")
