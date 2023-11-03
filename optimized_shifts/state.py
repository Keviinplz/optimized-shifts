from typing import TypeAlias, TypedDict
from optimized_shifts.ws import ConnectionManager

import asyncpg

Database: TypeAlias = "asyncpg.Pool[asyncpg.Record]"
DatabaseState: TypeAlias = "Database | None"
DatabaseConnection: TypeAlias = "asyncpg.Connection[asyncpg.Record]"


class State(TypedDict):
    database: DatabaseState
    manager: ConnectionManager | None 


state: State = {"database": None, "manager": None}
