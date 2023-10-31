import contextlib
import os
from typing import AsyncIterator

import asyncpg
from fastapi import FastAPI

from optimized_shifts.state import State


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[State]:
    pool = await asyncpg.create_pool(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        user=os.environ.get("POSTGRES_USER", "development"),
        password=os.environ.get("POSTGRES_PASSWORD", "insecure-password"),
        database=os.environ.get("POSTGRES_DB", "app"),
    )

    if not pool:
        raise Exception("Unable to connect with database")

    yield {"database": pool}

    await pool.close()
