from __future__ import annotations

import logging

from server.features.shared.text_sanitize import log_sanitization_stats, sanitize_text

logger = logging.getLogger(__name__)


def sanitize_message_content(
    content: str,
    *,
    strip: bool,
    location: str = "chat.message_content",
) -> str:
    cleaned, stats = sanitize_text(content, strip=strip)
    log_sanitization_stats(logger, location=location, stats=stats)
    return cleaned


def sanitize_message_suffix(
    content_suffix: str,
    *,
    location: str = "chat.message_suffix",
) -> str:
    cleaned, stats = sanitize_text(content_suffix, strip=False)
    log_sanitization_stats(logger, location=location, stats=stats)
    return cleaned


__all__ = [
    "sanitize_message_content",
    "sanitize_message_suffix",
]
