## Python Sandbox Tool

The agent can run isolated Python analysis against uploaded files when enabled.

### Build the sandbox image

```bash
make sandbox-image
```

This builds `bazaaryar-python-sandbox:latest` from `infra/sandbox/Dockerfile`.

### Enable sandbox execution

Set these environment variables (for example in `.env`):

```bash
SANDBOX_TOOL_ENABLED=true
SANDBOX_DOCKER_IMAGE=bazaaryar-python-sandbox:latest
SANDBOX_DOCKER_BIN=docker
SANDBOX_MAX_RUNTIME_SECONDS=90
SANDBOX_MAX_MEMORY_MB=1024
SANDBOX_MAX_CPU=1.0
SANDBOX_MAX_ARTIFACTS=8
SANDBOX_MAX_ARTIFACT_BYTES=10485760
SANDBOX_MAX_CODE_CHARS=20000
```

### Runtime requirements

- Backend host must have access to a Docker daemon/socket.
- Sandbox containers run with:
  - `--network none`
  - `--read-only`
  - `--cap-drop ALL`
  - `--security-opt no-new-privileges`
  - CPU/memory/pid limits
- Plot outputs and generated files are persisted as standard agent attachments and are streamed back to the frontend as artifact metadata.
