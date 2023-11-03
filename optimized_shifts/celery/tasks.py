import os
from typing import cast

import asyncpg

from .cloud.buckets import DataProcesorFactory, DataProcesorTypes


async def process_data_task(
    data_type: DataProcesorTypes,
    data: str,
):  # type: ignore
    processor = DataProcesorFactory.create(data_type)

    df = processor.data_to_pandas(data)

    if df is None:
        return None

    host = os.environ.get("POSTGRES_HOST")
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    database = os.environ.get("POSTGRES_DB")

    regions = set(df["region"].unique())  # type: ignore
    regions_id_mapped: dict[str, int | None] = {region: None for region in regions}

    conn = await asyncpg.connect(
        host=host, user=user, password=password, database=database
    )
    prepared = ", ".join(f"${i+1}" for i in range(len(regions)))
    stmt = f"""SELECT region_id, region_name FROM regions WHERE region_name in ({prepared})"""
    rows = await conn.fetch(stmt, *regions)
    for row in rows:
        regions_id_mapped[row["region_name"]] = row["region_id"]

    # Insert regions that doesn't exists yet
    to_insert = [key for key, value in regions_id_mapped.items() if value is None]
    stmt = """
        INSERT INTO regions (region_name) (
            SELECT r.region_name 
            FROM unnest($1::regions[]) as r
        ) 
        RETURNING region_id, region_name
    """
    rows = await conn.fetch(stmt, [(None, name) for name in to_insert])
    for row in rows:
        regions_id_mapped[row["region_name"]] = row["region_id"]

    stmt = """
    INSERT INTO trips (region_id, origin, destination, timestamp, source) (
        SELECT r.region_id, r.origin, r.destination, r.timestamp, r.source
        FROM unnest($1::trips[]) as r
    )
    RETURNING trip_id, region_id, origin, destination, timestamp, source
    """
    return await conn.fetch(
        stmt,
        [
            (
                None,
                cast(int, regions_id_mapped[df.loc[i, "region"]]),  # type: ignore
                (df.loc[i, "origin_x"], df.loc[i, "origin_y"]),
                (df.loc[i, "destination_x"], df.loc[i, "destination_y"]),
                df.loc[i, "timestamp"],
                df.loc[i, "source"],
            )
            for i in range(len(df))
        ],
    )
