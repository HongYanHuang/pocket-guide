"""
Google Maps Service for POI metadata collection.

This service handles:
1. Places API - POI details, coordinates, operation hours
2. Geocoding API - Coordinate lookups (fallback)
3. Distance Matrix API - Inter-POI travel times (CRITICAL for trip planning)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import googlemaps
from googlemaps.exceptions import ApiError, TransportError, Timeout


logger = logging.getLogger(__name__)


class GoogleMapsService:
    """Google Maps API integration for POI metadata collection."""

    def __init__(self, api_key: str):
        """
        Initialize Google Maps client.

        Args:
            api_key: Google Maps API key with Places, Geocoding, and Distance Matrix enabled
        """
        if not api_key:
            raise ValueError("Google Maps API key is required")

        self.client = googlemaps.Client(key=api_key)
        logger.info("Google Maps service initialized")

    def get_place_details(self, poi_name: str, city: str) -> Optional[Dict]:
        """
        Get POI details from Places API.

        Args:
            poi_name: Name of the POI
            city: City name for context

        Returns:
            Dictionary with coordinates, hours, accessibility, etc. or None if not found
        """
        try:
            # Search for the place
            query = f"{poi_name}, {city}"
            logger.info(f"Searching Google Maps for: {query}")

            place_result = self.client.places(query)

            if place_result.get('status') != 'OK' or not place_result.get('results'):
                logger.warning(f"No results found for {query}")
                return None

            # Get the first result (most relevant)
            place = place_result['results'][0]
            place_id = place['place_id']

            # Get detailed information
            logger.info(f"Fetching details for place_id: {place_id}")
            details = self.client.place(place_id)

            if details.get('status') != 'OK':
                logger.warning(f"Failed to get place details for {place_id}")
                return None

            place_details = details['result']

            # Extract coordinates
            location = place.get('geometry', {}).get('location', {})
            coordinates = {
                'latitude': location.get('lat'),
                'longitude': location.get('lng'),
                'source': 'google_maps_api',
                'collected_at': datetime.now(timezone.utc).isoformat()
            }

            # Extract operation hours
            operation_hours = self._parse_hours(
                place_details.get('opening_hours', {})
            )

            # Extract other metadata
            metadata = {
                'coordinates': coordinates,
                'operation_hours': operation_hours,
                'address': place_details.get('formatted_address'),
                'phone': place_details.get('formatted_phone_number'),
                'website': place_details.get('website'),
                'rating': place_details.get('rating'),
                'user_ratings_total': place_details.get('user_ratings_total'),
                'price_level': place_details.get('price_level'),  # 0-4 scale
                'types': place_details.get('types', []),
                'place_id': place_id
            }

            # Check wheelchair accessibility
            if 'wheelchair_accessible_entrance' in place_details:
                metadata['wheelchair_accessible'] = place_details['wheelchair_accessible_entrance']

            logger.info(f"Successfully retrieved metadata for {poi_name}")
            return metadata

        except (ApiError, TransportError, Timeout) as e:
            logger.error(f"Google Maps API error for {poi_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting place details: {e}")
            return None

    def get_coordinates_geocoding(self, poi_name: str, city: str) -> Optional[Dict]:
        """
        Get coordinates using Geocoding API (fallback method).

        Args:
            poi_name: Name of the POI
            city: City name

        Returns:
            Dictionary with coordinates or None if not found
        """
        try:
            query = f"{poi_name}, {city}"
            logger.info(f"Geocoding: {query}")

            result = self.client.geocode(query)

            if not result:
                logger.warning(f"No geocoding results for {query}")
                return None

            location = result[0]['geometry']['location']

            return {
                'latitude': location['lat'],
                'longitude': location['lng'],
                'source': 'google_geocoding_api',
                'collected_at': datetime.now(timezone.utc).isoformat()
            }

        except (ApiError, TransportError, Timeout) as e:
            logger.error(f"Geocoding API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected geocoding error: {e}")
            return None

    def calculate_distance_matrix(
        self,
        pois: List[Dict],
        city: str,
        batch_size: int = 25
    ) -> Dict:
        """
        Calculate all POI-to-POI travel times using Distance Matrix API.

        This is THE MOST IMPORTANT feature for trip planning. It calculates
        travel durations between all POI pairs for walking, transit, and driving.

        Args:
            pois: List of POI dictionaries with coordinates in metadata
            city: City name
            batch_size: Max origins/destinations per API call (default 25)

        Returns:
            Distance matrix with all POI pairs and transportation modes
        """
        logger.info(f"Calculating distance matrix for {len(pois)} POIs in {city}")

        # Extract coordinates and POI IDs
        poi_data = []
        for poi in pois:
            metadata = poi.get('metadata', {})
            coords = metadata.get('coordinates', {})

            if not coords.get('latitude') or not coords.get('longitude'):
                logger.warning(f"Skipping POI without coordinates: {poi.get('poi_id')}")
                continue

            poi_data.append({
                'poi_id': poi.get('poi_id'),
                'poi_name': poi.get('poi_name'),
                'coords': (coords['latitude'], coords['longitude'])
            })

        if len(poi_data) < 2:
            logger.error("Need at least 2 POIs with coordinates for distance matrix")
            return {
                'city': city,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'poi_count': len(poi_data),
                'poi_pairs': {}
            }

        # Initialize distance matrix
        distance_matrix = {
            'city': city,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'poi_count': len(poi_data),
            'poi_pairs': {}
        }

        # Calculate for each transportation mode
        modes = ['walking', 'transit', 'driving']

        for mode in modes:
            logger.info(f"Calculating {mode} distances...")

            try:
                # Build list of coordinates
                origins = [p['coords'] for p in poi_data]
                destinations = origins  # Calculate N x N matrix

                # Call Distance Matrix API
                # Note: For transit mode, we use departure_time='now'
                result = self.client.distance_matrix(
                    origins=origins,
                    destinations=destinations,
                    mode=mode,
                    units='metric',
                    departure_time='now' if mode == 'transit' else None
                )

                if result.get('status') != 'OK':
                    logger.warning(f"Distance Matrix API returned status: {result.get('status')} for {mode}")
                    continue

                # Parse results for all POI pairs
                for i, origin in enumerate(poi_data):
                    row = result.get('rows', [])[i]

                    for j, dest in enumerate(poi_data):
                        # Skip same POI
                        if i == j:
                            continue

                        element = row.get('elements', [])[j]

                        if element.get('status') != 'OK':
                            logger.debug(
                                f"No {mode} route from {origin['poi_id']} to {dest['poi_id']}: "
                                f"{element.get('status')}"
                            )
                            continue

                        # Create pair key
                        pair_key = f"{origin['poi_id']}_to_{dest['poi_id']}"

                        # Initialize pair dictionary if needed
                        if pair_key not in distance_matrix['poi_pairs']:
                            distance_matrix['poi_pairs'][pair_key] = {
                                'origin_poi_id': origin['poi_id'],
                                'origin_poi_name': origin['poi_name'],
                                'destination_poi_id': dest['poi_id'],
                                'destination_poi_name': dest['poi_name']
                            }

                        # Add mode-specific data
                        duration_seconds = element.get('duration', {}).get('value', 0)
                        distance_meters = element.get('distance', {}).get('value', 0)

                        distance_matrix['poi_pairs'][pair_key][mode] = {
                            'duration_minutes': round(duration_seconds / 60, 1),
                            'distance_km': round(distance_meters / 1000, 2),
                            'duration_text': element.get('duration', {}).get('text'),
                            'distance_text': element.get('distance', {}).get('text')
                        }

                        # For transit, include additional info if available
                        if mode == 'transit' and 'duration_in_traffic' in element:
                            traffic_seconds = element['duration_in_traffic']['value']
                            distance_matrix['poi_pairs'][pair_key][mode]['duration_in_traffic_minutes'] = \
                                round(traffic_seconds / 60, 1)

                logger.info(f"Successfully calculated {mode} distances")

            except (ApiError, TransportError, Timeout) as e:
                logger.error(f"Distance Matrix API error for {mode}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error calculating {mode} distances: {e}")
                continue

        logger.info(
            f"Distance matrix calculation complete: "
            f"{len(distance_matrix['poi_pairs'])} POI pairs calculated"
        )

        return distance_matrix

    def _parse_hours(self, opening_hours: Dict) -> Dict:
        """
        Parse opening hours from Google Maps API response.

        Args:
            opening_hours: Opening hours data from Places API

        Returns:
            Dictionary with weekday_text or structured hours
        """
        if not opening_hours:
            return {'status': 'unknown'}

        # Check if open 24/7
        if opening_hours.get('open_now') is not None:
            hours = {
                'open_now': opening_hours['open_now']
            }
        else:
            hours = {}

        # Get human-readable hours
        if 'weekday_text' in opening_hours:
            hours['weekday_text'] = opening_hours['weekday_text']

        # Get structured periods (if needed for more detailed parsing)
        if 'periods' in opening_hours:
            hours['periods'] = opening_hours['periods']

        return hours

    def validate_api_key(self) -> bool:
        """
        Validate that the API key has required permissions.

        Returns:
            True if API key is valid and has required permissions
        """
        try:
            # Try a simple geocoding request to validate the key
            result = self.client.geocode("London")
            return bool(result)
        except ApiError as e:
            logger.error(f"API key validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error validating API key: {e}")
            return False
