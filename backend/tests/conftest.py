import os
import tempfile

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://stock_pos:stock_pos@localhost:55432/stock_pos_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:56379/5")
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MINUTE", "1000")
os.environ.setdefault("RATE_LIMIT_REFRESH_PER_MINUTE", "1000")
os.environ.setdefault("RATE_LIMIT_RESET_PER_HOUR", "1000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault(
    "LOCAL_STORAGE_DIR",
    tempfile.mkdtemp(prefix="stock-pos-media-"),
)

import asyncio
from typing import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
ADMIN_DB_URL = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
TEST_DB_NAME = TEST_DATABASE_URL.rsplit("/", 1)[1]

@pytest.fixture(scope="session")
def _prepare_database() -> None:
    async def _run() -> None:
        admin_engine = create_async_engine(ADMIN_DB_URL, isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as conn:
            exists = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
            )
            if exists.scalar() is None:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
        await admin_engine.dispose()

        from app.core import database as db_module
        from app.core.database import Base

        import app.modules.administration.models  # noqa: F401
        import app.modules.auth.models  # noqa: F401
        import app.modules.brands.models  # noqa: F401
        import app.modules.categories.models  # noqa: F401
        import app.modules.customers.models  # noqa: F401
        import app.modules.pos.models  # noqa: F401
        import app.modules.reports.models  # noqa: F401
        import app.modules.stock.models  # noqa: F401
        import app.modules.suppliers.models  # noqa: F401
        import app.shared.audit.models  # noqa: F401
        import app.shared.documents.models  # noqa: F401

        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.run_sync(Base.metadata.create_all)

        temp_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        original_factory = db_module.SessionFactory
        db_module.SessionFactory = temp_factory
        try:
            from app.seed import seed

            await seed()

        finally:
            db_module.SessionFactory = original_factory
        await engine.dispose()

    asyncio.run(_run())


@pytest_asyncio.fixture
async def db_session(_prepare_database) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(_prepare_database) -> AsyncIterator[httpx.AsyncClient]:
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
