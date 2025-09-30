"""Conversation management endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import get_settings
from ..services import conversations as convo_service
from ..services.conversations import delete_all_conversations

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


async def _remove_media_for_conversation(conversation_id: str) -> None:
    settings = get_settings()
    media_root = settings.media_root
    conversation = await convo_service.get_conversation_with_messages(conversation_id)
    if not conversation:
        return
    for message in conversation["messages"]:
        for path_attr in (message.get("audio_path"), message.get("image_path")):
            if not path_attr:
                continue
            absolute = media_root / path_attr
            if absolute.exists():
                try:
                    absolute.unlink()
                except OSError:
                    continue


@router.get("")
async def list_conversations() -> list[dict[str, str]]:
    """Return available conversations."""

    return await convo_service.list_conversation_dtos()


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict[str, object]:
    """Return a conversation transcript."""

    conversation = await convo_service.get_conversation_with_messages(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("")
async def create_conversation(payload: dict[str, str]) -> dict[str, object]:
    title = payload.get("title", "New Conversation")
    conversation = await convo_service.create_conversation(title=title)
    return convo_service.serialize_conversation(conversation)


@router.patch("/{conversation_id}")
async def rename_conversation(conversation_id: str, payload: dict[str, str]) -> dict[str, object]:
    title = payload.get("title")
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    updated = await convo_service.rename_conversation(conversation_id, title)
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation = await convo_service.get_conversation_with_messages(conversation_id)
    assert conversation is not None
    return conversation


@router.delete("/{conversation_id}")
async def remove_conversation(conversation_id: str) -> dict[str, str]:
    conversation = await convo_service.get_conversation_with_messages(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await _remove_media_for_conversation(conversation_id)
    deleted = await convo_service.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted"}


@router.delete("")
async def remove_all_conversations() -> dict[str, str]:
    settings = get_settings()
    media_root = settings.media_root
    if media_root.exists():
        for path in list(media_root.rglob("*")):
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    continue
    await delete_all_conversations()
    return {"status": "cleared"}

