from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from offload.config import get_settings
from offload.models import Base

_engine = None
_session_factory = None


def _init_engine(database_url: str | None = None):
    global _engine, _session_factory
    url = database_url or get_settings().database_url
    _engine = create_async_engine(url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def init_db(database_url: str | None = None) -> None:
    engine = _init_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        _init_engine()
    async with _session_factory() as s:
        yield s
