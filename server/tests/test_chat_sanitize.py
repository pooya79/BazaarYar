from __future__ import annotations

from server.features.chat.sanitize import (
    sanitize_message_content,
    sanitize_message_suffix,
)


def test_sanitize_message_content_strips_nul_and_whitespace():
    value = "\x00  hello\x00 world  \x00"
    assert sanitize_message_content(value, strip=True) == "hello world"


def test_sanitize_message_content_preserves_whitespace_for_reasoning():
    value = "  line 1\x00\nline 2  "
    assert sanitize_message_content(value, strip=False) == "  line 1\nline 2  "


def test_sanitize_message_content_replaces_surrogates():
    value = "msg:\ud800done"
    assert sanitize_message_content(value, strip=False) == "msg:\ufffddone"


def test_sanitize_message_content_normalizes_newlines():
    value = "line1\r\nline2\rline3"
    assert sanitize_message_content(value, strip=False) == "line1\nline2\nline3"


def test_sanitize_message_suffix_strips_nul_and_normalizes_newlines_and_surrogates():
    value = "\x00suffix\ud800\r\nmore"
    assert sanitize_message_suffix(value) == "suffix\ufffd\nmore"
