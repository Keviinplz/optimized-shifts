from datetime import datetime, timedelta
from itertools import chain, combinations
from urllib.parse import urlencode

import pytest
from httpx import AsyncClient


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

        response = await test_app.get(f"/api/v1/travels?{urlencode(q)}")
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
    response = await test_app.get(f"/api/v1/travels?{urlencode(q)}")
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
    response = await test_app.get(f"/api/v1/travels?{urlencode(q)}")
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
    response = await test_app.get(f"/api/v1/travels?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when both are wrong formated is not {expected_http_code} as expected"
    assert (
        response.json() == expected_bboxes_bad_format_json
    ), f"HTTP Response response when both are wrong formated is not equal to {expected_bboxes_bad_format_json} as expected"


@pytest.mark.asyncio
async def test_should_success_when_parameters_are_correct_and_return_weekly_mean_of_quantity_of_travels_if_any(
    test_app: AsyncClient
):
    today = datetime.utcnow()
    one_week_ago = today - timedelta(days=7)

    today_str = today.strftime("%Y-%m-%d")
    one_week_ago_str = one_week_ago.strftime("%Y-%m-%d")

    expected_http_code = 200
    expected_response_json = {"mean": 3.7, "from": one_week_ago_str, "to": today_str}

    q = {
        "nortest": "4.44444444,5.555555555",
        "southest": "4.44444444,5.555555555",
        "region": "Paris",
    }
    response = await test_app.get(f"/api/v1/travels?{urlencode(q)}")
    assert (
        response.status_code == expected_http_code
    ), f"HTTP Response code when all parameters were sent is not {expected_http_code} as expected"
    assert (
        response.json() == expected_response_json
    ), f"HTTP Response response all parameters were sent is missing or is not equal to {expected_response_json} as expected"
