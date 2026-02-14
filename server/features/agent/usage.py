from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage


def extract_usage(message: AIMessage) -> dict[str, Any] | None:
    """Return usage metadata and surface reasoning tokens when present."""
    usage = getattr(message, "usage_metadata", None)
    response_meta = getattr(message, "response_metadata", None)
    reasoning_tokens = _find_reasoning_tokens(usage, response_meta)

    if reasoning_tokens is None:
        return usage

    if not isinstance(usage, dict):
        return {"reasoning_tokens": reasoning_tokens}

    usage_copy = dict(usage)
    usage_copy["reasoning_tokens"] = reasoning_tokens
    return usage_copy


def _find_reasoning_tokens(
    usage: dict[str, Any] | None,
    response_meta: dict[str, Any] | None,
) -> int | None:
    # Providers expose reasoning token counts under different keys.
    if isinstance(usage, dict):
        if isinstance(usage.get("reasoning_tokens"), int):
            return usage["reasoning_tokens"]
        for key in (
            "output_token_details",
            "completion_token_details",
            "completion_tokens_details",
        ):
            details = usage.get(key)
            if isinstance(details, dict) and isinstance(details.get("reasoning_tokens"), int):
                return details["reasoning_tokens"]

    if isinstance(response_meta, dict):
        for meta_key in ("token_usage", "usage"):
            token_usage = response_meta.get(meta_key)
            if isinstance(token_usage, dict):
                if isinstance(token_usage.get("reasoning_tokens"), int):
                    return token_usage["reasoning_tokens"]
                details = token_usage.get("completion_tokens_details")
                if isinstance(details, dict) and isinstance(details.get("reasoning_tokens"), int):
                    return details["reasoning_tokens"]

    return None
