from __future__ import annotations

import math

from server.db.models import Message


def estimate_tokens(text: str) -> int:
    compact = text.strip()
    if not compact:
        return 1
    return max(1, math.ceil(len(compact) / 4))


def token_value(message: Message) -> int:
    if message.token_estimate > 0:
        return int(message.token_estimate)
    return estimate_tokens(message.content)
