from datetime import datetime
from itertools import chain, combinations
from urllib.parse import urlencode

import pytest
import pytest_asyncio
from httpx import AsyncClient

from optimized_shifts.state import DatabaseConnection


@pytest_asyncio.fixture  # type: ignore # noqa
async def poblate_test_data(test_db: DatabaseConnection):
    stmt = """
    INSERT INTO regions (region_name) (
        SELECT r.region_name 
        FROM unnest($1::regions[]) as r
    ) 
    RETURNING region_id
    """

    paris, santiago = await test_db.fetch(stmt, [(None, "Paris"), (None, "Santiago")])

    stmt = """
    INSERT INTO trips (region_id, origin, destination, timestamp, source) (
        SELECT r.region_id, r.origin, r.destination, r.timestamp, r.source
        FROM unnest($1::trips[]) as r
    )        
    """

    await test_db.fetch(
        stmt,
        [
            (
                None,
                paris.get("region_id"),
                (1.0, 1.0),
                (1.5, 1.0),
                datetime(2023, 1, 1, 0, 0, 0),
                "test_point",
            ),
            (
                None,
                paris.get("region_id"),
                (1.69, 1.37),
                (1.5, 1.5),
                datetime(2023, 1, 9, 0, 0, 0),
                "test_point",
            ),
            (
                None,
                paris.get("region_id"),
                (1.23, 1.75),
                (1.0, 1.5),
                datetime(2023, 1, 9, 0, 0, 0),
                "test_point",
            ),
            (
                None,
                santiago.get("region_id"),
                (3.61, 2.33),
                (3.5, 2.5),
                datetime(2023, 1, 1, 0, 0, 0),
                "test_point",
            ),
            (
                None,
                santiago.get("region_id"),
                (3.37, 1.99),
                (3.5, 2.0),
                datetime(2023, 1, 1, 0, 0, 0),
                "test_point",
            ),
            (
                None,
                santiago.get("region_id"),
                (3.0, 2.0),
                (3.0, 2.5),
                datetime(2023, 1, 1, 0, 0, 0),
                "test_point",
            ),
        ],
    )

    yield

    await test_db.fetch("TRUNCATE TABLE regions, trips")


@pytest.mark.asyncio
async def test_should_fail_if_no_all_query_parameters_are_sent(test_app: AsyncClient):
    expected_http_code = 400

    parameters = ["nortest", "region", "southest"]

    for subset in chain.from_iterable(
        combinations(parameters, r) for r in range(len(parameters) + 1)
    ):
        if len(subset) == len(parameters):
            continue

        params = sorted(list(subset))
        missing = sorted(list(set(parameters) - set(params)))

        expected_response_json = {
            "message": f"Missing query parameters: {', '.join(missing)}"
        }

        q = {param: "aaa" for param in params}

        response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
        assert (
            response.status_code == expected_http_code
        ), f"HTTP Response code when there are query parameters missing is not {expected_http_code} as expected"
        assert (
            response.json() == expected_response_json
        ), f"HTTP Response response when there are query parameters missing is not equal to {expected_response_json} as expected"


@pytest.mark.asyncio
async def test_should_fail_if_bboxes_has_wrong_format(test_app: AsyncClient):
    expected_http_code = 400

    # Nortest has bad format
    q = {
        "nortest": "x=(4,4);y=(5,5)",
        "southest": "4.44444444,5.555555555",
        "region": "Paris",
    }
    expected_bboxes_bad_format_json = {
        "message": "Wrong format in query parameters: nortest"
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when nortest is wrong formated is not {expected_http_code} as expected"
    assert (
        response.json() == expected_bboxes_bad_format_json
    ), f"HTTP Response response when nortest is wrong formated is not equal to {expected_bboxes_bad_format_json} as expected"

    # Southest has bad format
    q = {
        "nortest": "4.44444444,5.555555555",
        "southest": "x=(4,4);y=(5,5)",
        "region": "Paris",
    }
    expected_bboxes_bad_format_json = {
        "message": "Wrong format in query parameters: southest"
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when southest is wrong formated is not {expected_http_code} as expected"
    assert (
        response.json() == expected_bboxes_bad_format_json
    ), f"HTTP Response response when southest is wrong formated is not equal to {expected_bboxes_bad_format_json} as expected"

    # Both has bad format
    q = {
        "nortest": "x=(4,4);y=(5,5)",
        "southest": "x=(4,4);y=(5,5)",
        "region": "Paris",
    }
    expected_bboxes_bad_format_json = {
        "message": "Wrong format in query parameters: nortest, southest"
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when both are wrong formated is not {expected_http_code} as expected"
    assert (
        response.json() == expected_bboxes_bad_format_json
    ), f"HTTP Response response when both are wrong formated is not equal to {expected_bboxes_bad_format_json} as expected"


@pytest.mark.asyncio
async def test_should_fail_if_region_doesnt_exists(test_app: AsyncClient):
    expected_http_code = 400
    expected_response_json = {"message": "Region Paris not found"}
    q = {
        "nortest": "4.44444444,5.555555555",
        "southest": "4.44444444,5.555555555",
        "region": "Paris",
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json} as expected"


@pytest.mark.asyncio
@pytest.mark.usefixtures("poblate_test_data")
async def test_should_success_when_parameters_are_correct_and_return_weekly_mean_of_quantity_of_trips_paris_case(
    test_app: AsyncClient
):
    # Paris with all points in bbox
    expected_http_code = 200
    expected_response_json = {"mean": 1.5}

    q = {
        "nortest": "2,2",
        "southest": "0.7,0.7",
        "region": "Paris",
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json} as expected"


@pytest.mark.asyncio
@pytest.mark.usefixtures("poblate_test_data")
async def test_should_success_when_parameters_are_correct_and_return_weekly_mean_of_quantity_of_trips_santiago_case(
    test_app: AsyncClient
):
    # Santiago with all points in bbox
    expected_http_code = 200
    expected_response_json = {"mean": 3}

    q = {
        "nortest": "4,3",
        "southest": "2.5,1.5",
        "region": "Santiago",
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json} as expected"


@pytest.mark.asyncio
@pytest.mark.usefixtures("poblate_test_data")
async def test_should_success_when_parameters_are_correct_and_return_weekly_mean_of_quantity_of_trips_bbox_no_points(
    test_app: AsyncClient
):
    # Bbox out of range
    expected_http_code = 200
    expected_response_json = {"mean": None}

    q = {
        "nortest": "3.5,0.5",
        "southest": "3,0",
        "region": "Santiago",
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json} as expected"

    q = {"nortest": "3.5,0.5", "southest": "3,0", "region": "Paris"}

    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json} as expected"


@pytest.mark.asyncio
@pytest.mark.usefixtures("poblate_test_data")
async def test_should_success_when_parameters_are_correct_and_return_weekly_mean_of_quantity_of_trips_bbox_all_points(
    test_app: AsyncClient
):
    # Bounding box cover all space, but must respect region filter
    expected_http_code = 200
    expected_response_json_santiago = {"mean": 3}
    expected_response_json_paris = {"mean": 1.5}

    q = {
        "nortest": "4.5,3.5",
        "southest": "0,-1",
        "region": "Santiago",
    }
    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json_santiago
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json_santiago} as expected"

    q = {"nortest": "4.5,3.5", "southest": "0,-1", "region": "Paris"}

    response = await test_app.get(f"/api/v1/trips/stats?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json_paris
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json_paris} as expected"
