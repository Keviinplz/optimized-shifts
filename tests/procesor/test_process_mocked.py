import tempfile

import pytest

from optimized_shifts.celery.tasks import process_data_task
from optimized_shifts.state import DatabaseConnection


@pytest.mark.asyncio
async def test_process_mocked_csv(test_db: DatabaseConnection):
    csv = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8")
    try:
        csv.write(
            """region,origin_coord,destination_coord,datetime,datasource
Prague,POINT (14.4973794438195 50.00136875782316),POINT (14.43109483523328 50.04052930943246),2018-05-28 09:03:40,funny_car
Turin,POINT (7.672837913286881 44.9957109242058),POINT (7.720368637535126 45.06782385393849),2018-05-21 02:54:04,baba_car
Prague,POINT (14.32427345662177 50.00002074358429),POINT (14.47767895969969 50.09339790740321),2018-05-13 08:52:25,cheap_mobile"""
        )
        csv.seek(0)
        await process_data_task("mocked", csv.name)

        row = await test_db.fetchrow("SELECT count(*) FROM trips")

        assert row is not None
        assert row.get("count") == 3

        row = await test_db.fetchrow("SELECT count(*) FROM regions")

        assert row is not None
        assert row.get("count") == 2

    finally:
        csv.close()
