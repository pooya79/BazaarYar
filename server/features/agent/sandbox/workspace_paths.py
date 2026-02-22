from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Literal

from server.core.config import get_settings

logger = logging.getLogger(__name__)
_FALLBACK_WARNED_FOR: set[tuple[str, str]] = set()


def _fallback_workspace_root() -> Path:
    uid = os.getuid() if hasattr(os, "getuid") else "user"
    return Path(f"/tmp/bazaaryar-sandbox-{uid}")


def _is_writable_directory(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.W_OK | os.X_OK)


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise NotADirectoryError(f"Sandbox path '{path}' is not a directory.")
    try:
        path.chmod(0o777)
    except PermissionError:
        # Host path may be root-owned in mixed prod/dev setups.
        pass


def _raise_unwritable_root_error(path: Path) -> None:
    raise PermissionError(
        "Sandbox workspace root is not writable/executable: "
        f"'{path}'. Fix directory ownership/permissions or set SANDBOX_WORKSPACE_ROOT "
        "to an absolute writable path."
    )


def _warn_fallback_once(configured: Path, fallback: Path, *, reason: str) -> None:
    key = (str(configured), str(fallback))
    if key in _FALLBACK_WARNED_FOR:
        return
    _FALLBACK_WARNED_FOR.add(key)
    logger.warning(
        "Configured sandbox workspace root '%s' is not usable (%s). Falling back to '%s' for this process.",
        configured,
        reason,
        fallback,
    )


def _prepare_root(path: Path) -> bool:
    _ensure_directory(path)
    return _is_writable_directory(path)


def get_effective_workspace_root() -> Path:
    settings = get_settings()
    configured_root = Path(settings.sandbox_workspace_root)
    is_production = settings.environment.lower() == "production"

    try:
        if _prepare_root(configured_root):
            return configured_root
        configured_issue = "not writable/executable"
    except Exception as exc:
        configured_issue = str(exc)
        if is_production:
            _raise_unwritable_root_error(configured_root)

    if is_production:
        _raise_unwritable_root_error(configured_root)

    fallback_root = _fallback_workspace_root()
    try:
        if not _prepare_root(fallback_root):
            _raise_unwritable_root_error(fallback_root)
    except Exception as exc:
        raise PermissionError(
            "Configured sandbox workspace root is unusable and fallback root also failed. "
            f"configured='{configured_root}', fallback='{fallback_root}', reason='{exc}'"
        ) from exc

    _warn_fallback_once(configured_root, fallback_root, reason=configured_issue)
    return fallback_root


def ensure_workspace_subdir(name: Literal["runs", "sessions"]) -> Path:
    root = get_effective_workspace_root()
    subdir = root / name
    try:
        _ensure_directory(subdir)
    except Exception as exc:
        raise PermissionError(
            f"Sandbox workspace subdirectory '{subdir}' is not usable: {exc}"
        ) from exc
    if not _is_writable_directory(subdir):
        raise PermissionError(f"Sandbox workspace subdirectory is not writable/executable: '{subdir}'.")
    return subdir
