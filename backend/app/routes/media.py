"""Media upload endpoints for images or other attachments."""

from __future__ import annotations

import logging
import secrets
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from ..config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/media", tags=["media"])


async def _save_upload(file: UploadFile, subdir: str) -> Path:
    settings = get_settings()
    sub_path = Path(subdir)
    target_dir = settings.media_root / sub_path
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "upload").suffix or ".bin"
    name = secrets.token_hex(8) + suffix
    relative_path = sub_path / name
    destination = settings.media_root / relative_path
    content = await file.read()
    destination.write_bytes(content)
    return relative_path


@router.post("/images")
async def upload_image(file: UploadFile) -> dict[str, str]:
    relative = await _save_upload(file, "images")
    return {
        "path": f"/media/{relative.as_posix()}",
        "relative_path": relative.as_posix(),
    }


@router.post("/audio")
async def upload_audio(file: UploadFile) -> dict[str, str]:
    try:
        relative = await _save_upload(file, "audio/input")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to save uploaded audio: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store audio") from exc

    return {
        "path": f"/media/{relative.as_posix()}",
        "relative_path": relative.as_posix(),
    }