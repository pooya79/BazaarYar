from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from server.db.session import get_db_session
from server.features.settings.types import ModelSettingsResolved
from server.main import app

settings_api = importlib.import_module("server.features.settings.api")


async def _override_db():
    yield object()


def test_get_model_settings_endpoint_returns_masked_key(monkeypatch):
    async def _fake_resolve(_session):
        return ModelSettingsResolved(
            model_name="openai/gpt-5-mini",
            api_key="sk-live-test-1234",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.8,
            reasoning_effort="high",
            reasoning_enabled=True,
            source="database",
        )

    monkeypatch.setattr(settings_api, "resolve_effective_model_settings", _fake_resolve)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.get("/api/settings/model")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "openai/gpt-5-mini"
    assert payload["has_api_key"] is True
    assert payload["api_key_preview"] == "sk-l...1234"
    assert payload["source"] == "database"


def test_patch_model_settings_endpoint_updates_values(monkeypatch):
    async def _fake_patch(_session, payload):
        assert payload.temperature == 0.6
        assert payload.reasoning_effort == "low"
        return ModelSettingsResolved(
            model_name="moonshotai/kimi-k2.5",
            api_key="db-key",
            base_url="https://openrouter.ai/api/v1",
            temperature=0.6,
            reasoning_effort="low",
            reasoning_enabled=False,
            source="database",
        )

    monkeypatch.setattr(settings_api, "patch_model_settings", _fake_patch)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.patch(
        "/api/settings/model",
        json={"temperature": 0.6, "reasoning_effort": "low", "reasoning_enabled": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_name"] == "moonshotai/kimi-k2.5"
    assert payload["temperature"] == 0.6
    assert payload["reasoning_effort"] == "low"
    assert payload["reasoning_enabled"] is False
    assert payload["source"] == "database"


def test_patch_model_settings_endpoint_validates_effort_and_temperature():
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    bad_effort = client.patch("/api/settings/model", json={"reasoning_effort": "max"})
    assert bad_effort.status_code == 422

    bad_temp = client.patch("/api/settings/model", json={"temperature": 3})
    assert bad_temp.status_code == 422


def test_delete_model_settings_endpoint(monkeypatch):
    async def _fake_reset(_session):
        return True

    monkeypatch.setattr(settings_api, "reset_model_settings", _fake_reset)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.delete("/api/settings/model")

    assert response.status_code == 200
    assert response.json() == {"reset": True}


def teardown_function():
    app.dependency_overrides.clear()
