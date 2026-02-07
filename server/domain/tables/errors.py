from __future__ import annotations


class TablesDomainError(Exception):
    """Base exception for reference table domain operations."""


class TableNotFoundError(TablesDomainError):
    pass


class ColumnValidationError(TablesDomainError):
    pass


class SchemaConflictError(TablesDomainError):
    pass


class RowValidationError(TablesDomainError):
    def __init__(self, message: str, *, errors: list[dict] | None = None):
        super().__init__(message)
        self.errors = errors or []


class QueryValidationError(TablesDomainError):
    pass


class ImportJobNotFoundError(TablesDomainError):
    pass


class ImportFormatError(TablesDomainError):
    pass


class TablesPermissionError(TablesDomainError):
    pass
