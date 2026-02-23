from __future__ import annotations

import asyncio
from uuid import uuid4

from server.features.prompts import repo as prompts_repo


class _FakeScalarResult:
    def all(self):
        return []


class _FakeExecuteResult:
    def scalars(self):
        return _FakeScalarResult()

    def scalar_one_or_none(self):
        return None


class _FakeSession:
    def __init__(self):
        self.last_params: dict[str, object] = {}

    async def execute(self, stmt):
        compiled = stmt.compile(compile_kwargs={"literal_binds": False})
        self.last_params = dict(compiled.params)
        return _FakeExecuteResult()


def test_list_prompts_sanitizes_query_before_ilike_binding():
    session = _FakeSession()

    rows = asyncio.run(
        prompts_repo.list_prompts(
            session,
            q="  qu\x00ery\ud800\r\ntext  ",
            limit=10,
            offset=0,
        )
    )

    assert rows == []
    bound_values = [value for value in session.last_params.values() if isinstance(value, str)]
    assert bound_values
    like_value = bound_values[0]
    assert like_value.startswith("%")
    assert like_value.endswith("%")
    assert "\x00" not in like_value
    assert "\ud800" not in like_value
    assert "\r" not in like_value
    assert "query\ufffd\ntext" in like_value


def test_get_prompt_by_name_uses_normalized_name_and_exclusion_id():
    session = _FakeSession()
    excluded_id = str(uuid4())

    row = asyncio.run(
        prompts_repo.get_prompt_by_name(
            session,
            name="Campaign-Plan",
            exclude_prompt_id=excluded_id,
        )
    )

    assert row is None
    bound_values = list(session.last_params.values())
    assert any(value == "campaign-plan" for value in bound_values)
    assert any(str(value) == excluded_id for value in bound_values)

