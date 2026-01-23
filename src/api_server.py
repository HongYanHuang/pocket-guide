"""
FastAPI Backend for POI Metadata Management

This API provides endpoints for viewing and editing POI metadata,
including coordinates, operation hours, and distance matrices.
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Optional
import logging
import yaml
from datetime import datetime

from api_models import (
    City, POISummary, POIDetail, POIMetadata, POIMetadataUpdate,
    DistanceMatrix, CollectionResult, VerificationReport,
    ErrorResponse, SuccessResponse,
    TranscriptData, TranscriptUpdate, ResearchData,
    ResearchBasicInfo, ResearchPerson, ResearchEvent,
    ResearchLocation, ResearchConcept
)
from poi_metadata_agent import POIMetadataAgent
from utils import load_config

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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load configuration
try:
    config = load_config()
    metadata_agent = POIMetadataAgent(config)
    logger.info("API server initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize API server: {e}")
    config = None
    metadata_agent = None


# ==== Helper Functions ====

def get_agent() -> POIMetadataAgent:
    """Get metadata agent instance or raise error"""
    if metadata_agent is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metadata agent not initialized. Check configuration."
        )
    return metadata_agent


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


def get_transcript_path(city: str, poi_id: str) -> Path:
    """Get path to transcript file"""
    city_slug = city.lower().replace(' ', '-')
    return Path("content") / city_slug / poi_id / "transcript.txt"


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


def create_transcript_backup(city: str, poi_id: str) -> str:
    """Create backup of transcript file before editing"""
    transcript_path = get_transcript_path(city, poi_id)

    if not transcript_path.exists():
        return ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = transcript_path.parent / f"transcript_backup_{timestamp}.txt"

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
async def get_transcript(city: str, poi_id: str):
    """
    Get transcript and summary for a POI.

    Args:
        city: City name (e.g., "Athens")
        poi_id: POI identifier in kebab-case (e.g., "acropolis-parthenon")

    Returns:
        TranscriptData with transcript text, summary points, and availability flags
    """
    transcript_path = get_transcript_path(city, poi_id)
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
            has_summary=has_summary
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
    Update transcript for a POI (creates backup before saving).

    Args:
        city: City name (e.g., "Athens")
        poi_id: POI identifier in kebab-case (e.g., "acropolis-parthenon")
        update: TranscriptUpdate with new transcript text

    Returns:
        SuccessResponse with backup filename
    """
    transcript_path = get_transcript_path(city, poi_id)

    if not transcript_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript not found for {city}/{poi_id}"
        )

    try:
        # Create backup before editing
        backup_filename = create_transcript_backup(city, poi_id)

        # Write new content
        transcript_path.write_text(update.transcript, encoding='utf-8')

        logger.info(f"Updated transcript for {city}/{poi_id}")

        return SuccessResponse(
            message="Transcript updated successfully",
            data={"backup_file": backup_filename}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transcript: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating transcript: {str(e)}"
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
