from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from server.db.session import get_db_session
from server.features.settings.types import CompanyProfileResolved
from server.main import app

settings_api = importlib.import_module("server.features.settings.api")


async def _override_db():
    yield object()


def test_get_company_profile_endpoint_returns_payload(monkeypatch):
    async def _fake_resolve(_session):
        return CompanyProfileResolved(
            name="Acme",
            description="We sell shoes.",
            enabled=True,
            source="database",
        )

    monkeypatch.setattr(settings_api, "resolve_effective_company_profile", _fake_resolve)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.get("/api/settings/company")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Acme",
        "description": "We sell shoes.",
        "enabled": True,
        "source": "database",
    }


def test_patch_company_profile_endpoint_updates_values(monkeypatch):
    async def _fake_patch(_session, payload):
        assert payload.name == "Acme"
        assert payload.description == "Shoes"
        assert payload.enabled is False
        return CompanyProfileResolved(
            name="Acme",
            description="Shoes",
            enabled=False,
            source="database",
        )

    monkeypatch.setattr(settings_api, "patch_company_profile", _fake_patch)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.patch(
        "/api/settings/company",
        json={"name": "Acme", "description": "Shoes", "enabled": False},
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "Acme",
        "description": "Shoes",
        "enabled": False,
        "source": "database",
    }


def test_patch_company_profile_endpoint_validates_payload():
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    bad_extra = client.patch("/api/settings/company", json={"foo": "bar"})
    assert bad_extra.status_code == 422

    bad_name = client.patch("/api/settings/company", json={"name": "x" * 256})
    assert bad_name.status_code == 422


def test_delete_company_profile_endpoint(monkeypatch):
    async def _fake_reset(_session):
        return True

    monkeypatch.setattr(settings_api, "reset_company_profile", _fake_reset)
    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)

    response = client.delete("/api/settings/company")

    assert response.status_code == 200
    assert response.json() == {"reset": True}


def teardown_function():
    app.dependency_overrides.clear()
