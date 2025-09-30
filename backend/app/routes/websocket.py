"""WebSocket endpoint for realtime chat and audio streaming."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import get_settings
from ..services.streaming import get_streaming_coordinator


router = APIRouter(prefix="/ws", tags=["realtime"])


@router.websocket("/chat")
async def chat_socket(socket: WebSocket) -> None:
    """Handle realtime chat interactions."""

    await socket.accept()
    try:
        while True:
            payload = await socket.receive_json()

            conversation_id = payload.get("conversation_id")
            message_type = payload.get("type")
            if conversation_id is None or message_type is None:
                await socket.send_json({"error": "invalid_payload"})
                continue

            coordinator = await get_streaming_coordinator()

            if message_type == "text":
                text = payload.get("text", "")
                image_ref = payload.get("image_path")
                image_path = None
                stored_image_path = None
                if image_ref:
                    settings = get_settings()
                    raw_image = Path(image_ref)
                    if raw_image.is_absolute():
                        image_path = raw_image
                        try:
                            stored_image_path = raw_image.relative_to(settings.media_root).as_posix()
                        except ValueError:
                            stored_image_path = raw_image.as_posix()
                    else:
                        image_path = settings.media_root / raw_image
                        stored_image_path = raw_image.as_posix()
                async for chunk in coordinator.handle_text_message(
                    conversation_id,
                    text,
                    image_path=image_path,
                    stored_image_path=stored_image_path,
                ):
                    await socket.send_json({"type": chunk.type, "data": chunk.data})
            elif message_type == "audio":
                audio_ref = payload.get("audio_path")
                if not audio_ref:
                    await socket.send_json({"error": "missing_audio_path"})
                    continue
                raw_path = Path(audio_ref)
                settings = get_settings()
                if raw_path.is_absolute():
                    audio_path = raw_path
                    relative_path = raw_path.relative_to(settings.media_root) if raw_path.is_relative_to(settings.media_root) else raw_path
                else:
                    audio_path = settings.media_root / raw_path
                    relative_path = raw_path
                async for chunk in coordinator.handle_voice_message(
                    conversation_id,
                    audio_path,
                    stored_audio_path=str(relative_path).replace("\\", "/"),
                ):
                    await socket.send_json({"type": chunk.type, "data": chunk.data})
            else:
                await socket.send_json({"error": "unsupported_type"})
    except WebSocketDisconnect:
        return

