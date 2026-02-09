from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

AttachmentMediaType = Literal["image", "pdf", "text", "spreadsheet", "binary"]


class StoredAttachment(BaseModel):
    id: str
    filename: str
    content_type: str
    media_type: AttachmentMediaType
    size_bytes: int
    storage_path: str
    preview_text: str | None = None
    extraction_note: str | None = None
    created_at: datetime
