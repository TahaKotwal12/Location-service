from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class AccuracyLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    APPROXIMATE = "approximate"

class PlaceType(str, Enum):
    STREET_ADDRESS = "street_address"
    ESTABLISHMENT = "establishment"
    LOCALITY = "locality"
    ADMINISTRATIVE = "administrative"
    POINT_OF_INTEREST = "point_of_interest"

class AddressComponents(BaseModel):
    houseNumber: Optional[str] = None
    buildingName: Optional[str] = None
    street: Optional[str] = None
    subLocality: Optional[str] = None
    locality: Optional[str] = None
    subDistrict: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    stateCode: Optional[str] = None
    country: Optional[str] = None
    countryCode: Optional[str] = None
    pincode: Optional[str] = None
    area: Optional[str] = None
    region: Optional[str] = None

class CoordinatesResponse(BaseModel):
    latitude: float
    longitude: float
    accuracy: AccuracyLevel

class Address(BaseModel):
    fullAddress: str
    formattedAddress: str
    shortAddress: str
    components: AddressComponents
    coordinates: CoordinatesResponse
    placeType: PlaceType
    confidence: float = Field(..., ge=0, le=1)
    timezone: Optional[str] = None

class Metadata(BaseModel):
    source: str
    processingTime: str
    cached: bool
    lastUpdated: datetime

class LocationData(BaseModel):
    address: Address
    metadata: Metadata

class LocationResponse(BaseModel):
    success: bool = True
    data: Optional[LocationData] = None
    error: Optional[Dict[str, Any]] = None
    coordinates: Optional[Dict[str, float]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requestId: Optional[str] = None

class BatchLocationResponse(BaseModel):
    success: bool = True
    total_requests: int
    successful_requests: int
    results: List[LocationResponse]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ErrorDetails(BaseModel):
    field: Optional[str] = None
    value: Optional[str] = None
    expectedRange: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requestId: Optional[str] = None

class HealthStatus(BaseModel):
    status: str
    uptime: str
    services: Dict[str, str]
    performance: Dict[str, str]