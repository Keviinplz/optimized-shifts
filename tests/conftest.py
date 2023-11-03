import asyncio
import os

import aiofiles
import asyncpg
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import AsyncClient

from main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)  # type: ignore # noqa
async def initialize_test_database():
    host = os.environ.get("POSTGRES_HOST")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    database = os.environ.get("POSTGRES_DB")

    assert (
        database == "test"
    ), "Attempt to run tests in a non-test database, aborting..."

    async with aiofiles.open(os.path.join(os.getcwd(), "init.sql")) as f:
        q = await f.read()

    try:
        pool = await asyncpg.create_pool(
            host=host,
            user=user,
            password=password,
            database=database,
        )
    except asyncpg.InvalidCatalogNameError:
        sys_conn = await asyncpg.connect(
            database="template1", user=user, password=password
        )
        await sys_conn.execute(f'CREATE DATABASE "{database}" OWNER "{user}"')

        await sys_conn.close()
        pool = await asyncpg.create_pool(
            host=host,
            user=user,
            password=password,
            database=database,
        )

    if not pool:
        raise ValueError("Unable to create connection with database")

    async with pool.acquire() as conn:
        await conn.execute(q)

    await pool.close()

    yield

    sys_conn = await asyncpg.connect(database="template1", user=user, password=password)

    await sys_conn.execute(
        """
        SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1;
        """,
        database,
    )
    await sys_conn.execute('DROP DATABASE IF EXISTS "{database}"')
    await sys_conn.close()


@pytest_asyncio.fixture()  # type: ignore  # noqa
async def test_db():
    host = os.environ.get("POSTGRES_HOST")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    database = os.environ.get("POSTGRES_DB")

    assert (
        database == "test"
    ), "Attempt to run tests in a non-test database, aborting..."

    conn = await asyncpg.connect(
        host=host, user=user, password=password, database=database
    )

    yield conn

    await conn.close()


@pytest_asyncio.fixture()  # type: ignore  # noqa
async def test_app():
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
