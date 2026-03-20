"""
FastAPI Router for Tour Generation

Provides endpoints for generating AI-powered walking tour itineraries.
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from trip_planner import POISelectorAgent, ItineraryOptimizerAgent, TourManager
from utils import load_config, get_language_name

# Import optional auth dependency
try:
    from auth.dependencies import get_current_user
except ImportError:
    # Auth not available, create a dummy dependency
    async def get_current_user():
        return None


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
    title_display: Optional[str] = None
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


# ==== Helper Functions (continued) ====

def generate_tour_title(
    city: str,
    duration_days: int,
    interests: List[str],
    selected_pois: List[Dict[str, Any]],
    language: str,
    conf: Dict[str, Any]
) -> str:
    """
    Generate a human-readable display title for the tour using AI.

    The title is language-aware: if the tour language is Chinese, the title
    will be generated in Chinese. Examples:
      - English: "Ancient Rome History · 3 Days"
      - Chinese: "古羅馬歷史之旅 · 3天"

    Falls back to a simple formatted title if AI call fails.

    Args:
        city: City name
        duration_days: Number of tour days
        interests: User interest tags
        selected_pois: List of selected POI dicts with 'poi' and 'reason' keys
        language: ISO 639-1 language code
        conf: Application config (for AI provider credentials)

    Returns:
        Generated title string
    """
    # Build fallback title first (used if AI fails)
    interests_str = ", ".join(interests[:2]) if interests else "Sightseeing"
    fallback_title = f"{city.title()} {interests_str} · {duration_days} {'Day' if duration_days == 1 else 'Days'}"

    try:
        ai_config = conf.get('ai_providers', {})
        provider_conf = ai_config.get('anthropic', {})
        api_key = provider_conf.get('api_key')

        if not api_key:
            return fallback_title

        poi_names = [p.get('poi', '') for p in selected_pois[:8]]
        language_name = get_language_name(language)

        language_instruction = ""
        if language != 'en':
            language_instruction = f"IMPORTANT: Write the title in {language_name}. Do NOT use English.\n\n"

        prompt = (
            f"{language_instruction}"
            f"Create a short, evocative tour title (max 8 words) for a {duration_days}-day tour in {city}.\n\n"
            f"Selected highlights: {', '.join(poi_names)}\n"
            f"Visitor interests: {', '.join(interests) if interests else 'general sightseeing'}\n\n"
            f"The title should capture the essence/theme of the tour (e.g. historical era, cultural focus).\n"
            f"Append ' · {duration_days} {'Day' if duration_days == 1 else 'Days'}' at the end.\n"
            f"Output ONLY the title, nothing else."
        )

        import anthropic as anthropic_sdk
        client = anthropic_sdk.Anthropic(api_key=api_key)
        model = provider_conf.get('model', 'claude-3-5-haiku-20241022')

        response = client.messages.create(
            model=model,
            max_tokens=60,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )

        title = response.content[0].text.strip().strip('"').strip("'")
        if title:
            return title

    except Exception as e:
        logger.warning(f"Failed to generate AI tour title: {e}. Using fallback.")

    return fallback_title


# ==== Endpoints ====

@router.post("/generate", response_model=TourGenerationResponse)
async def generate_tour(
    request: TourGenerationRequest,
    current_user: Optional[dict] = Depends(get_current_user)
):
    """
    Generate an AI-powered walking tour itinerary.

    This endpoint:
    1. Uses AI to select optimal POIs based on preferences
    2. Optimizes the visiting sequence using selected algorithm
    3. Creates a day-by-day itinerary
    4. Saves the tour if requested

    Args:
        request: Tour generation parameters
        current_user: Optional authenticated user info (auto-injected)

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

        # Generate display title (language-aware)
        logger.info("Generating tour display title...")
        title_display = generate_tour_title(
            city=request.city,
            duration_days=request.days,
            interests=request.interests,
            selected_pois=starting_pois,
            language=request.language,
            conf=conf
        )
        logger.info(f"Generated title: {title_display}")

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

            # Build input parameters for tracking
            input_parameters = {
                'city': request.city,
                'duration_days': request.days,
                'interests': request.interests,
                'preferences': preferences,
                'must_see': request.must_see,
                'provider': request.provider,
                'mode': request.mode,
                'start_location': request.start_location,
                'end_location': request.end_location,
                'start_date': request.start_date,
                'language': request.language,
                'generated_via': 'backstage_ui'
            }

            # Build tour data structure
            # Note: title_display is passed separately to save_tour()
            tour_data = {
                'itinerary': itinerary,
                'optimization_scores': optimization_scores
            }

            # Prepare user info for tour attribution
            user_info = None
            if current_user:
                user_info = {
                    'email': current_user.get('email'),
                    'role': current_user.get('role'),
                    'name': current_user.get('name')
                }

            # Save tour with full parameters
            result = tour_manager.save_tour(
                tour_data=tour_data,
                city=request.city,
                input_parameters=input_parameters,
                user_info=user_info,
                selection_result=selection_result,
                language=request.language,
                title_display=title_display
            )

            tour_id = result['tour_id']
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
            title_display=title_display,
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
