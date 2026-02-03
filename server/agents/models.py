from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_openai import ChatOpenAI

from server.core.config import get_settings


@dataclass(frozen=True)
class ModelSpec:
    name: str
    build_model: Callable[[], Any]


def openai_model_spec() -> ModelSpec:
    settings = get_settings()
    def _build_model() -> ChatOpenAI:
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=1.0,
            reasoning={
                "effort": "medium",
                "exclude": False,
                "enables": True,
            },
        )

    return ModelSpec(name=settings.openai_model, build_model=_build_model)


def openailike_model_spec() -> ModelSpec:
    settings = get_settings()
    def _build_model() -> ChatOpenAI:
        model_kwargs: dict[str, Any] = {
            "model": settings.openailike_model,
            "api_key": settings.openailike_api_key,
            "temperature": 1.0,
            "reasoning": {
                "effort": "medium",
                "exclude": False,
                "enables": True,
            },
        }
        if settings.openailike_base_url:
            # OpenAI-compatible providers often need a custom base URL.
            model_kwargs["base_url"] = settings.openailike_base_url

        return ChatOpenAI(**model_kwargs)

    return ModelSpec(name=settings.openailike_model, build_model=_build_model)


def gemini_model_spec() -> ModelSpec:
    settings = get_settings()

    def _build_model() -> Any:
        # Import lazily so non-Gemini environments can still load other agents.
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=settings.google_api_key,
            temperature=1.0,
            include_thoughts=True,
            thinking_level=settings.gemini_thinking_level,
        )

    return ModelSpec(name=settings.gemini_model, build_model=_build_model)
