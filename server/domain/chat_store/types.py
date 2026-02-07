from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ConversationListEntry:
    id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_at: datetime | None
