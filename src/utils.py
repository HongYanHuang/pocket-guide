"""
Utility functions for Pocket Guide CLI
"""
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any


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
