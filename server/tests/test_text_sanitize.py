from __future__ import annotations

from server.features.shared.text_sanitize import (
    sanitize_optional_text,
    sanitize_text,
)


def test_sanitize_text_removes_nul_bytes():
    cleaned, stats = sanitize_text("ab\x00cd\x00", strip=False)
    assert cleaned == "abcd"
    assert stats.nul_removed == 2
    assert stats.surrogates_replaced == 0
    assert stats.newlines_normalized == 0
    assert stats.changed is True


def test_sanitize_text_replaces_surrogates():
    value = "ok\ud800\udfffdone"
    cleaned, stats = sanitize_text(value, strip=False)
    assert cleaned == "ok\ufffd\ufffddone"
    assert stats.nul_removed == 0
    assert stats.surrogates_replaced == 2
    assert stats.newlines_normalized == 0
    assert stats.changed is True


def test_sanitize_text_normalizes_crlf_and_cr():
    cleaned, stats = sanitize_text("a\r\nb\rc\n", strip=False)
    assert cleaned == "a\nb\nc\n"
    assert stats.newlines_normalized == 2
    assert stats.changed is True


def test_sanitize_text_strip_toggle():
    cleaned_keep, _ = sanitize_text("  x \n", strip=False)
    cleaned_strip, _ = sanitize_text("  x \n", strip=True)
    assert cleaned_keep == "  x \n"
    assert cleaned_strip == "x"


def test_sanitize_optional_text_handles_none():
    cleaned, stats = sanitize_optional_text(None, strip=True)
    assert cleaned is None
    assert stats.changed is False
    assert stats.nul_removed == 0
    assert stats.surrogates_replaced == 0
    assert stats.newlines_normalized == 0


def test_sanitize_text_stats_zero_when_unchanged():
    cleaned, stats = sanitize_text("plain text", strip=False)
    assert cleaned == "plain text"
    assert stats.changed is False
    assert stats.nul_removed == 0
    assert stats.surrogates_replaced == 0
    assert stats.newlines_normalized == 0
