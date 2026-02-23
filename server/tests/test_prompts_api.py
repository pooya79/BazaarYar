from __future__ import annotations

import importlib
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

prompts_api = importlib.import_module("server.features.prompts.api")
from server.features.prompts.errors import PromptNotFoundError, PromptValidationError
from server.features.prompts.types import PromptDetail, PromptSummary
from server.main import app


class _DummySession:
    pass


class _PromptsStore:
    def __init__(self):
        self.prompts: dict[str, PromptDetail] = {}

    async def create_prompt(
        self,
        _session,
        *,
        name: str,
        description: str,
        prompt: str,
    ) -> PromptDetail:
        normalized_name = name.strip().lstrip("\\").lower()
        if any(
            item.name.lower() == normalized_name for item in self.prompts.values()
        ):
            raise PromptValidationError(f"Prompt '\\{normalized_name}' already exists.")
        now = datetime.now(timezone.utc)
        detail = PromptDetail(
            id=str(uuid4()),
            name=normalized_name,
            description=description.strip(),
            prompt=prompt.strip(),
            created_at=now,
            updated_at=now,
        )
        self.prompts[detail.id] = detail
        return detail

    async def list_prompts(self, _session, *, q="", limit=50, offset=0):
        items = list(self.prompts.values())
        clean_q = q.strip().lower()
        if clean_q:
            items = [item for item in items if clean_q in item.name.lower()]
        items.sort(key=lambda item: (item.created_at, item.id), reverse=True)
        page = items[offset : offset + limit]
        return [
            PromptSummary(
                id=item.id,
                name=item.name,
                description=item.description,
                prompt=item.prompt,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in page
        ]

    async def get_prompt(self, _session, *, prompt_id):
        prompt = self.prompts.get(str(prompt_id))
        if prompt is None:
            raise PromptNotFoundError(f"Prompt '{prompt_id}' was not found.")
        return prompt

    async def update_prompt(
        self,
        _session,
        *,
        prompt_id,
        name=None,
        description=None,
        prompt=None,
    ):
        item = await self.get_prompt(_session, prompt_id=prompt_id)
        if name is not None:
            normalized_name = name.strip().lstrip("\\").lower()
            if any(
                existing.id != item.id and existing.name.lower() == normalized_name
                for existing in self.prompts.values()
            ):
                raise PromptValidationError(
                    f"Prompt '\\{normalized_name}' already exists.",
                )
            item.name = normalized_name
        if description is not None:
            item.description = description.strip()
        if prompt is not None:
            item.prompt = prompt.strip()
        item.updated_at = datetime.now(timezone.utc)
        return item

    async def delete_prompt(self, _session, *, prompt_id):
        item = self.prompts.get(str(prompt_id))
        if item is None:
            raise PromptNotFoundError(f"Prompt '{prompt_id}' was not found.")
        self.prompts.pop(str(prompt_id), None)


def _patch_store(monkeypatch):
    store = _PromptsStore()
    monkeypatch.setattr(prompts_api, "create_prompt", store.create_prompt)
    monkeypatch.setattr(prompts_api, "list_prompts", store.list_prompts)
    monkeypatch.setattr(prompts_api, "get_prompt", store.get_prompt)
    monkeypatch.setattr(prompts_api, "update_prompt", store.update_prompt)
    monkeypatch.setattr(prompts_api, "delete_prompt", store.delete_prompt)

    async def _override_db():
        yield _DummySession()

    app.dependency_overrides[prompts_api.get_db_session] = _override_db
    return store


def test_prompts_crud_and_search(monkeypatch):
    store = _patch_store(monkeypatch)
    client = TestClient(app)

    first = client.post(
        "/api/prompts",
        json={
            "name": "\\Campaign-Launch",
            "description": "Launch planning prompt",
            "prompt": "Create a launch plan.",
        },
    )
    assert first.status_code == 201
    first_id = first.json()["id"]
    assert first.json()["name"] == "campaign-launch"

    second = client.post(
        "/api/prompts",
        json={
            "name": "seo-brief",
            "description": "SEO clustering",
            "prompt": "Create SEO topics.",
        },
    )
    assert second.status_code == 201
    second_id = second.json()["id"]

    listed = client.get("/api/prompts")
    assert listed.status_code == 200
    listed_ids = {item["id"] for item in listed.json()}
    assert first_id in listed_ids
    assert second_id in listed_ids

    searched = client.get("/api/prompts", params={"q": "seo"})
    assert searched.status_code == 200
    assert [item["id"] for item in searched.json()] == [second_id]

    patched = client.patch(
        f"/api/prompts/{second_id}",
        json={"description": "Updated", "prompt": "Updated prompt body"},
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "Updated"

    detail = client.get(f"/api/prompts/{first_id}")
    assert detail.status_code == 200
    assert detail.json()["prompt"] == "Create a launch plan."

    duplicate = client.post(
        "/api/prompts",
        json={
            "name": "CAMPAIGN-LAUNCH",
            "description": "",
            "prompt": "Duplicate",
        },
    )
    assert duplicate.status_code == 400

    deleted = client.delete(f"/api/prompts/{first_id}")
    assert deleted.status_code == 204
    assert first_id not in store.prompts

    missing = client.get(f"/api/prompts/{uuid4()}")
    assert missing.status_code == 404


def test_prompts_api_maps_validation_errors(monkeypatch):
    async def _raise_validation(_session, *, name, description, prompt):
        _ = (name, description, prompt)
        raise PromptValidationError("bad prompt")

    async def _override_db():
        yield _DummySession()

    monkeypatch.setattr(prompts_api, "create_prompt", _raise_validation)
    app.dependency_overrides[prompts_api.get_db_session] = _override_db

    client = TestClient(app)
    response = client.post(
        "/api/prompts",
        json={"name": "x", "description": "", "prompt": "y"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "bad prompt"

