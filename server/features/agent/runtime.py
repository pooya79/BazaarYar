"""Canonical runtime module for agent internals.

This module currently re-exports legacy runtime helpers to preserve behavior while
migrating imports to `server.features.agent`.
"""

from server.agents.runtime import (  # noqa: F401
    TOOLS,
    SYSTEM_PROMPT,
    build_agent_runtime,
    extract_trace,
    split_gemini_content,
    split_openai_like_content,
)
