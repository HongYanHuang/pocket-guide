"""
Combo Ticket Loader Module

Handles loading and enriching POI data with combo ticket information from
city-level combo_tickets.yaml files.

This provides a single source of truth for combo ticket data, avoiding
duplication and inconsistencies across individual POI files.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict


logger = logging.getLogger(__name__)


class ComboTicketLoader:
    """Loader for city-level combo ticket data"""

    def __init__(self):
        self.base_path = Path("poi_research")

    def load_city_combo_tickets(self, city: str) -> Dict[str, Dict[str, Any]]:
        """
        Load combo_tickets.yaml for a city.

        Args:
            city: City name (e.g., "rome", "paris")

        Returns:
            Dictionary mapping combo ticket ID to combo ticket data
            Example: {"archaeological_pass_rome": {...}, "vatican_combo": {...}}
        """
        combo_tickets_path = self.base_path / city / "combo_tickets.yaml"

        if not combo_tickets_path.exists():
            logger.info(f"No combo_tickets.yaml found for {city}")
            return {}

        try:
            with open(combo_tickets_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'combo_tickets' not in data:
                logger.warning(f"combo_tickets.yaml for {city} has no 'combo_tickets' key")
                return {}

            # Index by ID for fast lookup
            combo_tickets = {}
            for ticket in data['combo_tickets']:
                if 'id' not in ticket:
                    logger.warning(f"Combo ticket in {city} missing 'id' field: {ticket}")
                    continue

                ticket_id = ticket['id']
                combo_tickets[ticket_id] = ticket

            logger.info(f"Loaded {len(combo_tickets)} combo tickets for {city}")
            return combo_tickets

        except Exception as e:
            logger.error(f"Error loading combo tickets for {city}: {e}")
            return {}

    def enrich_pois_with_combo_tickets(
        self,
        pois: List[Dict[str, Any]],
        combo_tickets: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich POIs with full combo ticket data based on their references.

        Args:
            pois: List of POI dictionaries
            combo_tickets: Combo ticket data indexed by ID

        Returns:
            Enriched POI list with combo_ticket_groups added to metadata
        """
        if not combo_tickets:
            return pois

        for poi in pois:
            metadata = poi.setdefault('metadata', {})

            # Get combo ticket IDs referenced by this POI
            ticket_ids = metadata.get('combo_tickets', [])

            if not ticket_ids:
                continue

            # Expand IDs to full combo ticket objects
            combo_ticket_groups = []

            for ticket_id in ticket_ids:
                if ticket_id in combo_tickets:
                    combo_ticket_groups.append(combo_tickets[ticket_id])
                else:
                    logger.warning(
                        f"POI '{poi.get('poi', 'unknown')}' references "
                        f"unknown combo ticket: '{ticket_id}'"
                    )

            # Store enriched data
            if combo_ticket_groups:
                metadata['combo_ticket_groups'] = combo_ticket_groups

        return pois

    def validate_combo_tickets(
        self,
        city: str,
        combo_tickets: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Validate combo ticket data for consistency.

        Checks:
        1. All members in combo tickets are valid POIs
        2. All POIs referencing combo tickets have valid IDs
        3. Bi-directional consistency (combo -> POI and POI -> combo)

        Args:
            city: City name
            combo_tickets: Optional pre-loaded combo tickets (if None, will load)

        Returns:
            List of validation issues
            Example: [{"type": "error", "message": "...", "entity": "..."}]
        """
        if combo_tickets is None:
            combo_tickets = self.load_city_combo_tickets(city)

        issues = []

        # Load all POIs for the city
        poi_dir = self.base_path / city
        if not poi_dir.exists():
            issues.append({
                "type": "error",
                "message": f"City directory not found: {city}",
                "entity": city
            })
            return issues

        # Build POI name -> POI data mapping
        poi_data = {}
        for poi_file in poi_dir.glob("*.yaml"):
            if poi_file.name in ['combo_tickets.yaml', 'city_info.yaml']:
                continue

            try:
                with open(poi_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'poi' in data:
                        poi_name = data['poi'].get('name') or data['poi']
                        poi_data[poi_name] = data
            except Exception as e:
                issues.append({
                    "type": "error",
                    "message": f"Error loading POI file: {e}",
                    "entity": str(poi_file)
                })

        # Check 1: All combo ticket members exist as POIs
        for ticket_id, ticket in combo_tickets.items():
            members = ticket.get('members', [])

            for member in members:
                if member not in poi_data:
                    issues.append({
                        "type": "error",
                        "message": f"Combo ticket '{ticket_id}' references non-existent POI: '{member}'",
                        "entity": ticket_id,
                        "poi": member
                    })

        # Check 2: All POI combo ticket references are valid
        for poi_name, data in poi_data.items():
            ticket_ids = data.get('metadata', {}).get('combo_tickets', [])

            for ticket_id in ticket_ids:
                if ticket_id not in combo_tickets:
                    issues.append({
                        "type": "error",
                        "message": f"POI '{poi_name}' references non-existent combo ticket: '{ticket_id}'",
                        "entity": poi_name,
                        "combo_ticket": ticket_id
                    })

        # Check 3: Bi-directional consistency
        for ticket_id, ticket in combo_tickets.items():
            members = set(ticket.get('members', []))

            for member in members:
                if member not in poi_data:
                    continue  # Already reported in Check 1

                poi_tickets = poi_data[member].get('metadata', {}).get('combo_tickets', [])

                if ticket_id not in poi_tickets:
                    issues.append({
                        "type": "warning",
                        "message": (
                            f"Combo ticket '{ticket_id}' includes '{member}' "
                            f"but '{member}' doesn't reference it back"
                        ),
                        "entity": ticket_id,
                        "poi": member
                    })

        # Check 4: Reverse bi-directional consistency
        for poi_name, data in poi_data.items():
            ticket_ids = data.get('metadata', {}).get('combo_tickets', [])

            for ticket_id in ticket_ids:
                if ticket_id not in combo_tickets:
                    continue  # Already reported in Check 2

                members = combo_tickets[ticket_id].get('members', [])

                if poi_name not in members:
                    issues.append({
                        "type": "warning",
                        "message": (
                            f"POI '{poi_name}' references combo ticket '{ticket_id}' "
                            f"but the ticket doesn't include it in members"
                        ),
                        "entity": poi_name,
                        "combo_ticket": ticket_id
                    })

        return issues

    def get_combo_tickets_for_poi(
        self,
        poi_name: str,
        combo_tickets: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Get all combo tickets that include a specific POI.

        Args:
            poi_name: POI name
            combo_tickets: All combo tickets for the city

        Returns:
            List of combo ticket dictionaries
        """
        result = []

        for ticket_id, ticket in combo_tickets.items():
            if poi_name in ticket.get('members', []):
                result.append(ticket)

        return result

    def get_pois_by_combo_ticket(
        self,
        ticket_id: str,
        combo_tickets: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """
        Get list of POI names for a combo ticket.

        Args:
            ticket_id: Combo ticket ID
            combo_tickets: All combo tickets for the city

        Returns:
            List of POI names
        """
        if ticket_id not in combo_tickets:
            return []

        return combo_tickets[ticket_id].get('members', [])

    def save_combo_tickets(
        self,
        city: str,
        combo_tickets: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save combo tickets to city's combo_tickets.yaml file.

        Args:
            city: City name
            combo_tickets: List of combo ticket dictionaries
            metadata: Optional metadata to include in file

        Returns:
            True if successful, False otherwise
        """
        combo_tickets_path = self.base_path / city / "combo_tickets.yaml"

        try:
            # Ensure directory exists
            combo_tickets_path.parent.mkdir(parents=True, exist_ok=True)

            # Build data structure
            data = {
                'combo_tickets': combo_tickets
            }

            if metadata:
                data['metadata'] = metadata

            # Write to file
            with open(combo_tickets_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )

            logger.info(f"Saved {len(combo_tickets)} combo tickets to {combo_tickets_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving combo tickets for {city}: {e}")
            return False

    def update_poi_combo_references(
        self,
        city: str,
        poi_name: str,
        ticket_ids: List[str]
    ) -> bool:
        """
        Update a POI's combo ticket references.

        Args:
            city: City name
            poi_name: POI name
            ticket_ids: List of combo ticket IDs to reference

        Returns:
            True if successful, False otherwise
        """
        poi_dir = self.base_path / city

        # Find POI file
        poi_file = None
        for candidate in poi_dir.glob("*.yaml"):
            if candidate.name in ['combo_tickets.yaml', 'city_info.yaml']:
                continue

            try:
                with open(candidate, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and data.get('poi', {}).get('name') == poi_name:
                        poi_file = candidate
                        break
            except:
                continue

        if not poi_file:
            logger.error(f"POI file not found for '{poi_name}' in {city}")
            return False

        try:
            # Load POI data
            with open(poi_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # Update combo ticket references
            if 'metadata' not in data:
                data['metadata'] = {}

            if ticket_ids:
                data['metadata']['combo_tickets'] = ticket_ids
            else:
                # Remove if empty
                data['metadata'].pop('combo_tickets', None)

            # Save back
            with open(poi_file, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )

            logger.info(f"Updated combo ticket references for '{poi_name}'")
            return True

        except Exception as e:
            logger.error(f"Error updating POI '{poi_name}': {e}")
            return False
