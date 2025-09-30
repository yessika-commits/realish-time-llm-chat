"""Coordinator for realtime streaming conversation flows."""

from __future__ import annotations

import base64
import logging
import mimetypes
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Optional

from ..config import get_settings
from ..storage import Conversation, Message, get_db_manager
from ..utils import clean_llm_text
from .audio import get_speech_service
from .llm import get_llm_client
from .conversations import add_message, rename_conversation, update_message_audio_path
from .llm_naming import get_conversation_title


@dataclass
class StreamingChunk:
    """Represents a chunk of streamed data."""

    type: str
    data: dict[str, str]


logger = logging.getLogger(__name__)


class StreamingCoordinator:
    """Coordinates STT, LLM streaming, and TTS playback."""

    async def handle_voice_message(
        self,
        conversation_id: str,
        audio_path: Path,
        image_path: Optional[Path] = None,
        stored_audio_path: Optional[str] = None,
    ) -> AsyncIterator[StreamingChunk]:
        speech_service = await get_speech_service()
        transcription = await speech_service.transcribe_audio(audio_path)

        transcription_text = transcription or ""
        normalized_audio_path = (
            stored_audio_path.replace("\\", "/")
            if stored_audio_path
            else str(audio_path).replace("\\", "/")
        )
        yield StreamingChunk(
            type="transcription",
            data={
                "content": transcription_text,
                "audio_path": normalized_audio_path,
            },
        )

        async for chunk in self.handle_text_message(
            conversation_id,
            transcription,
            image_path=image_path,
            user_audio_path=stored_audio_path,
        ):
            yield chunk

    async def handle_text_message(
        self,
        conversation_id: str,
        text: str,
        image_path: Optional[Path] = None,
        user_audio_path: Optional[str] = None,
        stored_image_path: Optional[str] = None,
    ) -> AsyncIterator[StreamingChunk]:
        user_message = await add_message(
            conversation_id,
            role="user",
            content=text,
            image_path=stored_image_path or (str(image_path) if image_path else None),
        )
        if user_audio_path:
            await update_message_audio_path(user_message.id, user_audio_path)

        llm = await get_llm_client()
        messages = await self._load_messages(conversation_id)
        llm_messages = await self._build_llm_messages(messages)
        buffer = []
        assistant_message_id: int | None = None
        new_title: str | None = None
        async for event in llm.stream_chat(llm_messages):
            if event.get("done"):
                break
            if "message" in event:
                raw_content = event["message"].get("content", "")
                content_piece = clean_llm_text(raw_content)
                if content_piece:
                    buffer.append(content_piece)
                    yield StreamingChunk(type="assistant_delta", data={"content": content_piece})
        if buffer:
            full_content = "".join(buffer)
            assistant_message = await add_message(conversation_id, role="assistant", content=full_content)
            assistant_message_id = assistant_message.id
            new_title = await self._maybe_assign_conversation_title(
                conversation_id,
                messages,
                user_message,
                full_content,
            )
        else:
            assistant_message_id = None

        # Optionally synthesize audio response
        speech_service = await get_speech_service()
        audio_path = await speech_service.synthesize_speech("".join(buffer) or "")
        if audio_path and assistant_message_id:
            settings = get_settings()
            try:
                relative_path = audio_path.relative_to(settings.media_root)
            except ValueError:
                relative_path = audio_path
            normalized_path = relative_path.as_posix()
            await update_message_audio_path(assistant_message_id, normalized_path)
            yield StreamingChunk(type="assistant_audio", data={"audio_path": normalized_path})

        if new_title is not None:
            yield StreamingChunk(
                type="conversation_title",
                data={"title": new_title, "conversation_id": conversation_id},
            )

    async def _load_messages(self, conversation_id: str) -> list[dict[str, str]]:
        db = await get_db_manager()
        async with db.session() as session:
            result = await session.execute(
                Message.__table__.select().where(Message.conversation_id == conversation_id).order_by(Message.id)
            )
            rows = result.fetchall()
        return [
            {"role": row.role, "content": row.content, "image_path": row.image_path}
            for row in rows
        ]

    async def _build_llm_messages(self, messages: list[dict[str, str]]) -> list[dict[str, object]]:
        settings = get_settings()
        llm_messages: list[dict[str, object]] = []
        for message in messages:
            role = message.get("role") or "user"
            content_text = message.get("content") or ""
            image_path = message.get("image_path")
            if image_path:
                try:
                    data_uri = self._image_path_to_data_uri(self._resolve_image_path(str(image_path)))
                except FileNotFoundError:
                    logger.warning("Image not found for LLM payload: %s", image_path)
                    continue
                parts = [
                    {
                        "type": "image_url",
                        "image_url": {"url": data_uri, "detail": "high"},
                    }
                ]
                if content_text and content_text.strip() and content_text.strip() != "[image]":
                    parts.append({"type": "text", "text": content_text})
                llm_messages.append({"role": role, "content": parts})
            else:
                llm_messages.append({"role": role, "content": content_text})
        return llm_messages

    @staticmethod
    def _resolve_image_path(image_path: str) -> Path:
        settings = get_settings()
        normalized = image_path.replace("\\", "/")
        if normalized.startswith("/media/"):
            normalized = normalized[len("/media/") :]
        return settings.media_root / normalized

    @staticmethod
    def _image_path_to_data_uri(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(path)
        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type:
            mime_type = "image/png"
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime_type};base64,{b64}"

    async def _maybe_assign_conversation_title(
        self,
        conversation_id: str,
        prior_messages: list[dict[str, str]],
        user_message: Message,
        assistant_text: str,
    ) -> str | None:
        if not user_message.content or not assistant_text:
            return None
        if any(msg["role"] == "assistant" for msg in prior_messages if msg is not None):
            return None
        db = await get_db_manager()
        async with db.session() as session:
            conversation = await session.get(Conversation, conversation_id)
            if conversation is None or conversation.title != "New Conversation":
                return None
        proposal = await get_conversation_title(user_message.content, assistant_text)
        if not proposal:
            return None
        updated = await rename_conversation(conversation_id, proposal)
        return proposal if updated else None


_streaming_coordinator: StreamingCoordinator | None = None


async def get_streaming_coordinator() -> StreamingCoordinator:
    global _streaming_coordinator
    if _streaming_coordinator is None:
        _streaming_coordinator = StreamingCoordinator()
    return _streaming_coordinator


