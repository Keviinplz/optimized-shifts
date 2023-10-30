import asyncio

import pytest
import pytest_asyncio
from httpx import AsyncClient

from main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture()  # type: ignore  # noqa
async def test_app():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
