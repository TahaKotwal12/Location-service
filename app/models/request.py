from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime

class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class LocationRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    language: str = Field(default="en", pattern=r"^[a-z]{2}$")

class BatchLocationRequest(BaseModel):
    locations: List[Coordinates] = Field(..., max_items=100)
    language: str = Field(default="en", pattern=r"^[a-z]{2}$")