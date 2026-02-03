from __future__ import annotations


def normalize_database_url(url: str) -> str:
    """Ensure SQLAlchemy uses the psycopg driver even if a plain postgres URL is provided."""
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url
