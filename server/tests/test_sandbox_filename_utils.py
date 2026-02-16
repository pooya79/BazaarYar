from __future__ import annotations

from server.features.agent.sandbox.filename_utils import (
    allocate_sandbox_filename,
    next_sandbox_prefix_start,
    sanitize_sandbox_filename,
)


def test_sanitize_sandbox_filename_preserves_spaces_and_unicode() -> None:
    value = "campaign data \u65e5\u672c\u8a9e.csv"
    assert sanitize_sandbox_filename(value) == value


def test_sanitize_sandbox_filename_replaces_separators_and_control_chars() -> None:
    value = "a/b\\c\x00d\x1fe\x7ff.csv"
    assert sanitize_sandbox_filename(value) == "a_b_c_d_e_f.csv"


def test_sanitize_sandbox_filename_falls_back_for_empty_or_traversal_names() -> None:
    assert sanitize_sandbox_filename("") == "input"
    assert sanitize_sandbox_filename("   ") == "input"
    assert sanitize_sandbox_filename(".") == "input"
    assert sanitize_sandbox_filename("..") == "input"


def test_next_sandbox_prefix_start_uses_max_existing_prefix() -> None:
    assert next_sandbox_prefix_start({"campaign.csv", "01_campaign.csv", "9_misc.csv"}) == 10
    assert next_sandbox_prefix_start({"campaign.csv"}) == 1


def test_allocate_sandbox_filename_uses_exact_name_when_available() -> None:
    used_names: set[str] = set()
    target, next_prefix = allocate_sandbox_filename(
        "campaign data.csv",
        used_names=used_names,
        next_prefix=1,
    )
    assert target == "campaign data.csv"
    assert next_prefix == 1


def test_allocate_sandbox_filename_uses_prefixed_fallback_on_duplicate() -> None:
    used_names = {"campaign.csv"}
    target, next_prefix = allocate_sandbox_filename(
        "campaign.csv",
        used_names=used_names,
        next_prefix=1,
    )
    assert target == "01_campaign.csv"
    assert next_prefix == 2


def test_allocate_sandbox_filename_increments_when_fallback_name_is_taken() -> None:
    used_names = {"campaign.csv", "01_campaign.csv"}
    target, next_prefix = allocate_sandbox_filename(
        "campaign.csv",
        used_names=used_names,
        next_prefix=1,
    )
    assert target == "02_campaign.csv"
    assert next_prefix == 3
