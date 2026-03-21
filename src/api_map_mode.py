"""
Map Mode API Router

Handles tour progress tracking and GPS trail recording for Flutter client app.
Provides 4 endpoints for:
- POST /tours/{tour_id}/progress - Save POI completion status
- GET /tours/{tour_id}/progress - Get all POI completion statuses
- POST /tours/{tour_id}/trail - Upload GPS trail points (batch)
- GET /tours/{tour_id}/trail - Get all GPS trail points
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pathlib import Path
import json
from datetime import datetime
from typing import Optional

from api_models import (
    POIProgressUpdate,
    POIProgressResponse,
    TourProgressResponse,
    POICompletionStatus,
    TrailUploadRequest,
    TrailUploadResponse,
    TourTrailResponse,
    TrailPoint,
)
from auth.dependencies import require_client_app
from utils import poi_name_to_id, normalize_language_code

router = APIRouter(prefix="/tours", tags=["map-mode"])


# ==== Helper Functions ====

def get_user_data_dir(user_email: str) -> Path:
    """Create and return user data directory"""
    user_dir = Path("user_data") / user_email
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_progress_file_path(user_email: str, tour_id: str) -> Path:
    """Get path to progress file"""
    user_dir = get_user_data_dir(user_email)
    return user_dir / f"tour_{tour_id}_progress.json"


def get_trail_file_path(user_email: str, tour_id: str) -> Path:
    """Get path to trail file"""
    user_dir = get_user_data_dir(user_email)
    return user_dir / f"tour_{tour_id}_trail.json"


def load_progress_data(user_email: str, tour_id: str) -> dict:
    """Load progress data or create empty structure"""
    file_path = get_progress_file_path(user_email, tour_id)

    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Create new progress structure
    now = datetime.utcnow().isoformat()
    return {
        "tour_id": tour_id,
        "user_email": user_email,
        "created_at": now,
        "updated_at": now,
        "completions": {}
    }


def save_progress_data(user_email: str, tour_id: str, data: dict):
    """Save progress data with updated timestamp"""
    data["updated_at"] = datetime.utcnow().isoformat()
    file_path = get_progress_file_path(user_email, tour_id)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
    """
    Find tour directory by searching all city directories.
    Returns (tour_path, city_name)
    """
    tours_dir = Path("tours")

    if not tours_dir.exists():
        raise HTTPException(status_code=404, detail="Tours directory not found")

    for city_dir in tours_dir.iterdir():
        if not city_dir.is_dir():
            continue

        potential_path = city_dir / tour_id
        if potential_path.exists() and potential_path.is_dir():
            return potential_path, city_dir.name

    raise HTTPException(status_code=404, detail=f"Tour '{tour_id}' not found")


def verify_tour_access(tour_path: Path, user_email: str) -> bool:
    """
    Verify user can access the tour.
    - Public tours: accessible to all authenticated users
    - Private tours: only accessible to creator
    """
    metadata_file = tour_path / "metadata.json"

    if not metadata_file.exists():
        raise HTTPException(status_code=404, detail="Tour metadata not found")

    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    visibility = metadata.get("visibility", "public")
    creator_email = metadata.get("creator_email")

    # Public tours are accessible to everyone
    if visibility == "public":
        return True

    # Private tours only accessible to creator
    if visibility == "private":
        if creator_email == user_email:
            return True
        raise HTTPException(
            status_code=403,
            detail="Access denied. This is a private tour."
        )

    return True


def load_tour_pois(tour_path: Path, language: str = "en") -> list[dict]:
    """
    Load tour itinerary to get POI names and IDs.
    Returns list of POIs with poi_id, poi_name, and day.
    """
    language = normalize_language_code(language)
    itinerary_file = tour_path / f"itinerary_{language}.json"

    if not itinerary_file.exists():
        # Fallback to English
        itinerary_file = tour_path / "itinerary_en.json"
        if not itinerary_file.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Tour itinerary not found for language '{language}'"
            )

    with open(itinerary_file, 'r', encoding='utf-8') as f:
        itinerary = json.load(f)

    # Extract POIs from all days
    pois = []
    for day_data in itinerary.get("itinerary", []):
        day_num = day_data.get("day")
        for poi in day_data.get("pois", []):
            poi_name = poi.get("poi", "")
            poi_id = poi.get("poi_id")

            # Generate poi_id if not present
            if not poi_id:
                poi_id = poi_name_to_id(poi_name)

            pois.append({
                "poi_id": poi_id,
                "poi_name": poi_name,
                "day": day_num
            })

    return pois


# ==== API Endpoints ====

@router.post("/{tour_id}/progress", response_model=POIProgressResponse)
async def update_poi_progress(
    tour_id: str,
    request: POIProgressUpdate,
    user_info: dict = Depends(require_client_app)
):
    """
    Save POI completion status for authenticated user.

    Marks a POI as completed or not completed for the current user.
    Each user has their own independent progress tracking.
    """
    user_email = user_info["email"]

    # Verify tour exists and user has access
    tour_path, _ = find_tour_path(tour_id)
    verify_tour_access(tour_path, user_email)

    # Load current progress
    progress_data = load_progress_data(user_email, tour_id)

    # Create composite key: "poi_id:day"
    key = f"{request.poi_id}:{request.day}"

    # Update completion status
    completed_at = datetime.utcnow().isoformat() if request.completed else None

    progress_data["completions"][key] = {
        "poi_id": request.poi_id,
        "day": request.day,
        "completed": request.completed,
        "completed_at": completed_at
    }

    # Save progress
    save_progress_data(user_email, tour_id, progress_data)

    return POIProgressResponse(
        success=True,
        poi_id=request.poi_id,
        day=request.day,
        completed=request.completed,
        completed_at=completed_at,
        message="POI progress updated"
    )


@router.get("/{tour_id}/progress", response_model=TourProgressResponse)
async def get_tour_progress(
    tour_id: str,
    language: str = Query("en", description="Tour language for POI names"),
    user_info: dict = Depends(require_client_app)
):
    """
    Get all POI completion statuses for authenticated user.

    Returns completion status for all POIs in the tour, including:
    - POI ID and name
    - Day number
    - Completion status
    - Completion timestamp (if completed)
    - Overall completion percentage
    """
    user_email = user_info["email"]

    # Verify tour exists and user has access
    tour_path, _ = find_tour_path(tour_id)
    verify_tour_access(tour_path, user_email)

    # Load progress data
    progress_data = load_progress_data(user_email, tour_id)

    # Load tour POIs to get complete list
    tour_pois = load_tour_pois(tour_path, language)

    # Build completion status list
    completions = []
    completed_count = 0

    for poi_data in tour_pois:
        poi_id = poi_data["poi_id"]
        day = poi_data["day"]
        key = f"{poi_id}:{day}"

        # Check if POI has completion status
        completion = progress_data["completions"].get(key, {})
        completed = completion.get("completed", False)
        completed_at = completion.get("completed_at")

        if completed:
            completed_count += 1

        completions.append(POICompletionStatus(
            poi_id=poi_id,
            poi_name=poi_data["poi_name"],
            day=day,
            completed=completed,
            completed_at=completed_at
        ))

    # Calculate completion percentage
    total_pois = len(tour_pois)
    completion_percentage = (completed_count / total_pois * 100) if total_pois > 0 else 0.0

    return TourProgressResponse(
        tour_id=tour_id,
        completions=completions,
        total_pois=total_pois,
        completed_count=completed_count,
        completion_percentage=round(completion_percentage, 1)
    )


@router.post("/{tour_id}/trail", response_model=TrailUploadResponse)
async def upload_gps_trail(
    tour_id: str,
    request: TrailUploadRequest,
    user_info: dict = Depends(require_client_app)
):
    """
    Save GPS trail points for authenticated user (batch upload).

    Accepts up to 100 GPS points per request. Client should batch points
    and upload every 1 minute OR when 20 points collected, whichever comes first.
    """
    user_email = user_info["email"]

    # Verify tour exists and user has access
    tour_path, _ = find_tour_path(tour_id)
    verify_tour_access(tour_path, user_email)

    # Validate point count
    if len(request.points) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 points per request"
        )

    # Load current trail data
    trail_data = load_trail_data(user_email, tour_id)

    # Append new points
    for point in request.points:
        trail_data["points"].append({
            "lat": point.lat,
            "lng": point.lng,
            "timestamp": point.timestamp,
            "accuracy": point.accuracy
        })

    # Save trail data
    save_trail_data(user_email, tour_id, trail_data)

    points_saved = len(request.points)
    total_points = len(trail_data["points"])

    return TrailUploadResponse(
        success=True,
        points_saved=points_saved,
        total_points=total_points,
        message=f"Saved {points_saved} GPS points"
    )


@router.get("/{tour_id}/trail", response_model=TourTrailResponse)
async def get_gps_trail(
    tour_id: str,
    user_info: dict = Depends(require_client_app)
):
    """
    Get all GPS trail points for authenticated user.

    Returns complete GPS trail for the tour, including all recorded points
    with latitude, longitude, and timestamp.
    """
    user_email = user_info["email"]

    # Verify tour exists and user has access
    tour_path, _ = find_tour_path(tour_id)
    verify_tour_access(tour_path, user_email)

    # Load trail data
    trail_data = load_trail_data(user_email, tour_id)

    # Convert to TrailPoint objects (simplified format)
    points = [
        TrailPoint(
            lat=p["lat"],
            lng=p["lng"],
            timestamp=p["timestamp"]
        )
        for p in trail_data["points"]
    ]

    return TourTrailResponse(
        tour_id=tour_id,
        points=points,
        total_points=len(points)
    )
