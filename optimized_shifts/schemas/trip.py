""" Módulo que define los esquemas del modelo Trip, el cual representa un viaje de una persona """

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TripRequest(BaseModel):
    """ Esquema para la petición de la API de crear un viaje """
    region: str
    origin: tuple[float, float]
    destination: tuple[float, float]
    timestamp: datetime
    source: str

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def validate_string_point(cls, raw: str | list[Any]) -> tuple[float, float]:
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError) as exc:
                raise ValueError("Input is not a tuple of numbers") from exc

            if not isinstance(raw, list):
                raise ValueError("Input is not a tuple of numbers")

        if len(raw) != 2:  # type: ignore # noqa # sabemos que point es list, da lo mismo el valor dentro solo necesitamos el length
            raise ValueError("Point must have two values, x and y")

        x, y = float(raw[0]), float(raw[1])  # type: ignore

        return (x, y)

    @field_validator("timestamp", mode="before")
    @classmethod
    def validate_timestamp(cls, raw: str) -> datetime:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")


class TripCreate(BaseModel):
    """ Esquema para la creación de un viaje en la base de datos """
    region_id: int
    origin: tuple[float, float]
    destination: tuple[float, float]
    timestamp: datetime
    source: str


class TripInDB(BaseModel):
    """ Esquema que representa un viaje en la base de datos """
    id: int = Field(..., alias="trip_id")
    region_id: int
    origin: tuple[float, float]
    destination: tuple[float, float]
    timestamp: datetime
    source: str
