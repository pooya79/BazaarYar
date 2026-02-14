from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ConversationListEntry:
    id: UUID
    title: str | None
    starred: bool
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_at: datetime | None
    sort_at: datetime


@dataclass(frozen=True)
class ConversationListCursor:
    starred: bool
    sort_at: datetime
    created_at: datetime
    id: UUID
