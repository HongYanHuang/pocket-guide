"""
FastAPI Router for Combo Ticket Management

Provides CRUD endpoints for managing combo tickets at the city level.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import date
import logging

from data.combo_ticket_loader import ComboTicketLoader


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/combo-tickets", tags=["combo-tickets"])

# Initialize loader
combo_loader = ComboTicketLoader()


# ==== Pydantic Models ====

class ComboTicketConstraints(BaseModel):
    """Combo ticket visit constraints"""
    must_visit_together: bool = True
    max_separation_hours: float = 4.0
    visit_order: str = Field("flexible", pattern="^(fixed|flexible|chronological)$")
    same_day_required: bool = True


class ComboTicketPricing(BaseModel):
    """Combo ticket pricing information"""
    adult: Optional[float] = None
    reduced: Optional[float] = None
    child: Optional[float] = None
    free_under_age: Optional[int] = None
    currency: str = "EUR"
    validity_days: int = 1
    savings: Optional[float] = None
    savings_percentage: Optional[float] = None


class ComboTicketBookingInfo(BaseModel):
    """Combo ticket booking information"""
    required: bool = False
    recommended: bool = False
    advance_booking_days: Optional[int] = None
    url: Optional[str] = None
    notes: Optional[str] = None


class ComboTicketBase(BaseModel):
    """Base combo ticket model"""
    id: str = Field(..., pattern="^[a-z0-9_]+$")
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: str = Field("same_day_consecutive", pattern="^(same_day_consecutive|same_day_any_order|multi_day|same_day_clustered)$")
    members: List[str] = Field(..., min_items=2, max_items=10)
    constraints: Optional[ComboTicketConstraints] = None
    pricing: Optional[ComboTicketPricing] = None
    booking_info: Optional[ComboTicketBookingInfo] = None


class ComboTicketCreate(ComboTicketBase):
    """Model for creating a combo ticket"""
    pass


class ComboTicketUpdate(BaseModel):
    """Model for updating a combo ticket (all fields optional)"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: Optional[str] = Field(None, pattern="^(same_day_consecutive|same_day_any_order|multi_day|same_day_clustered)$")
    members: Optional[List[str]] = Field(None, min_items=2, max_items=10)
    constraints: Optional[ComboTicketConstraints] = None
    pricing: Optional[ComboTicketPricing] = None
    booking_info: Optional[ComboTicketBookingInfo] = None


class ComboTicket(ComboTicketBase):
    """Full combo ticket model with metadata"""
    pass


class ComboTicketsResponse(BaseModel):
    """Response containing list of combo tickets"""
    combo_tickets: List[ComboTicket]
    count: int
    city: str


class ValidationIssue(BaseModel):
    """Validation issue model"""
    type: str = Field(..., pattern="^(error|warning)$")
    message: str
    entity: str
    poi: Optional[str] = None
    combo_ticket: Optional[str] = None


class ValidationResponse(BaseModel):
    """Validation response"""
    valid: bool
    issues: List[ValidationIssue]
    count: int


class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ==== Endpoints ====

@router.get("/cities/{city}", response_model=ComboTicketsResponse)
async def list_combo_tickets(city: str):
    """
    List all combo tickets for a city.

    Args:
        city: City name (e.g., "rome", "paris")

    Returns:
        List of combo tickets with metadata
    """
    try:
        combo_tickets = combo_loader.load_city_combo_tickets(city)

        return ComboTicketsResponse(
            combo_tickets=[ComboTicket(**ticket) for ticket in combo_tickets.values()],
            count=len(combo_tickets),
            city=city
        )

    except Exception as e:
        logger.error(f"Error loading combo tickets for {city}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load combo tickets: {str(e)}"
        )


@router.get("/cities/{city}/{ticket_id}", response_model=ComboTicket)
async def get_combo_ticket(city: str, ticket_id: str):
    """
    Get a specific combo ticket by ID.

    Args:
        city: City name
        ticket_id: Combo ticket ID

    Returns:
        Combo ticket details
    """
    try:
        combo_tickets = combo_loader.load_city_combo_tickets(city)

        if ticket_id not in combo_tickets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Combo ticket '{ticket_id}' not found in {city}"
            )

        return ComboTicket(**combo_tickets[ticket_id])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting combo ticket {ticket_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get combo ticket: {str(e)}"
        )


@router.post("/cities/{city}", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_combo_ticket(city: str, ticket: ComboTicketCreate):
    """
    Create a new combo ticket for a city.

    Args:
        city: City name
        ticket: Combo ticket data

    Returns:
        Success response with created ticket ID
    """
    try:
        # Load existing combo tickets
        combo_tickets = combo_loader.load_city_combo_tickets(city)

        # Check if ID already exists
        if ticket.id in combo_tickets:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Combo ticket with ID '{ticket.id}' already exists"
            )

        # Add new ticket
        new_ticket = ticket.dict(exclude_none=True)
        combo_tickets[ticket.id] = new_ticket

        # Save back to file
        success = combo_loader.save_combo_tickets(
            city,
            list(combo_tickets.values()),
            metadata={
                'city': city.title(),
                'last_updated': date.today().isoformat()
            }
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save combo ticket"
            )

        # Update POI references
        for member_name in ticket.members:
            combo_loader.update_poi_combo_references(city, member_name, [ticket.id])

        return SuccessResponse(
            success=True,
            message=f"Combo ticket '{ticket.id}' created successfully",
            data={"ticket_id": ticket.id}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating combo ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create combo ticket: {str(e)}"
        )


@router.put("/cities/{city}/{ticket_id}", response_model=SuccessResponse)
async def update_combo_ticket(city: str, ticket_id: str, update: ComboTicketUpdate):
    """
    Update an existing combo ticket.

    Args:
        city: City name
        ticket_id: Combo ticket ID to update
        update: Updated fields

    Returns:
        Success response
    """
    try:
        # Load existing combo tickets
        combo_tickets = combo_loader.load_city_combo_tickets(city)

        if ticket_id not in combo_tickets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Combo ticket '{ticket_id}' not found"
            )

        existing_ticket = combo_tickets[ticket_id]
        old_members = set(existing_ticket.get('members', []))

        # Update fields
        update_data = update.dict(exclude_none=True)
        existing_ticket.update(update_data)

        # Save back to file
        success = combo_loader.save_combo_tickets(
            city,
            list(combo_tickets.values()),
            metadata={
                'city': city.title(),
                'last_updated': date.today().isoformat()
            }
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save combo ticket"
            )

        # Update POI references if members changed
        if 'members' in update_data:
            new_members = set(update_data['members'])

            # Remove reference from POIs no longer in group
            for removed_member in old_members - new_members:
                combo_loader.update_poi_combo_references(city, removed_member, [])

            # Add reference to new POIs
            for added_member in new_members - old_members:
                combo_loader.update_poi_combo_references(city, added_member, [ticket_id])

        return SuccessResponse(
            success=True,
            message=f"Combo ticket '{ticket_id}' updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating combo ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update combo ticket: {str(e)}"
        )


@router.delete("/cities/{city}/{ticket_id}", response_model=SuccessResponse)
async def delete_combo_ticket(city: str, ticket_id: str):
    """
    Delete a combo ticket and remove references from POIs.

    Args:
        city: City name
        ticket_id: Combo ticket ID to delete

    Returns:
        Success response
    """
    try:
        # Load existing combo tickets
        combo_tickets = combo_loader.load_city_combo_tickets(city)

        if ticket_id not in combo_tickets:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Combo ticket '{ticket_id}' not found"
            )

        # Get members to update their references
        members = combo_tickets[ticket_id].get('members', [])

        # Remove ticket
        del combo_tickets[ticket_id]

        # Save back to file
        success = combo_loader.save_combo_tickets(
            city,
            list(combo_tickets.values()),
            metadata={
                'city': city.title(),
                'last_updated': date.today().isoformat()
            }
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save combo tickets"
            )

        # Remove references from POIs
        for member_name in members:
            combo_loader.update_poi_combo_references(city, member_name, [])

        return SuccessResponse(
            success=True,
            message=f"Combo ticket '{ticket_id}' deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting combo ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete combo ticket: {str(e)}"
        )


@router.get("/cities/{city}/validate", response_model=ValidationResponse)
async def validate_combo_tickets(city: str):
    """
    Validate combo ticket data for consistency.

    Checks:
    - All members in combo tickets are valid POIs
    - All POIs referencing combo tickets have valid IDs
    - Bi-directional consistency

    Args:
        city: City name

    Returns:
        Validation results with list of issues
    """
    try:
        issues_data = combo_loader.validate_combo_tickets(city)

        issues = [ValidationIssue(**issue) for issue in issues_data]

        return ValidationResponse(
            valid=len(issues) == 0,
            issues=issues,
            count=len(issues)
        )

    except Exception as e:
        logger.error(f"Error validating combo tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate combo tickets: {str(e)}"
        )


@router.get("/cities/{city}/pois/{poi_name}", response_model=List[ComboTicket])
async def get_combo_tickets_for_poi(city: str, poi_name: str):
    """
    Get all combo tickets that include a specific POI.

    Args:
        city: City name
        poi_name: POI name

    Returns:
        List of combo tickets containing this POI
    """
    try:
        combo_tickets = combo_loader.load_city_combo_tickets(city)
        tickets_for_poi = combo_loader.get_combo_tickets_for_poi(poi_name, combo_tickets)

        return [ComboTicket(**ticket) for ticket in tickets_for_poi]

    except Exception as e:
        logger.error(f"Error getting combo tickets for POI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get combo tickets for POI: {str(e)}"
        )
