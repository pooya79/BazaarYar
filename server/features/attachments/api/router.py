from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.models import Attachment
from server.db.session import get_db_session
from server.features.agent.api import streaming as agent_streaming
from server.features.agent.api.schemas import UploadAttachmentsResponse, UploadedAttachment
from server.features.attachments import (
    StoredAttachment,
    resolve_storage_path,
)
from server.features.shared.ids import parse_uuid

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/attachments/{attachment_id}/content")
async def get_attachment_content(
    attachment_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> FileResponse:
    file_uuid = parse_uuid(attachment_id, field_name="attachment_id")
    row = await session.get(Attachment, file_uuid)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Attachment '{attachment_id}' was not found.")
    path = resolve_storage_path(row.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Attachment file '{attachment_id}' is missing.")
    return FileResponse(path, media_type=row.content_type, filename=row.filename)


@router.post("/attachments", response_model=UploadAttachmentsResponse)
async def upload_attachments(
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> UploadAttachmentsResponse:
    if not files:
        raise HTTPException(status_code=400, detail="Provide at least one file.")

    uploaded: list[StoredAttachment] = []
    for file in files:
        uploaded.append(await agent_streaming.store_uploaded_file(file))

    await agent_streaming.save_uploaded_attachments(session, uploaded)

    return UploadAttachmentsResponse(
        files=[
            UploadedAttachment(
                id=item.id,
                filename=item.filename,
                content_type=item.content_type,
                media_type=item.media_type,
                size_bytes=item.size_bytes,
                preview_text=item.preview_text,
                extraction_note=item.extraction_note,
            )
            for item in uploaded
        ]
    )
