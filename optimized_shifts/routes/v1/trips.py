import asyncio
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from optimized_shifts.celery.processer import process_data, pubsub
from optimized_shifts.crud.region import RegionRepository
from optimized_shifts.crud.trips import TripsRepository
from optimized_shifts.dependencies import get_db
from optimized_shifts.schemas.api import TripsInsertRequest
from optimized_shifts.schemas.trip import TripCreate
from optimized_shifts.state import Database

router = APIRouter()


@router.get("/trips/live")
async def message_stream(request: Request):
    async def listen_generator():
        while True:
            if await request.is_disconnected():
                break

            message = pubsub.get_message()
            if message:
                yield {"data": f"{message}"}

            await asyncio.sleep(1)

    return EventSourceResponse(listen_generator())


@router.get("/trips/stats")
async def handle_travels_request(
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
            description="Region in where trips are located",
        ),
    ],
    db: Database = Depends(get_db),
):
    px, py = southest.split(",")
    qx, qy = nortest.split(",")

    bbox = ((float(px), float(py)), (float(qx), float(qy)))
    region_db = await RegionRepository.get_by_name(region, db)
    if not region_db:
        return JSONResponse({"message": f"Region {region} not found"}, status_code=400)

    avg = await TripsRepository.get_count_weekly_average_by_bbox_and_region(
        bbox, region_db.id, db
    )

    return {"mean": avg}


@router.post("/trips")
async def handle_travels_insertion(
    insert_request: TripsInsertRequest, db: Database = Depends(get_db)
):
    if insert_request.data_type != "json":
        result = process_data.delay(
            data_type=insert_request.data_type, data=insert_request.data
        )
        return JSONResponse(
            status_code=202,
            content={
                "message": f"Task is processing: {result.id}",
                "metadata": result.status,
            },
        )

    data = insert_request.data

    regions = set(map(lambda trip: trip.region, data))
    regions_id_mapped: dict[str, int | None] = {region: None for region in regions}

    regions_db = await RegionRepository.get_by_name_multiple(regions, db)

    for region_db in regions_db:
        regions_id_mapped[region_db.name] = region_db.id

    # Insert regions that doesn't exists yet
    to_insert = [key for key, value in regions_id_mapped.items() if value is None]
    inserted = await RegionRepository.create_multiple(to_insert, db)
    for region_db in inserted:
        regions_id_mapped[region_db.name] = region_db.id

    points_to_be_inserted = [
        TripCreate(
            region_id=cast(int, regions_id_mapped[t.region]),
            origin=t.origin,
            destination=t.destination,
            timestamp=t.timestamp,
            source=t.source,
        )
        for t in data
    ]

    await TripsRepository.create_multiple(points_to_be_inserted, db)

    return JSONResponse(
        status_code=201,
        content={"message": "Points inserted"},
    )
