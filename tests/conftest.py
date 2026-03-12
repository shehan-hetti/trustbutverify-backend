"""
conftest.py — shared fixtures for backend tests.

Sets up an in-memory SQLite async engine so that integration tests
run without Docker / MySQL.

We override the DATABASE_URL setting *before* any app imports so the
module-level engine in app.database uses SQLite instead of MySQL.

MySQL-specific column types (TINYINT, MySQLDateTime) are given SQLite
compilation rules via @compiles so Base.metadata.create_all succeeds.
"""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio

# ---- Register cross-dialect type compilers BEFORE model import ------
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.dialects.mysql import DATETIME as MySQLDateTime


@compiles(TINYINT, "sqlite")
def _compile_tinyint_sqlite(type_, compiler, **kw):
    return "INTEGER"


@compiles(MySQLDateTime, "sqlite")
def _compile_mysql_datetime_sqlite(type_, compiler, **kw):
    return "DATETIME"


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(type_, compiler, **kw):
    """SQLite only auto-increments INTEGER PRIMARY KEY columns.
    Mapping BigInteger → INTEGER lets autoincrement work transparently."""
    return "INTEGER"


# ---- Override settings BEFORE any app module is imported --------
import app.config as _config_module  # noqa: E402
_config_module.settings.DATABASE_URL = "sqlite+aiosqlite://"  # type: ignore[assignment]

# NOW safe to import the rest of the app — engine will use SQLite.
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402

from app.models import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.database import engine, get_db  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
