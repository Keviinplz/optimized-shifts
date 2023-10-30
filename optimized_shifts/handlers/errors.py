from functools import partial, reduce
from typing import Any

from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse


def _filter_type_error(error: dict[str, Any], expected_type: str) -> bool:
    return error.get("type") == expected_type


def _get_query_params(acc: list[str], error: dict[str, Any]) -> list[str]:
    loc = error.get("loc")
    if not loc:
        return acc

    if loc[0] != "query":
        return acc

    acc.append(loc[1])
    return acc


_filter_missing_type_error = partial(_filter_type_error, expected_type="missing")
_filter_string_format_type_error = partial(
    _filter_type_error, expected_type="string_pattern_mismatch"
)


def handle_pydantic_validation_exception(req: Request, exc: RequestValidationError):
    errors = exc.errors()
    missing = list(filter(_filter_missing_type_error, errors))

    if len(missing) != 0:
        query_params = reduce(_get_query_params, missing, [])
        query_params.sort()

        return JSONResponse(
            status_code=400,
            content={"message": f"Missing query parameters: {', '.join(query_params)}"},
        )

    wrong_format = list(filter(_filter_string_format_type_error, errors))

    if len(wrong_format) != 0:
        query_params = reduce(_get_query_params, wrong_format, [])
        query_params.sort()

        return JSONResponse(
            status_code=400,
            content={
                "message": f"Wrong format in query parameters: {', '.join(query_params)}"
            },
        )

    return JSONResponse(status_code=400, content={"message": str(exc)})
