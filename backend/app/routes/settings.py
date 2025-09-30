"""Endpoints for retrieving and updating runtime settings."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..config import AppSettings, get_settings, patch_settings


router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def read_settings() -> AppSettings:
    """Return current application settings."""

    return get_settings()


@router.patch("")
async def update_settings(payload: dict) -> AppSettings:
    """Apply partial updates to settings."""

    try:
        return patch_settings(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

