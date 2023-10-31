from typing import TypeAlias, TypedDict

import asyncpg

Database: TypeAlias = "asyncpg.Pool[asyncpg.Record]"


class State(TypedDict):
    database: Database
