#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from server.core.config import get_settings
from server.db.models import Conversation, Message
from server.db.session import AsyncSessionLocal, async_engine


@dataclass
class SeedStats:
    existing_conversation_count: int
    created_conversations: int
    created_messages: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed an arbitrary number of synthetic conversations for local testing.",
    )
    parser.add_argument(
        "--count",
        required=True,
        type=int,
        help="Number of conversations to create.",
    )
    parser.add_argument(
        "--messages-per-conversation",
        type=int,
        default=4,
        help="Number of synthetic messages to create in each conversation (default: 4).",
    )
    parser.add_argument(
        "--title-prefix",
        default="Seed Conversation",
        help="Prefix used for conversation titles (default: 'Seed Conversation').",
    )
    parser.add_argument(
        "--minutes-between-conversations",
        type=int,
        default=15,
        help="Gap between conversations for timestamp staggering (default: 15).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Commit every N conversations (default: 100).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Execute seeding without interactive confirmation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be created.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running against non-dev environments.",
    )
    args = parser.parse_args()

    if args.count <= 0:
        raise SystemExit("--count must be greater than 0.")
    if args.messages_per_conversation < 0:
        raise SystemExit("--messages-per-conversation must be 0 or greater.")
    if args.minutes_between_conversations < 0:
        raise SystemExit("--minutes-between-conversations must be 0 or greater.")
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be greater than 0.")
    return args


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


def build_message_content(*, conversation_seq: int, message_seq: int, role: str) -> str:
    if role == "user":
        return (
            f"[Seed {conversation_seq}] User prompt #{message_seq + 1}: "
            "Review campaign performance and recommend the next action."
        )
    return (
        f"[Seed {conversation_seq}] Assistant response #{message_seq + 1}: "
        "Summary generated for sidebar pagination load testing."
    )


async def get_existing_conversation_count() -> int:
    async with AsyncSessionLocal() as session:
        return int(await session.scalar(select(func.count(Conversation.id))) or 0)


async def seed_conversations(args: argparse.Namespace) -> SeedStats:
    now = datetime.now(timezone.utc)
    existing_count = await get_existing_conversation_count()

    created_conversations = 0
    created_messages = 0
    async with AsyncSessionLocal() as session:
        for offset in range(args.count):
            sequence = existing_count + offset + 1
            created_at = now - timedelta(
                minutes=offset * args.minutes_between_conversations,
            )
            conversation = Conversation(
                title=f"{args.title_prefix} {sequence}",
                created_at=created_at,
                updated_at=created_at,
            )
            session.add(conversation)
            await session.flush()

            last_activity = created_at
            for message_offset in range(args.messages_per_conversation):
                role = "user" if message_offset % 2 == 0 else "assistant"
                message_time = created_at + timedelta(seconds=message_offset + 1)
                content = build_message_content(
                    conversation_seq=sequence,
                    message_seq=message_offset,
                    role=role,
                )
                token_estimate = max(1, len(content) // 4)
                session.add(
                    Message(
                        conversation_id=conversation.id,
                        role=role,
                        content=content,
                        token_estimate=token_estimate,
                        tokenizer_name="char4_approx_v1",
                        message_kind="normal",
                        created_at=message_time,
                    )
                )
                last_activity = message_time
                created_messages += 1

            conversation.updated_at = last_activity
            created_conversations += 1

            if created_conversations % args.batch_size == 0:
                await session.commit()

        if created_conversations % args.batch_size != 0:
            await session.commit()

    return SeedStats(
        existing_conversation_count=existing_count,
        created_conversations=created_conversations,
        created_messages=created_messages,
    )


def print_plan(args: argparse.Namespace, *, existing_count: int) -> None:
    print("Seed plan")
    print(f"- existing_conversations: {existing_count}")
    print(f"- conversations_to_create: {args.count}")
    print(f"- messages_per_conversation: {args.messages_per_conversation}")
    print(f"- total_messages_to_create: {args.count * args.messages_per_conversation}")
    print(f"- title_prefix: {args.title_prefix}")
    print(f"- minutes_between_conversations: {args.minutes_between_conversations}")
    print(f"- batch_size: {args.batch_size}")


async def main() -> int:
    args = parse_args()
    ensure_dev_target(force=args.force)

    existing_count = await get_existing_conversation_count()
    print_plan(args, existing_count=existing_count)

    if args.dry_run:
        print("Dry run complete. No data was created.")
        return 0

    if not args.yes:
        print("Aborted: pass --yes to execute seeding (or --dry-run to preview).")
        return 1

    stats = await seed_conversations(args)
    print("Seed complete")
    print(f"- existing_conversations_before: {stats.existing_conversation_count}")
    print(f"- created_conversations: {stats.created_conversations}")
    print(f"- created_messages: {stats.created_messages}")
    print(
        f"- total_conversations_after: "
        f"{stats.existing_conversation_count + stats.created_conversations}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    finally:
        asyncio.run(async_engine.dispose())
