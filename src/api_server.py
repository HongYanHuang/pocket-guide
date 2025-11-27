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

from api_models import (
    City, POISummary, POIDetail, POIMetadata, POIMetadataUpdate,
    DistanceMatrix, CollectionResult, VerificationReport,
    ErrorResponse, SuccessResponse
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


def load_poi_yaml(city: str, poi_id: str) -> dict:
    """Load POI YAML file"""
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


def save_poi_yaml(city: str, poi_id: str, data: dict) -> None:
    """Save POI YAML file"""
    # Convert hyphens to underscores for filename
    filename = poi_id.replace('-', '_')
    yaml_path = Path(f"poi_research/{city}/{filename}.yaml")

    try:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as e:
        logger.error(f"Error saving POI YAML: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving POI data: {str(e)}"
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
    List all cities with POI research data.

    Returns a list of cities with their POI counts.
    """
    try:
        poi_research_dir = Path("poi_research")

        if not poi_research_dir.exists():
            return []

        cities = []
        for city_dir in poi_research_dir.iterdir():
            if city_dir.is_dir() and not city_dir.name.startswith('.'):
                # Count POI files
                poi_count = len(list(city_dir.glob("*.yaml")))

                cities.append(City(
                    name=city_dir.name,
                    slug=city_dir.name.lower().replace(' ', '-'),
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
    """
    try:
        agent = get_agent()
        pois = agent._load_city_pois(city)

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
    """
    try:
        data = load_poi_yaml(city, poi_id)
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
    """
    try:
        # Load current data
        data = load_poi_yaml(city, poi_id)
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

        # Save back to YAML
        poi_data['metadata'] = current_metadata
        data['poi'] = poi_data
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

        # Load POI
        pois = agent._load_city_pois(city)
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
