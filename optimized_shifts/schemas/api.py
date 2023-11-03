from typing import Annotated, Literal

from fastapi import Body
from pydantic import BaseModel

from optimized_shifts.schemas.trip import TripRequest


class TripsFileInsertRequest(BaseModel):
    data_type: Literal["mocked"] | Literal["gcp"]
    data: str


class TripsJsonInsertRequest(BaseModel):
    data_type: Literal["json"]
    data: list[TripRequest]


TripsInsertRequest = Annotated[
    TripsJsonInsertRequest | TripsFileInsertRequest, Body(discriminator="data_type")
]
