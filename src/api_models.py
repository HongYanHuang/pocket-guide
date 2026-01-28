"""
Pydantic models for POI Metadata API

These models define the data structures for API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ==== Multilingual Name Models ====

class MultilingualName(BaseModel):
    """
    Multilingual name container for a POI.

    Stores names in multiple languages keyed by BCP 47 language codes.
    The 'default' key holds the canonical name (used for file paths, slugs, and
    as the fallback when a requested language is not available).

    Example:
        {
            "default": "Acropolis",
            "names": {
                "en": "Acropolis",
                "zh": "雅典卫城",
                "ja": "アクロポリス",
                "ko": "아크로폴리스"
            }
        }
    """
    default: str = Field(..., description="Canonical name used as fallback and for identifiers")
    names: Dict[str, str] = Field(
        default_factory=dict,
        description="Language-keyed name map (BCP 47 codes, e.g. 'en', 'zh', 'ja')"
    )

    def get_name(self, language: Optional[str] = None) -> str:
        """
        Resolve the POI name for a given language code.

        Falls back to the default name when the requested language is unavailable.

        Args:
            language: BCP 47 language code (e.g. 'en', 'zh', 'ja').
                      Supports full codes like 'zh-TW' by trying the base code first.

        Returns:
            Localized name string
        """
        if not language:
            return self.default

        # Try exact match first
        if language in self.names:
            return self.names[language]

        # Try base language code (e.g. 'zh-TW' → 'zh')
        base_lang = language.split('-')[0].lower()
        if base_lang in self.names:
            return self.names[base_lang]

        return self.default


def get_name_from_multilingual(
    multilingual: Optional[MultilingualName],
    fallback: str = "",
    language: Optional[str] = None
) -> str:
    """
    Safely extract a name from an optional MultilingualName, returning a plain string.

    This helper keeps existing code paths simple when they only need a single string.

    Args:
        multilingual: The MultilingualName instance (may be None)
        fallback: Value to return when multilingual is None or empty
        language: Optional language code for resolution

    Returns:
        Resolved name string
    """
    if not multilingual:
        return fallback
    return multilingual.get_name(language) or fallback


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
    name: Optional[MultilingualName] = Field(
        None,
        description="Multilingual name container. Use this for localized display; poi_name remains the default fallback."
    )
    city: str
    has_metadata: bool
    has_coordinates: bool
    last_updated: Optional[str] = None


class POIDetail(BaseModel):
    """Detailed POI information including metadata"""
    poi_id: str
    poi_name: str
    name: Optional[MultilingualName] = Field(
        None,
        description="Multilingual name container. Use this for localized display; poi_name remains the default fallback."
    )
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


# ==== Transcript Models ====

class TranscriptData(BaseModel):
    """Transcript and summary data for a POI"""
    transcript: Optional[str] = Field(None, description="Full transcript text")
    summary: Optional[List[str]] = Field(None, description="List of summary points")
    has_transcript: bool = Field(..., description="Whether transcript file exists")
    has_summary: bool = Field(..., description="Whether summary file exists")


class TranscriptUpdate(BaseModel):
    """Model for updating transcript content"""
    transcript: str = Field(..., min_length=1, description="Updated transcript text")


# ==== Research Models ====

class ResearchBasicInfo(BaseModel):
    """Basic information about a POI from research"""
    period: Optional[str] = Field(None, description="Historical period")
    date_built: Optional[str] = Field(None, description="Construction date")
    date_relative: Optional[str] = Field(None, description="Relative date (e.g., '447 BC')")
    current_state: Optional[str] = Field(None, description="Current condition/state")
    description: Optional[str] = Field(None, description="Brief description")
    labels: Optional[List[str]] = Field(None, description="Classification labels")


class ResearchPerson(BaseModel):
    """Person associated with a POI"""
    name: str = Field(..., description="Person's name")
    role: Optional[str] = Field(None, description="Role or title")
    personality: Optional[str] = Field(None, description="Personality description")
    origin: Optional[str] = Field(None, description="Place of origin")
    relationship_type: Optional[str] = Field(None, description="Type of relationship to POI")
    labels: Optional[List[str]] = Field(None, description="Classification labels")


class ResearchEvent(BaseModel):
    """Historical event associated with a POI"""
    name: str = Field(..., description="Event name")
    date: Optional[str] = Field(None, description="Event date")
    significance: Optional[str] = Field(None, description="Historical significance")
    labels: Optional[List[str]] = Field(None, description="Classification labels")


class ResearchLocation(BaseModel):
    """Location or sub-location within a POI"""
    name: str = Field(..., description="Location name")
    description: Optional[str] = Field(None, description="Location description")
    labels: Optional[List[str]] = Field(None, description="Classification labels")


class ResearchConcept(BaseModel):
    """Concept or theme associated with a POI"""
    name: str = Field(..., description="Concept name")
    explanation: Optional[str] = Field(None, description="Detailed explanation")
    labels: Optional[List[str]] = Field(None, description="Classification labels")


class ResearchData(BaseModel):
    """Complete research data for a POI"""
    poi_id: str = Field(..., description="POI identifier")
    name: str = Field(..., description="POI name (default language)")
    multilingual_name: Optional[MultilingualName] = Field(None, description="Multilingual name container")
    city: str = Field(..., description="City name")
    basic_info: Optional[ResearchBasicInfo] = None
    core_features: Optional[List[str]] = Field(None, description="List of core features")
    people: Optional[List[ResearchPerson]] = Field(None, description="Associated people")
    events: Optional[List[ResearchEvent]] = Field(None, description="Associated events")
    locations: Optional[List[ResearchLocation]] = Field(None, description="Sub-locations")
    concepts: Optional[List[ResearchConcept]] = Field(None, description="Associated concepts")
    raw_yaml: str = Field(..., description="Raw YAML content")
