# Unit Tests for Pocket Guide

This directory contains comprehensive unit tests for the Pocket Guide backend and API layers.

## Quick Start

### Install Test Dependencies

```bash
# Install all development dependencies including test tools
pip install -r requirements-dev.txt
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_example_utils.py

# Run tests matching a pattern
pytest -k "test_language"

# Run with verbose output
pytest -v -s

# Run only unit tests (skip integration if they exist)
pytest -m unit
```

### View Coverage Report

After running tests with coverage, open the HTML report:

```bash
# Coverage report will be in htmlcov/index.html
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

## Directory Structure

```
tests/
├── README.md                   # This file
├── conftest.py                 # Shared fixtures and test configuration
├── test_example_utils.py       # Example: Testing utility functions
├── test_example_api.py         # Example: Testing API endpoints
│
├── fixtures/                   # (To be created) Test data and fixtures
│   ├── ai_responses.py        # Mocked AI API responses
│   ├── research_data.py       # Sample research YAML data
│   └── poi_data.py            # Sample POI metadata
│
├── unit/                      # (To be created) Unit tests
│   ├── test_utils.py
│   ├── test_content_generator.py
│   ├── test_api_models.py
│   ├── agents/
│   │   ├── test_research_agent.py
│   │   ├── test_verification_agent.py
│   │   └── ...
│   └── trip_planner/
│       ├── test_tour_manager.py
│       └── ...
│
└── api/                       # (To be created) API endpoint tests
    └── test_api_server.py
```

## Testing Philosophy

### Core Principles

1. **No AI API Calls**: All AI provider calls (OpenAI, Anthropic, Google) are mocked to avoid costs
2. **Fast Execution**: Full test suite should run in < 30 seconds
3. **Isolated Tests**: Each test is independent and can run in any order
4. **Realistic Fixtures**: Use real output files as test data when possible
5. **High Coverage**: Target 90%+ code coverage for critical components

### Mocking Strategy

All external dependencies are mocked:

- **AI Providers**: OpenAI, Anthropic (Claude), Google (Gemini)
- **Google Maps API**: Distance Matrix, Places API
- **TTS Services**: OpenAI TTS, Google TTS, Edge TTS
- **File System**: Use temporary directories or mock file operations
- **Network Calls**: Mock all HTTP requests

### Example Test Pattern

```python
def test_feature_with_mocking(mock_openai_client, sample_config):
    """Test description explaining what this test verifies"""
    # Arrange: Set up test data and mocks
    config = sample_config
    mock_openai_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Mocked response"))]
    )

    # Act: Execute the code being tested
    result = some_function(config)

    # Assert: Verify expected behavior
    assert result is not None
    assert "expected value" in result
    mock_openai_client.chat.completions.create.assert_called_once()
```

## Available Fixtures

### Configuration Fixtures

- `sample_config`: Complete configuration dict without loading config.yaml

### AI Provider Mocks

- `mock_openai_client`: Mocked OpenAI client
- `mock_anthropic_client`: Mocked Anthropic (Claude) client
- `mock_google_genai`: Mocked Google Gemini client

### Test Data

- `sample_poi_metadata`: Sample POI metadata structure
- `sample_tour_data`: Sample tour/itinerary data
- `sample_research_data`: Sample research YAML structure (to be added)

## Writing New Tests

### 1. Choose the Right Location

- `tests/unit/` - For testing individual functions/classes
- `tests/api/` - For testing API endpoints
- `tests/integration/` - For end-to-end tests (use sparingly)

### 2. Use Fixtures

Always use fixtures from `conftest.py` for common test data:

```python
def test_my_function(sample_config, mock_openai_client):
    # Test using fixtures
    pass
```

### 3. Mock External Calls

Never let tests make real API calls:

```python
from unittest.mock import patch

@patch('src.content_generator.openai.OpenAI')
def test_content_generation(mock_openai):
    # Configure mock
    mock_openai.return_value.chat.completions.create.return_value = ...

    # Run test
    pass
```

### 4. Name Tests Clearly

Use descriptive names that explain what is being tested:

```python
def test_normalize_language_code_handles_chinese_variants():
    """Test that zh, zh-cn, and zh-tw are all normalized correctly"""
    assert normalize_language_code('zh') == 'zh-cn'
    assert normalize_language_code('zh-cn') == 'zh-cn'
    assert normalize_language_code('zh-tw') == 'zh-tw'
```

### 5. Test Both Success and Failure Cases

```python
def test_function_success():
    """Test the happy path"""
    result = my_function(valid_input)
    assert result == expected_output

def test_function_raises_error_on_invalid_input():
    """Test error handling"""
    with pytest.raises(ValueError):
        my_function(invalid_input)
```

## Test Markers

Use markers to categorize tests:

```python
import pytest

@pytest.mark.unit
def test_pure_logic():
    """Fast unit test with full mocking"""
    pass

@pytest.mark.integration
def test_with_real_services():
    """Slower test that may use real services"""
    pass

@pytest.mark.slow
def test_expensive_operation():
    """Test that takes a long time"""
    pass
```

Run specific categories:

```bash
# Run only unit tests
pytest -m unit

# Run everything except slow tests
pytest -m "not slow"
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running pytest from the project root:

```bash
cd /path/to/pocket-guide
pytest
```

### Missing Dependencies

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

### Mocks Not Working

Make sure you're patching at the right location. Patch where the function is used, not where it's defined:

```python
# If content_generator.py does: from openai import OpenAI
# Patch at the usage location:
@patch('src.content_generator.OpenAI')
def test_function(mock_openai):
    pass
```

## Next Steps

1. Review the test plan in `UNIT_TEST_PLAN.md`
2. Run the example tests to verify setup works
3. Gradually implement tests following the priority order in the plan
4. Aim for 90%+ coverage
5. Integrate tests into CI/CD pipeline

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
