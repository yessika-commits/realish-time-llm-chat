"""Conversation management utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy import delete, select, update

from ..config import get_settings
from ..storage import Conversation, Message, get_db_manager


def _normalize_media_path(path: Optional[str]) -> Optional[str]:
    if not path:
        return None

    value = str(path).replace("\\", "/")
    if value.startswith("/media/"):
        value = value[len("/media/") :]

    original_path = Path(path)
    if original_path.is_absolute():
        settings = get_settings()
        try:
            return original_path.relative_to(settings.media_root).as_posix()
        except ValueError:
            # Path lies outside media root; fall back to cleaned string
            return value

    return value


def serialize_conversation(conversation: Conversation) -> dict[str, object]:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }


def serialize_message(message: Message) -> dict[str, object]:
    audio_path = _normalize_media_path(message.audio_path)
    image_path = _normalize_media_path(message.image_path)
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "audio_path": audio_path,
        "image_path": image_path,
    }


async def list_conversation_dtos() -> list[dict[str, object]]:
    db = await get_db_manager()
    async with db.session() as session:
        result = await session.execute(select(Conversation))
        conversations = result.scalars().all()
    return [serialize_conversation(convo) for convo in conversations]


async def get_conversation_with_messages(conversation_id: str) -> Optional[dict[str, object]]:
    db = await get_db_manager()
    async with db.session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            return None
        await session.refresh(conversation, attribute_names=["messages"])
        messages = [
            serialize_message(message)
            for message in sorted(conversation.messages, key=lambda m: m.created_at)
        ]
        return {
            **serialize_conversation(conversation),
            "messages": messages,
        }


async def create_conversation(title: Optional[str] = "New Conversation") -> Conversation:
    """Creates a new conversation with a generated UUID for its ID."""
    db = await get_db_manager()
    async with db.session() as session:
        # The fix is here: generate an ID before creating the Conversation object.
        conversation = Conversation(id=uuid4().hex, title=title)
        session.add(conversation)
        await session.flush()  # Ensures the object is persisted in the session before commit
        await session.refresh(conversation) # Loads db-defaults like created_at
        return conversation


async def rename_conversation(conversation_id: str, title: str) -> bool:
    db = await get_db_manager()
    async with db.session() as session:
        result = await session.execute(
            update(Conversation).where(Conversation.id == conversation_id).values(title=title)
        )
        return result.rowcount > 0


async def delete_conversation(conversation_id: str) -> bool:
    db = await get_db_manager()
    async with db.session() as session:
        result = await session.execute(delete(Conversation).where(Conversation.id == conversation_id))
        return result.rowcount > 0


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    audio_path: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Message:
    db = await get_db_manager()
    async with db.session() as session:
        conversation = await session.get(Conversation, conversation_id)
        if conversation is None:
            conversation = Conversation(id=conversation_id, title="New Conversation")
            session.add(conversation)
        normalized_audio_path = _normalize_media_path(audio_path)
        normalized_image_path = _normalize_media_path(image_path)

        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            audio_path=normalized_audio_path,
            image_path=normalized_image_path,
        )
        session.add(message)
        await session.flush()
        await session.refresh(message)
        return message


async def update_message_audio_path(message_id: int, audio_path: str) -> None:
    db = await get_db_manager()
    async with db.session() as session:
        message = await session.get(Message, message_id)
        if message is None:
            return
        message.audio_path = _normalize_media_path(audio_path)


async def delete_all_conversations() -> None:
    db = await get_db_manager()
    async with db.session() as session:
        await session.execute(delete(Message))
        await session.execute(delete(Conversation))