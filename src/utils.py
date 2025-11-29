"""
Utility functions for Pocket Guide CLI
"""
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple, List


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Please copy config.example.yaml to config.yaml and add your API keys."
        )

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_city_path(content_dir: str, city: str) -> Path:
    """Get the path for a city directory"""
    city_slug = city.lower().replace(' ', '-')
    return Path(content_dir) / city_slug


def get_poi_path(content_dir: str, city: str, poi: str) -> Path:
    """Get the path for a POI directory"""
    city_path = get_city_path(content_dir, city)
    poi_slug = poi.lower().replace(' ', '-')
    return city_path / poi_slug


def ensure_poi_directory(content_dir: str, city: str, poi: str) -> Path:
    """Create POI directory if it doesn't exist and return the path"""
    poi_path = get_poi_path(content_dir, city, poi)
    poi_path.mkdir(parents=True, exist_ok=True)
    return poi_path


def save_metadata(poi_path: Path, metadata: Dict[str, Any]):
    """Save POI metadata to JSON file"""
    metadata_file = poi_path / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, indent=2, fp=f, ensure_ascii=False)


def load_metadata(poi_path: Path) -> Dict[str, Any]:
    """Load POI metadata from JSON file"""
    metadata_file = poi_path / "metadata.json"
    if not metadata_file.exists():
        return {}

    with open(metadata_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_transcript(poi_path: Path, content: str, format: str = "txt"):
    """Save transcript to file"""
    if format == "txt":
        file_path = poi_path / "transcript.txt"
    elif format == "ssml":
        file_path = poi_path / "transcript.ssml"
    else:
        raise ValueError(f"Unsupported format: {format}")

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def load_transcript(poi_path: Path, format: str = "txt") -> str:
    """Load transcript from file"""
    if format == "txt":
        file_path = poi_path / "transcript.txt"
    elif format == "ssml":
        file_path = poi_path / "transcript.ssml"
    else:
        raise ValueError(f"Unsupported format: {format}")

    if not file_path.exists():
        raise FileNotFoundError(f"Transcript not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def list_cities(content_dir: str) -> list:
    """List all cities in the content directory"""
    content_path = Path(content_dir)
    if not content_path.exists():
        return []

    cities = []
    for item in content_path.iterdir():
        if item.is_dir():
            # Convert slug back to readable name
            city_name = item.name.replace('-', ' ').title()
            cities.append({
                'name': city_name,
                'slug': item.name,
                'path': str(item)
            })
    return cities


def list_pois(content_dir: str, city: str) -> list:
    """List all POIs for a city"""
    city_path = get_city_path(content_dir, city)
    if not city_path.exists():
        return []

    pois = []
    for item in city_path.iterdir():
        if item.is_dir():
            metadata = load_metadata(item)
            poi_name = item.name.replace('-', ' ').title()
            pois.append({
                'name': poi_name,
                'slug': item.name,
                'path': str(item),
                'metadata': metadata
            })
    return pois


def text_to_ssml(text: str, language: str = "en-US") -> str:
    """Convert plain text to SSML format for better TTS control"""
    # Basic SSML wrapper with prosody controls
    ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}">
    <prosody rate="medium" pitch="medium">
        {text}
    </prosody>
</speak>'''
    return ssml


# ==== Version Tracking Functions ====

def get_next_version(metadata: Dict[str, Any]) -> Tuple[int, str]:
    """
    Calculate next version number and string

    Args:
        metadata: Current metadata dict

    Returns:
        (version_number, version_string) e.g. (3, "v3_2025-01-15")
    """
    from datetime import datetime

    # If no version history, start at v1
    if 'version_history' not in metadata or not metadata['version_history']:
        version = 1
    else:
        version = metadata.get('current_version', 0) + 1

    date_str = datetime.now().strftime('%Y-%m-%d')
    version_string = f"v{version}_{date_str}"

    return version, version_string


def save_versioned_transcript(
    poi_path: Path,
    content: str,
    version_string: str,
    format: str = "txt"
) -> None:
    """
    Save transcript with version in filename
    Also saves copy as current transcript for backward compatibility

    Args:
        poi_path: POI directory path
        content: Transcript content
        version_string: e.g. "v1_2025-01-15"
        format: "txt" or "ssml"
    """
    # Save versioned file
    versioned_path = poi_path / f"transcript_{version_string}.{format}"
    with open(versioned_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Also save as current transcript (backward compat)
    current_path = poi_path / f"transcript.{format}"
    with open(current_path, 'w', encoding='utf-8') as f:
        f.write(content)


def save_generation_record(
    poi_path: Path,
    version_string: str,
    record_data: Dict[str, Any]
) -> None:
    """
    Save generation record JSON

    Args:
        poi_path: POI directory path
        version_string: e.g. "v1_2025-01-15"
        record_data: Complete record dictionary
    """
    record_path = poi_path / f"generation_record_{version_string}.json"
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, indent=2, ensure_ascii=False)


def extract_used_nodes(
    transcript: str,
    research_data: Dict
) -> Dict[str, List]:
    """
    Extract which knowledge nodes were used in transcript via string matching

    Args:
        transcript: Generated transcript text
        research_data: Full research YAML data

    Returns:
        Dict with keys: 'poi', 'core_features', 'entities'
    """
    if not research_data:
        return {'poi': [], 'core_features': [], 'entities': []}

    used_nodes = {
        'poi': [research_data.get('poi', {}).get('poi_id', 'unknown')],
        'core_features': list(range(len(research_data.get('core_features', [])))),
        'entities': []
    }

    transcript_lower = transcript.lower()

    # Check each entity by name
    for entity_id, entity_data in research_data.get('entities', {}).items():
        entity_name = entity_data.get('name', '')

        if entity_name and entity_name.lower() in transcript_lower:
            used_nodes['entities'].append(entity_id)

    return used_nodes


# ==== Tour Storage and Versioning Functions ====

def get_tour_directory(tours_dir: str, city: str, tour_id: str) -> Path:
    """
    Get the directory path for a specific tour

    Args:
        tours_dir: Base tours directory
        city: City name
        tour_id: Unique tour identifier

    Returns:
        Path to tour directory
    """
    city_slug = city.lower().replace(' ', '-')
    return Path(tours_dir) / city_slug / tour_id


def ensure_tour_directory(tours_dir: str, city: str, tour_id: str) -> Path:
    """
    Create tour directory if it doesn't exist

    Args:
        tours_dir: Base tours directory
        city: City name
        tour_id: Unique tour identifier

    Returns:
        Path to tour directory
    """
    tour_path = get_tour_directory(tours_dir, city, tour_id)
    tour_path.mkdir(parents=True, exist_ok=True)
    return tour_path


def load_tour_metadata(tour_path: Path) -> Dict[str, Any]:
    """
    Load tour metadata from JSON file

    Args:
        tour_path: Path to tour directory

    Returns:
        Metadata dictionary
    """
    metadata_file = tour_path / "metadata.json"
    if not metadata_file.exists():
        return {}

    with open(metadata_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tour_metadata(tour_path: Path, metadata: Dict[str, Any]) -> None:
    """
    Save tour metadata to JSON file

    Args:
        tour_path: Path to tour directory
        metadata: Metadata dictionary
    """
    metadata_file = tour_path / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def get_next_tour_version(metadata: Dict[str, Any]) -> Tuple[int, str]:
    """
    Calculate next tour version number and string

    Args:
        metadata: Current tour metadata dict

    Returns:
        (version_number, version_string) e.g. (2, "v2_2025-11-29")
    """
    from datetime import datetime

    # If no version history, start at v1
    if 'version_history' not in metadata or not metadata['version_history']:
        version = 1
    else:
        version = metadata.get('current_version', 0) + 1

    date_str = datetime.now().strftime('%Y-%m-%d')
    version_string = f"v{version}_{date_str}"

    return version, version_string


def save_versioned_tour(
    tour_path: Path,
    tour_data: Dict[str, Any],
    version_string: str
) -> None:
    """
    Save tour with version in filename
    Also saves copy as current tour for easy access

    Args:
        tour_path: Tour directory path
        tour_data: Complete tour itinerary data
        version_string: e.g. "v1_2025-11-29"
    """
    # Save versioned file
    versioned_path = tour_path / f"tour_{version_string}.json"
    with open(versioned_path, 'w', encoding='utf-8') as f:
        json.dump(tour_data, f, indent=2, ensure_ascii=False)

    # Also save as current tour (for easy access)
    current_path = tour_path / "tour.json"
    with open(current_path, 'w', encoding='utf-8') as f:
        json.dump(tour_data, f, indent=2, ensure_ascii=False)


def save_tour_generation_record(
    tour_path: Path,
    version_string: str,
    record_data: Dict[str, Any]
) -> None:
    """
    Save tour generation record with input parameters and results

    Args:
        tour_path: Tour directory path
        version_string: e.g. "v1_2025-11-29"
        record_data: Complete generation record
    """
    record_path = tour_path / f"generation_record_{version_string}.json"
    with open(record_path, 'w', encoding='utf-8') as f:
        json.dump(record_data, f, indent=2, ensure_ascii=False)


def create_tour_id(city: str, user_id: str = None) -> str:
    """
    Generate a unique tour ID

    Args:
        city: City name
        user_id: Optional user identifier

    Returns:
        Unique tour ID (e.g., "athens-tour-20251129-143052-abc123")
    """
    from datetime import datetime
    import hashlib

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    city_slug = city.lower().replace(' ', '-')

    # Create hash from timestamp + city + user
    hash_input = f"{timestamp}{city}{user_id or 'anonymous'}".encode()
    hash_suffix = hashlib.md5(hash_input).hexdigest()[:6]

    tour_id = f"{city_slug}-tour-{timestamp}-{hash_suffix}"
    return tour_id
