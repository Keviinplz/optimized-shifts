from typing import TypeAlias, TypedDict

import asyncpg

Database: TypeAlias = "asyncpg.Pool[asyncpg.Record]"
DatabaseState: TypeAlias = "Database | None"
DatabaseConnection: TypeAlias = "asyncpg.Connection[asyncpg.Record]"


class State(TypedDict):
    database: DatabaseState


state: State = {"database": None}
