from pydantic import BaseModel, Field


class RegionInDB(BaseModel):
    id: int = Field(..., alias="region_id")
    name: str = Field(..., alias="region_name")
