""" Módulo que define el comportamiento de inicio y cierre de la aplicación """

import contextlib
import os

import asyncpg
from fastapi import FastAPI

from optimized_shifts.state import state
from optimized_shifts.ws import ConnectionManager


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """ Inicializa la base de datos y los estados globales, una vez finalizada cierra la conexión con la base de datos"""
    host = os.environ.get("POSTGRES_HOST")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    database = os.environ.get("POSTGRES_DB")

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
        raise Exception("Unable to connect with database")

    state["database"] = pool
    state["manager"] = ConnectionManager()

    yield

    await pool.close()
