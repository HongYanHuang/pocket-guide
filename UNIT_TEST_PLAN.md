# Unit Test Plan for Pocket Guide

## Overview

This document outlines a comprehensive unit testing strategy for the Pocket Guide backend and API layers. The goal is to ensure program reliability and prevent failures while avoiding expensive AI API calls during testing.

## Executive Summary

- **Current State**: No formal test framework, existing tests call real AI APIs
- **Goal**: 100% unit test coverage for backend/API with mocked AI calls
- **Approach**: pytest framework + fixtures + comprehensive mocking
- **Priority**: High-value components first, then comprehensive coverage

## Testing Strategy

### 1. Test Framework Setup

**Framework**: pytest with the following plugins:
- `pytest` - Core testing framework
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `pytest-asyncio` - Async test support (for FastAPI)
- `httpx` - FastAPI test client

**Directory Structure**:
```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
├── fixtures/                   # Mock data and fixtures
│   ├── __init__.py
│   ├── ai_responses.py        # Mocked AI API responses
│   ├── research_data.py       # Sample research YAML data
│   ├── tour_data.py           # Sample tour/itinerary data
│   └── poi_data.py            # Sample POI metadata
├── unit/                      # Unit tests
│   ├── __init__.py
│   ├── test_content_generator.py
│   ├── test_utils.py
│   ├── test_api_models.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── test_research_agent.py
│   │   ├── test_poi_research_agent.py
│   │   ├── test_poi_metadata_agent.py
│   │   ├── test_verification_agent.py
│   │   ├── test_insertion_agent.py
│   │   └── test_diagnosis_agent.py
│   ├── trip_planner/
│   │   ├── __init__.py
│   │   ├── test_tour_manager.py
│   │   ├── test_poi_selector_agent.py
│   │   └── test_itinerary_optimizer.py
│   └── services/
│       ├── __init__.py
│       ├── test_google_maps_service.py
│       └── test_tts_generator.py
├── api/                       # API tests
│   ├── __init__.py
│   └── test_api_server.py
└── integration/               # Integration tests (optional, lower priority)
    ├── __init__.py
    └── test_end_to_end.py
```

### 2. Mocking Strategy for AI APIs

**Problem**: AI API calls are expensive and unpredictable for testing.

**Solution**: Comprehensive mocking with realistic fixtures.

#### AI Provider Mocking Approach

```python
# tests/fixtures/ai_responses.py

# OpenAI mock responses
OPENAI_TRANSCRIPT_RESPONSE = {
    "choices": [{
        "message": {
            "content": "Welcome to the Eiffel Tower... [realistic transcript]"
        }
    }]
}

# Anthropic (Claude) mock responses
ANTHROPIC_TRANSCRIPT_RESPONSE = {
    "content": [{
        "text": "Welcome to the Acropolis... [realistic transcript]"
    }]
}

# Google (Gemini) mock responses
GEMINI_TRANSCRIPT_RESPONSE = {
    "candidates": [{
        "content": {
            "parts": [{
                "text": "Welcome to the Colosseum... [realistic transcript]"
            }]
        }
    }]
}

# POI Selector responses
POI_SELECTION_RESPONSE = {
    "starting_pois": [
        {"poi": "Acropolis", "reason": "Iconic ancient site"},
        {"poi": "Parthenon", "reason": "Architectural masterpiece"}
    ],
    "backup_pois": {
        "Acropolis": [{"poi": "Ancient Agora", "reason": "Alternative"}]
    },
    "rejected_pois": [
        {"poi": "Random Site", "reason": "Not relevant"}
    ]
}
```

#### Mock Implementation Pattern

```python
# conftest.py
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client to avoid API calls"""
    with patch('openai.OpenAI') as mock:
        client = MagicMock()
        mock.return_value = client

        # Mock chat completion
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content="Mocked transcript content")
            )]
        )

        yield client

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client to avoid API calls"""
    with patch('anthropic.Anthropic') as mock:
        client = MagicMock()
        mock.return_value = client

        # Mock message creation
        client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Mocked transcript content")]
        )

        yield client

@pytest.fixture
def mock_google_client():
    """Mock Google Gemini client to avoid API calls"""
    with patch('google.generativeai.GenerativeModel') as mock:
        model = MagicMock()
        mock.return_value = model

        # Mock generate_content
        response = MagicMock()
        response.text = "Mocked transcript content"
        model.generate_content.return_value = response

        yield model
```

### 3. Using Existing Output Files as Test Fixtures

**Available Fixtures**:
- `examples/arch-of-galerius-gold-standard.txt` - Gold standard transcript
- Existing test output files can be captured and reused

**Fixture Creation Strategy**:

```python
# tests/fixtures/research_data.py
import yaml
from pathlib import Path

def load_sample_research():
    """Load a real research YAML file for testing"""
    # We'll create sample YAML based on project structure
    return {
        'poi': {
            'name': 'Arch of Galerius',
            'city': 'Thessaloniki',
            'basic_info': {
                'period': 'Roman Imperial',
                'date_built': '297-303 AD',
                'current_state': 'Partially preserved',
                'description': 'Triumphal arch commemorating victory'
            },
            'people': [
                {
                    'name': 'Galerius',
                    'role': 'Roman Emperor',
                    'personality': 'Military leader, started as shepherd'
                }
            ],
            'events': [
                {
                    'name': 'Battle against Persians',
                    'date': '298 AD',
                    'significance': 'Major victory'
                }
            ]
        }
    }

def load_gold_standard_transcript():
    """Load the gold standard example transcript"""
    example_path = Path(__file__).parent.parent.parent / 'examples' / 'arch-of-galerius-gold-standard.txt'
    if example_path.exists():
        return example_path.read_text()
    return "Mock gold standard transcript..."
```

### 4. Component Test Coverage Plan

#### Priority 1: Core Backend Components (Week 1)

**A. `utils.py` - Utility Functions**
- Test coverage: 100%
- Tests needed:
  - File path operations (normalize, create directories)
  - Language code normalization
  - Tour ID generation
  - Metadata loading/saving
  - Version management functions

**B. `api_models.py` - Pydantic Models**
- Test coverage: 100%
- Tests needed:
  - Model validation (valid data)
  - Model validation (invalid data - should raise errors)
  - Field constraints (latitude/longitude ranges, etc.)
  - Optional field handling
  - Serialization/deserialization

**C. `content_generator.py` - Content Generation**
- Test coverage: 90%+ (mock all AI calls)
- Tests needed:
  - Module detection logic (without AI)
  - Research data loading
  - Prompt construction
  - Verification flow (mocked)
  - SSML generation
  - File saving operations
  - **Critical**: Mock all `openai`, `anthropic`, `google.generativeai` calls

#### Priority 2: Agent Layer (Week 2)

**D. Research Agents**
- `research_agent.py`: Research orchestration logic
- `poi_research_agent.py`: POI-specific research
- Tests needed:
  - Research data parsing
  - Knowledge graph construction (without AI)
  - File I/O operations
  - **Mock**: All AI API calls for recursive research

**E. Verification Agents**
- `verification_agent.py`: Coverage verification
- `insertion_agent.py`: Content insertion
- `diagnosis_agent.py`: Issue diagnosis
- Tests needed:
  - Coverage calculation (pure logic, no AI)
  - Similarity scoring
  - Insertion point detection
  - Diagnostic logic
  - **Mock**: AI calls in insertion agent

**F. Metadata Agent**
- `poi_metadata_agent.py`: POI metadata management
- Tests needed:
  - Metadata parsing
  - Validation logic
  - File operations
  - **Mock**: Google Maps API calls

#### Priority 3: Trip Planner (Week 3)

**G. `tour_manager.py`**
- Test coverage: 100%
- Tests needed:
  - Tour saving (versioning logic)
  - Metadata tracking
  - Transcript linking
  - File organization
  - **No AI mocking needed** - pure data management

**H. `poi_selector_agent.py`**
- Test coverage: 90%
- Tests needed:
  - Selection logic structure
  - Backup POI generation structure
  - Rejection reasoning structure
  - **Mock**: All AI API calls for selection decisions

**I. `itinerary_optimizer.py`**
- Test coverage: 90%
- Tests needed:
  - Optimization algorithm logic
  - Distance calculation
  - Coherence scoring
  - Constraint validation
  - **Mock**: AI calls for optimization decisions

#### Priority 4: Services (Week 3)

**J. `google_maps_service.py`**
- Test coverage: 85%
- Tests needed:
  - Distance matrix parsing
  - Coordinate validation
  - Error handling
  - **Mock**: All Google Maps API calls with realistic responses

**K. `tts_generator.py`**
- Test coverage: 80%
- Tests needed:
  - SSML parsing
  - Audio file generation flow
  - Provider selection logic
  - **Mock**: OpenAI TTS, Google TTS, Edge TTS calls

#### Priority 5: API Layer (Week 4)

**L. `api_server.py` - FastAPI Endpoints**
- Test coverage: 95%
- Tests needed:
  - All GET endpoints (cities, POIs, tours, transcripts)
  - All POST endpoints (recollect, recalculate)
  - All PUT endpoints (metadata updates, transcript updates)
  - Error handling (404, 500, etc.)
  - CORS handling
  - Response models
  - **Mock**: All backend agent calls and file I/O

**Test Pattern for API**:
```python
from fastapi.testclient import TestClient
from src.api_server import app

def test_list_cities(mock_content_dir):
    """Test GET /cities endpoint"""
    client = TestClient(app)
    response = client.get("/cities")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    # ... more assertions

def test_get_poi_metadata(mock_poi_data):
    """Test GET /pois/{city}/{poi_id} endpoint"""
    client = TestClient(app)
    response = client.get("/pois/athens/acropolis")

    assert response.status_code == 200
    data = response.json()
    assert data['poi_id'] == 'acropolis'
    assert 'metadata' in data
```

### 5. Test Data Management

**Approach**: Create reusable fixtures based on real data

**Sample Fixtures to Create**:

```python
# tests/fixtures/poi_data.py

SAMPLE_POI_METADATA = {
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
        "verified": True
    }
}

SAMPLE_TOUR_DATA = {
    "tour_id": "athens-tour-20250115-123456-abc123",
    "city": "Athens",
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
                    "reason": "Iconic ancient site"
                }
            ],
            "total_hours": 6.0,
            "total_walking_km": 3.5,
            "start_time": "09:00"
        }
    ],
    "optimization_scores": {
        "distance_score": 0.85,
        "coherence_score": 0.90,
        "overall_score": 0.875,
        "total_distance_km": 3.5
    }
}
```

### 6. Implementation Phases

**Phase 1: Setup (3-4 hours)**
- Install pytest and plugins
- Create tests/ directory structure
- Set up conftest.py with base fixtures
- Create initial mock data files

**Phase 2: Core Tests (8-10 hours)**
- Test utils.py (all utility functions)
- Test api_models.py (all Pydantic models)
- Create comprehensive AI mocking fixtures

**Phase 3: Backend Agent Tests (12-16 hours)**
- Test all agent files with mocked AI
- Test content_generator.py
- Test research agents
- Test verification agents

**Phase 4: Trip Planner Tests (8-10 hours)**
- Test tour_manager.py
- Test poi_selector_agent.py
- Test itinerary_optimizer.py

**Phase 5: Service & API Tests (8-12 hours)**
- Test google_maps_service.py
- Test tts_generator.py
- Test all API endpoints in api_server.py

**Phase 6: Integration & Coverage (4-6 hours)**
- Run coverage reports
- Fill gaps to reach 90%+ coverage
- Add integration tests for critical paths

**Total Estimate**: 45-60 hours of development

### 7. Running Tests

**Commands**:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/unit/test_utils.py

# Run tests matching pattern
pytest -k "test_content_generator"

# Run tests with output
pytest -v -s

# Run only unit tests (skip integration)
pytest tests/unit/
```

**Coverage Goals**:
- Overall: 90%+ coverage
- Critical components (utils, api_models, tour_manager): 100%
- AI-dependent components: 85%+ (focus on non-AI logic)

### 8. Continuous Integration

**GitHub Actions Workflow** (`.github/workflows/test.yml`):
```yaml
name: Unit Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-mock pytest-asyncio httpx

    - name: Run tests with coverage
      run: |
        pytest --cov=src --cov-report=xml --cov-report=term

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Success Criteria

1. ✅ All unit tests run in < 30 seconds (no real API calls)
2. ✅ 90%+ code coverage across backend and API
3. ✅ All AI API calls properly mocked
4. ✅ Tests use existing output files as fixtures where possible
5. ✅ CI/CD pipeline runs tests automatically
6. ✅ Zero test failures on main branch
7. ✅ Clear documentation for adding new tests

## Key Benefits

1. **Cost Savings**: No expensive AI API calls during testing
2. **Speed**: Fast test execution (< 30 seconds for full suite)
3. **Reliability**: Consistent, reproducible test results
4. **Confidence**: High coverage prevents regressions
5. **Documentation**: Tests serve as usage examples
6. **CI/CD Ready**: Automated testing on every commit

## Next Steps

1. Get approval for this plan
2. Create initial test framework setup
3. Implement Priority 1 tests (utils, api_models)
4. Gradually expand coverage following priority order
5. Integrate into CI/CD pipeline
6. Document testing best practices for future contributors

## Appendix: Dependencies to Add

Add to `requirements.txt`:
```
# Testing dependencies
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-mock>=3.11.0,<4.0.0
pytest-asyncio>=0.21.0,<1.0.0
httpx>=0.24.0,<1.0.0  # For FastAPI testing
```

Or create separate `requirements-dev.txt`:
```
-r requirements.txt
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-mock>=3.11.0,<4.0.0
pytest-asyncio>=0.21.0,<1.0.0
httpx>=0.24.0,<1.0.0
```
