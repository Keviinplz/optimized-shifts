import json
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class TripRequest(BaseModel):
    region: str
    origin: tuple[float, float]
    destination: tuple[float, float]
    timestamp: datetime
    source: str

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def validate_string_point(cls, raw: str) -> tuple[float, float]:
        try:
            point = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("Input is not a tuple of numbers") from exc

        if not isinstance(point, list):
            raise ValueError("Input is not a tuple of numbers")

        if len(point) != 2:  # type: ignore # noqa # sabemos que point es list, da lo mismo el valor dentro solo necesitamos el length
            raise ValueError("Point must have two values, x and y")

        x, y = float(point[0]), float(point[1])  # type: ignore

        return (x, y)

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, raw: str) -> datetime:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")


class TripCreate(BaseModel):
    region_id: int
    origin: tuple[float, float]
    destination: tuple[float, float]
    timestamp: datetime
    source: str


class TripInDB(BaseModel):
    id: int = Field(..., alias="trip_id")
    region_id: int
    origin: tuple[float, float]
    destination: tuple[float, float]
    timestamp: datetime
    source: str
