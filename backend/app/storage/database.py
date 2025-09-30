"""SQLite conversation storage layer."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..config import get_settings


class Base(DeclarativeBase):
    """Base declarative model."""


class DatabaseManager:
    """Manages the async SQLAlchemy engine and sessions."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._engine: AsyncEngine | None = None
        self._session_maker: async_sessionmaker[AsyncSession] | None = None

    def _get_database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self._db_path}"

    async def initialize(self) -> None:
        if self._engine is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._engine = create_async_engine(self._get_database_url(), future=True)
            self._session_maker = async_sessionmaker(self._engine, expire_on_commit=False)

        assert self._engine is not None
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_maker = None

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._session_maker is None:
            raise RuntimeError("DatabaseManager not initialized")
        session = self._session_maker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


_db_manager: DatabaseManager | None = None


async def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        settings = get_settings()
        _db_manager = DatabaseManager(settings.conversation_db_path)
        await _db_manager.initialize()
    return _db_manager


async def shutdown_database() -> None:
    global _db_manager
    if _db_manager is not None:
        await _db_manager.dispose()
        _db_manager = None

