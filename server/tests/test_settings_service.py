from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from server.features.settings.types import (
    CompanyProfilePatch,
    ModelCardCreate,
    ModelCardPatch,
    ToolSettingsPatch,
    ToolSettingsResolved,
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
    async def _fake_get_active(_session):
        return SimpleNamespace(
            model_name="openai/gpt-5-mini",
            api_key="db-key",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.4,
            reasoning_effort="high",
            reasoning_enabled=False,
        )

    async def _fake_get_default(_session):
        return None

    monkeypatch.setattr(settings_service.repo, "get_active_model_card", _fake_get_active)
    monkeypatch.setattr(settings_service.repo, "get_default_model_card", _fake_get_default)

    resolved = asyncio.run(settings_service.resolve_effective_model_settings(_DummySession()))

    assert resolved.model_name == "openai/gpt-5-mini"
    assert resolved.api_key == "db-key"
    assert resolved.base_url == "https://openrouter.ai/api/v1"
    assert resolved.temperature == 0.4
    assert resolved.reasoning_effort == "high"
    assert resolved.reasoning_enabled is False
    assert resolved.source == "database"


def test_resolve_effective_model_settings_falls_back_to_env(monkeypatch):
    monkeypatch.setattr(settings_service, "get_settings", lambda: _fake_env_settings())

    async def _fake_get_active(_session):
        return None

    async def _fake_get_default(_session):
        return None

    monkeypatch.setattr(settings_service.repo, "get_active_model_card", _fake_get_active)
    monkeypatch.setattr(settings_service.repo, "get_default_model_card", _fake_get_default)

    resolved = asyncio.run(settings_service.resolve_effective_model_settings(_DummySession()))

    assert resolved.model_name == "gpt-4.1-mini"
    assert resolved.api_key == "env-key"
    assert resolved.source == "environment_defaults"


def test_create_model_card_returns_masked_api_key_preview(monkeypatch):
    stored_rows: list[SimpleNamespace] = []

    async def _fake_create(_session, **kwargs):
        row = SimpleNamespace(
            id="00000000-0000-0000-0000-000000000001",
            display_name=kwargs["display_name"],
            model_name=kwargs["model_name"],
            api_key=kwargs["api_key"],
            base_url=kwargs["base_url"],
            temperature=kwargs["temperature"],
            reasoning_effort=kwargs["reasoning_effort"],
            reasoning_enabled=kwargs["reasoning_enabled"],
            is_default=kwargs["is_default"],
            is_active=kwargs["is_active"],
            created_at=1,
        )
        stored_rows.append(row)
        return row

    async def _fake_list(_session):
        return stored_rows

    async def _fake_set_default(_session, model_id):
        for row in stored_rows:
            row.is_default = str(row.id) == str(model_id)
        return next((row for row in stored_rows if str(row.id) == str(model_id)), None)

    async def _fake_set_active(_session, model_id):
        for row in stored_rows:
            row.is_active = str(row.id) == str(model_id)
        return next((row for row in stored_rows if str(row.id) == str(model_id)), None)

    monkeypatch.setattr(settings_service.repo, "create_model_card", _fake_create)
    monkeypatch.setattr(settings_service.repo, "list_model_cards", _fake_list)
    monkeypatch.setattr(settings_service.repo, "set_default_model_card", _fake_set_default)
    monkeypatch.setattr(settings_service.repo, "set_active_model_card", _fake_set_active)

    response = asyncio.run(
        settings_service.create_model_card(
            _DummySession(),
            ModelCardCreate(
                display_name="Primary",
                model_name="gpt-4.1-mini",
                api_key="sk-test-secret",
                is_default=True,
                is_active=True,
            ),
        )
    )

    assert response.items[0].display_name == "Primary"
    assert response.items[0].has_api_key is True
    assert response.items[0].api_key_preview == "sk-t...cret"
    assert response.default_model_id == "00000000-0000-0000-0000-000000000001"
    assert response.active_model_id == "00000000-0000-0000-0000-000000000001"


def test_patch_model_card_sanitizes_text_fields(monkeypatch):
    row = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000111",
        display_name="Current",
        model_name="current-model",
        api_key="current-key",
        base_url="https://current",
        temperature=0.5,
        reasoning_effort="medium",
        reasoning_enabled=True,
        is_default=True,
        is_active=True,
        created_at=1,
    )

    async def _fake_get(_session, _model_id):
        return row

    async def _fake_update(_session, _row, **kwargs):
        for key, value in kwargs.items():
            setattr(row, key, value)
        return row

    async def _fake_list(_session):
        return [row]

    async def _fake_set_default(_session, model_id):
        row.is_default = str(row.id) == str(model_id)
        return row

    async def _fake_set_active(_session, model_id):
        row.is_active = str(row.id) == str(model_id)
        return row

    monkeypatch.setattr(settings_service.repo, "get_model_card", _fake_get)
    monkeypatch.setattr(settings_service.repo, "update_model_card", _fake_update)
    monkeypatch.setattr(settings_service.repo, "list_model_cards", _fake_list)
    monkeypatch.setattr(settings_service.repo, "set_default_model_card", _fake_set_default)
    monkeypatch.setattr(settings_service.repo, "set_active_model_card", _fake_set_active)

    response = asyncio.run(
            settings_service.patch_model_card(
                _DummySession(),
                str(row.id),
                ModelCardPatch(
                    display_name="  Prime\x00 Model ",
                    model_name="  open\x00-model  ",
                    api_key="sk-\x00abc\r\n",
                    base_url="https://exa\x00mple\r\npath",
                ),
            )
        )

    updated = response.items[0]
    assert updated.display_name == "Prime Model"
    assert updated.model_name == "open-model"
    assert updated.has_api_key is True
    assert updated.api_key_preview is not None
    assert updated.base_url == "https://example\npath"


def test_delete_model_card_requires_at_least_one_row(monkeypatch):
    row = SimpleNamespace(id="00000000-0000-0000-0000-000000000222")

    async def _fake_list(_session):
        return [row]

    monkeypatch.setattr(settings_service.repo, "list_model_cards", _fake_list)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(settings_service.delete_model_card(_DummySession(), str(row.id)))

    assert exc.value.status_code == 400


def test_resolve_effective_model_settings_activates_selected_model(monkeypatch):
    selected_row = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000333",
        model_name="openai/gpt-5-mini",
        api_key="db-key",
        base_url="https://openrouter.ai/api/v1",
        temperature=0.2,
        reasoning_effort="high",
        reasoning_enabled=False,
        is_active=False,
    )

    async def _fake_get_model(_session, _model_id):
        return selected_row

    called: dict[str, str] = {}

    async def _fake_set_active(_session, model_id):
        called["id"] = str(model_id)
        selected_row.is_active = True
        return selected_row

    monkeypatch.setattr(settings_service.repo, "get_model_card", _fake_get_model)
    monkeypatch.setattr(settings_service.repo, "set_active_model_card", _fake_set_active)

    resolved = asyncio.run(
        settings_service.resolve_effective_model_settings(
            _DummySession(),
            model_id=str(selected_row.id),
            activate_selected=True,
        )
    )

    assert called["id"] == str(selected_row.id)
    assert resolved.model_name == "openai/gpt-5-mini"


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


def test_patch_company_profile_sanitizes_text_fields(monkeypatch):
    async def _fake_get_global(_session):
        return SimpleNamespace(
            name="Current Co",
            description="Current desc",
            enabled=False,
        )

    captured: dict[str, object] = {}

    async def _fake_upsert(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(settings_service.repo, "get_global_company_profile", _fake_get_global)
    monkeypatch.setattr(settings_service.repo, "upsert_global_company_profile", _fake_upsert)

    patch = CompanyProfilePatch(
        name="  Ac\x00me  ",
        description="  Line 1\x00\r\nLine 2  ",
        enabled=True,
    )
    resolved = asyncio.run(settings_service.patch_company_profile(_DummySession(), patch))

    assert captured["name"] == "Acme"
    assert captured["description"] == "Line 1\nLine 2"
    assert resolved.name == "Acme"
    assert resolved.description == "Line 1\nLine 2"
    assert resolved.enabled is True


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


def test_resolve_effective_tool_settings_filters_unknown_overrides(monkeypatch):
    async def _fake_get_global(_session):
        return SimpleNamespace(
            tool_overrides_json={
                "utc_time": False,
                "run_python_code": True,
                "removed_tool": True,
                "bad_value": "yes",
            }
        )

    monkeypatch.setattr(settings_service.repo, "get_global_tool_settings", _fake_get_global)

    resolved = asyncio.run(settings_service.resolve_effective_tool_settings(_DummySession()))

    assert resolved.tool_overrides["utc_time"] is False
    assert resolved.tool_overrides["run_python_code"] is True
    assert "removed_tool" not in resolved.tool_overrides
    assert "bad_value" not in resolved.tool_overrides
    assert resolved.source == "database"


def test_patch_tool_settings_rejects_unknown_tool_keys(monkeypatch):
    async def _fake_get_global(_session):
        return None

    monkeypatch.setattr(settings_service.repo, "get_global_tool_settings", _fake_get_global)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            settings_service.patch_tool_settings(
                _DummySession(),
                ToolSettingsPatch(tool_overrides={"unknown_tool": True}),
            )
        )

    assert exc.value.status_code == 422
    assert "unknown_tool" in str(exc.value.detail)


def test_patch_tool_settings_stores_only_non_default_overrides(monkeypatch):
    async def _fake_get_global(_session):
        return None

    captured: dict[str, object] = {}

    async def _fake_upsert(_session, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(settings_service.repo, "get_global_tool_settings", _fake_get_global)
    monkeypatch.setattr(settings_service.repo, "upsert_global_tool_settings", _fake_upsert)

    patch = ToolSettingsPatch(
        tool_overrides={
            "utc_time": False,
            "reverse_text": True,
        }
    )
    resolved = asyncio.run(settings_service.patch_tool_settings(_DummySession(), patch))

    assert captured["tool_overrides_json"] == {"utc_time": False}
    assert resolved.tool_overrides == {"utc_time": False}
    assert resolved.source == "database"


def test_to_tool_settings_response_derives_group_enabled_state():
    response = settings_service.to_tool_settings_response(
        ToolSettingsResolved(
            tool_overrides={"utc_time": False},
            source="database",
        )
    )

    basic_group = next(group for group in response.groups if group.key == "basic_tools")
    assert basic_group.enabled is True
    utc_tool = next(tool for tool in basic_group.tools if tool.key == "utc_time")
    assert utc_tool.enabled is False
