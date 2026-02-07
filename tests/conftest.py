"""
Pytest configuration and shared fixtures for unit tests

This file contains:
- Mock AI client fixtures (OpenAI, Anthropic, Google)
- Mock file system fixtures
- Common test data fixtures
- Test configuration
"""

import pytest
import yaml
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, Any


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Provide a sample config for testing without loading config.yaml"""
    return {
        'ai_providers': {
            'openai': {
                'api_key': 'test-openai-key',
                'model': 'gpt-4'
            },
            'anthropic': {
                'api_key': 'test-anthropic-key',
                'model': 'claude-3-sonnet-20240229'
            },
            'google': {
                'api_key': 'test-google-key',
                'model': 'gemini-pro'
            }
        },
        'research': {
            'enabled': True,
            'recursive_depth': 2
        },
        'verification': {
            'enabled': True,
            'smart_mode': True,
            'coverage_threshold': 0.90,
            'similarity_threshold': 0.35
        },
        'content_generation': {
            'prompt_modules': {
                'architecture': {
                    'trigger_interests': ['architecture', 'design'],
                    'trigger_keywords': ['architect', 'building', 'design']
                },
                'biography': {
                    'trigger_interests': ['biography', 'history'],
                    'trigger_keywords': ['person', 'emperor', 'artist']
                }
            }
        },
        'tts_providers': {
            'openai': {
                'api_key': 'test-openai-key',
                'voice': 'nova'
            },
            'google': {
                'credentials_file': '/path/to/creds.json'
            },
            'edge': {
                'voice': 'en-US-AriaNeural'
            }
        }
    }


# ============================================================================
# AI Provider Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI client to avoid API calls during testing.

    Returns a MagicMock that simulates OpenAI API responses.
    """
    with patch('openai.OpenAI') as mock_class:
        # Create mock client instance
        client = MagicMock()
        mock_class.return_value = client

        # Mock chat completion response
        mock_message = MagicMock()
        mock_message.content = "This is a mocked AI-generated transcript about the Eiffel Tower."

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        client.chat.completions.create.return_value = mock_response

        # Mock TTS response
        mock_audio = MagicMock()
        mock_audio.content = b"mock audio data"
        client.audio.speech.create.return_value = mock_audio

        yield client


@pytest.fixture
def mock_anthropic_client():
    """
    Mock Anthropic (Claude) client to avoid API calls during testing.

    Returns a MagicMock that simulates Anthropic API responses.
    """
    with patch('anthropic.Anthropic') as mock_class:
        # Create mock client instance
        client = MagicMock()
        mock_class.return_value = client

        # Mock message content
        mock_content_block = MagicMock()
        mock_content_block.text = "This is a mocked Claude-generated transcript about the Acropolis."

        # Mock message response
        mock_message = MagicMock()
        mock_message.content = [mock_content_block]

        client.messages.create.return_value = mock_message

        yield client


@pytest.fixture
def mock_google_genai():
    """
    Mock Google Generative AI (Gemini) to avoid API calls during testing.

    Returns a MagicMock that simulates Google Gemini API responses.
    """
    with patch('google.generativeai.configure') as mock_configure:
        with patch('google.generativeai.GenerativeModel') as mock_model_class:
            # Create mock model instance
            model = MagicMock()
            mock_model_class.return_value = model

            # Mock generation response
            mock_response = MagicMock()
            mock_response.text = "This is a mocked Gemini-generated transcript about the Colosseum."

            model.generate_content.return_value = mock_response

            yield model


@pytest.fixture
def sample_poi_metadata():
    """Sample POI metadata for testing"""
    return {
        "poi_id": "acropolis",
        "poi_name": "Acropolis",
        "city": "Athens",
        "metadata": {
            "coordinates": {
                "latitude": 37.9715,
                "longitude": 23.7267,
                "source": "google_maps_api",
                "collected_at": "2025-01-15T10:30:00Z"
            },
            "operation_hours": {
                "open_now": True,
                "weekday_text": [
                    "Monday: 8:00 AM – 8:00 PM",
                    "Tuesday: 8:00 AM – 8:00 PM"
                ]
            },
            "visit_info": {
                "indoor_outdoor": "outdoor",
                "typical_duration_minutes": 120,
                "accessibility": "Partial wheelchair access"
            },
            "address": "Athens 105 58, Greece",
            "phone": "+30 21 0321 4172",
            "website": "https://odysseus.culture.gr",
            "verified": True,
            "last_metadata_update": "2025-01-15T10:30:00Z"
        }
    }


@pytest.fixture
def sample_tour_data():
    """Sample tour/itinerary data for testing"""
    return {
        "itinerary": [
            {
                "day": 1,
                "pois": [
                    {
                        "poi": "Acropolis",
                        "poi_id": "acropolis",
                        "duration": 2.0,
                        "order": 1,
                        "estimated_hours": 2.0,
                        "period": "Classical",
                        "reason": "Iconic ancient citadel with Parthenon"
                    }
                ],
                "total_hours": 6.0,
                "total_walking_km": 2.5,
                "start_time": "09:00"
            }
        ],
        "optimization_scores": {
            "distance_score": 0.85,
            "coherence_score": 0.90,
            "overall_score": 0.875,
            "total_distance_km": 2.5
        },
        "constraints_violated": []
    }
