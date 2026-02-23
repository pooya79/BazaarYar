from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from server.features.prompts import service as prompts_service
from server.features.prompts.errors import PromptValidationError


class _DummySession:
    pass


def _prompt_row(
    *,
    name: str = "campaign-launch",
    description: str = "",
    prompt: str = "Build a plan",
):
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        description=description,
        prompt=prompt,
        created_at=now,
        updated_at=now,
    )


def test_create_prompt_normalizes_name_and_sanitizes_fields(monkeypatch):
    captured: dict[str, object] = {}

    async def _fake_get_prompt_by_name(_session, *, name, exclude_prompt_id=None):
        _ = exclude_prompt_id
        captured["checked_name"] = name
        return None

    async def _fake_create_prompt(_session, *, name, description, prompt):
        captured["name"] = name
        captured["description"] = description
        captured["prompt"] = prompt
        return _prompt_row(name=name, description=description, prompt=prompt)

    monkeypatch.setattr(
        prompts_service.repo,
        "get_prompt_by_name",
        _fake_get_prompt_by_name,
    )
    monkeypatch.setattr(prompts_service.repo, "create_prompt", _fake_create_prompt)

    result = asyncio.run(
        prompts_service.create_prompt(
            _DummySession(),
            name="  \\Campaign-Plan  ",
            description="  desc\x00\ud800  ",
            prompt="  body\r\nline\x00\ud800  ",
        )
    )

    assert captured["checked_name"] == "campaign-plan"
    assert captured["name"] == "campaign-plan"
    assert captured["description"] == "desc\ufffd"
    assert captured["prompt"] == "body\nline\ufffd"
    assert result.name == "campaign-plan"


def test_create_prompt_rejects_invalid_input():
    with pytest.raises(PromptValidationError):
        asyncio.run(
            prompts_service.create_prompt(
                _DummySession(),
                name="",
                description="",
                prompt="ok",
            )
        )

    with pytest.raises(PromptValidationError):
        asyncio.run(
            prompts_service.create_prompt(
                _DummySession(),
                name="INVALID NAME",
                description="",
                prompt="ok",
            )
        )

    with pytest.raises(PromptValidationError):
        asyncio.run(
            prompts_service.create_prompt(
                _DummySession(),
                name="ab",
                description="",
                prompt="",
            )
        )


def test_create_prompt_rejects_duplicate_name(monkeypatch):
    async def _existing(_session, *, name, exclude_prompt_id=None):
        _ = (name, exclude_prompt_id)
        return _prompt_row(name="campaign-launch")

    monkeypatch.setattr(prompts_service.repo, "get_prompt_by_name", _existing)

    with pytest.raises(PromptValidationError):
        asyncio.run(
            prompts_service.create_prompt(
                _DummySession(),
                name="campaign-launch",
                description="",
                prompt="Build a plan",
            )
        )


def test_create_prompt_maps_unique_constraint_violation(monkeypatch):
    async def _no_existing(_session, *, name, exclude_prompt_id=None):
        _ = (name, exclude_prompt_id)
        return None

    async def _raise_integrity(_session, *, name, description, prompt):
        _ = (name, description, prompt)
        raise IntegrityError("insert", {}, Exception("uq_prompt_templates_name_lower"))

    monkeypatch.setattr(prompts_service.repo, "get_prompt_by_name", _no_existing)
    monkeypatch.setattr(prompts_service.repo, "create_prompt", _raise_integrity)

    with pytest.raises(PromptValidationError):
        asyncio.run(
            prompts_service.create_prompt(
                _DummySession(),
                name="campaign-launch",
                description="",
                prompt="Build a plan",
            )
        )


def test_update_prompt_normalizes_name_and_rejects_duplicate(monkeypatch):
    row = _prompt_row(name="old-name")

    async def _get_prompt(_session, *, prompt_id):
        _ = prompt_id
        return row

    async def _get_prompt_by_name(_session, *, name, exclude_prompt_id=None):
        _ = (name, exclude_prompt_id)
        return _prompt_row(name="campaign-plan")

    monkeypatch.setattr(prompts_service.repo, "get_prompt", _get_prompt)
    monkeypatch.setattr(prompts_service.repo, "get_prompt_by_name", _get_prompt_by_name)

    with pytest.raises(PromptValidationError):
        asyncio.run(
            prompts_service.update_prompt(
                _DummySession(),
                prompt_id=str(row.id),
                name="\\campaign-plan",
            )
        )

