from __future__ import annotations

import logging
from dataclasses import dataclass


@dataclass
class SanitizationStats:
    nul_removed: int = 0
    surrogates_replaced: int = 0
    newlines_normalized: int = 0
    changed: bool = False


def _compute_changed(stats: SanitizationStats) -> None:
    stats.changed = (
        stats.nul_removed > 0
        or stats.surrogates_replaced > 0
        or stats.newlines_normalized > 0
    )


def sanitize_text(
    value: str,
    *,
    strip: bool,
    normalize_newlines: bool = True,
) -> tuple[str, SanitizationStats]:
    stats = SanitizationStats()
    chars: list[str] = []
    index = 0
    length = len(value)

    while index < length:
        char = value[index]

        if char == "\x00":
            stats.nul_removed += 1
            index += 1
            continue

        codepoint = ord(char)
        if 0xD800 <= codepoint <= 0xDFFF:
            chars.append("\uFFFD")
            stats.surrogates_replaced += 1
            index += 1
            continue

        if normalize_newlines and char == "\r":
            next_char = value[index + 1] if index + 1 < length else ""
            chars.append("\n")
            stats.newlines_normalized += 1
            if next_char == "\n":
                index += 2
            else:
                index += 1
            continue

        chars.append(char)
        index += 1

    sanitized = "".join(chars)
    if strip:
        sanitized = sanitized.strip()

    _compute_changed(stats)
    return sanitized, stats


def sanitize_optional_text(
    value: str | None,
    *,
    strip: bool,
    normalize_newlines: bool = True,
) -> tuple[str | None, SanitizationStats]:
    if value is None:
        return None, SanitizationStats()
    sanitized, stats = sanitize_text(
        value,
        strip=strip,
        normalize_newlines=normalize_newlines,
    )
    return sanitized, stats


def log_sanitization_stats(
    logger: logging.Logger,
    *,
    location: str,
    stats: SanitizationStats,
) -> None:
    if not stats.changed:
        return
    logger.debug(
        (
            "Sanitized text write for %s "
            "(nul_removed=%d, surrogates_replaced=%d, newlines_normalized=%d)."
        ),
        location,
        stats.nul_removed,
        stats.surrogates_replaced,
        stats.newlines_normalized,
    )


__all__ = [
    "SanitizationStats",
    "log_sanitization_stats",
    "sanitize_optional_text",
    "sanitize_text",
]
