from __future__ import annotations


class PromptsDomainError(Exception):
    """Base exception for prompt template operations."""


class PromptNotFoundError(PromptsDomainError):
    pass


class PromptValidationError(PromptsDomainError):
    pass

