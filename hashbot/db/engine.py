"""Async database engine and session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hashbot.config import get_settings

_engine = None
_session_factory = None


async def init_db() -> None:
    """Create async engine, session factory, and run create_all."""
    global _engine, _session_factory

    settings = get_settings()
    _engine = create_async_engine(settings.database_url, echo=False)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    from hashbot.db.models import Base

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_db() -> AsyncSession:
    """Return a new async session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _session_factory()


async def close_db() -> None:
    """Dispose engine on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
