"""
POI Metadata Collection Agent

Orchestrates metadata collection for POIs including:
- Geographic coordinates
- Operation hours
- Indoor/outdoor classification
- Accessibility information
- Inter-POI distance matrix (CRITICAL for trip planning)
"""

import os
import json
import logging
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from google_maps_service import GoogleMapsService
from utils import load_config


logger = logging.getLogger(__name__)


class POIMetadataAgent:
    """Agent for collecting and managing POI metadata."""

    def __init__(self, config: Dict):
        """
        Initialize POI metadata agent.

        Args:
            config: Configuration dictionary with poi_metadata settings
        """
        self.config = config
        self.content_dir = config.get('content_dir', './content')

        # Initialize Google Maps service
        google_maps_config = config.get('poi_metadata', {}).get('google_maps', {})
        api_key = google_maps_config.get('api_key', '')

        if api_key:
            self.google_maps = GoogleMapsService(api_key)
            logger.info("Google Maps service initialized")
        else:
            self.google_maps = None
            logger.warning("Google Maps API key not configured")

        # Initialize Nominatim fallback
        nominatim_config = config.get('poi_metadata', {}).get('nominatim', {})
        if nominatim_config.get('enabled', True):
            user_agent = nominatim_config.get('user_agent', 'pocket-guide')
            self.nominatim = Nominatim(user_agent=user_agent)
            logger.info("Nominatim geocoder initialized")
        else:
            self.nominatim = None

        # Distance matrix settings
        self.distance_matrix_config = config.get('poi_metadata', {}).get('distance_matrix', {})

    def collect_all_metadata(self, city: str) -> Dict:
        """
        Collect metadata for all POIs in a city.

        Args:
            city: City name

        Returns:
            Summary dictionary with collection results
        """
        logger.info(f"Starting metadata collection for {city}")

        # Load all POI research files
        pois = self._load_city_pois(city)

        if not pois:
            logger.error(f"No POI research files found for {city}")
            return {
                'city': city,
                'pois_updated': 0,
                'errors': [f"No POI research files found"]
            }

        # Collect metadata for each POI
        updated_count = 0
        errors = []

        for poi in pois:
            poi_id = poi.get('poi_id', 'unknown')
            poi_name = poi.get('poi_name', 'unknown')

            try:
                # Check if metadata needs updating
                needs_update = self._needs_metadata_update(poi)

                if needs_update:
                    logger.info(f"Collecting metadata for {poi_name}...")
                    metadata = self._collect_poi_metadata(poi)

                    if metadata:
                        # Save metadata to POI YAML file
                        self._save_poi_metadata(poi, metadata)
                        updated_count += 1
                        logger.info(f"✓ Updated metadata for {poi_name}")
                    else:
                        error_msg = f"Failed to collect metadata for {poi_name}"
                        logger.warning(error_msg)
                        errors.append(error_msg)
                else:
                    logger.info(f"Metadata up-to-date for {poi_name}")

            except Exception as e:
                error_msg = f"Error collecting metadata for {poi_name}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Reload POIs with updated metadata
        pois_with_metadata = self._load_city_pois(city)

        # Calculate distance matrix
        distance_matrix_result = {}
        try:
            logger.info(f"Calculating distance matrix for {city}...")
            distance_matrix = self._calculate_city_distance_matrix(pois_with_metadata, city)

            if distance_matrix:
                # Save distance matrix
                self._save_distance_matrix(city, distance_matrix)
                distance_matrix_result = {
                    'poi_pairs': len(distance_matrix.get('poi_pairs', {})),
                    'success': True
                }
                logger.info(f"✓ Distance matrix calculated: {distance_matrix_result['poi_pairs']} pairs")
            else:
                distance_matrix_result = {
                    'success': False,
                    'error': 'Distance matrix calculation failed'
                }

        except Exception as e:
            error_msg = f"Error calculating distance matrix: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            distance_matrix_result = {
                'success': False,
                'error': str(e)
            }

        return {
            'city': city,
            'pois_total': len(pois),
            'pois_updated': updated_count,
            'distance_matrix': distance_matrix_result,
            'errors': errors
        }

    def verify_metadata(self, city: str) -> Dict:
        """
        Verify metadata completeness for all POIs in a city.

        Args:
            city: City name

        Returns:
            Verification report
        """
        pois = self._load_city_pois(city)

        report = {
            'city': city,
            'total_pois': len(pois),
            'complete': 0,
            'incomplete': 0,
            'missing_fields': {},
            'pois': []
        }

        for poi in pois:
            poi_id = poi.get('poi_id', 'unknown')
            poi_name = poi.get('poi_name', 'unknown')

            metadata = poi.get('metadata', {})

            # Check completeness
            missing = []

            if not metadata.get('coordinates'):
                missing.append('coordinates')

            if not metadata.get('operation_hours'):
                missing.append('operation_hours')

            if not metadata.get('visit_info'):
                missing.append('visit_info')

            if missing:
                report['incomplete'] += 1
                for field in missing:
                    report['missing_fields'][field] = report['missing_fields'].get(field, 0) + 1
            else:
                report['complete'] += 1

            report['pois'].append({
                'poi_id': poi_id,
                'poi_name': poi_name,
                'has_metadata': bool(metadata),
                'missing_fields': missing
            })

        return report

    def _load_city_pois(self, city: str) -> List[Dict]:
        """
        Load all POI research files for a city.

        Args:
            city: City name

        Returns:
            List of POI dictionaries with research data
        """
        # Look for POI research files in poi_research/{city}/
        research_dir = Path('poi_research') / city

        if not research_dir.exists():
            logger.warning(f"POI research directory not found: {research_dir}")
            return []

        pois = []

        for yaml_file in research_dir.glob('*.yaml'):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                if not data or 'poi' not in data:
                    logger.warning(f"Invalid POI YAML structure in {yaml_file}")
                    continue

                poi_data = data['poi']
                poi_data['_yaml_file'] = str(yaml_file)

                # Ensure we have poi_id and poi_name
                if 'poi_id' not in poi_data:
                    poi_data['poi_id'] = yaml_file.stem

                if 'poi_name' not in poi_data:
                    poi_data['poi_name'] = poi_data.get('name', yaml_file.stem)

                pois.append(poi_data)

            except Exception as e:
                logger.error(f"Error loading POI YAML {yaml_file}: {e}")
                continue

        logger.info(f"Loaded {len(pois)} POIs for {city}")
        return pois

    def _needs_metadata_update(self, poi: Dict) -> bool:
        """
        Check if POI metadata needs updating.

        Args:
            poi: POI dictionary

        Returns:
            True if metadata needs updating
        """
        metadata = poi.get('metadata', {})

        # If no metadata at all, definitely needs update
        if not metadata:
            return True

        # Check if coordinates exist
        if not metadata.get('coordinates'):
            return True

        # Could add more sophisticated checks here
        # For now, if basic metadata exists, consider it complete

        return False

    def _collect_poi_metadata(self, poi: Dict) -> Optional[Dict]:
        """
        Collect metadata for a single POI.

        Args:
            poi: POI dictionary

        Returns:
            Metadata dictionary or None if collection failed
        """
        poi_name = poi.get('poi_name', poi.get('name', 'unknown'))
        city = poi.get('city', 'unknown')

        metadata = {}

        # Try Google Maps first
        if self.google_maps:
            logger.info(f"Querying Google Maps for {poi_name}...")
            gm_metadata = self.google_maps.get_place_details(poi_name, city)

            if gm_metadata:
                metadata.update(gm_metadata)
            else:
                # Try geocoding API as fallback
                logger.info(f"Trying Google Geocoding for {poi_name}...")
                coords = self.google_maps.get_coordinates_geocoding(poi_name, city)

                if coords:
                    metadata['coordinates'] = coords

        # Fallback to Nominatim if no coordinates yet
        if not metadata.get('coordinates') and self.nominatim:
            logger.info(f"Falling back to Nominatim for {poi_name}...")
            coords = self._get_nominatim_coordinates(poi_name, city)

            if coords:
                metadata['coordinates'] = coords

        # If still no coordinates, fail
        if not metadata.get('coordinates'):
            logger.error(f"Failed to get coordinates for {poi_name}")
            return None

        # Classify indoor/outdoor if not already done
        if 'visit_info' not in metadata:
            metadata['visit_info'] = self._infer_visit_info(poi)

        # Add timestamp
        metadata['last_metadata_update'] = datetime.now(timezone.utc).isoformat()
        metadata['verified'] = False  # Needs manual verification

        return metadata

    def _get_nominatim_coordinates(self, poi_name: str, city: str) -> Optional[Dict]:
        """
        Get coordinates using Nominatim geocoder.

        Args:
            poi_name: POI name
            city: City name

        Returns:
            Coordinates dictionary or None
        """
        try:
            query = f"{poi_name}, {city}"
            location = self.nominatim.geocode(query, timeout=10)

            if location:
                return {
                    'latitude': location.latitude,
                    'longitude': location.longitude,
                    'source': 'nominatim',
                    'collected_at': datetime.now(timezone.utc).isoformat()
                }

        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.error(f"Nominatim error: {e}")

        return None

    def _infer_visit_info(self, poi: Dict) -> Dict:
        """
        Infer visit information from POI data.

        Args:
            poi: POI dictionary

        Returns:
            Visit info dictionary
        """
        # Check POI types from Google Maps
        types = poi.get('types', [])

        # Simple heuristic for indoor/outdoor
        outdoor_types = ['park', 'monument', 'plaza', 'square', 'archaeological_site']
        indoor_types = ['museum', 'church', 'library', 'shopping_mall']

        indoor_outdoor = 'unknown'

        for outdoor_type in outdoor_types:
            if outdoor_type in types:
                indoor_outdoor = 'outdoor'
                break

        for indoor_type in indoor_types:
            if indoor_type in types:
                indoor_outdoor = 'indoor'
                break

        # Check POI name/description for keywords
        if indoor_outdoor == 'unknown':
            poi_name = poi.get('poi_name', '').lower()
            description = poi.get('basic_info', {}).get('description', '').lower()

            if any(word in poi_name or word in description for word in ['park', 'square', 'arch', 'gate']):
                indoor_outdoor = 'outdoor'
            elif any(word in poi_name or word in description for word in ['museum', 'church', 'cathedral', 'hall']):
                indoor_outdoor = 'indoor'

        return {
            'indoor_outdoor': indoor_outdoor,
            'typical_duration_minutes': 30,  # Default estimate
            'accessibility': 'unknown'
        }

    def _save_poi_metadata(self, poi: Dict, metadata: Dict) -> None:
        """
        Save metadata to POI YAML file.

        Args:
            poi: POI dictionary
            metadata: Metadata to save
        """
        yaml_file = poi.get('_yaml_file')

        if not yaml_file:
            logger.error("POI has no _yaml_file path")
            return

        # Read current YAML file
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Add/update metadata section
        if 'poi' in data:
            data['poi']['metadata'] = metadata
        else:
            logger.error(f"Invalid YAML structure in {yaml_file}")
            return

        # Write back to file
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        logger.info(f"Saved metadata to {yaml_file}")

    def _calculate_city_distance_matrix(self, pois: List[Dict], city: str) -> Optional[Dict]:
        """
        Calculate distance matrix for all POIs in a city.

        Args:
            pois: List of POI dictionaries with metadata
            city: City name

        Returns:
            Distance matrix dictionary or None
        """
        if not self.google_maps:
            logger.error("Google Maps service not available for distance matrix")
            return None

        # Filter POIs that have coordinates
        pois_with_coords = [
            poi for poi in pois
            if poi.get('metadata', {}).get('coordinates')
        ]

        if len(pois_with_coords) < 2:
            logger.warning(f"Need at least 2 POIs with coordinates for distance matrix (found {len(pois_with_coords)})")
            return None

        # Get batch size from config
        batch_size = self.distance_matrix_config.get('batch_size', 25)

        # Calculate distance matrix
        return self.google_maps.calculate_distance_matrix(
            pois_with_coords,
            city,
            batch_size=batch_size
        )

    def _save_distance_matrix(self, city: str, distance_matrix: Dict) -> None:
        """
        Save distance matrix to JSON file.

        Args:
            city: City name
            distance_matrix: Distance matrix dictionary
        """
        # Create poi_distances directory if needed
        distances_dir = Path('poi_distances') / city
        distances_dir.mkdir(parents=True, exist_ok=True)

        # Save distance matrix
        matrix_file = distances_dir / 'distance_matrix.json'

        with open(matrix_file, 'w', encoding='utf-8') as f:
            json.dump(distance_matrix, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved distance matrix to {matrix_file}")

    def load_distance_matrix(self, city: str) -> Optional[Dict]:
        """
        Load distance matrix from JSON file.

        Args:
            city: City name

        Returns:
            Distance matrix dictionary or None if not found
        """
        matrix_file = Path('poi_distances') / city / 'distance_matrix.json'

        if not matrix_file.exists():
            logger.warning(f"Distance matrix not found: {matrix_file}")
            return None

        with open(matrix_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_city_pois_from_content(self, city: str) -> List[Dict]:
        """
        Load all POI metadata from content directory.

        Args:
            city: City name

        Returns:
            List of POI dictionaries with metadata
        """
        content_dir = Path(self.content_dir) / city.lower().replace(' ', '-')

        if not content_dir.exists():
            logger.warning(f"Content directory not found: {content_dir}")
            return []

        pois = []

        for poi_dir in content_dir.iterdir():
            if not poi_dir.is_dir():
                continue

            metadata_file = poi_dir / 'metadata.json'
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                pois.append({
                    'poi_id': poi_dir.name,
                    'poi_name': metadata.get('poi', poi_dir.name),
                    'metadata': metadata
                })

            except Exception as e:
                logger.error(f"Error loading POI metadata from {metadata_file}: {e}")
                continue

        logger.info(f"Loaded {len(pois)} POIs from content directory for {city}")
        return pois

    def calculate_incremental_distances(
        self,
        new_poi: Dict,
        city: str
    ) -> Optional[Dict]:
        """
        Calculate distances incrementally for a new POI.

        Only calculates: new_poi ↔ existing_pois (not recalculating existing pairs).

        Args:
            new_poi: New POI dictionary with metadata containing coordinates
            city: City name

        Returns:
            Updated distance matrix or None if failed
        """
        if not self.google_maps:
            logger.error("Google Maps service not available for distance calculation")
            return None

        # Check if new POI has coordinates
        new_coords = new_poi.get('metadata', {}).get('coordinates', {})
        if not new_coords.get('latitude') or not new_coords.get('longitude'):
            logger.warning(f"New POI {new_poi.get('poi_id')} missing coordinates, skipping distance calculation")
            return None

        # Load existing POIs from content directory
        existing_pois = self._load_city_pois_from_content(city)

        # Filter existing POIs that have coordinates and are not the new POI
        new_poi_id = new_poi.get('poi_id')
        existing_with_coords = [
            poi for poi in existing_pois
            if poi.get('poi_id') != new_poi_id and
               poi.get('metadata', {}).get('coordinates')
        ]

        if not existing_with_coords:
            logger.info(f"No existing POIs with coordinates found for {city}, skipping distance calculation")
            return None

        logger.info(
            f"Calculating incremental distances: {new_poi_id} ↔ "
            f"{len(existing_with_coords)} existing POIs"
        )

        # Load or create distance matrix
        distance_matrix = self.load_distance_matrix(city)
        if not distance_matrix:
            # Create new matrix
            distance_matrix = {
                'city': city,
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'poi_count': len(existing_with_coords) + 1,
                'poi_pairs': {}
            }

        # Prepare POI data for API call
        new_poi_data = {
            'poi_id': new_poi.get('poi_id'),
            'poi_name': new_poi.get('poi_name'),
            'coords': (new_coords['latitude'], new_coords['longitude'])
        }

        existing_poi_data = []
        for poi in existing_with_coords:
            coords = poi.get('metadata', {}).get('coordinates', {})
            existing_poi_data.append({
                'poi_id': poi.get('poi_id'),
                'poi_name': poi.get('poi_name'),
                'coords': (coords['latitude'], coords['longitude'])
            })

        # Calculate for each transportation mode
        modes = ['walking', 'transit', 'driving']

        for mode in modes:
            logger.info(f"Calculating {mode} distances for new POI...")

            try:
                # INCREMENTAL CALCULATION: Only calculate new_poi ↔ existing_pois
                # This avoids MAX_ELEMENTS_EXCEEDED error

                # Call 1: new_poi → existing_pois
                origins = [new_poi_data['coords']]  # 1 origin
                destinations = [p['coords'] for p in existing_poi_data]  # N destinations

                result = self.google_maps.client.distance_matrix(
                    origins=origins,
                    destinations=destinations,
                    mode=mode,
                    units='metric',
                    departure_time='now' if mode == 'transit' else None
                )

                if result.get('status') != 'OK':
                    logger.warning(f"Distance Matrix API returned status: {result.get('status')} for {mode}")
                    continue

                # Parse results: new_poi → existing_pois
                row = result.get('rows', [{}])[0]  # Only one row (new_poi)

                for j, dest_poi in enumerate(existing_poi_data):
                    element = row.get('elements', [])[j]

                    if element.get('status') != 'OK':
                        logger.debug(
                            f"No {mode} route from {new_poi_id} to {dest_poi['poi_id']}: "
                            f"{element.get('status')}"
                        )
                        continue

                    # Create pair key: new_poi → existing_poi
                    pair_key = f"{new_poi_id}_to_{dest_poi['poi_id']}"

                    # Initialize pair dictionary if needed
                    if pair_key not in distance_matrix['poi_pairs']:
                        distance_matrix['poi_pairs'][pair_key] = {
                            'origin_poi_id': new_poi_id,
                            'origin_poi_name': new_poi_data['poi_name'],
                            'destination_poi_id': dest_poi['poi_id'],
                            'destination_poi_name': dest_poi['poi_name']
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

                # Call 2: existing_pois → new_poi (reverse direction)
                # For walking/driving, distances are symmetric, but transit may differ
                origins = [p['coords'] for p in existing_poi_data]  # N origins
                destinations = [new_poi_data['coords']]  # 1 destination

                result_reverse = self.google_maps.client.distance_matrix(
                    origins=origins,
                    destinations=destinations,
                    mode=mode,
                    units='metric',
                    departure_time='now' if mode == 'transit' else None
                )

                if result_reverse.get('status') == 'OK':
                    # Parse results: existing_pois → new_poi
                    for i, origin_poi in enumerate(existing_poi_data):
                        row = result_reverse.get('rows', [])[i]
                        element = row.get('elements', [{}])[0]  # Only one destination (new_poi)

                        if element.get('status') != 'OK':
                            logger.debug(
                                f"No {mode} route from {origin_poi['poi_id']} to {new_poi_id}: "
                                f"{element.get('status')}"
                            )
                            continue

                        # Create pair key: existing_poi → new_poi
                        pair_key = f"{origin_poi['poi_id']}_to_{new_poi_id}"

                        # Initialize pair dictionary if needed
                        if pair_key not in distance_matrix['poi_pairs']:
                            distance_matrix['poi_pairs'][pair_key] = {
                                'origin_poi_id': origin_poi['poi_id'],
                                'origin_poi_name': origin_poi['poi_name'],
                                'destination_poi_id': new_poi_id,
                                'destination_poi_name': new_poi_data['poi_name']
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

                logger.info(f"Successfully calculated {mode} distances for new POI (both directions)")

            except Exception as e:
                logger.error(f"Error calculating {mode} distances: {e}")
                continue

        # Update metadata
        distance_matrix['generated_at'] = datetime.now(timezone.utc).isoformat()
        distance_matrix['poi_count'] = len(existing_with_coords) + 1

        # Save updated matrix
        self._save_distance_matrix(city, distance_matrix)

        logger.info(
            f"Incremental distance calculation complete: "
            f"{len([k for k in distance_matrix['poi_pairs'].keys() if new_poi_id in k])} new pairs added"
        )

        return distance_matrix

    def show_metadata(self, city: str, poi_id: Optional[str] = None) -> Dict:
        """
        Show metadata for POI(s) in a city.

        Args:
            city: City name
            poi_id: Optional POI ID to show specific POI

        Returns:
            Metadata dictionary
        """
        pois = self._load_city_pois(city)

        if poi_id:
            # Find specific POI
            poi = next((p for p in pois if p.get('poi_id') == poi_id), None)

            if not poi:
                return {'error': f"POI not found: {poi_id}"}

            return {
                'poi_id': poi.get('poi_id'),
                'poi_name': poi.get('poi_name'),
                'metadata': poi.get('metadata', {})
            }
        else:
            # Show all POIs
            return {
                'city': city,
                'pois': [
                    {
                        'poi_id': p.get('poi_id'),
                        'poi_name': p.get('poi_name'),
                        'has_metadata': bool(p.get('metadata')),
                        'has_coordinates': bool(p.get('metadata', {}).get('coordinates'))
                    }
                    for p in pois
                ]
            }
