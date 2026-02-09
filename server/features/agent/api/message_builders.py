from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import Message
from server.features.attachments.schemas import StoredAttachment
from server.features.attachments.service import (
    build_attachment_message_parts_async,
    build_attachment_message_parts_for_items,
    from_db_attachment,
)

from .schemas import AgentRequest


def _message_attachments(message: Message) -> list[StoredAttachment]:
    attachments: list[StoredAttachment] = []
    for link in message.attachment_links:
        if link.attachment is None:
            continue
        attachments.append(from_db_attachment(link.attachment))
    return attachments


def to_langchain_message(message: Message) -> HumanMessage | AIMessage:
    if message.role == "assistant":
        return AIMessage(content=message.content)

    attachments = _message_attachments(message)
    if not attachments:
        return HumanMessage(content=message.content)

    attachment_context, attachment_blocks = build_attachment_message_parts_for_items(attachments)
    content: list[dict[str, Any]] = []
    if message.content.strip():
        content.append({"type": "text", "text": message.content})
    if attachment_context:
        content.append(
            {
                "type": "text",
                "text": (
                    "Attached file context:\n"
                    f"{attachment_context}\n\n"
                    "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                ),
            }
        )
    content.extend(attachment_blocks)
    if not content:
        return HumanMessage(content=message.content)
    return HumanMessage(content=content)


async def build_messages(payload: AgentRequest, session: AsyncSession) -> list[Any]:
    messages: list[Any] = []
    if payload.history:
        for item in payload.history:
            if item.role == "assistant":
                messages.append(AIMessage(content=item.content))
            else:
                messages.append(HumanMessage(content=item.content))

    user_message = (payload.message or "").strip()
    attachment_ids = [item.strip() for item in (payload.attachment_ids or []) if item.strip()]
    attachment_context = ""
    attachment_blocks: list[dict[str, Any]] = []
    if attachment_ids:
        attachment_context, attachment_blocks = await build_attachment_message_parts_async(
            session,
            attachment_ids,
            allow_json_fallback=True,
        )

    if user_message or attachment_context or attachment_blocks:
        if attachment_blocks:
            content: list[dict[str, Any]] = []
            if user_message:
                content.append({"type": "text", "text": user_message})
            if attachment_context:
                content.append(
                    {
                        "type": "text",
                        "text": (
                            "Attached file context:\n"
                            f"{attachment_context}\n\n"
                            "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                        ),
                    }
                )
            content.extend(attachment_blocks)
            messages.append(HumanMessage(content=content))
        else:
            content_parts: list[str] = []
            if user_message:
                content_parts.append(user_message)
            if attachment_context:
                content_parts.append(
                    "Attached file context:\n"
                    f"{attachment_context}\n\n"
                    "Use extracted content when relevant and call out uncertainty if extraction is incomplete."
                )
            messages.append(HumanMessage(content="\n\n".join(content_parts)))
    return messages
