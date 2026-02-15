from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

from server.features.settings.types import (
    CompanyProfilePatch,
    ModelSettingsPatch,
    ModelSettingsResolved,
)

settings_service = importlib.import_module("server.features.settings.service")


class _DummySession:
    pass


def _fake_env_settings(**overrides):
    base = {
        "openailike_model": "gpt-4.1-mini",
        "openailike_api_key": "env-key",
        "openailike_base_url": "",
        "openailike_temperature": 1.0,
        "openailike_reasoning_effort": "medium",
        "openailike_reasoning_enabled": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_default_model_settings_from_env(monkeypatch):
    monkeypatch.setattr(
        settings_service,
        "get_settings",
        lambda: _fake_env_settings(openailike_model="moonshotai/kimi-k2.5"),
    )

    resolved = settings_service.default_model_settings_from_env()

    assert resolved.model_name == "moonshotai/kimi-k2.5"
    assert resolved.temperature == 1.0
    assert resolved.reasoning_effort == "medium"
    assert resolved.reasoning_enabled is True
    assert resolved.source == "environment_defaults"


def test_resolve_effective_model_settings_prefers_database_row(monkeypatch):
    async def _fake_get_global(_session):
        return SimpleNamespace(
            model_name="openai/gpt-5-mini",
            api_key="db-key",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.4,
            reasoning_effort="high",
            reasoning_enabled=False,
        )

    monkeypatch.setattr(settings_service.repo, "get_global_model_settings", _fake_get_global)

    resolved = asyncio.run(settings_service.resolve_effective_model_settings(_DummySession()))

    assert resolved.model_name == "openai/gpt-5-mini"
    assert resolved.api_key == "db-key"
    assert resolved.base_url == "https://openrouter.ai/api/v1"
    assert resolved.temperature == 0.4
    assert resolved.reasoning_effort == "high"
    assert resolved.reasoning_enabled is False
    assert resolved.source == "database"


def test_patch_model_settings_merges_defaults_when_row_absent(monkeypatch):
    monkeypatch.setattr(
        settings_service,
        "get_settings",
        lambda: _fake_env_settings(openailike_api_key="env-default-key"),
    )

    async def _fake_get_global(_session):
        return None

    captured: dict[str, object] = {}

    async def _fake_upsert(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(settings_service.repo, "get_global_model_settings", _fake_get_global)
    monkeypatch.setattr(settings_service.repo, "upsert_global_model_settings", _fake_upsert)

    patch = ModelSettingsPatch(temperature=0.25, reasoning_effort="low")
    resolved = asyncio.run(settings_service.patch_model_settings(_DummySession(), patch))

    assert captured["model_name"] == "gpt-4.1-mini"
    assert captured["api_key"] == "env-default-key"
    assert captured["base_url"] == ""
    assert captured["temperature"] == 0.25
    assert captured["reasoning_effort"] == "low"
    assert captured["reasoning_enabled"] is True
    assert resolved.source == "database"


def test_to_model_settings_response_masks_api_key():
    resolved = ModelSettingsResolved(
        model_name="gpt-4.1-mini",
        api_key="sk-test-secret",
        base_url="",
        temperature=1.0,
        reasoning_effort="medium",
        reasoning_enabled=True,
        source="database",
    )

    response = settings_service.to_model_settings_response(resolved)

    assert response.has_api_key is True
    assert response.api_key_preview == "sk-t...cret"


def test_resolve_effective_company_profile_defaults_when_row_missing(monkeypatch):
    async def _fake_get_global(_session):
        return None

    monkeypatch.setattr(settings_service.repo, "get_global_company_profile", _fake_get_global)

    resolved = asyncio.run(settings_service.resolve_effective_company_profile(_DummySession()))

    assert resolved.name == ""
    assert resolved.description == ""
    assert resolved.enabled is True
    assert resolved.source == "defaults"


def test_patch_company_profile_trims_and_merges_defaults_when_row_absent(monkeypatch):
    async def _fake_get_global(_session):
        return None

    captured: dict[str, object] = {}

    async def _fake_upsert(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(settings_service.repo, "get_global_company_profile", _fake_get_global)
    monkeypatch.setattr(settings_service.repo, "upsert_global_company_profile", _fake_upsert)

    patch = CompanyProfilePatch(name="  Acme Inc  ", description="  B2B analytics  ", enabled=False)
    resolved = asyncio.run(settings_service.patch_company_profile(_DummySession(), patch))

    assert captured["name"] == "Acme Inc"
    assert captured["description"] == "B2B analytics"
    assert captured["enabled"] is False
    assert resolved.source == "database"


def test_patch_company_profile_noop_returns_current(monkeypatch):
    async def _fake_get_global(_session):
        return SimpleNamespace(
            name="Current Co",
            description="Current desc",
            enabled=False,
        )

    monkeypatch.setattr(settings_service.repo, "get_global_company_profile", _fake_get_global)

    resolved = asyncio.run(
        settings_service.patch_company_profile(_DummySession(), CompanyProfilePatch())
    )

    assert resolved.name == "Current Co"
    assert resolved.description == "Current desc"
    assert resolved.enabled is False
    assert resolved.source == "database"


def test_reset_company_profile_calls_repo(monkeypatch):
    async def _fake_delete(_session):
        return True

    monkeypatch.setattr(settings_service.repo, "delete_global_company_profile", _fake_delete)
    result = asyncio.run(settings_service.reset_company_profile(_DummySession()))
    assert result is True
