from __future__ import annotations

from fastapi import HTTPException


def not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=404, detail=detail)
