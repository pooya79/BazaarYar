from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import Attachment
from server.features.shared.ids import parse_uuid

from .schemas import StoredAttachment


def from_db_attachment(attachment: Attachment) -> StoredAttachment:
    return StoredAttachment(
        id=str(attachment.id),
        filename=attachment.filename,
        content_type=attachment.content_type,
        media_type=attachment.media_type,
        size_bytes=attachment.size_bytes,
        storage_path=attachment.storage_path,
        preview_text=attachment.preview_text,
        extraction_note=attachment.extraction_note,
        created_at=attachment.created_at,
    )


async def load_attachments_for_ids(
    session: AsyncSession,
    attachment_ids: list[str],
    *,
    allow_json_fallback: bool = True,
) -> list[StoredAttachment]:
    from .service import load_attachment

    clean_ids = [item.strip() for item in attachment_ids if item.strip()]
    if not clean_ids:
        return []

    uuid_ids = [parse_uuid(item, field_name="attachment_id") for item in clean_ids]
    rows = (
        await session.execute(select(Attachment).where(Attachment.id.in_(uuid_ids)))
    ).scalars().all()
    attachments_by_id = {str(row.id): row for row in rows}

    missing = [item for item in clean_ids if item not in attachments_by_id]
    if missing and not allow_json_fallback:
        raise HTTPException(status_code=404, detail=f"Attachment(s) not found: {', '.join(missing)}")

    loaded: list[StoredAttachment] = []
    for attachment_id in clean_ids:
        row = attachments_by_id.get(attachment_id)
        if row is not None:
            loaded.append(from_db_attachment(row))
            continue
        if allow_json_fallback:
            fallback = load_attachment(attachment_id)
            if fallback is not None:
                loaded.append(fallback)

    if missing and len(loaded) != len(clean_ids):
        unresolved = [item for item in clean_ids if item not in {item.id for item in loaded}]
        if unresolved:
            raise HTTPException(status_code=404, detail=f"Attachment(s) not found: {', '.join(unresolved)}")

    return loaded
