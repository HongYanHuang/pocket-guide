"""
Pydantic models for POI Metadata API

These models define the data structures for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==== Coordinate Models ====

class Coordinates(BaseModel):
    """Geographic coordinates for a POI"""
    latitude: float = Field(..., description="Latitude in decimal degrees")
    longitude: float = Field(..., description="Longitude in decimal degrees")
    source: str = Field(..., description="Data source (e.g., google_maps_api, nominatim)")
    collected_at: str = Field(..., description="ISO 8601 timestamp of collection")


class CoordinatesUpdate(BaseModel):
    """Model for updating coordinates"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# ==== Operation Hours Models ====

class OperationHours(BaseModel):
    """Operation hours for a POI"""
    open_now: Optional[bool] = Field(None, description="Whether POI is currently open")
    weekday_text: Optional[List[str]] = Field(None, description="Human-readable hours for each day")
    periods: Optional[List[Dict[str, Any]]] = Field(None, description="Structured opening periods")


# ==== Visit Info Models ====

class VisitInfo(BaseModel):
    """Visit information for a POI"""
    indoor_outdoor: str = Field(..., description="Whether POI is indoor, outdoor, or unknown")
    typical_duration_minutes: int = Field(..., description="Typical visit duration in minutes")
    accessibility: Optional[str] = Field(None, description="Accessibility information")


class VisitInfoUpdate(BaseModel):
    """Model for updating visit information"""
    indoor_outdoor: str = Field(..., pattern="^(indoor|outdoor|mixed|unknown)$")
    typical_duration_minutes: int = Field(..., ge=1, le=480)
    accessibility: Optional[str] = None


# ==== POI Metadata Models ====

class POIMetadata(BaseModel):
    """Complete metadata for a POI"""
    coordinates: Optional[Coordinates] = None
    operation_hours: Optional[OperationHours] = None
    visit_info: Optional[VisitInfo] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None
    types: Optional[List[str]] = None
    place_id: Optional[str] = None
    wheelchair_accessible: Optional[bool] = None
    last_metadata_update: Optional[str] = None
    verified: Optional[bool] = False


class POIMetadataUpdate(BaseModel):
    """Model for updating POI metadata"""
    coordinates: Optional[CoordinatesUpdate] = None
    visit_info: Optional[VisitInfoUpdate] = None
    operation_hours: Optional[Dict[str, Any]] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    wheelchair_accessible: Optional[bool] = None
    verified: Optional[bool] = None


# ==== POI Models ====

class POISummary(BaseModel):
    """Summary information about a POI"""
    poi_id: str
    poi_name: str
    city: str
    has_metadata: bool
    has_coordinates: bool
    last_updated: Optional[str] = None


class POIDetail(BaseModel):
    """Detailed POI information including metadata"""
    poi_id: str
    poi_name: str
    city: str
    metadata: Optional[POIMetadata] = None


# ==== City Models ====

class City(BaseModel):
    """City information"""
    name: str
    slug: str
    poi_count: int


# ==== Distance Matrix Models ====

class TravelMode(BaseModel):
    """Travel information for a specific mode"""
    duration_minutes: float = Field(..., description="Duration in minutes")
    distance_km: float = Field(..., description="Distance in kilometers")
    duration_text: str = Field(..., description="Human-readable duration")
    distance_text: str = Field(..., description="Human-readable distance")


class POIPair(BaseModel):
    """Distance/duration between two POIs"""
    origin_poi_id: str
    origin_poi_name: str
    destination_poi_id: str
    destination_poi_name: str
    walking: Optional[TravelMode] = None
    transit: Optional[TravelMode] = None
    driving: Optional[TravelMode] = None


class DistanceMatrix(BaseModel):
    """Complete distance matrix for a city"""
    city: str
    generated_at: str
    poi_count: int
    poi_pairs: Dict[str, POIPair]


# ==== API Response Models ====

class CollectionResult(BaseModel):
    """Result of metadata collection operation"""
    city: str
    pois_total: int
    pois_updated: int
    distance_matrix: Dict[str, Any]
    errors: List[str] = []


class VerificationReport(BaseModel):
    """POI metadata verification report"""
    city: str
    total_pois: int
    complete: int
    incomplete: int
    missing_fields: Dict[str, int]
    pois: List[Dict[str, Any]]


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None


class SuccessResponse(BaseModel):
    """Generic success response"""
    message: str
    data: Optional[Dict[str, Any]] = None
