from datetime import datetime

import pytest
from httpx import AsyncClient

from optimized_shifts.state import DatabaseConnection


@pytest.mark.asyncio
async def test_create_point_sending_json_request(
    test_app: AsyncClient, test_db: DatabaseConnection
):
    utcnow = datetime.utcnow().replace(microsecond=0)
    request = {
        "data_type": "json",
        "data": [
            {
                "region": "Paris",
                "origin": "[1.0, 1.0]",
                "destination": "[1.5, 1.0]",
                "timestamp": utcnow.strftime("%Y-%m-%d %H:%M:%S"),
                "source": "test_point",
            }
        ],
    }

    response = await test_app.post("/api/v1/trips", json=request)

    assert response.status_code == 201, response.text
    region_fetch = await test_db.fetch("SELECT * FROM regions")
    point_fetch = await test_db.fetch("SELECT * FROM trips")

    assert len(region_fetch) == 1
    assert len(point_fetch) == 1

    region = region_fetch[0]
    point = point_fetch[0]

    assert region.get("region_name") == "Paris"
    assert point.get("region_id") == region["region_id"]
    assert point.get("timestamp") == utcnow
    assert point.get("source") == "test_point"
