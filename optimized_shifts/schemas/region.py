""" Modulo que define los esquemas de una region """

from pydantic import BaseModel, Field


class RegionInDB(BaseModel):
    """ Esquema que define una Region en la base de datos """
    id: int = Field(..., alias="region_id")
    name: str = Field(..., alias="region_name")
