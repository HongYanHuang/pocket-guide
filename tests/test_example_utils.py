"""
Example unit tests for utils.py

This file demonstrates how to write unit tests with proper mocking.
Tests utility functions without making any external API calls.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from src.utils import (
    normalize_language_code,
    create_tour_id,
    get_language_name
)


class TestLanguageUtils:
    """Test language-related utility functions"""

    def test_normalize_language_code_en(self):
        """Test English language code normalization"""
        assert normalize_language_code('en') == 'en'
        assert normalize_language_code('EN') == 'en'
        assert normalize_language_code('english') == 'en'
        assert normalize_language_code('English') == 'en'

    def test_normalize_language_code_chinese(self):
        """Test Chinese language code normalization"""
        assert normalize_language_code('zh') == 'zh-cn'
        assert normalize_language_code('zh-cn') == 'zh-cn'
        assert normalize_language_code('zh-tw') == 'zh-tw'
        assert normalize_language_code('chinese') == 'zh-cn'

    def test_normalize_language_code_invalid(self):
        """Test invalid language code raises error"""
        with pytest.raises(ValueError, match="Unsupported language"):
            normalize_language_code('invalid-lang')

    def test_get_language_name_en(self):
        """Test getting language name for English"""
        assert get_language_name('en') == 'English'

    def test_get_language_name_zh_cn(self):
        """Test getting language name for Simplified Chinese"""
        assert get_language_name('zh-cn') == 'Simplified Chinese'

    def test_get_language_name_zh_tw(self):
        """Test getting language name for Traditional Chinese"""
        assert get_language_name('zh-tw') == 'Traditional Chinese'


class TestTourIdGeneration:
    """Test tour ID generation utilities"""

    @patch('src.utils.datetime')
    def test_create_tour_id_format(self, mock_datetime):
        """Test tour ID format is correct"""
        # Mock datetime to return consistent value
        mock_datetime.now.return_value.strftime.return_value = "20250115-123456"

        tour_id = create_tour_id('Athens')

        # Should be: city-tour-YYYYMMDD-HHMMSS-random
        assert tour_id.startswith('athens-tour-20250115-123456-')
        assert len(tour_id.split('-')) == 6  # city, tour, date, time, random, (maybe more)

    @patch('src.utils.random.choices')
    @patch('src.utils.datetime')
    def test_create_tour_id_randomness(self, mock_datetime, mock_random):
        """Test tour ID includes random component"""
        mock_datetime.now.return_value.strftime.return_value = "20250115-123456"
        mock_random.return_value = ['a', 'b', 'c', 'd', 'e', 'f']

        tour_id = create_tour_id('Rome')

        assert 'abcdef' in tour_id

    def test_create_tour_id_city_slug(self):
        """Test city name is properly slugified in tour ID"""
        tour_id = create_tour_id('New York')

        # City name should be lowercase and hyphenated
        assert tour_id.startswith('new-york-tour-')

    def test_create_tour_id_uniqueness(self):
        """Test that repeated calls generate unique IDs"""
        tour_ids = [create_tour_id('Paris') for _ in range(10)]

        # All IDs should be unique
        assert len(set(tour_ids)) == 10


# This is an example of how the tests should be structured
# Each test:
# 1. Tests a single function or behavior
# 2. Uses mocking to avoid external dependencies
# 3. Has a clear, descriptive name
# 4. Includes docstring explaining what it tests
# 5. Uses assertions to verify expected behavior
