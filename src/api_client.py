"""
Client App API Router

Handles client-specific features like background GPS tracking.
These endpoints are separate from the general map-mode endpoints
to support advanced client app features.
"""

from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import json
from datetime import datetime
import logging

from api_models import (
    BatchTrailUploadRequest,
    BatchTrailUploadResponse,
)
from auth.dependencies import require_client_app

router = APIRouter(prefix="/client/tours", tags=["client-app"])
logger = logging.getLogger(__name__)


# ==== Helper Functions ====

def get_user_data_dir(user_email: str) -> Path:
    """Create and return user data directory"""
    user_dir = Path("user_data") / user_email
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_trail_file_path(user_email: str, tour_id: str) -> Path:
    """Get path to trail file"""
    user_dir = get_user_data_dir(user_email)
    return user_dir / f"tour_{tour_id}_trail.json"


def load_trail_data(user_email: str, tour_id: str) -> dict:
    """Load trail data or create empty structure"""
    file_path = get_trail_file_path(user_email, tour_id)

    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Create new trail structure
    now = datetime.utcnow().isoformat()
    return {
        "tour_id": tour_id,
        "user_email": user_email,
        "created_at": now,
        "updated_at": now,
        "points": []
    }


def save_trail_data(user_email: str, tour_id: str, data: dict):
    """Save trail data with updated timestamp"""
    data["updated_at"] = datetime.utcnow().isoformat()
    file_path = get_trail_file_path(user_email, tour_id)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_tour_path(tour_id: str) -> tuple[Path, str]:
    """Find tour directory by searching all city directories"""
    tours_dir = Path("tours")

    if not tours_dir.exists():
        raise HTTPException(status_code=404, detail="Tours directory not found")

    # Search through all city directories
    for city_dir in tours_dir.iterdir():
        if not city_dir.is_dir():
            continue

        tour_path = city_dir / tour_id
        if tour_path.exists():
            return tour_path, city_dir.name

    raise HTTPException(status_code=404, detail=f"Tour not found: {tour_id}")


def verify_tour_access(tour_path: Path, user_email: str):
    """Verify user has access to the tour"""
    metadata_file = tour_path / "metadata.json"

    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail="Tour metadata not found")

    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    visibility = metadata.get("visibility", "public")
    creator_email = metadata.get("creator_email")

    # Allow access if tour is public or user is the creator
    if visibility == "public":
        return

    if creator_email and creator_email == user_email:
        return

    raise HTTPException(
        status_code=403,
        detail="Access denied. This is a private tour."
    )


# ==== Endpoints ====

@router.post("/{tour_id}/trail/batch", response_model=BatchTrailUploadResponse)
async def batch_upload_gps_trail(
    tour_id: str,
    request: BatchTrailUploadRequest,
    user_info: dict = Depends(require_client_app)
):
    """
    Upload batched GPS coordinates from background or foreground tracking.

    This endpoint supports the client app's background location tracking feature.
    It accepts extended GPS data including altitude, heading, and speed.

    Background tracking uploads:
    - Collected every 30 seconds
    - Batched and uploaded every 1 minute
    - Includes upload_type: "background"

    Foreground tracking uploads:
    - Collected every 5 seconds
    - Can be uploaded more frequently
    - Includes upload_type: "foreground"

    Args:
        tour_id: Tour identifier
        request: Batch of GPS coordinates with metadata
        user_info: Authenticated user information

    Returns:
        Status of the upload including number of coordinates received
    """
    user_email = user_info["email"]

    # Verify tour exists and user has access
    try:
        tour_path, _ = find_tour_path(tour_id)
        verify_tour_access(tour_path, user_email)
    except HTTPException as e:
        logger.error(f"Tour access denied for {user_email} on tour {tour_id}: {e.detail}")
        raise

    # Validate coordinate data
    if not request.coordinates:
        raise HTTPException(
            status_code=400,
            detail="No coordinates provided"
        )

    # Log upload info
    logger.info(
        f"Batch trail upload: user={user_email}, tour={tour_id}, "
        f"count={len(request.coordinates)}, type={request.upload_type}, day={request.day}"
    )

    # Load current trail data
    trail_data = load_trail_data(user_email, tour_id)

    # Append new coordinates with extended fields
    for coord in request.coordinates:
        point = {
            "lat": coord.latitude,
            "lng": coord.longitude,
            "timestamp": coord.timestamp,
            "accuracy": coord.accuracy,
            "day": request.day,
            "upload_type": request.upload_type
        }

        # Add optional fields if available
        if coord.altitude is not None:
            point["altitude"] = coord.altitude
        if coord.heading is not None:
            point["heading"] = coord.heading
        if coord.speed is not None:
            point["speed"] = coord.speed

        trail_data["points"].append(point)

    # Save trail data
    try:
        save_trail_data(user_email, tour_id, trail_data)
        trail_updated = True
    except Exception as e:
        logger.error(f"Failed to save trail data: {e}")
        trail_updated = False
        raise HTTPException(
            status_code=500,
            detail="Failed to save trail data"
        )

    coordinates_received = len(request.coordinates)

    logger.info(
        f"Batch trail upload successful: {coordinates_received} coordinates saved, "
        f"total trail points: {len(trail_data['points'])}"
    )

    return BatchTrailUploadResponse(
        status="success",
        coordinates_received=coordinates_received,
        trail_updated=trail_updated
    )
