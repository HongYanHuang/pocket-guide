"""
FastAPI Backend for POI Metadata Management

This API provides endpoints for viewing and editing POI metadata,
including coordinates, operation hours, and distance matrices.
"""

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import yaml
from datetime import datetime

from api_models import (
    City, POISummary, POIDetail, POIMetadata, POIMetadataUpdate,
    DistanceMatrix, CollectionResult, VerificationReport,
    ErrorResponse, SuccessResponse,
    TranscriptData, TranscriptUpdate, TranscriptLink, TranscriptLinks,
    TranscriptSection, SectionedTranscriptData,
    ResearchData,
    ResearchBasicInfo, ResearchPerson, ResearchEvent,
    ResearchLocation, ResearchConcept,
    TourSummary, TourDetail, TourMetadata, TourDay, TourPOI,
    BackupPOI, RejectedPOI, OptimizationScores,
    POIReplacementRequest, POIReplacementResponse,
    BatchPOIReplacementRequest, BatchPOIReplacementResponse, POIReplacementItem,
    POIVisitStatus, TourVisitStatus, MarkVisitedRequest, MarkVisitedResponse,
    BulkMarkVisitedRequest, BulkMarkVisitedResponse
)
from poi_metadata_agent import POIMetadataAgent
from utils import load_config, normalize_language_code, list_available_languages, get_tour_filename
from api_combo_tickets import router as combo_tickets_router
from api_tour_generator import router as tour_generator_router
from api_client_tours import router as client_tours_router
from api_auth import router as auth_router
from api_map_mode import router as map_mode_router
from api_poi_images import router as poi_images_router
from api_tour_images import router as tour_images_router
from auth.jwt_handler import JWTHandler
from auth.session_manager import SessionManager
from auth.oauth_handler import GoogleOAuthHandler
from auth.dependencies import get_current_user, get_optional_user, require_backstage_admin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Pocket Guide POI Metadata API",
    description="API for managing POI metadata including coordinates, hours, and travel distances",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==== Global Exception Handlers ====

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors gracefully.

    FastAPI already ignores undefined query parameters by default.
    This handler makes validation error messages more user-friendly.
    """
    errors = exc.errors()

    # Log the validation error for debugging
    logger.warning(f"Validation error on {request.url}: {errors}")

    # Return user-friendly error message
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request parameters",
            "errors": [
                {
                    "field": ".".join(str(loc) for loc in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"]
                }
                for err in errors
            ]
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected errors.
    Prevents server from returning HTML error pages.
    """
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)

    # Don't leak internal error details to client
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": "An unexpected error occurred. Please contact support if this persists."
        }
    )


# Load configuration first (needed for CORS and auth)
try:
    config = load_config()
    metadata_agent = POIMetadataAgent(config)
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    config = {}
    metadata_agent = None

# Initialize authentication handlers
auth_config = config.get('authentication', {})
if auth_config.get('enabled', False):
    try:
        jwt_handler = JWTHandler(
            secret_key=auth_config.get('jwt', {}).get('secret_key')
        )

        session_manager = SessionManager(
            refresh_token_expire_days=auth_config.get('session', {}).get('refresh_token_expire_days', 7)
        )

        oauth_config = auth_config.get('google_oauth', {})

        # Support both new multi-client format and old single-client format
        clients = oauth_config.get('clients', {})
        if not clients:
            # Fallback to old format for backward compatibility
            clients = {
                "web": {
                    "client_id": oauth_config.get('client_id'),
                    "client_secret": oauth_config.get('client_secret')
                }
            }

        oauth_handler = GoogleOAuthHandler(
            clients=clients,
            default_redirect_uri=oauth_config.get('default_redirect_uri') or oauth_config.get('redirect_uri')
        )

        logger.info(f"OAuth clients configured: {list(clients.keys())}")

        logger.info("Authentication handlers initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize authentication: {e}")
        jwt_handler = None
        session_manager = None
        oauth_handler = None
else:
    logger.info("Authentication is disabled in config")
    jwt_handler = None
    session_manager = None
    oauth_handler = None

# Configure CORS
cors_origins = auth_config.get('cors', {}).get('allowed_origins', ['*'])
cors_regex = auth_config.get('cors', {}).get('allow_origin_regex', None)

# Allow all localhost URLs during development (any port)
# In production, use specific allowed_origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_regex,  # Regex pattern for flexible origin matching
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Include routers
app.include_router(auth_router)
app.include_router(combo_tickets_router)
app.include_router(tour_generator_router)
app.include_router(client_tours_router)
app.include_router(map_mode_router)
app.include_router(poi_images_router)
app.include_router(tour_images_router)


# ==== Helper Functions ====

def get_agent() -> POIMetadataAgent:
    """Get metadata agent instance or raise error"""
    if metadata_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metadata agent not initialized. Check configuration."
        )
    return metadata_agent


def remove_null_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove keys with None values from a dictionary.

    This ensures OpenAPI-generated clients don't receive null values
    for optional fields, which can cause deserialization errors.

    Args:
        data: Dictionary that may contain None values

    Returns:
        Dictionary with None values removed
    """
    return {k: v for k, v in data.items() if v is not None}


def load_poi_from_content(city: str, poi_id: str) -> dict:
    """Load POI metadata from content directory"""
    import json

    # Try to load from content directory first (batch-generated POIs)
    city_slug = city.lower().replace(' ', '-')
    content_path = Path(f"content/{city_slug}/{poi_id}/metadata.json")

    if content_path.exists():
        try:
            with open(content_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            # Return in expected format
            return {
                'poi': {
                    'poi_id': poi_id,
                    'poi_name': metadata.get('poi', poi_id),
                    'metadata': metadata
                }
            }
        except Exception as e:
            logger.error(f"Error loading POI from content: {e}")
            pass

    # Fallback to YAML in poi_research directory
    return load_poi_yaml(city, poi_id)


def load_poi_yaml(city: str, poi_id: str) -> dict:
    """Load POI YAML file from poi_research directory"""
    # Convert hyphens to underscores for filename
    filename = poi_id.replace('-', '_')
    yaml_path = Path(f"poi_research/{city}/{filename}.yaml")

    if not yaml_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"POI not found: {poi_id} in {city}"
        )

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    except Exception as e:
        logger.error(f"Error loading POI YAML: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading POI data: {str(e)}"
        )


def save_poi_to_content(city: str, poi_id: str, data: dict) -> None:
    """Save POI metadata to content directory"""
    import json

    city_slug = city.lower().replace(' ', '-')
    content_path = Path(f"content/{city_slug}/{poi_id}/metadata.json")

    # Create directory if needed
    content_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Extract metadata from data structure
        metadata = data.get('poi', {}).get('metadata', {})

        with open(content_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving POI to content: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving POI data: {str(e)}"
        )


def save_poi_yaml(city: str, poi_id: str, data: dict) -> None:
    """Save POI YAML file to poi_research directory"""
    # Convert hyphens to underscores for filename
    filename = poi_id.replace('-', '_')
    yaml_path = Path(f"poi_research/{city}/{filename}.yaml")

    # Create directory if needed
    yaml_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as e:
        logger.error(f"Error saving POI YAML: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving POI data: {str(e)}"
        )


# ==== Transcript and Research Helper Functions ====

def kebab_to_snake(text: str) -> str:
    """
    Convert kebab-case to snake_case, handling special characters

    This matches the naming convention used by ContentGenerator._get_research_path()
    which converts any non-alphanumeric character (except space, -, _) to underscore
    """
    # Convert any special character (including apostrophes) to underscore
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in text)
    # Replace spaces and hyphens with underscores
    safe_name = safe_name.replace(' ', '_').replace('-', '_').lower()
    return safe_name


def snake_to_kebab(text: str) -> str:
    """Convert snake_case to kebab-case"""
    return text.replace('_', '-')


def get_transcript_path(city: str, poi_id: str, language: str = "en") -> Path:
    """
    Get path to transcript file with language support

    Args:
        city: City name
        poi_id: POI identifier
        language: ISO 639-1 language code (e.g., 'en', 'fr')

    Returns:
        Path to language-specific transcript file
    """
    city_slug = city.lower().replace(' ', '-')
    poi_dir = Path("content") / city_slug / poi_id

    # Try language-specific file first
    lang_path = poi_dir / f"transcript_{language}.txt"

    # Fallback to backward-compatible filename for English
    if not lang_path.exists() and language == "en":
        compat_path = poi_dir / "transcript.txt"
        if compat_path.exists():
            return compat_path

    return lang_path


def get_summary_path(city: str, poi_id: str) -> Path:
    """Get path to summary file"""
    city_slug = city.lower().replace(' ', '-')
    return Path("content") / city_slug / poi_id / "summary.txt"


def get_research_path(city: str, poi_id: str) -> Path:
    """Get path to research YAML file"""
    filename = kebab_to_snake(poi_id)
    city_name = city.title().replace(' ', '')
    return Path("poi_research") / city_name / f"{filename}.yaml"


def parse_summary_points(summary_text: str) -> List[str]:
    """Parse summary text into list of points"""
    if not summary_text:
        return []

    lines = summary_text.strip().split('\n')
    points = []
    for line in lines:
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
            # Remove numbering and bullet points
            clean_line = line.lstrip('0123456789.-•) ').strip()
            if clean_line:
                points.append(clean_line)
    return points


def create_transcript_backup(city: str, poi_id: str, language: str = "en") -> str:
    """
    Create backup of transcript file before editing

    Args:
        city: City name
        poi_id: POI identifier
        language: ISO 639-1 language code

    Returns:
        Backup filename
    """
    transcript_path = get_transcript_path(city, poi_id, language)

    if not transcript_path.exists():
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = transcript_path.parent / f"transcript_backup_{language}_{timestamp}.txt"

    try:
        backup_path.write_text(transcript_path.read_text(encoding='utf-8'), encoding='utf-8')
        logger.info(f"Created backup: {backup_path}")
        return backup_path.name
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating backup: {str(e)}"
        )


# ==== API Endpoints ====

@app.get("/", response_model=dict)
async def root():
    """API root endpoint"""
    return {
        "name": "Pocket Guide POI Metadata API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "cities": "/cities",
            "pois": "/cities/{city}/pois",
            "poi_detail": "/pois/{city}/{poi_id}",
            "distances": "/distances/{city}"
        }
    }


@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_initialized": metadata_agent is not None
    }


# ==== Admin Endpoints ====

@app.get("/admin/sessions")
async def list_active_sessions(current_user: dict = Depends(require_backstage_admin)):
    """
    List all active user sessions (admin only).

    Returns information about logged-in users including email, role, scopes, and last access time.
    """
    if session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication not enabled"
        )

    sessions = []
    for refresh_token, session_data in session_manager.sessions.items():
        user = session_data.get("user", {})
        sessions.append({
            "email": user.get("email"),
            "name": user.get("name"),
            "role": user.get("role"),
            "scopes": user.get("scopes", []),
            "client_type": user.get("client_type"),
            "created_at": session_data.get("created_at").isoformat() if session_data.get("created_at") else None,
            "expires_at": session_data.get("expires_at").isoformat() if session_data.get("expires_at") else None,
            "last_accessed": session_data.get("last_accessed").isoformat() if session_data.get("last_accessed") else None
        })

    return {
        "total_sessions": len(sessions),
        "sessions": sessions
    }


# ==== City Endpoints ====

@app.get("/cities", response_model=List[City])
async def list_cities():
    """
    List all cities with POI data.

    Returns a list of cities with their POI counts from content directory.
    """
    try:
        content_dir = Path("content")

        if not content_dir.exists():
            return []

        cities = []
        for city_dir in content_dir.iterdir():
            if city_dir.is_dir() and not city_dir.name.startswith('.'):
                # Count POI subdirectories (each POI has its own directory)
                poi_count = len([
                    d for d in city_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('.')
                ])

                # Convert slug back to proper city name (capitalize first letter)
                city_name = city_dir.name.replace('-', ' ').title()

                cities.append(City(
                    name=city_name,
                    slug=city_dir.name,
                    poi_count=poi_count
                ))

        return sorted(cities, key=lambda x: x.name)

    except Exception as e:
        logger.error(f"Error listing cities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing cities: {str(e)}"
        )


@app.get("/cities/{city}/pois", response_model=List[POISummary])
async def list_city_pois(city: str):
    """
    List all POIs for a specific city.

    Returns summary information for each POI including metadata status.
    Loads from content directory (content/{city}/) instead of poi_research.
    """
    try:
        agent = get_agent()

        # Load POIs from content directory (where batch-generated POIs are stored)
        pois = agent._load_city_pois_from_content(city)

        if not pois:
            return []

        summaries = []
        for poi in pois:
            metadata = poi.get('metadata', {})

            summaries.append(POISummary(
                poi_id=poi.get('poi_id', 'unknown'),
                poi_name=poi.get('poi_name', 'unknown'),
                city=city,
                has_metadata=bool(metadata),
                has_coordinates=bool(metadata.get('coordinates')),
                last_updated=metadata.get('last_metadata_update')
            ))

        return summaries

    except Exception as e:
        logger.error(f"Error listing POIs for {city}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing POIs: {str(e)}"
        )


# ==== POI Metadata Endpoints ====

@app.get("/pois/{city}/{poi_id}", response_model=POIDetail)
async def get_poi_metadata(city: str, poi_id: str):
    """
    Get detailed metadata for a specific POI.

    Returns all metadata including coordinates, hours, and visit information.
    Tries to load from content directory first, then falls back to poi_research.
    """
    try:
        data = load_poi_from_content(city, poi_id)
        poi_data = data.get('poi', {})

        return POIDetail(
            poi_id=poi_data.get('poi_id', poi_id),
            poi_name=poi_data.get('poi_name', poi_data.get('name', poi_id)),
            city=city,
            metadata=poi_data.get('metadata')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting POI metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving POI metadata: {str(e)}"
        )


@app.put("/pois/{city}/{poi_id}/metadata", response_model=SuccessResponse)
async def update_poi_metadata(city: str, poi_id: str, metadata_update: POIMetadataUpdate):
    """
    Update metadata for a specific POI.

    Allows manual editing of coordinates, visit info, and other metadata fields.
    Saves to content directory if POI exists there, otherwise to poi_research.
    """
    try:
        # Load current data (tries content first, then poi_research)
        data = load_poi_from_content(city, poi_id)
        poi_data = data.get('poi', {})

        # Get or create metadata section
        current_metadata = poi_data.get('metadata', {})

        # Update coordinates if provided
        if metadata_update.coordinates:
            coords = metadata_update.coordinates.dict()
            current_metadata['coordinates'] = {
                'latitude': coords['latitude'],
                'longitude': coords['longitude'],
                'source': current_metadata.get('coordinates', {}).get('source', 'manual'),
                'collected_at': current_metadata.get('coordinates', {}).get('collected_at', '')
            }

        # Update visit info if provided
        if metadata_update.visit_info:
            current_metadata['visit_info'] = metadata_update.visit_info.dict()

        # Update other fields
        if metadata_update.operation_hours is not None:
            current_metadata['operation_hours'] = metadata_update.operation_hours

        if metadata_update.address is not None:
            current_metadata['address'] = metadata_update.address

        if metadata_update.phone is not None:
            current_metadata['phone'] = metadata_update.phone

        if metadata_update.website is not None:
            current_metadata['website'] = metadata_update.website

        if metadata_update.wheelchair_accessible is not None:
            current_metadata['wheelchair_accessible'] = metadata_update.wheelchair_accessible

        if metadata_update.verified is not None:
            current_metadata['verified'] = metadata_update.verified

        # Update timestamp
        from datetime import datetime, timezone
        current_metadata['last_metadata_update'] = datetime.now(timezone.utc).isoformat()

        # Save back to appropriate location
        poi_data['metadata'] = current_metadata
        data['poi'] = poi_data

        # Check if POI exists in content directory
        import json
        city_slug = city.lower().replace(' ', '-')
        content_path = Path(f"content/{city_slug}/{poi_id}/metadata.json")

        if content_path.exists():
            # Save to content directory
            save_poi_to_content(city, poi_id, data)
        else:
            # Save to poi_research directory
            save_poi_yaml(city, poi_id, data)

        return SuccessResponse(
            message=f"Metadata updated successfully for {poi_id}",
            data={"poi_id": poi_id, "city": city}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating POI metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating metadata: {str(e)}"
        )


@app.post("/pois/{city}/{poi_id}/recollect", response_model=SuccessResponse)
async def recollect_poi_metadata(city: str, poi_id: str):
    """
    Re-collect metadata from Google Maps API for a specific POI.

    Useful for refreshing outdated information.
    """
    try:
        agent = get_agent()

        # Load POI from content directory
        pois = agent._load_city_pois_from_content(city)
        poi = next((p for p in pois if p.get('poi_id') == poi_id), None)

        if not poi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"POI not found: {poi_id}"
            )

        # Collect new metadata
        logger.info(f"Re-collecting metadata for {poi_id}...")
        metadata = agent._collect_poi_metadata(poi)

        if not metadata:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to collect metadata from Google Maps"
            )

        # Save metadata
        agent._save_poi_metadata(poi, metadata)

        return SuccessResponse(
            message=f"Metadata re-collected successfully for {poi_id}",
            data={"poi_id": poi_id, "city": city, "source": "google_maps_api"}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-collecting POI metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error re-collecting metadata: {str(e)}"
        )


# ==== Distance Matrix Endpoints ====

@app.get("/distances/{city}", response_model=DistanceMatrix)
async def get_distance_matrix(city: str):
    """
    Get the distance matrix for all POIs in a city.

    Returns travel times and distances for walking, transit, and driving.
    """
    try:
        agent = get_agent()
        matrix = agent.load_distance_matrix(city)

        if not matrix:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Distance matrix not found for {city}. Run collection first."
            )

        return matrix

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading distance matrix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading distance matrix: {str(e)}"
        )


@app.post("/distances/{city}/recalculate", response_model=SuccessResponse)
async def recalculate_distance_matrix(city: str):
    """
    Recalculate the distance matrix for a city.

    Uses Google Maps Distance Matrix API to calculate fresh travel times.
    """
    try:
        agent = get_agent()

        # Load POIs
        pois = agent._load_city_pois(city)

        if not pois:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No POIs found for {city}"
            )

        # Calculate distance matrix
        logger.info(f"Recalculating distance matrix for {city}...")
        distance_matrix = agent._calculate_city_distance_matrix(pois, city)

        if not distance_matrix:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to calculate distance matrix"
            )

        # Save distance matrix
        agent._save_distance_matrix(city, distance_matrix)

        return SuccessResponse(
            message=f"Distance matrix recalculated successfully for {city}",
            data={
                "city": city,
                "poi_count": distance_matrix.get('poi_count', 0),
                "pair_count": len(distance_matrix.get('poi_pairs', {}))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recalculating distance matrix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recalculating distance matrix: {str(e)}"
        )


# ==== Collection and Verification Endpoints ====

@app.post("/cities/{city}/collect", response_model=CollectionResult)
async def collect_city_metadata(city: str):
    """
    Collect metadata for all POIs in a city.

    This endpoint triggers full metadata collection including:
    - POI coordinates and details from Google Maps
    - Distance matrix calculation
    """
    try:
        agent = get_agent()

        logger.info(f"Starting metadata collection for {city}...")
        result = agent.collect_all_metadata(city)

        return result

    except Exception as e:
        logger.error(f"Error collecting metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error collecting metadata: {str(e)}"
        )


@app.get("/cities/{city}/verify", response_model=VerificationReport)
async def verify_city_metadata(city: str):
    """
    Verify metadata completeness for all POIs in a city.

    Returns a report showing which POIs have complete metadata
    and which fields are missing.
    """
    try:
        agent = get_agent()

        report = agent.verify_metadata(city)

        return report

    except Exception as e:
        logger.error(f"Error verifying metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying metadata: {str(e)}"
        )


# ==== Transcript Endpoints ====

@app.get("/pois/{city}/{poi_id}/transcript", response_model=TranscriptData)
async def get_transcript(
    city: str,
    poi_id: str,
    language: str = "en",
    tour_id: Optional[str] = None
):
    """
    Get transcript and summary for a POI in a specific language.

    If tour_id is provided, will try to use the tour's linked transcript.
    Falls back to standard POI transcript if tour link doesn't exist.

    Args:
        city: City name (e.g., "Athens")
        poi_id: POI identifier in kebab-case (e.g., "acropolis-parthenon")
        language: ISO 639-1 language code (e.g., 'en', 'fr', 'es') - defaults to 'en'
        tour_id: Optional tour ID to load tour-specific transcript link

    Returns:
        TranscriptData with transcript text, summary points, availability flags, and language info
    """
    import json

    # Validate and normalize language code
    try:
        language = normalize_language_code(language)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Get POI directory path
    city_slug = city.lower().replace(' ', '-')
    poi_dir = Path("content") / city_slug / poi_id

    # Get available languages for this POI
    available_languages = []
    if poi_dir.exists():
        available_languages = list_available_languages(poi_dir)

    # Try to get transcript path from tour links if tour_id provided
    transcript_path = None
    used_tour_link = False

    if tour_id:
        try:
            # Find tour directory
            tours_dir = Path("tours")
            tour_path = None

            for city_dir in tours_dir.iterdir():
                if not city_dir.is_dir():
                    continue
                potential_path = city_dir / tour_id
                if potential_path.exists():
                    tour_path = potential_path
                    break

            if tour_path:
                # Load transcript links
                links_file = tour_path / f"transcript_links_{language}.json"
                if links_file.exists():
                    with open(links_file, 'r', encoding='utf-8') as f:
                        links_data = json.load(f)

                    # Find link for this POI
                    for link in links_data.get('links', []):
                        if link['poi_id'] == poi_id:
                            transcript_path = Path(link['transcript_path'])
                            used_tour_link = True
                            break
        except Exception as e:
            logger.warning(f"Could not load tour transcript link: {e}")
            # Fall through to standard path

    # Fallback to standard transcript path
    if not transcript_path or not transcript_path.exists():
        transcript_path = get_transcript_path(city, poi_id, language)
        used_tour_link = False

    summary_path = get_summary_path(city, poi_id)

    transcript_text = None
    summary_points = None
    has_transcript = transcript_path.exists()
    has_summary = summary_path.exists()

    try:
        if has_transcript:
            transcript_text = transcript_path.read_text(encoding='utf-8')

        if has_summary:
            summary_text = summary_path.read_text(encoding='utf-8')
            summary_points = parse_summary_points(summary_text)

        return TranscriptData(
            transcript=transcript_text,
            summary=summary_points,
            has_transcript=has_transcript,
            has_summary=has_summary,
            language=language,
            available_languages=available_languages
        )

    except Exception as e:
        logger.error(f"Error reading transcript/summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading transcript/summary: {str(e)}"
        )


@app.put("/pois/{city}/{poi_id}/transcript", response_model=SuccessResponse)
async def update_transcript(city: str, poi_id: str, update: TranscriptUpdate):
    """
    Update transcript for a POI in a specific language (creates backup before saving).

    Args:
        city: City name (e.g., "Athens")
        poi_id: POI identifier in kebab-case (e.g., "acropolis-parthenon")
        update: TranscriptUpdate with new transcript text and optional language code

    Returns:
        SuccessResponse with backup filename
    """
    # Validate and normalize language code
    try:
        language = normalize_language_code(update.language)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    transcript_path = get_transcript_path(city, poi_id, language)

    if not transcript_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript not found for {city}/{poi_id} in language '{language}'"
        )

    try:
        # Create backup before editing
        backup_filename = create_transcript_backup(city, poi_id, language)

        # Write new content
        transcript_path.write_text(update.transcript, encoding='utf-8')

        logger.info(f"Updated transcript for {city}/{poi_id} (language: {language})")

        return SuccessResponse(
            message=f"Transcript updated successfully for language '{language}'",
            data={"backup_file": backup_filename, "language": language}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transcript: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating transcript: {str(e)}"
        )


@app.get("/pois/{city}/{poi_id}/sectioned-transcript", response_model=SectionedTranscriptData)
async def get_sectioned_transcript(
    city: str,
    poi_id: str,
    language: str = "en",
    tour_id: Optional[str] = None
):
    """
    Get sectioned transcript with knowledge points and titles.

    Args:
        city: City name
        poi_id: POI identifier
        language: Language code (default: en)
        tour_id: Optional tour ID for tour-specific transcripts

    Returns:
        Sectioned transcript data with sections array
    """
    import json

    # Normalize inputs
    city_slug = city.lower().replace(' ', '-')
    poi_slug = poi_id.lower().replace(' ', '-')
    lang_code = normalize_language_code(language)

    # Get POI path
    poi_path = Path(config.get('content_dir', 'content')) / city_slug / poi_slug

    if not poi_path.exists():
        raise HTTPException(status_code=404, detail=f"POI not found: {poi_id}")

    # Try to load sectioned transcript
    sectioned_file = poi_path / f"sectioned_transcript_{lang_code}.json"

    if not sectioned_file.exists():
        # Fallback: Create sectioned format from plain transcript
        plain_transcript_file = poi_path / f"transcript_{lang_code}.txt"
        if plain_transcript_file.exists():
            with open(plain_transcript_file, 'r', encoding='utf-8') as f:
                plain_text = f.read()

            # Return as single section
            word_count = len(plain_text.split())
            return SectionedTranscriptData(
                poi=poi_id,
                language=lang_code,
                generated_at=datetime.now().isoformat(),
                version="legacy",
                total_sections=1,
                estimated_duration_seconds=int((word_count / 150) * 60),
                sections=[
                    TranscriptSection(
                        section_number=1,
                        title="Full Narrative",
                        knowledge_point="Complete tour guide narrative",
                        transcript=plain_text,
                        estimated_duration_seconds=int((word_count / 150) * 60),
                        word_count=word_count,
                        audio_file=f"audio_{lang_code}.mp3"
                    )
                ],
                summary_points=[],
                has_sectioned_transcript=False
            )
        else:
            raise HTTPException(status_code=404, detail=f"No transcript found for language: {language}")

    # Load sectioned transcript
    with open(sectioned_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return SectionedTranscriptData(**data, has_sectioned_transcript=True)


@app.get("/pois/{city}/{poi_id}/audio/{filename}")
async def get_poi_audio(city: str, poi_id: str, filename: str):
    """
    Serve audio file for POI section or full audio.

    Args:
        city: City name
        poi_id: POI identifier
        filename: Audio filename (e.g., audio_section_1_en.mp3 or audio_en.mp3)

    Returns:
        MP3 audio file
    """
    city_slug = city.lower().replace(' ', '-')
    poi_slug = poi_id.lower().replace(' ', '-')

    poi_path = Path(config.get('content_dir', 'content')) / city_slug / poi_slug
    audio_file = poi_path / filename

    if not audio_file.exists():
        raise HTTPException(status_code=404, detail=f"Audio file not found: {filename}")

    return FileResponse(
        audio_file,
        media_type="audio/mpeg",
        filename=filename
    )


# ==== Research Endpoints ====

@app.get("/pois/{city}/{poi_id}/research", response_model=ResearchData)
async def get_research(city: str, poi_id: str):
    """
    Get research data for a POI (both structured and raw YAML).

    Args:
        city: City name (e.g., "Athens")
        poi_id: POI identifier in kebab-case (e.g., "acropolis-parthenon")

    Returns:
        ResearchData with structured fields and raw YAML content
    """
    research_path = get_research_path(city, poi_id)

    if not research_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research data not found for {city}/{poi_id}"
        )

    try:
        # Read raw YAML
        raw_yaml = research_path.read_text(encoding='utf-8')

        # Parse YAML
        data = yaml.safe_load(raw_yaml)

        # Extract POI section if it exists (some YAML files have 'poi' root, some don't)
        if 'poi' in data:
            data = data['poi']

        # Extract basic info
        basic_info_data = data.get('basic_info', {})
        basic_info = ResearchBasicInfo(
            period=basic_info_data.get('period'),
            date_built=basic_info_data.get('date_built'),
            date_relative=basic_info_data.get('date_relative'),
            current_state=basic_info_data.get('current_state'),
            description=basic_info_data.get('description'),
            labels=basic_info_data.get('labels')
        ) if basic_info_data else None

        # Extract core features
        core_features = data.get('core_features', [])

        # Extract people
        people_data = data.get('people', [])
        people = [
            ResearchPerson(
                name=p.get('name', ''),
                role=p.get('role'),
                personality=p.get('personality'),
                origin=p.get('origin'),
                relationship_type=p.get('relationship_type'),
                labels=p.get('labels')
            ) for p in people_data
        ] if people_data else None

        # Extract events
        events_data = data.get('events', [])
        events = [
            ResearchEvent(
                name=e.get('name', ''),
                date=e.get('date'),
                significance=e.get('significance'),
                labels=e.get('labels')
            ) for e in events_data
        ] if events_data else None

        # Extract locations
        locations_data = data.get('locations', [])
        locations = [
            ResearchLocation(
                name=l.get('name', ''),
                description=l.get('description'),
                labels=l.get('labels')
            ) for l in locations_data
        ] if locations_data else None

        # Extract concepts
        concepts_data = data.get('concepts', [])
        concepts = [
            ResearchConcept(
                name=c.get('name', ''),
                explanation=c.get('explanation'),
                labels=c.get('labels')
            ) for c in concepts_data
        ] if concepts_data else None

        return ResearchData(
            poi_id=poi_id,
            name=data.get('name', ''),
            city=data.get('city', city),
            basic_info=basic_info,
            core_features=core_features,
            people=people,
            events=events,
            locations=locations,
            concepts=concepts,
            raw_yaml=raw_yaml
        )

    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing YAML: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error reading research data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading research data: {str(e)}"
        )


# ==== Tour/Itinerary Endpoints ====

@app.get("/tours", response_model=List[TourSummary])
def list_tours(current_user: Optional[dict] = Depends(get_optional_user)):
    """
    List all saved tours, grouped by city.

    Returns list of tour summaries with key metadata.
    """
    import json

    try:
        tours = []
        tours_dir = Path("tours")

        if not tours_dir.exists():
            return []

        # Iterate through city directories
        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir() or city_dir.name.startswith('.'):
                continue

            city = city_dir.name

            # Iterate through tour directories
            for tour_dir in city_dir.iterdir():
                if not tour_dir.is_dir() or tour_dir.name.startswith('.'):
                    continue

                # Load metadata
                metadata_file = tour_dir / "metadata.json"
                if not metadata_file.exists():
                    continue

                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    # Get available languages
                    available_languages = metadata.get('languages', ['en'])
                    # Use first available language for loading details
                    language = available_languages[0] if available_languages else 'en'

                    # Load generation record for details (with language-specific pattern)
                    gen_record_pattern = f"generation_record_*_{language}.json"
                    gen_record_files = list(tour_dir.glob(gen_record_pattern))

                    # Fallback to old naming if new pattern not found (backward compatibility)
                    if not gen_record_files:
                        gen_record_files = list(tour_dir.glob("generation_record_*.json"))

                    interests = []
                    duration_days = 0
                    total_pois = 0
                    optimization_score = None

                    if gen_record_files:
                        with open(gen_record_files[0], 'r', encoding='utf-8') as f:
                            gen_record = json.load(f)

                        input_params = gen_record.get('input_parameters', {})
                        interests = input_params.get('interests', [])
                        duration_days = input_params.get('duration_days', 0)
                        total_pois = gen_record.get('metadata', {}).get('total_pois', 0)

                        opt_scores = gen_record.get('optimization_scores', {})
                        optimization_score = opt_scores.get('overall_score')

                    # Check visibility permissions
                    visibility = metadata.get('visibility', 'public')
                    creator_email = metadata.get('creator_email')

                    # Determine if user can see this tour
                    can_view = False

                    if visibility == 'public':
                        # Public tours are visible to everyone
                        can_view = True
                    elif current_user:
                        # Private tours: check if user is creator or backstage admin
                        user_email = current_user.get('email')
                        user_role = current_user.get('role')

                        if user_role == 'backstage_admin':
                            # Backstage admins can see all tours
                            can_view = True
                        elif user_email == creator_email:
                            # Creator can see their own private tours
                            can_view = True

                    # Only add tour if user has permission to view it
                    if can_view:
                        tours.append(TourSummary(
                            tour_id=metadata['tour_id'],
                            city=metadata['city'],
                            duration_days=duration_days,
                            total_pois=total_pois,
                            interests=interests,
                            created_at=metadata['created_at'],
                            optimization_score=optimization_score,
                            title_display=metadata.get('title_display'),
                            creator_email=creator_email,
                            visibility=visibility
                        ))

                except Exception as e:
                    logger.warning(f"Error loading tour {tour_dir.name}: {e}")
                    continue

        # Sort by city, then by creation date (newest first)
        tours.sort(key=lambda t: (t.city, t.created_at), reverse=True)

        return tours

    except Exception as e:
        logger.error(f"Error listing tours: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing tours: {str(e)}"
        )


@app.get("/tours/{tour_id}", response_model=TourDetail)
def get_tour(tour_id: str, language: str = "en", current_user: Optional[dict] = Depends(get_optional_user)):
    """
    Get complete tour details including itinerary, backup POIs, and selection transparency.

    Args:
        tour_id: Tour identifier (e.g., "rome-tour-20260129-111100-aa7baf")
        language: ISO 639-1 language code (e.g., 'en', 'zh-tw') - defaults to 'en'

    Returns:
        Complete tour details with all metadata
    """
    import json

    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Find tour directory
        tours_dir = Path("tours")
        tour_path = None

        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir():
                continue
            potential_path = city_dir / tour_id
            if potential_path.exists():
                tour_path = potential_path
                break

        if not tour_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour not found: {tour_id}"
            )

        # Load metadata
        metadata_file = tour_path / "metadata.json"
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        # Check visibility permissions
        visibility = metadata.get('visibility', 'public')
        creator_email = metadata.get('creator_email')

        # Determine if user can access this tour
        can_access = False

        if visibility == 'public':
            # Public tours are accessible to everyone
            can_access = True
        elif current_user:
            # Private tours: check if user is creator or backstage admin
            user_email = current_user.get('email')
            user_role = current_user.get('role')

            if user_role == 'backstage_admin':
                # Backstage admins can access all tours
                can_access = True
            elif user_email == creator_email:
                # Creator can access their own private tours
                can_access = True

        if not can_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have permission to access this tour"
            )

        # Check if requested language is available
        available_languages = metadata.get('languages', ['en'])
        if language not in available_languages:
            # Fallback to first available language
            if available_languages:
                logger.info(f"Language '{language}' not available. Using '{available_languages[0]}' instead.")
                language = available_languages[0]
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tour not found for language '{language}'. Available languages: {available_languages}"
                )

        # Load tour itinerary with language-specific filename
        tour_file = tour_path / get_tour_filename('tour', language)
        if not tour_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour file not found for language '{language}'"
            )

        with open(tour_file, 'r', encoding='utf-8') as f:
            tour_data = json.load(f)

        # Load and merge visit status
        visit_status = load_tour_visit_status(tour_path, language)
        tour_data = merge_visit_status_into_tour(tour_data, visit_status)

        # Load generation record with language-specific pattern
        gen_record_pattern = f"generation_record_*_{language}.json"
        gen_record_files = list(tour_path.glob(gen_record_pattern))
        if not gen_record_files:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation record not found for tour in language '{language}'"
            )

        with open(gen_record_files[0], 'r', encoding='utf-8') as f:
            gen_record = json.load(f)

        # Parse itinerary with POIs
        # Get city name from tour path
        city = tour_path.parent.name

        itinerary = []
        for day_data in tour_data.get('itinerary', []):
            pois = []
            for poi_data in day_data.get('pois', []):
                # Create POI object
                poi = TourPOI(**poi_data)

                # Add poi_id for URL construction
                from utils import poi_name_to_id, check_audio_exists, get_poi_audio_url
                poi.poi_id = poi_name_to_id(poi.poi)

                # Check if audio is available and add URL
                if check_audio_exists(city, poi.poi, language):
                    poi.audio_url = get_poi_audio_url(city, poi.poi, language)
                    poi.audio_available = True
                else:
                    poi.audio_available = False

                pois.append(poi)

            itinerary.append(TourDay(
                day=day_data['day'],
                pois=pois,
                total_hours=day_data['total_hours'],
                total_walking_km=day_data['total_walking_km'],
                start_time=day_data['start_time']
            ))

        # Parse backup POIs
        # Load from tour_data (which includes updates from replacements)
        # Fallback to gen_record if not present in tour_data (for old tours)
        backup_pois = {}
        raw_backup = tour_data.get('backup_pois', {}) or gen_record.get('poi_selection', {}).get('backup_pois', {})
        for poi_name, backups in raw_backup.items():
            backup_pois[poi_name] = [BackupPOI(**b) for b in backups]

        # Parse rejected POIs
        rejected_pois = []
        raw_rejected = gen_record.get('poi_selection', {}).get('rejected_pois', [])
        for rejected in raw_rejected:
            rejected_pois.append(RejectedPOI(**rejected))

        # Parse optimization scores
        opt_scores = gen_record.get('optimization_scores', {})
        optimization_scores = OptimizationScores(**opt_scores)

        # Build tour detail
        # Remove null values from input_parameters to prevent OpenAPI deserialization errors
        input_params = gen_record.get('input_parameters', {})
        if input_params:
            input_params = remove_null_values(input_params)

        tour_detail = TourDetail(
            metadata=TourMetadata(**metadata),
            itinerary=itinerary,
            input_parameters=input_params,
            backup_pois=backup_pois,
            rejected_pois=rejected_pois,
            optimization_scores=optimization_scores,
            constraints_violated=gen_record.get('constraints_violated', [])
        )

        return tour_detail

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading tour {tour_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading tour: {str(e)}"
        )


@app.get("/tours/{tour_id}/transcript-links", response_model=TranscriptLinks)
def get_tour_transcript_links(tour_id: str, language: str = "en"):
    """
    Get transcript links for a tour.

    Returns which transcripts are linked to this specific tour.
    This allows the tour to reference specific transcript versions.

    Args:
        tour_id: Tour identifier (e.g., "rome-tour-20260205-121250-11edf4")
        language: Language code (e.g., 'en', 'zh-tw')

    Returns:
        TranscriptLinks with all POI transcript mappings for this tour
    """
    import json

    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Find tour directory
        tours_dir = Path("tours")
        tour_path = None

        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir():
                continue
            potential_path = city_dir / tour_id
            if potential_path.exists():
                tour_path = potential_path
                break

        if not tour_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour not found: {tour_id}"
            )

        # Load transcript links
        links_file = tour_path / f"transcript_links_{language}.json"
        if not links_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcript links not found for tour '{tour_id}' in language '{language}'"
            )

        with open(links_file, 'r', encoding='utf-8') as f:
            links_data = json.load(f)

        return links_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading transcript links for tour {tour_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error loading transcript links: {str(e)}"
        )


# ==== POI Replacement Helper Functions ====

def poi_name_to_id(poi_name: str) -> str:
    """Convert POI name to identifier (kebab-case)"""
    return poi_name.lower().replace(' ', '-').replace('(', '').replace(')', '').replace("'", '')


def update_backup_pois_for_replacement(tour_data: dict, gen_record: dict, original_poi: str, replacement_poi: str):
    """
    Defensive swap in backup_pois structure that preserves all backup options.

    Concept: Each itinerary position has a GROUP of POIs (1 selected + N backups).
    When replacing, just swap which POI is selected vs backup in that group.
    CRITICAL: All backup POIs must be preserved - we never lose options!

    Example:
        Before: Selected: Colosseum, Backups: [Theater of Marcellus, Circus Maximus, Baths of Caracalla]
        Replace Colosseum → Theater of Marcellus
        After:  Selected: Theater of Marcellus, Backups: [Colosseum, Circus Maximus, Baths of Caracalla]
                (Colosseum is now a backup, Theater of Marcellus removed from backups since it's selected)

    Args:
        tour_data: Tour data dictionary
        gen_record: Generation record (fallback if tour_data missing backup_pois)
        original_poi: POI being replaced (currently selected)
        replacement_poi: POI to select (currently in backups)
    """
    if 'backup_pois' not in tour_data:
        tour_data['backup_pois'] = {}

    # DEFENSIVE: Get backup list from tour_data first, fallback to gen_record
    original_backups = tour_data['backup_pois'].get(original_poi, [])

    # If not in tour_data, try generation record (defensive - should have been loaded earlier)
    if not original_backups and gen_record:
        gen_backup_pois = gen_record.get('poi_selection', {}).get('backup_pois', {})
        original_backups = gen_backup_pois.get(original_poi, [])
        logger.info(f"Retrieved {len(original_backups)} backup POIs for '{original_poi}' from generation record")

    # DEFENSIVE: Ensure replacement_poi is actually in the backup list
    replacement_poi_metadata = next(
        (b for b in original_backups if b['poi'] == replacement_poi),
        None
    )

    if not replacement_poi_metadata:
        logger.error(f"DEFENSIVE CHECK FAILED: '{replacement_poi}' not found in backup list for '{original_poi}'")
        logger.error(f"Available backups: {[b['poi'] for b in original_backups]}")
        raise ValueError(f"Cannot replace: '{replacement_poi}' is not a valid backup for '{original_poi}'")

    # Create new backup list: original becomes backup, replacement removed (it's now selected)
    remaining_backups = [b for b in original_backups if b['poi'] != replacement_poi]

    # Build new backup list for replacement_poi (now the selected POI)
    new_backups = []

    # Add original POI as first backup (with metadata from replacement for consistency)
    new_backups.append({
        'poi': original_poi,
        'similarity_score': replacement_poi_metadata.get('similarity_score', 1.0),
        'reason': replacement_poi_metadata.get('reason', 'Original POI, now alternative option'),
        'substitute_scenario': f"Reverse replacement - swap back to {original_poi}"
    })

    # CRITICAL: Preserve all other backup options
    new_backups.extend(remaining_backups)

    # Defensive logging
    logger.info(f"POI swap: '{original_poi}' → '{replacement_poi}'")
    logger.info(f"  Original had {len(original_backups)} backups")
    logger.info(f"  New selection '{replacement_poi}' now has {len(new_backups)} backups (including original)")
    logger.info(f"  Backup POIs preserved: {[b['poi'] for b in new_backups]}")

    # Update backup_pois structure for the NEW selected POI
    tour_data['backup_pois'][replacement_poi] = new_backups

    # KEEP the old backup_pois entry for original_poi (allows future swaps back)
    # Don't delete tour_data['backup_pois'][original_poi] - keep it for reference!

    # Remove original POI's entry (it's no longer selected)
    if original_poi in tour_data['backup_pois']:
        del tour_data['backup_pois'][original_poi]

    logger.info(f"Swapped POIs: {original_poi} → {replacement_poi}. New backup count: {len(new_backups)}")


def simple_poi_replacement(tour_data: dict, original_poi: str, replacement_poi: str, day_num: int, city: str) -> dict:
    """
    Simple POI swap - maintains order and timing.
    Only updates POI name and metadata.

    Args:
        tour_data: Tour data dictionary
        original_poi: POI name to replace
        replacement_poi: New POI name
        day_num: Day number where POI is located
        city: City name

    Returns:
        Updated tour data dictionary
    """
    replacement_poi_id = poi_name_to_id(replacement_poi)

    # Load replacement POI metadata
    try:
        replacement_data = load_poi_from_content(city, replacement_poi_id)
        replacement_metadata = replacement_data.get('poi', {}).get('metadata', {})
    except Exception as e:
        logger.warning(f"Could not load metadata for replacement POI {replacement_poi}: {e}")
        replacement_metadata = {}

    # Find and replace POI in itinerary
    for day in tour_data['itinerary']:
        if day['day'] == day_num:
            for i, poi_obj in enumerate(day['pois']):
                if poi_obj['poi'] == original_poi:
                    # Update POI while preserving tour-specific fields
                    day['pois'][i] = {
                        'poi': replacement_poi,
                        'reason': poi_obj.get('reason', 'Selected POI'),
                        'suggested_day': poi_obj.get('suggested_day', day_num),
                        'estimated_hours': replacement_metadata.get('estimated_hours', poi_obj.get('estimated_hours', 2.0)),
                        'priority': poi_obj.get('priority', 'medium'),
                        'coordinates': replacement_metadata.get('coordinates', {}),
                        'operation_hours': replacement_metadata.get('operation_hours', {}),
                        'visit_info': replacement_metadata.get('visit_info', {}),
                        'period': replacement_metadata.get('period'),
                        'date_built': replacement_metadata.get('date_built'),
                        'walking_time_to_next': poi_obj.get('walking_time_to_next'),
                        'distance_to_next_km': poi_obj.get('distance_to_next_km')
                    }
                    logger.info(f"Replaced {original_poi} with {replacement_poi} in day {day_num}")
                    break
            break

    return tour_data


def update_transcript_links_for_replacement(tour_path: Path, original_poi: str, replacement_poi: str, language: str, city: str):
    """
    Update transcript links file to point to replacement POI.

    Args:
        tour_path: Path to tour directory
        original_poi: Original POI name
        replacement_poi: Replacement POI name
        language: Language code
        city: City name
    """
    import json

    links_file = tour_path / f"transcript_links_{language}.json"

    if not links_file.exists():
        logger.warning(f"Transcript links file not found: {links_file}")
        return

    # Load transcript links
    with open(links_file, 'r', encoding='utf-8') as f:
        links_data = json.load(f)

    # Find and update link
    original_poi_id = poi_name_to_id(original_poi)
    replacement_poi_id = poi_name_to_id(replacement_poi)

    for link in links_data['links']:
        if link['poi_id'] == original_poi_id:
            # Update to point to replacement POI
            city_slug = city.lower().replace(' ', '-')
            replacement_transcript_path = Path(f"content/{city_slug}/{replacement_poi_id}/transcript_{language}.txt")

            # Load replacement POI metadata for version
            try:
                poi_metadata_path = Path(f"content/{city_slug}/{replacement_poi_id}/metadata.json")
                if poi_metadata_path.exists():
                    with open(poi_metadata_path, 'r', encoding='utf-8') as f:
                        poi_metadata = json.load(f)
                        current_version = poi_metadata.get('current_version', 1)
                else:
                    current_version = 1
            except Exception as e:
                logger.warning(f"Could not load version for {replacement_poi}: {e}")
                current_version = 1

            link['poi'] = replacement_poi
            link['poi_id'] = replacement_poi_id
            link['transcript_path'] = str(replacement_transcript_path)
            link['transcript_version'] = f"v{current_version}"
            link['linked_at'] = datetime.now().isoformat()

            logger.info(f"Updated transcript link from {original_poi} to {replacement_poi}")
            break

    # Save updated links
    with open(links_file, 'w', encoding='utf-8') as f:
        json.dump(links_data, f, indent=2, ensure_ascii=False)


def reoptimize_with_replacement(tour_data: dict, gen_record: dict, original_poi: str, replacement_poi: str, city: str, day: int) -> dict:
    """
    Re-run itinerary optimizer with replacement POI using smart 3-tier strategy.

    Uses ItineraryReoptimizer which selects optimal strategy:
    - Tier 1: Local swap for single POI on small day
    - Tier 2: Day-level optimization for few affected days
    - Tier 3: Full tour re-optimization for many affected days

    Args:
        tour_data: Tour data dictionary
        gen_record: Generation record with input parameters
        original_poi: POI name to replace
        replacement_poi: New POI name
        city: City name
        day: Day number where replacement occurs

    Returns:
        Updated tour data dictionary with re-optimized itinerary
    """
    from trip_planner.itinerary_reoptimizer import ItineraryReoptimizer

    # Create reoptimizer instance
    reoptimizer = ItineraryReoptimizer(config)

    # Prepare replacement list
    replacements = [{
        'original_poi': original_poi,
        'replacement_poi': replacement_poi,
        'day': day
    }]

    # Extract preferences from generation record
    input_params = gen_record.get('input_parameters', {})
    preferences = input_params.get('preferences', {})

    logger.info(f"Re-optimizing tour: replacing {original_poi} with {replacement_poi} on day {day}")

    # Run smart re-optimization
    result = reoptimizer.reoptimize(
        tour_data=tour_data,
        replacements=replacements,
        city=city,
        preferences=preferences
    )

    # Update tour data with re-optimized itinerary
    tour_data['itinerary'] = result['itinerary']
    tour_data['optimization_scores'] = result['optimization_scores']
    tour_data['distance_cache'] = result['distance_cache']

    # Add metadata about re-optimization
    if 'reoptimization_history' not in tour_data:
        tour_data['reoptimization_history'] = []

    tour_data['reoptimization_history'].append({
        'timestamp': datetime.now().isoformat(),
        'strategy_used': result['strategy_used'],
        'replacements': replacements,
        'scores': result['optimization_scores']
    })

    logger.info(f"Re-optimization complete using {result['strategy_used']} strategy. New score: {result['optimization_scores'].get('overall_score', 0):.2f}")

    return tour_data


# ==== Visit Tracking Helper Functions ====

def get_visit_status_path(tour_path: Path, language: str) -> Path:
    """Get path to visit status file"""
    return tour_path / f"visit_status_{language}.json"


def load_tour_visit_status(tour_path: Path, language: str) -> dict:
    """Load visit status, return empty structure if file doesn't exist"""
    import json

    visit_file = get_visit_status_path(tour_path, language)
    if visit_file.exists():
        try:
            with open(visit_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading visit status: {e}")

    return {
        'tour_id': tour_path.name,
        'language': language,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'visits': {}
    }


def save_tour_visit_status(tour_path: Path, visit_data: dict, language: str):
    """Save visit status to file"""
    import json

    visit_data['updated_at'] = datetime.now().isoformat()
    visit_file = get_visit_status_path(tour_path, language)
    try:
        with open(visit_file, 'w', encoding='utf-8') as f:
            json.dump(visit_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving visit status: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving visit status: {str(e)}")


def merge_visit_status_into_tour(tour_data: dict, visit_status: dict) -> dict:
    """Merge visit status into tour POIs for display"""
    visits = visit_status.get('visits', {})
    for day in tour_data.get('itinerary', []):
        for poi_obj in day['pois']:
            poi_name = poi_obj['poi']
            if poi_name in visits:
                visit_info = visits[poi_name]
                poi_obj['visited'] = visit_info.get('visited', False)
                poi_obj['visited_at'] = visit_info.get('visited_at')
                poi_obj['visit_notes'] = visit_info.get('notes')
            else:
                poi_obj['visited'] = False
                poi_obj['visited_at'] = None
                poi_obj['visit_notes'] = None
    return tour_data


@app.post("/tours/{tour_id}/replace-poi", response_model=POIReplacementResponse)
def replace_poi_in_tour(tour_id: str, request: POIReplacementRequest):
    """
    Replace a POI in a tour with a backup POI.

    Supports two modes:
    - simple: Replace POI and keep current order/timing
    - reoptimize: Replace POI and re-run itinerary optimizer (NOT YET IMPLEMENTED)

    Args:
        tour_id: Tour identifier
        request: POI replacement request with mode, POI names, language, and day

    Returns:
        POI replacement response with success status and new version info
    """
    import json
    from trip_planner.tour_manager import TourManager

    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(request.language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Find tour directory
        tours_dir = Path("tours")
        tour_path = None
        city = None

        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir():
                continue
            potential_path = city_dir / tour_id
            if potential_path.exists():
                tour_path = potential_path
                city = city_dir.name
                break

        if not tour_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour not found: {tour_id}"
            )

        # Load tour data
        tour_file = tour_path / get_tour_filename('tour', language)
        if not tour_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour file not found for language '{language}'"
            )

        with open(tour_file, 'r', encoding='utf-8') as f:
            tour_data = json.load(f)

        # Load generation record
        gen_record_pattern = f"generation_record_*_{language}.json"
        gen_record_files = list(tour_path.glob(gen_record_pattern))
        if not gen_record_files:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation record not found for tour in language '{language}'"
            )

        with open(gen_record_files[0], 'r', encoding='utf-8') as f:
            gen_record = json.load(f)

        # CRITICAL FIX: Merge ALL backup_pois from generation record into tour_data
        # This prevents losing backup POIs for unreplaced POIs when we save
        backup_pois_from_gen = gen_record.get('poi_selection', {}).get('backup_pois', {})

        if 'backup_pois' not in tour_data:
            tour_data['backup_pois'] = {}

        # Merge: gen_record has ALL original backup POIs, tour_data has updates from replacements
        for poi_name, backup_list in backup_pois_from_gen.items():
            if poi_name not in tour_data['backup_pois']:
                tour_data['backup_pois'][poi_name] = backup_list
                logger.debug(f"Preserved {len(backup_list)} backup POIs for '{poi_name}' from generation record")

        logger.info(f"Complete backup_pois loaded: {len(tour_data['backup_pois'])} POIs with backup options")

        # Validate: Original POI should be in tour
        poi_in_tour = False
        for day in tour_data['itinerary']:
            for poi_obj in day['pois']:
                if poi_obj['poi'] == request.original_poi:
                    poi_in_tour = True
                    break
            if poi_in_tour:
                break

        if not poi_in_tour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Original POI '{request.original_poi}' not found in tour"
            )

        # Validate: Replacement POI should be in backup list for original POI
        if request.original_poi not in tour_data['backup_pois']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No backup POIs available for '{request.original_poi}'"
            )

        backup_list = tour_data['backup_pois'][request.original_poi]

        backup_poi_obj = next(
            (b for b in backup_list if b['poi'] == request.replacement_poi),
            None
        )

        if not backup_poi_obj:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"'{request.replacement_poi}' is not in backup list for '{request.original_poi}'"
            )

        # Perform replacement based on mode
        if request.mode == 'simple':
            # Simple swap - keep order and timing
            updated_tour = simple_poi_replacement(
                tour_data,
                request.original_poi,
                request.replacement_poi,
                request.day,
                city
            )
        else:  # mode == 'reoptimize'
            # Re-run optimizer with replacement POI
            updated_tour = reoptimize_with_replacement(
                tour_data,
                gen_record,
                request.original_poi,
                request.replacement_poi,
                city,
                request.day
            )

        # Update backup_pois structure
        update_backup_pois_for_replacement(
            updated_tour,
            gen_record,
            request.original_poi,
            request.replacement_poi
        )

        # Update transcript links
        update_transcript_links_for_replacement(
            tour_path,
            request.original_poi,
            request.replacement_poi,
            language,
            city
        )

        # Save new tour version
        tour_manager = TourManager(config, content_dir="content")
        result = tour_manager.save_tour(
            tour_data=updated_tour,
            city=city,
            input_parameters=gen_record.get('input_parameters', {}),
            tour_id=tour_id,
            selection_result=gen_record.get('poi_selection', {}),
            language=language
        )

        return POIReplacementResponse(
            success=True,
            tour_id=tour_id,
            new_version=result['version'],
            new_version_string=result['version_string'],
            replaced_poi=request.original_poi,
            with_poi=request.replacement_poi,
            mode_used=request.mode,
            optimization_scores=updated_tour.get('optimization_scores'),
            message=f"Successfully replaced '{request.original_poi}' with '{request.replacement_poi}' using {request.mode} mode"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replacing POI in tour {tour_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error replacing POI: {str(e)}"
        )


@app.post("/tours/{tour_id}/replace-pois-batch", response_model=BatchPOIReplacementResponse)
def batch_replace_pois_in_tour(tour_id: str, request: BatchPOIReplacementRequest):
    """
    Replace multiple POIs in a tour with backup POIs in a single operation.

    DEFENSIVE DESIGN:
    - Frontend only needs to specify: which POI to replace (original_poi) and what to replace it with (replacement_poi)
    - Backend handles all the logic: finding the POI, detecting which day it's on, validating the replacement
    - Day parameter is optional - backend auto-detects if not provided, and validates/corrects if provided incorrectly
    - All backup POIs are preserved - no data loss even if frontend makes mistakes
    - Replacement POI must be from the original POI's backup list (validated by backend)

    Example Request:
        {
          "replacements": [
            {"original_poi": "Colosseum", "replacement_poi": "Baths of Caracalla"}
          ],
          "mode": "simple",
          "language": "zh-tw"
        }

    Backend will:
    1. Find "Colosseum" in the tour (any day)
    2. Verify "Baths of Caracalla" is in Colosseum's backup list
    3. Swap them safely, preserving all other backup options
    4. Keep all backup POIs intact for future replacements

    Supports two modes:
    - simple: Replace POIs and keep current order/timing
    - reoptimize: Replace POIs and re-run itinerary optimizer

    Args:
        tour_id: Tour identifier
        request: Batch POI replacement request with mode, list of replacements, and language

    Returns:
        Batch POI replacement response with success status and new version info
    """
    import json
    from trip_planner.tour_manager import TourManager

    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(request.language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Find tour directory
        tours_dir = Path("tours")
        tour_path = None
        city = None

        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir():
                continue
            potential_path = city_dir / tour_id
            if potential_path.exists():
                tour_path = potential_path
                city = city_dir.name
                break

        if not tour_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour not found: {tour_id}"
            )

        # Load tour data
        tour_file = tour_path / get_tour_filename('tour', language)
        if not tour_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour file not found for language '{language}'"
            )

        with open(tour_file, 'r', encoding='utf-8') as f:
            tour_data = json.load(f)

        # Load generation record
        gen_record_pattern = f"generation_record_*_{language}.json"
        gen_record_files = list(tour_path.glob(gen_record_pattern))
        if not gen_record_files:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Generation record not found for tour in language '{language}'"
            )

        with open(gen_record_files[0], 'r', encoding='utf-8') as f:
            gen_record = json.load(f)

        # CRITICAL FIX: Merge ALL backup_pois from generation record into tour_data
        # This prevents losing backup POIs for unreplaced POIs when we save
        backup_pois_from_gen = gen_record.get('poi_selection', {}).get('backup_pois', {})

        if 'backup_pois' not in tour_data:
            tour_data['backup_pois'] = {}

        # Merge: gen_record has ALL original backup POIs, tour_data has updates from replacements
        # We need to preserve both - tour_data updates take precedence, but add missing ones from gen_record
        for poi_name, backup_list in backup_pois_from_gen.items():
            if poi_name not in tour_data['backup_pois']:
                # POI hasn't been replaced yet, use original backup list
                tour_data['backup_pois'][poi_name] = backup_list
                logger.debug(f"Preserved {len(backup_list)} backup POIs for '{poi_name}' from generation record")

        logger.info(f"Complete backup_pois loaded: {len(tour_data['backup_pois'])} POIs with backup options")

        # Get references for validation (now both point to same merged data)
        backup_pois_from_tour = tour_data['backup_pois']

        # Validate all replacements and auto-detect day if needed
        for replacement_item in request.replacements:
            # Validate: Original POI should be in tour and auto-detect day if not provided
            poi_in_tour = False
            detected_day = None

            for day in tour_data['itinerary']:
                for poi_obj in day['pois']:
                    if poi_obj['poi'] == replacement_item.original_poi:
                        poi_in_tour = True
                        detected_day = day['day']
                        break
                if poi_in_tour:
                    break

            if not poi_in_tour:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Original POI '{replacement_item.original_poi}' not found in tour"
                )

            # Auto-detect day if not provided by frontend (defensive programming)
            if replacement_item.day is None:
                replacement_item.day = detected_day
                logger.info(f"Auto-detected day {detected_day} for POI '{replacement_item.original_poi}'")
            else:
                # Validate frontend-provided day matches actual location
                if replacement_item.day != detected_day:
                    logger.warning(f"Frontend provided day {replacement_item.day} but POI is actually on day {detected_day}. Using actual day {detected_day}.")
                    replacement_item.day = detected_day

            # Validate: Replacement POI should be in backup list for original POI
            # Now backup_pois_from_tour has complete merged data
            if replacement_item.original_poi not in backup_pois_from_tour:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No backup POIs available for '{replacement_item.original_poi}'"
                )

            backup_list = backup_pois_from_tour[replacement_item.original_poi]

            backup_poi_obj = next(
                (b for b in backup_list if b['poi'] == replacement_item.replacement_poi),
                None
            )

            if not backup_poi_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{replacement_item.replacement_poi}' is not in backup list for '{replacement_item.original_poi}'. Available backups: {[b['poi'] for b in backup_list]}"
                )

        # Process replacements based on mode
        if request.mode == 'simple':
            # Apply simple replacements sequentially
            updated_tour = tour_data
            for replacement_item in request.replacements:
                updated_tour = simple_poi_replacement(
                    updated_tour,
                    replacement_item.original_poi,
                    replacement_item.replacement_poi,
                    replacement_item.day,
                    city
                )
        else:  # mode == 'reoptimize'
            # Use smart re-optimization with 3-tier strategy
            from trip_planner.itinerary_reoptimizer import ItineraryReoptimizer

            # Create reoptimizer instance
            reoptimizer = ItineraryReoptimizer(config)

            # Prepare replacement list
            replacements_list = [
                {
                    'original_poi': item.original_poi,
                    'replacement_poi': item.replacement_poi,
                    'day': item.day
                }
                for item in request.replacements
            ]

            # Extract preferences from generation record
            input_params = gen_record.get('input_parameters', {})
            preferences = input_params.get('preferences', {})

            logger.info(f"Re-optimizing tour with {len(replacements_list)} replacement(s)")

            # Run smart re-optimization (handles all replacements at once)
            result = reoptimizer.reoptimize(
                tour_data=tour_data,
                replacements=replacements_list,
                city=city,
                preferences=preferences
            )

            # Update tour data with re-optimized itinerary
            updated_tour = tour_data
            updated_tour['itinerary'] = result['itinerary']
            updated_tour['optimization_scores'] = result['optimization_scores']
            updated_tour['distance_cache'] = result['distance_cache']

            # Add metadata about re-optimization
            if 'reoptimization_history' not in updated_tour:
                updated_tour['reoptimization_history'] = []

            updated_tour['reoptimization_history'].append({
                'timestamp': datetime.now().isoformat(),
                'strategy_used': result['strategy_used'],
                'replacements': replacements_list,
                'scores': result['optimization_scores']
            })

            logger.info(f"Re-optimization complete using {result['strategy_used']} strategy. New score: {result['optimization_scores'].get('overall_score', 0):.2f}")

        # Update backup_pois structure for all replacements
        for replacement_item in request.replacements:
            update_backup_pois_for_replacement(
                updated_tour,
                gen_record,
                replacement_item.original_poi,
                replacement_item.replacement_poi
            )

        # Update transcript links for all replacements
        for replacement_item in request.replacements:
            update_transcript_links_for_replacement(
                tour_path,
                replacement_item.original_poi,
                replacement_item.replacement_poi,
                language,
                city
            )

        # Save new tour version
        tour_manager = TourManager(config, content_dir="content")
        result = tour_manager.save_tour(
            tour_data=updated_tour,
            city=city,
            input_parameters=gen_record.get('input_parameters', {}),
            tour_id=tour_id,
            selection_result=gen_record.get('poi_selection', {}),
            language=language
        )

        # Build replacement list for response
        replacements_list = [
            {
                "original": item.original_poi,
                "replacement": item.replacement_poi,
                "day": str(item.day)
            }
            for item in request.replacements
        ]

        return BatchPOIReplacementResponse(
            success=True,
            tour_id=tour_id,
            new_version=result['version'],
            new_version_string=result['version_string'],
            replacements_applied=len(request.replacements),
            replacements=replacements_list,
            mode_used=request.mode,
            optimization_scores=updated_tour.get('optimization_scores'),
            message=f"Successfully replaced {len(request.replacements)} POI(s) using {request.mode} mode"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch replacing POIs in tour {tour_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error batch replacing POIs: {str(e)}"
        )


# ==== Visit Tracking Endpoints ====

@app.post("/tours/{tour_id}/visit", response_model=MarkVisitedResponse)
def mark_poi_visited(tour_id: str, request: MarkVisitedRequest, language: str = "en"):
    """
    Mark a POI as visited or unvisited.

    Args:
        tour_id: Tour identifier
        request: Mark visited request with POI name and status
        language: ISO 639-1 language code (e.g., 'en', 'zh-tw')

    Returns:
        Mark visited response with success status
    """
    import json

    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Find tour directory
        tours_dir = Path("tours")
        tour_path = None

        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir():
                continue
            potential_path = city_dir / tour_id
            if potential_path.exists():
                tour_path = potential_path
                break

        if not tour_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour not found: {tour_id}"
            )

        # Load tour data to verify POI exists
        tour_file = tour_path / get_tour_filename('tour', language)
        if not tour_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour file not found for language '{language}'"
            )

        with open(tour_file, 'r', encoding='utf-8') as f:
            tour_data = json.load(f)

        # Verify POI exists in tour
        poi_found = False
        for day in tour_data.get('itinerary', []):
            for poi_obj in day.get('pois', []):
                if poi_obj['poi'] == request.poi:
                    poi_found = True
                    break
            if poi_found:
                break

        if not poi_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"POI '{request.poi}' not found in tour"
            )

        # Load visit status
        visit_status = load_tour_visit_status(tour_path, language)

        # Update visit status for this POI
        visited_at = datetime.now().isoformat() if request.visited else None

        visit_status['visits'][request.poi] = {
            'poi': request.poi,
            'visited': request.visited,
            'visited_at': visited_at,
            'notes': request.notes
        }

        # Save updated visit status
        save_tour_visit_status(tour_path, visit_status, language)

        return MarkVisitedResponse(
            success=True,
            tour_id=tour_id,
            poi=request.poi,
            visited=request.visited,
            visited_at=visited_at,
            message=f"Marked '{request.poi}' as {'visited' if request.visited else 'not visited'}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking POI visited in tour {tour_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating visit status: {str(e)}"
        )


@app.post("/tours/{tour_id}/visit-bulk", response_model=BulkMarkVisitedResponse)
def bulk_mark_visited(tour_id: str, request: BulkMarkVisitedRequest, language: str = "en"):
    """
    Mark multiple POIs as visited/unvisited in bulk.

    Use case: Mark all POIs on a day as visited.

    Args:
        tour_id: Tour identifier
        request: Bulk mark visited request with list of POI names
        language: ISO 639-1 language code (e.g., 'en', 'zh-tw')

    Returns:
        Bulk mark visited response with success status
    """
    import json

    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Find tour directory
        tours_dir = Path("tours")
        tour_path = None

        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir():
                continue
            potential_path = city_dir / tour_id
            if potential_path.exists():
                tour_path = potential_path
                break

        if not tour_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour not found: {tour_id}"
            )

        # Load tour data to verify POIs exist
        tour_file = tour_path / get_tour_filename('tour', language)
        if not tour_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour file not found for language '{language}'"
            )

        with open(tour_file, 'r', encoding='utf-8') as f:
            tour_data = json.load(f)

        # Verify all POIs exist in tour
        tour_pois = set()
        for day in tour_data.get('itinerary', []):
            for poi_obj in day.get('pois', []):
                tour_pois.add(poi_obj['poi'])

        missing_pois = [poi for poi in request.pois if poi not in tour_pois]
        if missing_pois:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"POIs not found in tour: {', '.join(missing_pois)}"
            )

        # Load visit status
        visit_status = load_tour_visit_status(tour_path, language)

        # Update visit status for all POIs
        visited_at = datetime.now().isoformat() if request.visited else None

        for poi_name in request.pois:
            visit_status['visits'][poi_name] = {
                'poi': poi_name,
                'visited': request.visited,
                'visited_at': visited_at,
                'notes': None
            }

        # Save updated visit status
        save_tour_visit_status(tour_path, visit_status, language)

        return BulkMarkVisitedResponse(
            success=True,
            tour_id=tour_id,
            updated_count=len(request.pois),
            pois=request.pois,
            message=f"Marked {len(request.pois)} POI(s) as {'visited' if request.visited else 'not visited'}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk marking POIs visited in tour {tour_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating visit status: {str(e)}"
        )


@app.delete("/tours/{tour_id}/visit")
def reset_visit_status(tour_id: str, language: str = "en"):
    """
    Reset all visit status (deletes visit_status file).

    Args:
        tour_id: Tour identifier
        language: ISO 639-1 language code (e.g., 'en', 'zh-tw')

    Returns:
        Success response
    """
    try:
        # Validate and normalize language code
        try:
            language = normalize_language_code(language)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

        # Find tour directory
        tours_dir = Path("tours")
        tour_path = None

        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir():
                continue
            potential_path = city_dir / tour_id
            if potential_path.exists():
                tour_path = potential_path
                break

        if not tour_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tour not found: {tour_id}"
            )

        # Delete visit status file
        visit_file = get_visit_status_path(tour_path, language)
        if visit_file.exists():
            visit_file.unlink()
            logger.info(f"Deleted visit status file: {visit_file}")
            return SuccessResponse(
                message=f"Visit status reset successfully for tour {tour_id}"
            )
        else:
            return SuccessResponse(
                message=f"No visit status to reset for tour {tour_id}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting visit status for tour {tour_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting visit status: {str(e)}"
        )


# ==== Admin Endpoints ====

@app.get("/admin/users")
async def list_users(current_user: dict = Depends(require_backstage_admin)):
    """
    List all active user sessions (admin only)

    Returns information about all users with active sessions,
    separated by backstage and client app users.
    """
    backstage_users = []
    client_users = []

    for token, session in session_manager.sessions.items():
        user_data = session["user"]
        user_info = {
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "role": user_data.get("role", "client_user"),
            "scopes": user_data.get("scopes", []),
            "client_type": user_data.get("client_type", "backstage"),
            "last_accessed": session["last_accessed"].isoformat(),
            "created_at": session["created_at"].isoformat(),
            "expires_at": session["expires_at"].isoformat()
        }

        # Separate by client type
        if "backstage" in user_data.get("scopes", []):
            backstage_users.append(user_info)
        else:
            client_users.append(user_info)

    return {
        "backstage": {
            "users": backstage_users,
            "count": len(backstage_users)
        },
        "client": {
            "users": client_users,
            "count": len(client_users)
        },
        "total": len(backstage_users) + len(client_users)
    }


@app.post("/admin/migrate-tours-visibility")
async def migrate_tours_visibility(current_user: dict = Depends(require_backstage_admin)):
    """
    Migrate all existing tours to have proper visibility settings.

    This endpoint marks all existing tours as public and adds creator metadata.
    Should be run once after deploying the visibility feature.

    Admin only.
    """
    import json

    try:
        migrated_count = 0
        error_count = 0
        tours_dir = Path("tours")

        if not tours_dir.exists():
            return {"message": "No tours directory found", "migrated": 0}

        # Iterate through all tours
        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir() or city_dir.name.startswith('.'):
                continue

            for tour_dir in city_dir.iterdir():
                if not tour_dir.is_dir() or tour_dir.name.startswith('.'):
                    continue

                metadata_file = tour_dir / "metadata.json"
                if not metadata_file.exists():
                    continue

                try:
                    # Load existing metadata
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)

                    # Check if already migrated
                    if 'visibility' in metadata:
                        continue

                    # Set default values for existing tours
                    metadata['visibility'] = 'public'  # All existing tours are public

                    # Try to infer creator from version history
                    if 'creator_email' not in metadata:
                        # Check first version history entry for user_id
                        for lang in metadata.get('languages', ['en']):
                            version_history_key = f'version_history_{lang}'
                            version_history = metadata.get(version_history_key, [])
                            if version_history and len(version_history) > 0:
                                first_version = version_history[0]
                                user_id = first_version.get('user_id', 'anonymous')
                                if user_id != 'anonymous':
                                    metadata['creator_email'] = user_id
                                    metadata['creator_role'] = 'backstage_admin'  # Assume backstage
                                break

                    # Set created_via based on presence of creator
                    if 'created_via' not in metadata:
                        metadata['created_via'] = 'backstage_ui'

                    # Save updated metadata
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)

                    migrated_count += 1
                    logger.info(f"Migrated tour: {metadata.get('tour_id', tour_dir.name)}")

                except Exception as e:
                    logger.error(f"Error migrating tour {tour_dir.name}: {e}")
                    error_count += 1
                    continue

        return {
            "success": True,
            "message": f"Migration complete",
            "migrated": migrated_count,
            "errors": error_count,
            "total_processed": migrated_count + error_count
        }

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )


# ==== Main Entry Point ====

if __name__ == "__main__":
    import uvicorn

    # Run the server
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
