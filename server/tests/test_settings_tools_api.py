from __future__ import annotations

import importlib

from fastapi import HTTPException
from fastapi.testclient import TestClient

from server.db.session import get_db_session
from server.features.settings.types import ToolSettingsResolved
from server.main import app

settings_api = importlib.import_module("server.features.settings.api")


async def _override_db():
    yield object()


def test_get_tool_settings_endpoint_returns_catalog(monkeypatch):
    async def _fake_resolve(_session):
        return ToolSettingsResolved(
            tool_overrides={"utc_time": False},
            source="database",
        )

    monkeypatch.setattr(settings_api, "resolve_effective_tool_settings", _fake_resolve)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.get("/api/settings/tools")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "database"
    assert payload["tool_overrides"] == {"utc_time": False}
    assert isinstance(payload["groups"], list)
    assert len(payload["groups"]) > 0


def test_patch_tool_settings_endpoint_updates_values(monkeypatch):
    async def _fake_patch(_session, payload):
        assert payload.tool_overrides == {"utc_time": False}
        return ToolSettingsResolved(
            tool_overrides={"utc_time": False},
            source="database",
        )

    monkeypatch.setattr(settings_api, "patch_tool_settings", _fake_patch)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.patch(
        "/api/settings/tools",
        json={"tool_overrides": {"utc_time": False}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "database"
    assert payload["tool_overrides"] == {"utc_time": False}


def test_patch_tool_settings_endpoint_rejects_unknown_keys(monkeypatch):
    async def _fake_patch(_session, _payload):
        raise HTTPException(status_code=422, detail="Unknown tool key(s): unknown_tool")

    monkeypatch.setattr(settings_api, "patch_tool_settings", _fake_patch)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.patch(
        "/api/settings/tools",
        json={"tool_overrides": {"unknown_tool": True}},
    )

    assert response.status_code == 422
    assert "unknown_tool" in response.text


def test_delete_tool_settings_endpoint(monkeypatch):
    async def _fake_reset(_session):
        return True

    monkeypatch.setattr(settings_api, "reset_tool_settings", _fake_reset)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.delete("/api/settings/tools")

    assert response.status_code == 200
    assert response.json() == {"reset": True}


def teardown_function():
    app.dependency_overrides.clear()
