from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from server.db.session import get_db_session
from server.main import app

settings_api = importlib.import_module("server.features.settings.api")


async def _override_db():
    yield object()


def _cards_payload():
    return {
        "items": [
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "display_name": "Primary",
                "model_name": "openai/gpt-5-mini",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.6,
                "reasoning_effort": "high",
                "reasoning_enabled": True,
                "has_api_key": True,
                "api_key_preview": "sk-l...1234",
                "is_default": True,
                "is_active": True,
            }
        ],
        "active_model_id": "00000000-0000-0000-0000-000000000001",
        "default_model_id": "00000000-0000-0000-0000-000000000001",
    }


def test_get_model_cards_endpoint(monkeypatch):
    async def _fake_list(_session):
        return _cards_payload()

    monkeypatch.setattr(settings_api, "list_model_cards", _fake_list)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.get("/api/settings/models")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["display_name"] == "Primary"
    assert payload["items"][0]["api_key_preview"] == "sk-l...1234"
    assert payload["active_model_id"] == "00000000-0000-0000-0000-000000000001"


def test_create_model_card_endpoint(monkeypatch):
    async def _fake_create(_session, payload):
        assert payload.display_name == "New model"
        assert payload.model_name == "gpt-4.1-mini"
        return _cards_payload()

    monkeypatch.setattr(settings_api, "create_model_card", _fake_create)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.post(
        "/api/settings/models",
        json={"display_name": "New model", "model_name": "gpt-4.1-mini"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["model_name"] == "openai/gpt-5-mini"


def test_patch_model_card_endpoint(monkeypatch):
    async def _fake_patch(_session, model_id, payload):
        assert model_id == "00000000-0000-0000-0000-000000000001"
        assert payload.temperature == 0.4
        return _cards_payload()

    monkeypatch.setattr(settings_api, "patch_model_card", _fake_patch)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.patch(
        "/api/settings/models/00000000-0000-0000-0000-000000000001",
        json={"temperature": 0.4},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["display_name"] == "Primary"


def test_delete_model_card_endpoint(monkeypatch):
    async def _fake_delete(_session, model_id):
        assert model_id == "00000000-0000-0000-0000-000000000001"
        return _cards_payload()

    monkeypatch.setattr(settings_api, "delete_model_card", _fake_delete)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.delete("/api/settings/models/00000000-0000-0000-0000-000000000001")

    assert response.status_code == 200
    assert response.json()["default_model_id"] == "00000000-0000-0000-0000-000000000001"


def test_activate_model_card_endpoint(monkeypatch):
    async def _fake_activate(_session, model_id):
        assert model_id == "00000000-0000-0000-0000-000000000001"
        return _cards_payload()

    monkeypatch.setattr(settings_api, "activate_model_card", _fake_activate)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.post("/api/settings/models/00000000-0000-0000-0000-000000000001/activate")

    assert response.status_code == 200
    assert response.json()["active_model_id"] == "00000000-0000-0000-0000-000000000001"


def test_set_default_model_card_endpoint(monkeypatch):
    async def _fake_set_default(_session, model_id):
        assert model_id == "00000000-0000-0000-0000-000000000001"
        return _cards_payload()

    monkeypatch.setattr(settings_api, "set_default_model_card", _fake_set_default)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.post("/api/settings/models/00000000-0000-0000-0000-000000000001/default")

    assert response.status_code == 200
    assert response.json()["default_model_id"] == "00000000-0000-0000-0000-000000000001"


def test_patch_model_card_validates_temperature_and_effort():
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    bad_effort = client.patch(
        "/api/settings/models/00000000-0000-0000-0000-000000000001",
        json={"reasoning_effort": "max"},
    )
    assert bad_effort.status_code == 422

    bad_temp = client.patch(
        "/api/settings/models/00000000-0000-0000-0000-000000000001",
        json={"temperature": 3},
    )
    assert bad_temp.status_code == 422


def teardown_function():
    app.dependency_overrides.clear()
