from __future__ import annotations

import logging
from threading import Lock

from server.core.config import get_settings

logger = logging.getLogger(__name__)

_configure_lock = Lock()
_is_configured = False


def configure_agent_observability() -> None:
    global _is_configured
    if _is_configured:
        return

    settings = get_settings()
    if not settings.phoenix_enabled:
        return

    with _configure_lock:
        if _is_configured:
            return
        try:
            from phoenix.otel import register

            register(
                project_name=settings.phoenix_project_name,
                endpoint=settings.phoenix_collector_endpoint,
                auto_instrument=True,
            )
        except Exception:
            logger.warning(
                "Phoenix observability setup failed; continuing without tracing.",
                exc_info=True,
            )
            return
        _is_configured = True
