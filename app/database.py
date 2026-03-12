from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# SQLite does not support pool_size / max_overflow; only apply them for
# connection-pool-capable backends like MySQL/PostgreSQL.
_engine_kwargs: dict = {"echo": False}
if "sqlite" not in settings.DATABASE_URL:
    _engine_kwargs.update(pool_size=10, max_overflow=5, pool_pre_ping=True)

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields an async DB session."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
