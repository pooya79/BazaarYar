from __future__ import annotations

import asyncio

from server.features.reports import repo as reports_repo


class _FakeScalarResult:
    def all(self):
        return []


class _FakeExecuteResult:
    def scalars(self):
        return _FakeScalarResult()


class _FakeSession:
    def __init__(self):
        self.last_params: dict[str, object] = {}

    async def execute(self, stmt):
        compiled = stmt.compile(compile_kwargs={"literal_binds": False})
        self.last_params = dict(compiled.params)
        return _FakeExecuteResult()


def test_list_reports_sanitizes_query_before_ilike_binding():
    session = _FakeSession()

    rows = asyncio.run(
        reports_repo.list_reports(
            session,
            q="  qu\x00ery\ud800\r\ntext  ",
            limit=10,
            offset=0,
            include_disabled=True,
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
