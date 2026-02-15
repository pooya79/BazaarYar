from __future__ import annotations


class ReportsDomainError(Exception):
    """Base exception for conversation report operations."""


class ReportNotFoundError(ReportsDomainError):
    pass


class ReportValidationError(ReportsDomainError):
    pass
