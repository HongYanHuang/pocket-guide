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


# ==== Transcript Models ====

class TranscriptData(BaseModel):
    """Transcript and summary data for a POI"""
    transcript: Optional[str] = Field(None, description="Full transcript text")
    summary: Optional[List[str]] = Field(None, description="List of summary points")
    has_transcript: bool = Field(..., description="Whether transcript file exists")
    has_summary: bool = Field(..., description="Whether summary file exists")
    language: Optional[str] = Field(None, description="ISO 639-1 language code of returned transcript (e.g., 'en', 'fr')")
    available_languages: Optional[List[str]] = Field(None, description="List of available language codes for this POI")


class TranscriptUpdate(BaseModel):
    """Model for updating transcript content"""
    transcript: str = Field(..., min_length=1, description="Updated transcript text")
    language: Optional[str] = Field("en", description="ISO 639-1 language code (e.g., 'en', 'fr', 'es')")


class TranscriptLink(BaseModel):
    """Link from tour to transcript file"""
    poi: str = Field(..., description="POI name")
    poi_id: str = Field(..., description="POI identifier (kebab-case)")
    transcript_path: str = Field(..., description="Relative path to transcript file")
    transcript_version: str = Field(..., description="Transcript version (e.g., 'v1')")
    transcript_type: str = Field(..., description="Type: 'standard' or 'custom'")
    linked_at: str = Field(..., description="ISO timestamp when link was created")


class TranscriptLinks(BaseModel):
    """Collection of transcript links for a tour"""
    tour_id: str = Field(..., description="Tour identifier")
    language: str = Field(..., description="Language code")
    created_at: str = Field(..., description="ISO timestamp when links were created")
    links: List[TranscriptLink] = Field(..., description="List of transcript links")


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
    name: str = Field(..., description="POI name")
    city: str = Field(..., description="City name")
    basic_info: Optional[ResearchBasicInfo] = None
    core_features: Optional[List[str]] = Field(None, description="List of core features")
    people: Optional[List[ResearchPerson]] = Field(None, description="Associated people")
    events: Optional[List[ResearchEvent]] = Field(None, description="Associated events")
    locations: Optional[List[ResearchLocation]] = Field(None, description="Sub-locations")
    concepts: Optional[List[ResearchConcept]] = Field(None, description="Associated concepts")
    raw_yaml: str = Field(..., description="Raw YAML content")


# ==== Tour/Itinerary Models ====

class TourPOI(BaseModel):
    """POI within a tour itinerary"""
    poi: str = Field(..., description="POI name")
    reason: str = Field(..., description="Why this POI was selected")
    suggested_day: int = Field(..., description="Suggested day number")
    estimated_hours: float = Field(..., description="Estimated visit duration in hours")
    priority: str = Field(..., description="Priority level (high/medium/low)")
    coordinates: Dict[str, Any] = Field(default_factory=dict)
    operation_hours: Dict[str, Any] = Field(default_factory=dict)
    visit_info: Dict[str, Any] = Field(default_factory=dict)
    period: Optional[str] = Field(None, description="Historical period")
    date_built: Optional[str] = Field(None, description="Construction date")
    walking_time_to_next: Optional[str] = Field(None, description="Walking time to next POI")
    distance_to_next_km: Optional[float] = Field(None, description="Distance to next POI in km")


class TourDay(BaseModel):
    """Single day in a tour itinerary"""
    day: int = Field(..., description="Day number")
    pois: List[TourPOI] = Field(..., description="POIs for this day")
    total_hours: float = Field(..., description="Total hours for this day")
    total_walking_km: float = Field(..., description="Total walking distance in km")
    start_time: str = Field(..., description="Start time for the day")


class BackupPOI(BaseModel):
    """Backup/alternative POI"""
    poi: str = Field(..., description="Backup POI name")
    similarity_score: float = Field(..., description="Similarity score to original POI")
    reason: str = Field(..., description="Why this is a good backup")
    substitute_scenario: str = Field(..., description="When to use this backup")


class RejectedPOI(BaseModel):
    """POI that was rejected during selection"""
    poi: str = Field(..., description="Rejected POI name")
    reason: str = Field(..., description="Why this POI was rejected")


class OptimizationScores(BaseModel):
    """Optimization metrics for the tour"""
    distance_score: float = Field(..., description="Distance optimization score (0-1)")
    coherence_score: float = Field(..., description="Thematic coherence score (0-1)")
    overall_score: float = Field(..., description="Overall optimization score (0-1)")
    total_distance_km: float = Field(..., description="Total walking distance in km")


class TourMetadata(BaseModel):
    """Tour metadata and version history"""
    tour_id: str = Field(..., description="Unique tour identifier")
    city: str = Field(..., description="City name")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    languages: List[str] = Field(default_factory=lambda: ["en"], description="Available language codes")

    # Legacy fields (for backward compatibility with old tours)
    current_version: Optional[int] = Field(None, description="Current version number (legacy)")
    version_history: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Version history (legacy)")

    class Config:
        extra = "allow"  # Allow extra fields like current_version_en, version_history_zh-tw, etc.


class TourSummary(BaseModel):
    """Summary of a tour for list view"""
    tour_id: str = Field(..., description="Unique tour identifier")
    city: str = Field(..., description="City name")
    duration_days: int = Field(..., description="Number of days")
    total_pois: int = Field(..., description="Total number of POIs")
    interests: List[str] = Field(default_factory=list, description="User interests")
    created_at: str = Field(..., description="Creation timestamp")
    optimization_score: Optional[float] = Field(None, description="Overall optimization score")


class TourDetail(BaseModel):
    """Complete tour details"""
    metadata: TourMetadata = Field(..., description="Tour metadata")
    itinerary: List[TourDay] = Field(..., description="Day-by-day itinerary")
    input_parameters: Dict[str, Any] = Field(..., description="Input parameters for tour generation")
    backup_pois: Dict[str, List[BackupPOI]] = Field(default_factory=dict, description="Backup POIs per selected POI")
    rejected_pois: List[RejectedPOI] = Field(default_factory=list, description="POIs that were rejected")
    optimization_scores: OptimizationScores = Field(..., description="Optimization metrics")
    constraints_violated: List[str] = Field(default_factory=list, description="List of constraint violations")


# ==== POI Replacement Models ====

class POIReplacementItem(BaseModel):
    """Single POI replacement item"""
    original_poi: str = Field(..., description="POI name to replace")
    replacement_poi: str = Field(..., description="Backup POI name to use as replacement")
    day: int = Field(..., ge=1, description="Day number where POI is located")


class BatchPOIReplacementRequest(BaseModel):
    """Request to replace multiple POIs in a tour"""
    replacements: List[POIReplacementItem] = Field(..., min_items=1, description="List of POI replacements to apply")
    mode: str = Field(..., pattern="^(simple|reoptimize)$", description="Save mode: 'simple' or 'reoptimize'")
    language: str = Field("en", description="Tour language code (ISO 639-1, e.g., 'en', 'zh-cn')")


class BatchPOIReplacementResponse(BaseModel):
    """Response after batch POI replacement"""
    success: bool = Field(..., description="Whether replacement was successful")
    tour_id: str = Field(..., description="Tour identifier")
    new_version: int = Field(..., description="New version number")
    new_version_string: str = Field(..., description="New version string (e.g., 'v2_2026-02-06')")
    replacements_applied: int = Field(..., description="Number of replacements applied")
    replacements: List[Dict[str, str]] = Field(..., description="List of applied replacements")
    mode_used: str = Field(..., description="Save mode that was used")
    optimization_scores: Optional[OptimizationScores] = Field(None, description="New optimization scores (if reoptimized)")
    message: str = Field(..., description="Success message")


# Legacy single replacement models (kept for backward compatibility)
class POIReplacementRequest(BaseModel):
    """Request to replace a POI in a tour (deprecated - use BatchPOIReplacementRequest)"""
    original_poi: str = Field(..., description="POI name to replace")
    replacement_poi: str = Field(..., description="Backup POI name to use as replacement")
    mode: str = Field(..., pattern="^(simple|reoptimize)$", description="Save mode: 'simple' or 'reoptimize'")
    language: str = Field("en", description="Tour language code (ISO 639-1, e.g., 'en', 'zh-cn')")
    day: int = Field(..., ge=1, description="Day number where POI is located")


class POIReplacementResponse(BaseModel):
    """Response after POI replacement (deprecated - use BatchPOIReplacementResponse)"""
    success: bool = Field(..., description="Whether replacement was successful")
    tour_id: str = Field(..., description="Tour identifier")
    new_version: int = Field(..., description="New version number")
    new_version_string: str = Field(..., description="New version string (e.g., 'v2_2026-02-06')")
    replaced_poi: str = Field(..., description="Original POI that was replaced")
    with_poi: str = Field(..., description="New POI that replaced the original")
    mode_used: str = Field(..., description="Save mode that was used")
    optimization_scores: Optional[OptimizationScores] = Field(None, description="New optimization scores (if reoptimized)")
    message: str = Field(..., description="Success message")
