""" Módulo que define esquemas para las peticiones de la API """

from typing import Annotated, Literal

from fastapi import Body
from pydantic import BaseModel

from optimized_shifts.schemas.trip import TripRequest


class TripsFileInsertRequest(BaseModel):
    """ Esquema de petición de inserción de datos desde un archivo """
    data_type: Literal["mocked"] | Literal["gcp"]
    data: str


class TripsJsonInsertRequest(BaseModel):
    """ Esquema de petición de inserción de datos via JSON """
    data_type: Literal["json"]
    data: list[TripRequest]


TripsInsertRequest = Annotated[
    TripsJsonInsertRequest | TripsFileInsertRequest, Body(discriminator="data_type")
]
