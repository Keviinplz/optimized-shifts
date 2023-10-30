from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/travels")
def handle_travels_request(
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
    region: Annotated[str, Query()],
):
    today = datetime.utcnow()
    week_ago = today - timedelta(days=7)
    return {
        "mean": 3.7,
        "from": week_ago.strftime("%Y-%m-%d"),
        "to": today.strftime("%Y-%m-%d"),
    }


@router.post("/travels")
def handle_travels_insertion():
    return {"response": "done"}
