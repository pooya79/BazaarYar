from __future__ import annotations

import re
from collections.abc import Iterable


def sanitize_sandbox_filename(value: str) -> str:
    """Return a sandbox-safe filename while preserving readable names."""
    cleaned_chars: list[str] = []
    for char in value:
        codepoint = ord(char)
        if char in {"/", "\\"} or codepoint < 32 or codepoint == 127:
            cleaned_chars.append("_")
            continue
        cleaned_chars.append(char)

    cleaned = "".join(cleaned_chars)
    if cleaned in {"", ".", ".."} or not cleaned.strip():
        return "input"
    return cleaned


_PREFIXED_SANDBOX_NAME_RE = re.compile(r"^(\d+)_")


def next_sandbox_prefix_start(used_names: Iterable[str]) -> int:
    max_seen = 0
    for name in used_names:
        match = _PREFIXED_SANDBOX_NAME_RE.match(name)
        if match is None:
            continue
        try:
            candidate = int(match.group(1))
        except ValueError:
            continue
        if candidate > max_seen:
            max_seen = candidate
    return max_seen + 1 if max_seen > 0 else 1


def allocate_sandbox_filename(
    filename: str,
    *,
    used_names: set[str],
    next_prefix: int,
) -> tuple[str, int]:
    safe_name = sanitize_sandbox_filename(filename)
    if safe_name not in used_names:
        return safe_name, next_prefix

    prefix = max(1, next_prefix)
    while True:
        candidate = f"{prefix:02d}_{safe_name}"
        prefix += 1
        if candidate not in used_names:
            return candidate, prefix
