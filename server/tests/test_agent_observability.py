from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def observability_module():
    module = importlib.import_module("server.features.agent.observability")
    return importlib.reload(module)


def _install_phoenix_stub(monkeypatch: pytest.MonkeyPatch, register_impl):
    phoenix_module = ModuleType("phoenix")
    otel_module = ModuleType("phoenix.otel")
    otel_module.register = register_impl
    phoenix_module.otel = otel_module
    monkeypatch.setitem(sys.modules, "phoenix", phoenix_module)
    monkeypatch.setitem(sys.modules, "phoenix.otel", otel_module)


def test_configure_agent_observability_noops_when_disabled(
    observability_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        observability_module,
        "get_settings",
        lambda: SimpleNamespace(
            phoenix_enabled=False,
            phoenix_project_name="bazaaryar-agent",
            phoenix_collector_endpoint="http://localhost:4317",
        ),
    )

    observability_module.configure_agent_observability()
    assert observability_module._is_configured is False


def test_configure_agent_observability_registers_when_enabled(
    observability_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def _register(**kwargs):
        calls.append(kwargs)
        return object()

    _install_phoenix_stub(monkeypatch, _register)
    monkeypatch.setattr(
        observability_module,
        "get_settings",
        lambda: SimpleNamespace(
            phoenix_enabled=True,
            phoenix_project_name="bazaaryar-agent",
            phoenix_collector_endpoint="http://localhost:4317",
        ),
    )

    observability_module.configure_agent_observability()

    assert observability_module._is_configured is True
    assert calls == [
        {
            "project_name": "bazaaryar-agent",
            "endpoint": "http://localhost:4317",
            "auto_instrument": True,
        }
    ]


def test_configure_agent_observability_is_idempotent(
    observability_module,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def _register(**_kwargs):
        nonlocal call_count
        call_count += 1
        return object()

    _install_phoenix_stub(monkeypatch, _register)
    monkeypatch.setattr(
        observability_module,
        "get_settings",
        lambda: SimpleNamespace(
            phoenix_enabled=True,
            phoenix_project_name="bazaaryar-agent",
            phoenix_collector_endpoint="http://localhost:4317",
        ),
    )

    observability_module.configure_agent_observability()
    observability_module.configure_agent_observability()

    assert call_count == 1


def test_configure_agent_observability_fails_open(
    observability_module,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _register(**_kwargs):
        raise RuntimeError("register exploded")

    _install_phoenix_stub(monkeypatch, _register)
    monkeypatch.setattr(
        observability_module,
        "get_settings",
        lambda: SimpleNamespace(
            phoenix_enabled=True,
            phoenix_project_name="bazaaryar-agent",
            phoenix_collector_endpoint="http://localhost:4317",
        ),
    )

    observability_module.configure_agent_observability()

    assert observability_module._is_configured is False
    assert "setup failed" in caplog.text.lower()
