from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_openai import ChatOpenAI

from server.core.config import get_settings
from server.features.settings.types import ModelSettingsResolved


@dataclass(frozen=True)
class ModelSpec:
    name: str
    build_model: Callable[[], Any]


_ASSISTANT_ALLOWED_BLOCKS = {"output_text", "refusal"}
_USER_ALLOWED_BLOCKS = {"input_text", "input_image", "input_file"}


def _drop_none_values(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _drop_none_values(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_drop_none_values(item) for item in value]
    return value


def _normalize_user_block(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    block_type = block.get("type")
    if block_type == "text":
        text = block.get("text")
        if text is None:
            return None
        return {"type": "input_text", "text": str(text)}
    if block_type == "image_url":
        image_url = block.get("image_url")
        if isinstance(image_url, dict):
            url = image_url.get("url")
        else:
            url = image_url
        if not url:
            return None
        converted = {"type": "input_image", "image_url": url}
        detail = image_url.get("detail") if isinstance(image_url, dict) else None
        if detail:
            converted["detail"] = detail
        return converted
    if block_type == "file":
        payload = block.get("file")
        if isinstance(payload, dict):
            return {"type": "input_file", **payload}
        return None
    if block_type in _USER_ALLOWED_BLOCKS:
        return _drop_none_values(block)
    return None


def _normalize_assistant_block(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    block_type = block.get("type")
    if block_type == "text":
        text = block.get("text")
        if text is None:
            return None
        return {"type": "output_text", "text": str(text), "annotations": []}
    if block_type == "output_text":
        text = block.get("text")
        if text is None:
            return None
        return {
            "type": "output_text",
            "text": str(text),
            "annotations": block.get("annotations") or [],
        }
    if block_type in _ASSISTANT_ALLOWED_BLOCKS:
        return _drop_none_values(block)
    return None


def sanitize_responses_input(input_items: list[Any]) -> list[Any]:
    sanitized: list[Any] = []
    for raw_item in input_items:
        if not isinstance(raw_item, dict):
            continue

        item = _drop_none_values(raw_item)
        item_type = item.get("type")

        if item_type == "reasoning":
            # Some providers emit non-standard reasoning blocks that fail OpenAI
            # Responses request validation when replayed into the next model turn.
            continue

        if item_type == "message":
            role = item.get("role")
            content = item.get("content")
            if isinstance(content, list):
                if role == "assistant":
                    blocks = [
                        block
                        for block in (_normalize_assistant_block(block) for block in content)
                        if block is not None
                    ]
                elif role in {"user", "system", "developer"}:
                    blocks = [
                        block
                        for block in (_normalize_user_block(block) for block in content)
                        if block is not None
                    ]
                else:
                    blocks = []
                if not blocks:
                    continue
                item["content"] = blocks
            elif isinstance(content, str):
                if not content.strip():
                    continue
                item["content"] = content
            else:
                continue
            sanitized.append(item)
            continue

        sanitized.append(item)

    return sanitized


class CompatibleChatOpenAI(ChatOpenAI):
    def _get_request_payload(self, input_: Any, *, stop: list[str] | None = None, **kwargs: Any) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        if isinstance(payload.get("input"), list):
            payload["input"] = sanitize_responses_input(payload["input"])
        return payload


def _default_runtime_settings() -> ModelSettingsResolved:
    settings = get_settings()
    return ModelSettingsResolved(
        model_name=settings.openailike_model,
        api_key=settings.openailike_api_key,
        base_url=settings.openailike_base_url,
        temperature=settings.openailike_temperature,
        reasoning_effort=settings.openailike_reasoning_effort,
        reasoning_enabled=settings.openailike_reasoning_enabled,
        source="environment_defaults",
    )


def openailike_model_spec(runtime_settings: ModelSettingsResolved | None = None) -> ModelSpec:
    resolved = runtime_settings or _default_runtime_settings()

    def _build_model() -> CompatibleChatOpenAI:
        model_kwargs: dict[str, Any] = {
            "model": resolved.model_name,
            "api_key": resolved.api_key,
            "temperature": resolved.temperature,
            "reasoning": {
                "effort": resolved.reasoning_effort,
                "exclude": False,
                "enables": resolved.reasoning_enabled,
            },
        }
        if resolved.base_url:
            # OpenAI-compatible providers often need a custom base URL.
            model_kwargs["base_url"] = resolved.base_url

        return CompatibleChatOpenAI(**model_kwargs)

    return ModelSpec(name=resolved.model_name, build_model=_build_model)
