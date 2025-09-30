"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .services.audio import get_speech_service, shutdown_speech_service
from .services.llm import get_llm_client
from .storage.database import get_db_manager, shutdown_database
from .routes import conversations, media, settings, websocket


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan hooks for initializing heavy resources."""

    app_settings = get_settings()
    logger.info(
        "Starting realtime-chat backend with LLM host=%s model=%s",
        app_settings.LLM.host,
        app_settings.LLM.model,
    )

    # Initialize database and other heavy resources.
    await get_db_manager()
    await get_speech_service()
    await get_llm_client()
    logger.info("Database initialized at %s", app_settings.conversation_db_path)
    yield

    # Graceful shutdown / cleanup
    await shutdown_database()
    await shutdown_speech_service()
    logger.info("Stopping realtime-chat backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app_settings = get_settings()
    app = FastAPI(title="Realtime Voice Chat", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost",
            "http://localhost:8000",
            "http://localhost:8080",
            "https://localhost",
            "https://localhost:8000",
            "https://localhost:8080",
            "http://127.0.0.1",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8080",
            "https://127.0.0.1",
            "https://127.0.0.1:8000",
            "https://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(conversations.router)
    app.include_router(media.router)
    app.include_router(settings.router)
    app.include_router(websocket.router)

    media_root = app_settings.media_root
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=media_root), name="media")

    return app

