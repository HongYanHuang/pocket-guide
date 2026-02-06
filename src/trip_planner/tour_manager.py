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
        create_tour_id,
        get_poi_path,
        load_metadata,
        normalize_language_code,
        get_tour_filename,
        get_tour_directory
    )
except ImportError:
    try:
        from src.utils import (
            ensure_tour_directory,
            load_tour_metadata,
            save_tour_metadata,
            get_next_tour_version,
            save_versioned_tour,
            save_tour_generation_record,
            create_tour_id,
            get_poi_path,
            load_metadata,
            normalize_language_code,
            get_tour_filename,
            get_tour_directory
        )
    except ImportError:
        from utils import (
            ensure_tour_directory,
            load_tour_metadata,
            save_tour_metadata,
            get_next_tour_version,
            save_versioned_tour,
            save_tour_generation_record,
            create_tour_id,
            get_poi_path,
            load_metadata,
            normalize_language_code,
            get_tour_filename,
            get_tour_directory
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

    def __init__(self, config: Dict[str, Any], tours_dir: str = "tours", content_dir: str = "content"):
        """
        Initialize Tour Manager.

        Args:
            config: Application configuration
            tours_dir: Base directory for tours (default: "tours")
            content_dir: Base directory for content/POIs (default: "content")
        """
        self.config = config
        self.tours_dir = tours_dir
        self.content_dir = content_dir

    def save_tour(
        self,
        tour_data: Dict[str, Any],
        city: str,
        input_parameters: Dict[str, Any],
        user_info: Dict[str, Any] = None,
        tour_id: str = None,
        selection_result: Dict[str, Any] = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Save tour with full versioning and metadata tracking.

        Args:
            tour_data: Complete tour itinerary (from optimizer)
            city: City name
            input_parameters: All input params used to generate tour
            user_info: Optional user information
            tour_id: Optional tour ID (creates new if None)
            selection_result: Optional POI selection result (with backup_pois and rejected_pois)
            language: Target language for tour (ISO 639-1 code)

        Returns:
            Dictionary with tour_id, version, and paths
        """
        # Normalize language
        language = normalize_language_code(language)

        # Generate tour ID if not provided
        if not tour_id:
            user_id = user_info.get('user_id') if user_info else None
            tour_id = create_tour_id(city, user_id)

        # Ensure tour directory exists
        tour_path = ensure_tour_directory(self.tours_dir, city, tour_id)

        # Load existing metadata or create new
        metadata = load_tour_metadata(tour_path)

        # Track languages in metadata
        if 'languages' not in metadata:
            metadata['languages'] = []
        if language not in metadata['languages']:
            metadata['languages'].append(language)

        # Calculate next version for this language
        version_key = f'current_version_{language}'
        version_num = metadata.get(version_key, 0) + 1
        date_str = datetime.now().strftime('%Y-%m-%d')
        version_string = f"v{version_num}_{date_str}"

        # Prepare generation record
        timestamp = datetime.now().isoformat()
        generation_record = {
            'version': version_num,
            'version_string': version_string,
            'timestamp': timestamp,
            'language': language,
            'user_info': user_info or {'user_id': 'anonymous'},
            'input_parameters': input_parameters,
            'optimization_scores': tour_data.get('optimization_scores', {}),
            'constraints_violated': tour_data.get('constraints_violated', []),
            'metadata': tour_data.get('metadata', {}),
            'total_pois': len(tour_data.get('itinerary', [])),
            'total_days': len(tour_data.get('itinerary', []))
        }

        # Add POI selection details if available
        if selection_result:
            generation_record['poi_selection'] = {
                'backup_pois': selection_result.get('backup_pois', {}),
                'rejected_pois': selection_result.get('rejected_pois', []),
                'total_backup_pois': sum(len(backups) for backups in selection_result.get('backup_pois', {}).values()),
                'total_rejected_pois': len(selection_result.get('rejected_pois', []))
            }

        # Save versioned tour with language suffix
        versioned_tour_file = tour_path / get_tour_filename('tour', language, version_string)
        with open(versioned_tour_file, 'w', encoding='utf-8') as f:
            json.dump(tour_data, f, indent=2, ensure_ascii=False)

        # Save current tour file with language suffix
        current_tour_file = tour_path / get_tour_filename('tour', language)
        with open(current_tour_file, 'w', encoding='utf-8') as f:
            json.dump(tour_data, f, indent=2, ensure_ascii=False)

        # Save generation record with language suffix
        gen_record_file = tour_path / get_tour_filename('generation_record', language, version_string)
        with open(gen_record_file, 'w', encoding='utf-8') as f:
            json.dump(generation_record, f, indent=2, ensure_ascii=False)

        # Create and save transcript links
        transcript_links = self._create_transcript_links(
            tour_data['itinerary'],
            city,
            language,
            tour_id
        )
        links_file = tour_path / f"transcript_links_{language}.json"
        with open(links_file, 'w', encoding='utf-8') as f:
            json.dump(transcript_links, f, indent=2, ensure_ascii=False)

        # Update metadata with language-specific version tracking
        version_history_key = f'version_history_{language}'
        if version_history_key not in metadata:
            metadata[version_history_key] = []

        # Add to version history for this language
        version_entry = {
            'version': version_num,
            'version_string': version_string,
            'timestamp': timestamp,
            'language': language,
            'user_id': user_info.get('user_id', 'anonymous') if user_info else 'anonymous',
            'input_hash': self._hash_inputs(input_parameters),
            'optimization_score': tour_data.get('optimization_scores', {}).get('overall_score', 0),
            'constraints_violated': len(tour_data.get('constraints_violated', []))
        }

        metadata[version_history_key].append(version_entry)
        metadata[version_key] = version_num
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
            'language': language,
            'tour_path': str(tour_path),
            'transcript_links_file': str(links_file),
            'files': {
                'tour': str(current_tour_file),
                'tour_versioned': str(versioned_tour_file),
                'generation_record': str(gen_record_file),
                'metadata': str(tour_path / "metadata.json"),
                'transcript_links': str(links_file)
            }
        }

    def load_tour(
        self,
        city: str,
        tour_id: str,
        version: Optional[int] = None,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Load a tour by ID and optional version.

        Args:
            city: City name
            tour_id: Tour identifier
            version: Optional version number (loads latest if None)
            language: Language version to load (default: 'en')

        Returns:
            Tour data dictionary
        """
        language = normalize_language_code(language)
        tour_path = get_tour_directory(self.tours_dir, city, tour_id)

        if not tour_path.exists():
            raise FileNotFoundError(f"Tour not found: {tour_id}")

        # Load metadata to check available languages
        metadata = load_tour_metadata(tour_path)
        available_languages = metadata.get('languages', ['en'])

        if language not in available_languages:
            raise FileNotFoundError(
                f"Tour not found for language '{language}'. "
                f"Available languages: {available_languages}"
            )

        if version is None:
            # Load latest version for this language
            tour_file = tour_path / get_tour_filename('tour', language)
        else:
            # Load specific version for this language
            version_history_key = f'version_history_{language}'
            version_history = metadata.get(version_history_key, [])

            # Find version string for requested version
            version_entry = next(
                (v for v in version_history if v['version'] == version),
                None
            )

            if not version_entry:
                raise ValueError(f"Version {version} not found for language '{language}' in tour {tour_id}")

            tour_file = tour_path / get_tour_filename('tour', language, version_entry['version_string'])

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

    def _create_transcript_links(
        self,
        itinerary: List[Dict[str, Any]],
        city: str,
        language: str,
        tour_id: str
    ) -> Dict[str, Any]:
        """
        Create links from tour to transcripts.

        This creates a record of which transcript files this tour should use.
        Links can point to standard transcripts or custom transcripts.

        Args:
            itinerary: Tour itinerary with POI list
            city: City name
            language: Language code
            tour_id: Tour identifier

        Returns:
            Dictionary with transcript links
        """
        links = {
            'tour_id': tour_id,
            'language': language,
            'created_at': datetime.now().isoformat(),
            'links': []
        }

        for day in itinerary:
            for poi_obj in day['pois']:
                poi_name = poi_obj['poi']
                poi_id = poi_name.lower().replace(' ', '-').replace('(', '').replace(')', '')

                # Get transcript path and version
                poi_path = get_poi_path(self.content_dir, city, poi_id)

                # Check if POI directory exists
                if not poi_path.exists():
                    # POI doesn't exist yet, skip linking
                    continue

                transcript_path = poi_path / f"transcript_{language}.txt"

                # Check if transcript exists
                if not transcript_path.exists():
                    # Transcript doesn't exist, skip linking
                    continue

                # Load metadata to get version
                poi_metadata = load_metadata(poi_path)
                version = f"v{poi_metadata.get('current_version', 1)}"

                # Create relative path from project root
                # If path is already relative, use it; if absolute, make it relative
                if transcript_path.is_absolute():
                    relative_path = transcript_path.relative_to(Path.cwd())
                else:
                    relative_path = transcript_path

                links['links'].append({
                    'poi': poi_name,
                    'poi_id': poi_id,
                    'transcript_path': str(relative_path),
                    'transcript_version': version,
                    'transcript_type': 'standard',
                    'linked_at': datetime.now().isoformat()
                })

        return links

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
