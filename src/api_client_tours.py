"""
FastAPI Router for Client-Side Tour Generation

Provides endpoints for client apps (mobile/web) to create personalized tours.
Requires authentication and creates private tours by default.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from trip_planner import POISelectorAgent, ItineraryOptimizerAgent, TourManager
from utils import load_config, get_language_name
from auth.dependencies import require_client_app


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/client/tours", tags=["client-tours"])

# Load configuration
try:
    config = load_config()
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    config = None


# ==== Pydantic Models ====

class ClientTourGenerationRequest(BaseModel):
    """Request model for client-side tour generation"""
    city: str = Field(..., description="City name (e.g., rome, paris, athens)", example="rome")
    days: int = Field(..., ge=1, le=14, description="Number of days for the trip (1-14)")

    # Optional tour preferences
    interests: List[str] = Field(
        default=[],
        description="List of interests (e.g., history, architecture, food)",
        example=["history", "architecture"]
    )
    must_see: List[str] = Field(
        default=[],
        description="POIs that must be included in the tour",
        example=["Colosseum", "Roman Forum"]
    )

    # Trip pacing preferences
    pace: str = Field(
        default="normal",
        pattern="^(relaxed|normal|packed)$",
        description="Trip pace: relaxed (2-3 POIs/day), normal (4-5 POIs/day), or packed (6+ POIs/day)"
    )
    walking: str = Field(
        default="moderate",
        pattern="^(low|moderate|high)$",
        description="Walking tolerance: low (<3km/day), moderate (3-6km/day), or high (>6km/day)"
    )

    # Localization
    language: str = Field(
        default="en",
        description="Language code (ISO 639-1, e.g., en, zh-tw, pt-br, fr, es)",
        example="en"
    )

    # Advanced options
    mode: str = Field(
        default="simple",
        pattern="^(simple|ilp)$",
        description="Optimization mode: simple (fast, greedy algorithm) or ilp (optimal, slower)"
    )
    start_location: Optional[str] = Field(
        None,
        description="Starting point (POI name or 'lat,lng' coordinates)",
        example="Colosseum"
    )
    end_location: Optional[str] = Field(
        None,
        description="Ending point (POI name or 'lat,lng' coordinates)",
        example="Trevi Fountain"
    )
    start_date: Optional[str] = Field(
        None,
        description="Trip start date (YYYY-MM-DD format). Used to check opening hours.",
        example="2026-04-15"
    )

    # AI provider (optional - defaults to configured provider)
    provider: str = Field(
        default="anthropic",
        pattern="^(anthropic|openai|google)$",
        description="AI provider for POI selection"
    )


class ClientTourGenerationResponse(BaseModel):
    """Response model for client-side tour generation"""
    success: bool = Field(..., description="Whether tour generation succeeded")
    tour_id: str = Field(..., description="Unique tour identifier")
    city: str = Field(..., description="City name")
    duration_days: int = Field(..., description="Number of days")
    total_pois: int = Field(..., description="Total number of POIs in the tour")
    message: str = Field(..., description="Success message")

    # Tour details
    title_display: Optional[str] = Field(None, description="Human-readable tour title")
    itinerary: List[Dict[str, Any]] = Field(..., description="Day-by-day itinerary")
    optimization_scores: Dict[str, float] = Field(..., description="Optimization metrics")
    input_parameters: Dict[str, Any] = Field(..., description="Input parameters used to generate this tour")

    # Creator information
    visibility: str = Field(default="private", description="Tour visibility (private for client-created tours)")
    creator_email: str = Field(..., description="Email of the user who created this tour")


class ClientTourListResponse(BaseModel):
    """Response model for listing client's tours"""
    tours: List[Dict[str, Any]] = Field(..., description="List of user's tours")
    total_count: int = Field(..., description="Total number of tours")


# ==== Helper Functions ====

def get_config():
    """Get configuration or raise error"""
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuration not loaded. Check config.yaml."
        )
    return config


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

    Falls back to a simple formatted title if AI call fails.
    """
    # Build fallback title first
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
            f"The title should capture the essence/theme of the tour.\n"
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

@router.post("/generate", response_model=ClientTourGenerationResponse)
async def generate_client_tour(
    request: ClientTourGenerationRequest,
    current_user: dict = Depends(require_client_app)
):
    """
    Generate a personalized tour for authenticated client app users.

    This endpoint:
    1. Uses AI to select optimal POIs based on user preferences
    2. Optimizes the visiting sequence using the selected algorithm
    3. Creates a day-by-day itinerary
    4. Saves the tour as PRIVATE (only visible to creator)

    **Authentication Required**: Client app users only

    **Tour Visibility**: Tours created via this endpoint are PRIVATE by default.
    Only the creator and backstage admins can view these tours.

    **Parameters**:
    - `city`: City name (required)
    - `days`: Number of days (1-14, required)
    - `interests`: List of interests (optional)
    - `must_see`: POIs that must be included (optional)
    - `pace`: Trip pace - relaxed, normal, or packed (default: normal)
    - `walking`: Walking tolerance - low, moderate, or high (default: moderate)
    - `language`: Tour language ISO code (default: en)
    - `mode`: Optimization mode - simple or ilp (default: simple)
    - `start_location`: Starting point (optional)
    - `end_location`: Ending point (optional)
    - `start_date`: Trip start date for checking hours (optional)
    - `provider`: AI provider (default: anthropic)

    **Example Request**:
    ```json
    {
      "city": "rome",
      "days": 3,
      "interests": ["history", "architecture"],
      "pace": "normal",
      "walking": "moderate",
      "language": "en"
    }
    ```

    **Returns**: Tour details with itinerary, optimization scores, and tour ID
    """
    try:
        conf = get_config()

        logger.info(f"Client user {current_user['email']} generating tour for {request.city}, {request.days} days")

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
                    detail=f"Invalid start_date format. Use YYYY-MM-DD (e.g., 2026-04-15)."
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
                detail="No POIs were selected for the tour. Try adjusting your preferences."
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

        # Step 3: Save tour
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
            'generated_via': 'client_app'  # Mark as client-created
        }

        # Remove null values to prevent OpenAPI deserialization errors
        input_parameters = remove_null_values(input_parameters)

        # Build tour data structure
        tour_data = {
            'itinerary': itinerary,
            'optimization_scores': optimization_scores
        }

        # Prepare user info for tour attribution
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
        logger.info(f"Tour saved with ID: {tour_id} (visibility: private)")

        return ClientTourGenerationResponse(
            success=True,
            tour_id=tour_id,
            city=request.city,
            duration_days=request.days,
            total_pois=len(starting_pois),
            message=f"Tour generated successfully with {len(starting_pois)} POIs",
            title_display=title_display,
            itinerary=itinerary,
            optimization_scores=optimization_scores,
            input_parameters=input_parameters,
            visibility="private",
            creator_email=current_user['email']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating client tour: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tour: {str(e)}"
        )


@router.get("/my-tours", response_model=ClientTourListResponse)
async def list_my_tours(
    current_user: dict = Depends(require_client_app)
):
    """
    List all tours created by the current user.

    **Authentication Required**: Client app users only

    **Returns**: List of tours with metadata, sorted by creation date (newest first)
    """
    import json
    from pathlib import Path

    try:
        user_email = current_user['email']
        tours = []
        tours_dir = Path("tours")

        if not tours_dir.exists():
            return ClientTourListResponse(tours=[], total_count=0)

        # Iterate through all tours
        for city_dir in tours_dir.iterdir():
            if not city_dir.is_dir() or city_dir.name.startswith('.'):
                continue

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

                    # Filter: only show tours created by this user
                    creator_email = metadata.get('creator_email')
                    if creator_email != user_email:
                        continue

                    # Get tour details
                    available_languages = metadata.get('languages', ['en'])
                    language = available_languages[0] if available_languages else 'en'

                    # Load generation record for details
                    gen_record_pattern = f"generation_record_*_{language}.json"
                    gen_record_files = list(tour_dir.glob(gen_record_pattern))

                    if not gen_record_files:
                        gen_record_files = list(tour_dir.glob("generation_record_*.json"))

                    interests = []
                    duration_days = 0
                    total_pois = 0

                    if gen_record_files:
                        with open(gen_record_files[0], 'r', encoding='utf-8') as f:
                            gen_record = json.load(f)

                        input_params = gen_record.get('input_parameters', {})
                        interests = input_params.get('interests', [])
                        duration_days = input_params.get('duration_days', 0)
                        total_pois = gen_record.get('metadata', {}).get('total_pois', 0)

                    tours.append({
                        'tour_id': metadata['tour_id'],
                        'city': metadata['city'],
                        'duration_days': duration_days,
                        'total_pois': total_pois,
                        'interests': interests,
                        'created_at': metadata['created_at'],
                        'title_display': metadata.get('title_display'),
                        'visibility': metadata.get('visibility', 'private'),
                        'languages': available_languages
                    })

                except Exception as e:
                    logger.warning(f"Error loading tour {tour_dir.name}: {e}")
                    continue

        # Sort by creation date (newest first)
        tours.sort(key=lambda t: t['created_at'], reverse=True)

        return ClientTourListResponse(
            tours=tours,
            total_count=len(tours)
        )

    except Exception as e:
        logger.error(f"Error listing user tours: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tours: {str(e)}"
        )
