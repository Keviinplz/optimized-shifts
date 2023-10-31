import asyncio
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from optimized_shifts.celery.processer import process_data, pubsub
from optimized_shifts.state import Database

router = APIRouter()


@router.get("/travels/live")
async def message_stream(request: Request):
    async def listen_generator():
        while True:
            if await request.is_disconnected():
                break

            message = pubsub.get_message()
            if message:  # type: ignore
                yield {"data": f"{message}"}

            await asyncio.sleep(1)

    return EventSourceResponse(listen_generator())


@router.get("/travels/mean")
async def handle_travels_request(
    request: Request,
    nortest: Annotated[
        str,
        Query(
            title="Nortest Point",
            description="Nortest point of the bounding box defined as px,py",
            pattern=r"^-?\d+(?:\.\d+)?,+-?\d+(?:\.\d+)?$",
        ),
    ],
    southest: Annotated[
        str,
        Query(
            title="Southest Point",
            description="Southest point of the bounding box defined as px,py",
            pattern=r"^-?\d+(?:\.\d+)?,+-?\d+(?:\.\d+)?$",
        ),
    ],
    region: Annotated[
        str,
        Query(
            title="Region",
            description="Region in where travels are located",
        ),
    ],
):
    db: Database = request.state.database

    async with db.acquire() as conn:
        travels = await conn.fetch("SELECT * FROM information_schema.tables")
        print(travels)

    today = datetime.utcnow()
    week_ago = today - timedelta(days=7)
    return {
        "mean": 3.7,
        "from": week_ago.strftime("%Y-%m-%d"),
        "to": today.strftime("%Y-%m-%d"),
    }


@router.get("/travels")
async def handle_travels_insertion():
    result = process_data.delay("testing")
    return JSONResponse(
        status_code=202,
        content={
            "message": f"Task is processing: {result.id}",
            "metadata": result.status,
        },
    )
