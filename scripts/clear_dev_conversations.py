#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, func, select

from server.core.config import get_settings
from server.db.models import Attachment, Conversation, Message, MessageAttachment
from server.db.session import AsyncSessionLocal, async_engine
from server.features.attachments.service import resolve_storage_path


@dataclass
class CleanupStats:
    conversation_count: int
    message_count: int
    message_attachment_count: int
    attachment_ids: list[UUID]
    storage_paths: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove all conversations, messages, and linked attachment files from the dev database.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Execute deletion without interactive confirmation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be deleted.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running against non-dev environments.",
    )
    return parser.parse_args()


def ensure_dev_target(*, force: bool) -> None:
    settings = get_settings()
    environment = settings.environment.lower()
    db_name = settings.db_name.lower()

    looks_like_dev = environment in {"development", "dev", "local"} or "dev" in db_name
    if looks_like_dev or force:
        return

    raise SystemExit(
        "Refusing to run outside a dev-like database target. "
        "Set ENVIRONMENT=development / DB_NAME containing 'dev', or pass --force."
    )


async def collect_stats() -> CleanupStats:
    async with AsyncSessionLocal() as session:
        conversation_count = int(await session.scalar(select(func.count(Conversation.id))) or 0)
        message_count = int(await session.scalar(select(func.count(Message.id))) or 0)
        message_attachment_count = int(
            await session.scalar(select(func.count()).select_from(MessageAttachment)) or 0
        )

        attachment_rows = (
            await session.execute(
                select(Attachment.id, Attachment.storage_path)
                .join(
                    MessageAttachment,
                    MessageAttachment.attachment_id == Attachment.id,
                )
                .distinct()
            )
        ).all()

    attachment_ids = [row.id for row in attachment_rows]
    storage_paths = [row.storage_path for row in attachment_rows]
    return CleanupStats(
        conversation_count=conversation_count,
        message_count=message_count,
        message_attachment_count=message_attachment_count,
        attachment_ids=attachment_ids,
        storage_paths=storage_paths,
    )


def remove_files(storage_paths: list[str]) -> tuple[int, int, list[str]]:
    deleted = 0
    missing = 0
    failed: list[str] = []

    for raw_path in storage_paths:
        path = resolve_storage_path(raw_path)
        try:
            if not path.exists():
                missing += 1
                continue
            path.unlink()
            deleted += 1
        except OSError as exc:
            failed.append(f"{path}: {exc}")

    return deleted, missing, failed


async def execute_delete(stats: CleanupStats) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Conversation))
        if stats.attachment_ids:
            await session.execute(delete(Attachment).where(Attachment.id.in_(stats.attachment_ids)))
        await session.commit()


def print_plan(stats: CleanupStats) -> None:
    print("Cleanup plan")
    print(f"- conversations: {stats.conversation_count}")
    print(f"- messages: {stats.message_count}")
    print(f"- message_attachments: {stats.message_attachment_count}")
    print(f"- attachments_to_remove: {len(stats.attachment_ids)}")
    print(f"- files_to_remove: {len(stats.storage_paths)}")


async def main() -> int:
    args = parse_args()
    ensure_dev_target(force=args.force)

    stats = await collect_stats()
    print_plan(stats)

    if args.dry_run:
        print("Dry run complete. No data was deleted.")
        return 0

    if not args.yes:
        print("Aborted: pass --yes to execute deletion (or --dry-run to preview).")
        return 1

    await execute_delete(stats)
    deleted_files, missing_files, failed_files = remove_files(stats.storage_paths)

    print("Cleanup complete")
    print(f"- deleted conversations: {stats.conversation_count}")
    print(f"- deleted messages: {stats.message_count}")
    print(f"- deleted attachments: {len(stats.attachment_ids)}")
    print(f"- deleted files: {deleted_files}")
    print(f"- missing files: {missing_files}")
    if failed_files:
        print("- file delete errors:")
        for error in failed_files:
            print(f"  - {error}")
        return 2

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    finally:
        asyncio.run(async_engine.dispose())
