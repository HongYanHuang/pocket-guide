"""
Tour Manager - Handles tour storage, versioning, and metadata tracking.

Similar to transcript versioning, this provides complete audit trail for tours.
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    from ..utils import (
        ensure_tour_directory,
        load_tour_metadata,
        save_tour_metadata,
        get_next_tour_version,
        save_versioned_tour,
        save_tour_generation_record,
        create_tour_id
    )
except ImportError:
    from src.utils import (
        ensure_tour_directory,
        load_tour_metadata,
        save_tour_metadata,
        get_next_tour_version,
        save_versioned_tour,
        save_tour_generation_record,
        create_tour_id
    )


class TourManager:
    """
    Manages tour storage, versioning, and metadata tracking.

    Features:
    - Automatic versioning (v1, v2, v3...)
    - Complete audit trail
    - Input parameter tracking
    - User attribution
    - Generation history
    """

    def __init__(self, config: Dict[str, Any], tours_dir: str = "tours"):
        """
        Initialize Tour Manager.

        Args:
            config: Application configuration
            tours_dir: Base directory for tours (default: "tours")
        """
        self.config = config
        self.tours_dir = tours_dir

    def save_tour(
        self,
        tour_data: Dict[str, Any],
        city: str,
        input_parameters: Dict[str, Any],
        user_info: Dict[str, Any] = None,
        tour_id: str = None
    ) -> Dict[str, Any]:
        """
        Save tour with full versioning and metadata tracking.

        Args:
            tour_data: Complete tour itinerary (from optimizer)
            city: City name
            input_parameters: All input params used to generate tour
            user_info: Optional user information
            tour_id: Optional tour ID (creates new if None)

        Returns:
            Dictionary with tour_id, version, and paths
        """
        # Generate tour ID if not provided
        if not tour_id:
            user_id = user_info.get('user_id') if user_info else None
            tour_id = create_tour_id(city, user_id)

        # Ensure tour directory exists
        tour_path = ensure_tour_directory(self.tours_dir, city, tour_id)

        # Load existing metadata or create new
        metadata = load_tour_metadata(tour_path)

        # Calculate next version
        version_num, version_string = get_next_tour_version(metadata)

        # Prepare generation record
        timestamp = datetime.now().isoformat()
        generation_record = {
            'version': version_num,
            'version_string': version_string,
            'timestamp': timestamp,
            'user_info': user_info or {'user_id': 'anonymous'},
            'input_parameters': input_parameters,
            'optimization_scores': tour_data.get('optimization_scores', {}),
            'constraints_violated': tour_data.get('constraints_violated', []),
            'metadata': tour_data.get('metadata', {}),
            'total_pois': len(tour_data.get('itinerary', [])),
            'total_days': len(tour_data.get('itinerary', []))
        }

        # Save versioned tour
        save_versioned_tour(tour_path, tour_data, version_string)

        # Save generation record
        save_tour_generation_record(tour_path, version_string, generation_record)

        # Update metadata
        if 'version_history' not in metadata:
            metadata['version_history'] = []

        # Add to version history
        version_entry = {
            'version': version_num,
            'version_string': version_string,
            'timestamp': timestamp,
            'user_id': user_info.get('user_id', 'anonymous') if user_info else 'anonymous',
            'input_hash': self._hash_inputs(input_parameters),
            'optimization_score': tour_data.get('optimization_scores', {}).get('overall_score', 0),
            'constraints_violated': len(tour_data.get('constraints_violated', []))
        }

        metadata['version_history'].append(version_entry)
        metadata['current_version'] = version_num
        metadata['tour_id'] = tour_id
        metadata['city'] = city
        metadata['created_at'] = metadata.get('created_at', timestamp)
        metadata['updated_at'] = timestamp

        # Save updated metadata
        save_tour_metadata(tour_path, metadata)

        print(f"\n✓ Tour saved: {tour_id}")
        print(f"  Version: {version_string}")
        print(f"  Location: {tour_path}")

        return {
            'tour_id': tour_id,
            'version': version_num,
            'version_string': version_string,
            'tour_path': str(tour_path),
            'files': {
                'tour': str(tour_path / "tour.json"),
                'tour_versioned': str(tour_path / f"tour_{version_string}.json"),
                'generation_record': str(tour_path / f"generation_record_{version_string}.json"),
                'metadata': str(tour_path / "metadata.json")
            }
        }

    def load_tour(
        self,
        city: str,
        tour_id: str,
        version: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Load a tour by ID and optional version.

        Args:
            city: City name
            tour_id: Tour identifier
            version: Optional version number (loads latest if None)

        Returns:
            Tour data dictionary
        """
        from src.utils import get_tour_directory

        tour_path = get_tour_directory(self.tours_dir, city, tour_id)

        if not tour_path.exists():
            raise FileNotFoundError(f"Tour not found: {tour_id}")

        if version is None:
            # Load latest version
            tour_file = tour_path / "tour.json"
        else:
            # Load specific version
            metadata = load_tour_metadata(tour_path)
            version_history = metadata.get('version_history', [])

            # Find version string for requested version
            version_entry = next(
                (v for v in version_history if v['version'] == version),
                None
            )

            if not version_entry:
                raise ValueError(f"Version {version} not found for tour {tour_id}")

            tour_file = tour_path / f"tour_{version_entry['version_string']}.json"

        if not tour_file.exists():
            raise FileNotFoundError(f"Tour file not found: {tour_file}")

        with open(tour_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_tour_history(self, city: str, tour_id: str) -> Dict[str, Any]:
        """
        Get complete version history for a tour.

        Args:
            city: City name
            tour_id: Tour identifier

        Returns:
            Metadata dictionary with version_history
        """
        from src.utils import get_tour_directory

        tour_path = get_tour_directory(self.tours_dir, city, tour_id)
        return load_tour_metadata(tour_path)

    def list_tours(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all tours, optionally filtered by city.

        Args:
            city: Optional city filter

        Returns:
            List of tour metadata dictionaries
        """
        tours = []
        tours_path = Path(self.tours_dir)

        if not tours_path.exists():
            return tours

        if city:
            # List tours for specific city
            city_slug = city.lower().replace(' ', '-')
            city_path = tours_path / city_slug

            if city_path.exists():
                for tour_dir in city_path.iterdir():
                    if tour_dir.is_dir():
                        metadata = load_tour_metadata(tour_dir)
                        if metadata:
                            tours.append(metadata)
        else:
            # List all tours across all cities
            for city_dir in tours_path.iterdir():
                if city_dir.is_dir():
                    for tour_dir in city_dir.iterdir():
                        if tour_dir.is_dir():
                            metadata = load_tour_metadata(tour_dir)
                            if metadata:
                                tours.append(metadata)

        # Sort by updated_at descending
        tours.sort(key=lambda t: t.get('updated_at', ''), reverse=True)
        return tours

    def compare_versions(
        self,
        city: str,
        tour_id: str,
        version1: int,
        version2: int
    ) -> Dict[str, Any]:
        """
        Compare two versions of a tour.

        Args:
            city: City name
            tour_id: Tour identifier
            version1: First version number
            version2: Second version number

        Returns:
            Comparison results
        """
        tour_v1 = self.load_tour(city, tour_id, version1)
        tour_v2 = self.load_tour(city, tour_id, version2)

        # Compare key metrics
        scores_v1 = tour_v1.get('optimization_scores', {})
        scores_v2 = tour_v2.get('optimization_scores', {})

        comparison = {
            'version1': version1,
            'version2': version2,
            'score_changes': {
                'distance_score': scores_v2.get('distance_score', 0) - scores_v1.get('distance_score', 0),
                'coherence_score': scores_v2.get('coherence_score', 0) - scores_v1.get('coherence_score', 0),
                'overall_score': scores_v2.get('overall_score', 0) - scores_v1.get('overall_score', 0)
            },
            'itinerary_changes': {
                'days_v1': len(tour_v1.get('itinerary', [])),
                'days_v2': len(tour_v2.get('itinerary', [])),
                'pois_changed': self._compare_pois(tour_v1, tour_v2)
            }
        }

        return comparison

    def _hash_inputs(self, input_parameters: Dict[str, Any]) -> str:
        """
        Create hash of input parameters for change tracking.

        Args:
            input_parameters: Input dictionary

        Returns:
            Hash string
        """
        import hashlib
        import json

        # Serialize inputs to JSON string
        inputs_str = json.dumps(input_parameters, sort_keys=True)
        return hashlib.md5(inputs_str.encode()).hexdigest()

    def _compare_pois(self, tour1: Dict, tour2: Dict) -> Dict[str, Any]:
        """
        Compare POIs between two tour versions.

        Args:
            tour1: First tour data
            tour2: Second tour data

        Returns:
            POI comparison results
        """
        pois1 = set()
        pois2 = set()

        for day in tour1.get('itinerary', []):
            for poi in day.get('pois', []):
                pois1.add(poi.get('poi', ''))

        for day in tour2.get('itinerary', []):
            for poi in day.get('pois', []):
                pois2.add(poi.get('poi', ''))

        return {
            'added': list(pois2 - pois1),
            'removed': list(pois1 - pois2),
            'unchanged': list(pois1 & pois2)
        }
