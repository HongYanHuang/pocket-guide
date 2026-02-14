"""
FastAPI Router for Tour Generation

Provides endpoints for generating AI-powered walking tour itineraries.
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from trip_planner import POISelectorAgent, ItineraryOptimizerAgent, TourManager
from utils import load_config


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tour", tags=["tour"])

# Load configuration
try:
    config = load_config()
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    config = None


# ==== Pydantic Models ====

class TourGenerationRequest(BaseModel):
    """Request model for tour generation"""
    city: str = Field(..., description="City name (e.g., rome, paris)")
    days: int = Field(..., ge=1, le=14, description="Number of days for the trip")
    interests: List[str] = Field(default=[], description="List of interests")
    provider: str = Field(default="anthropic", pattern="^(anthropic|openai|google)$")
    must_see: List[str] = Field(default=[], description="POIs that must be included")
    pace: str = Field(default="normal", pattern="^(relaxed|normal|packed)$")
    walking: str = Field(default="moderate", pattern="^(low|moderate|high)$")
    language: str = Field(default="en", description="Language code (ISO 639-1)")
    mode: str = Field(default="simple", pattern="^(simple|ilp)$")
    start_location: Optional[str] = Field(None, description="Starting point")
    end_location: Optional[str] = Field(None, description="Ending point")
    start_date: Optional[str] = Field(None, description="Trip start date (YYYY-MM-DD)")
    save: bool = Field(default=True, description="Whether to save the tour")


class TourGenerationResponse(BaseModel):
    """Response model for tour generation"""
    success: bool
    tour_id: str
    city: str
    duration_days: int
    total_pois: int
    message: str
    itinerary: Optional[List[Dict[str, Any]]] = None
    optimization_scores: Optional[Dict[str, float]] = None


# ==== Helper Functions ====

def get_config():
    """Get configuration or raise error"""
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration not loaded. Check config.yaml."
        )
    return config


# ==== Endpoints ====

@router.post("/generate", response_model=TourGenerationResponse)
async def generate_tour(request: TourGenerationRequest):
    """
    Generate an AI-powered walking tour itinerary.

    This endpoint:
    1. Uses AI to select optimal POIs based on preferences
    2. Optimizes the visiting sequence using selected algorithm
    3. Creates a day-by-day itinerary
    4. Saves the tour if requested

    Args:
        request: Tour generation parameters

    Returns:
        Generated tour data with itinerary and metadata
    """
    try:
        conf = get_config()

        logger.info(f"Generating tour for {request.city}, {request.days} days")

        # Build preferences dictionary
        preferences = {
            'pace': request.pace,
            'walking_tolerance': request.walking,
            'indoor_outdoor': 'balanced'
        }

        # Parse start date
        trip_start_date = None
        if request.start_date:
            try:
                trip_start_date = datetime.strptime(request.start_date, '%Y-%m-%d')
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid start_date format. Use YYYY-MM-DD."
                )

        # Step 1: Select POIs using AI
        logger.info("Step 1: Selecting POIs with AI...")
        poi_selector = POISelectorAgent(conf, provider=request.provider)

        selection_result = poi_selector.select_pois(
            city=request.city,
            duration_days=request.days,
            interests=request.interests,
            preferences=preferences,
            must_see=request.must_see,
            avoid=[],
            language=request.language
        )

        starting_pois = selection_result['starting_pois']
        backup_pois = selection_result['backup_pois']

        if not starting_pois:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No POIs were selected for the tour"
            )

        logger.info(f"Selected {len(starting_pois)} POIs")

        # Step 2: Optimize itinerary
        logger.info("Step 2: Optimizing itinerary...")
        optimizer = ItineraryOptimizerAgent(conf)

        itinerary_result = optimizer.optimize_itinerary(
            selected_pois=starting_pois,
            city=request.city,
            duration_days=request.days,
            start_time="09:00",
            preferences=preferences,
            mode=request.mode,
            start_location=request.start_location,
            end_location=request.end_location,
            trip_start_date=trip_start_date
        )

        itinerary = itinerary_result['itinerary']
        optimization_scores = itinerary_result.get('optimization_scores', {})

        # Step 3: Save tour if requested
        tour_id = None
        if request.save:
            logger.info("Step 3: Saving tour...")
            tour_manager = TourManager(conf)

            tour_data = {
                'city': request.city,
                'duration_days': request.days,
                'interests': request.interests,
                'preferences': preferences,
                'language': request.language,
                'itinerary': itinerary,
                'optimization_scores': optimization_scores,
                'backup_pois': backup_pois,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'provider': request.provider,
                    'mode': request.mode,
                    'start_location': request.start_location,
                    'end_location': request.end_location,
                    'start_date': request.start_date
                }
            }

            tour_id = tour_manager.save_tour(
                city=request.city,
                tour_data=tour_data,
                language=request.language
            )

            logger.info(f"Tour saved with ID: {tour_id}")
        else:
            # Generate a temporary ID
            tour_id = f"{request.city}-tour-preview-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        return TourGenerationResponse(
            success=True,
            tour_id=tour_id,
            city=request.city,
            duration_days=request.days,
            total_pois=len(starting_pois),
            message=f"Tour generated successfully with {len(starting_pois)} POIs",
            itinerary=itinerary,
            optimization_scores=optimization_scores
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating tour: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tour: {str(e)}"
        )


@router.get("/status/{tour_id}")
async def get_tour_generation_status(tour_id: str):
    """
    Get the status of a tour generation request.

    This is useful for async generation in the future.

    Args:
        tour_id: Tour ID or generation task ID

    Returns:
        Generation status
    """
    # For now, just return completed status
    # In the future, we can track async generation tasks
    return {
        "tour_id": tour_id,
        "status": "completed",
        "progress": 100
    }
