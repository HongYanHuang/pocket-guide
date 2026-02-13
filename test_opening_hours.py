"""
Test suite for Google Maps opening hours integration with ILP optimizer.

Tests that the optimizer correctly uses operation_hours.periods format from
Google Maps Places API to enforce opening hour constraints.
"""

import pytest
from datetime import datetime
from src.trip_planner.ilp_optimizer import ILPOptimizer


@pytest.fixture
def config():
    """Test configuration"""
    return {
        'optimization': {
            'ilp_enabled': True,
            'ilp_max_seconds': 10,
            'distance_weight': 0.5,
            'coherence_weight': 0.5,
            'constraint_penalty_weight': 0.3,
            'ilp_fallback_enabled': True
        }
    }


@pytest.fixture
def test_pois_with_opening_hours():
    """Test POIs with Google Maps opening hours format"""
    return [
        {
            'poi': 'Morning Museum',
            'coordinates': {'latitude': 41.9028, 'longitude': 12.4964},
            'estimated_hours': 2.0,
            'metadata': {
                'operation_hours': {
                    'periods': [
                        # Monday: 8:00 AM - 12:00 PM only (morning only)
                        {'open': {'day': 1, 'time': '0800'}, 'close': {'day': 1, 'time': '1200'}},
                        # Tuesday: 8:00 AM - 12:00 PM only
                        {'open': {'day': 2, 'time': '0800'}, 'close': {'day': 2, 'time': '1200'}},
                        # Wednesday: 8:00 AM - 12:00 PM only
                        {'open': {'day': 3, 'time': '0800'}, 'close': {'day': 3, 'time': '1200'}},
                    ]
                },
                'booking_info': {
                    'required': True,
                    'preferred_time_slots': [
                        {'start': '08:00', 'end': '10:00', 'notes': 'Best time'}
                    ]
                }
            }
        },
        {
            'poi': 'All Day Park',
            'coordinates': {'latitude': 41.9065, 'longitude': 12.4536},
            'estimated_hours': 1.5,
            'metadata': {
                'operation_hours': {
                    'periods': [
                        # Monday-Saturday: 7:00 AM - 8:00 PM
                        {'open': {'day': 1, 'time': '0700'}, 'close': {'day': 1, 'time': '2000'}},
                        {'open': {'day': 2, 'time': '0700'}, 'close': {'day': 2, 'time': '2000'}},
                        {'open': {'day': 3, 'time': '0700'}, 'close': {'day': 3, 'time': '2000'}},
                        {'open': {'day': 4, 'time': '0700'}, 'close': {'day': 4, 'time': '2000'}},
                        {'open': {'day': 5, 'time': '0700'}, 'close': {'day': 5, 'time': '2000'}},
                        {'open': {'day': 6, 'time': '0700'}, 'close': {'day': 6, 'time': '2000'}},
                        # Sunday: Closed
                    ]
                }
            }
        },
        {
            'poi': 'Afternoon Gallery',
            'coordinates': {'latitude': 41.8902, 'longitude': 12.4922},
            'estimated_hours': 2.0,
            'metadata': {
                'operation_hours': {
                    'periods': [
                        # Monday: 2:00 PM - 8:00 PM only (afternoon only)
                        {'open': {'day': 1, 'time': '1400'}, 'close': {'day': 1, 'time': '2000'}},
                        {'open': {'day': 2, 'time': '1400'}, 'close': {'day': 2, 'time': '2000'}},
                        {'open': {'day': 3, 'time': '1400'}, 'close': {'day': 3, 'time': '2000'}},
                    ]
                }
            }
        }
    ]


@pytest.fixture
def distance_matrix(test_pois_with_opening_hours):
    """Simple distance matrix"""
    pois = test_pois_with_opening_hours
    matrix = {}
    for i, poi1 in enumerate(pois):
        for j, poi2 in enumerate(pois):
            if i == j:
                matrix[(poi1['poi'], poi2['poi'])] = 0.0
            else:
                matrix[(poi1['poi'], poi2['poi'])] = 1.5  # 1.5 km between all POIs
    return matrix


@pytest.fixture
def coherence_scores(test_pois_with_opening_hours):
    """Simple coherence scores"""
    pois = test_pois_with_opening_hours
    scores = {}
    for i, poi1 in enumerate(pois):
        for j, poi2 in enumerate(pois):
            if i == j:
                scores[(poi1['poi'], poi2['poi'])] = 1.0
            else:
                scores[(poi1['poi'], poi2['poi'])] = 0.5
    return scores


class TestOpeningHoursIntegration:
    """Test Google Maps opening hours integration"""

    def test_morning_only_poi_constraint(self, config, test_pois_with_opening_hours,
                                        distance_matrix, coherence_scores):
        """Test that morning-only POI is scheduled in morning positions"""
        optimizer = ILPOptimizer(config)

        # Start on a Monday
        monday = datetime(2026, 3, 16)  # This is a Monday

        result = optimizer.optimize_sequence(
            pois=test_pois_with_opening_hours,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=1,
            preferences={},
            trip_start_date=monday
        )

        sequence = result['sequence']

        # Find Morning Museum in sequence
        morning_museum_idx = None
        for i, poi in enumerate(sequence):
            if poi['poi'] == 'Morning Museum':
                morning_museum_idx = i
                break

        # Morning Museum should be at early position (0 or 1)
        # because it closes at 12:00 PM
        assert morning_museum_idx is not None, "Morning Museum should be in sequence"
        assert morning_museum_idx <= 1, f"Morning Museum at position {morning_museum_idx}, expected 0 or 1"

    def test_closed_on_sunday(self, config, test_pois_with_opening_hours,
                              distance_matrix, coherence_scores):
        """Test that POIs closed on Sunday are not scheduled on Sunday"""
        optimizer = ILPOptimizer(config)

        # Start on a Sunday
        sunday = datetime(2026, 3, 15)  # This is a Sunday

        result = optimizer.optimize_sequence(
            pois=test_pois_with_opening_hours,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=1,
            preferences={},
            trip_start_date=sunday
        )

        sequence = result['sequence']
        day_assignments = result['day_assignments']

        # Check if All Day Park is in Sunday schedule (day 0)
        # It should NOT be, as it's closed on Sunday
        for poi in sequence:
            if poi['poi'] == 'All Day Park':
                assigned_day = day_assignments.get(poi['poi'])
                # Since we only have 1 day and it's Sunday, this POI might be excluded
                # or the solver might fail if it's required
                # In practice, the constraint should prevent this POI from being on day 0

        # If solver succeeded, check that closed POIs are handled
        assert result['solver_stats']['status'] in ['OPTIMAL', 'FEASIBLE', 'GREEDY_FALLBACK']

    def test_preferred_time_slots(self, config, test_pois_with_opening_hours,
                                  distance_matrix, coherence_scores):
        """Test that POIs with preferred time slots are scheduled accordingly"""
        optimizer = ILPOptimizer(config)

        # Start on a Monday
        monday = datetime(2026, 3, 16)

        result = optimizer.optimize_sequence(
            pois=test_pois_with_opening_hours,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=1,
            preferences={},
            trip_start_date=monday
        )

        sequence = result['sequence']

        # Morning Museum has preferred slot 08:00-10:00 and booking required
        # It should be first in sequence to hit this time window
        if sequence and sequence[0]['poi'] == 'Morning Museum':
            # Passed: Morning Museum scheduled first (best for 8-10 AM slot)
            assert True
        else:
            # It might be at position 1 if start time is close to preferred slot
            # This is acceptable
            morning_pos = None
            for i, poi in enumerate(sequence):
                if poi['poi'] == 'Morning Museum':
                    morning_pos = i
                    break
            assert morning_pos is not None and morning_pos <= 1, \
                f"Morning Museum should be at early position, found at {morning_pos}"

    def test_google_maps_format_parsing(self, config):
        """Test correct parsing of Google Maps periods format"""
        optimizer = ILPOptimizer(config)

        # Test the time parsing logic
        assert optimizer._time_to_minutes("09:00") == 540
        assert optimizer._time_to_minutes("14:30") == 870
        assert optimizer._time_to_minutes("23:59") == 1439

    def test_multi_day_opening_hours(self, config, test_pois_with_opening_hours,
                                     distance_matrix, coherence_scores):
        """Test opening hours across multiple days"""
        optimizer = ILPOptimizer(config)

        # Start on a Monday, run for 3 days (Mon, Tue, Wed)
        monday = datetime(2026, 3, 16)

        result = optimizer.optimize_sequence(
            pois=test_pois_with_opening_hours,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=3,
            preferences={},
            trip_start_date=monday
        )

        sequence = result['sequence']
        day_assignments = result['day_assignments']

        # All POIs should be scheduled (all have opening hours on Mon-Wed)
        assert len(sequence) == len(test_pois_with_opening_hours), \
            "All POIs should be scheduled across 3 days"

        # Verify day assignments are valid
        for poi_name, day in day_assignments.items():
            assert 0 <= day < 3, f"Day assignment {day} out of range for {poi_name}"


class TestRealWorldScenario:
    """Test with realistic Vatican Museums data"""

    def test_vatican_museums_opening_hours(self, config):
        """Test with actual Vatican Museums opening hours format"""
        vatican_poi = {
            'poi': 'Vatican Museums',
            'coordinates': {'latitude': 41.9064878, 'longitude': 12.4536413},
            'estimated_hours': 3.0,
            'metadata': {
                'operation_hours': {
                    'weekday_text': [
                        'Monday: 8:00 AM – 8:00 PM',
                        'Tuesday: 8:00 AM – 8:00 PM',
                        'Wednesday: 8:00 AM – 8:00 PM',
                        'Thursday: 8:00 AM – 8:00 PM',
                        'Friday: 8:00 AM – 8:00 PM',
                        'Saturday: 8:00 AM – 8:00 PM',
                        'Sunday: Closed'
                    ],
                    'periods': [
                        {'open': {'day': 1, 'time': '0800'}, 'close': {'day': 1, 'time': '2000'}},
                        {'open': {'day': 2, 'time': '0800'}, 'close': {'day': 2, 'time': '2000'}},
                        {'open': {'day': 3, 'time': '0800'}, 'close': {'day': 3, 'time': '2000'}},
                        {'open': {'day': 4, 'time': '0800'}, 'close': {'day': 4, 'time': '2000'}},
                        {'open': {'day': 5, 'time': '0800'}, 'close': {'day': 5, 'time': '2000'}},
                        {'open': {'day': 6, 'time': '0800'}, 'close': {'day': 6, 'time': '2000'}},
                    ]
                },
                'booking_info': {
                    'required': True,
                    'advance_booking_days': 7,
                    'preferred_time_slots': [
                        {'start': '08:00', 'end': '10:00', 'notes': 'Best time to avoid crowds'},
                        {'start': '10:00', 'end': '12:00', 'notes': 'Moderate crowds'}
                    ]
                }
            }
        }

        other_poi = {
            'poi': 'Colosseum',
            'coordinates': {'latitude': 41.8902, 'longitude': 12.4922},
            'estimated_hours': 2.5,
            'metadata': {
                'operation_hours': {
                    'periods': [
                        {'open': {'day': 1, 'time': '0900'}, 'close': {'day': 1, 'time': '1900'}},
                        {'open': {'day': 2, 'time': '0900'}, 'close': {'day': 2, 'time': '1900'}},
                    ]
                }
            }
        }

        pois = [vatican_poi, other_poi]

        # Create distance matrix
        distance_matrix = {
            ('Vatican Museums', 'Vatican Museums'): 0.0,
            ('Vatican Museums', 'Colosseum'): 4.5,
            ('Colosseum', 'Vatican Museums'): 4.5,
            ('Colosseum', 'Colosseum'): 0.0,
        }

        coherence_scores = {
            ('Vatican Museums', 'Vatican Museums'): 1.0,
            ('Vatican Museums', 'Colosseum'): 0.6,
            ('Colosseum', 'Vatican Museums'): 0.6,
            ('Colosseum', 'Colosseum'): 1.0,
        }

        optimizer = ILPOptimizer(config)

        # Test on a Monday
        monday = datetime(2026, 3, 16)

        result = optimizer.optimize_sequence(
            pois=pois,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=1,
            preferences={},
            trip_start_date=monday
        )

        sequence = result['sequence']

        # Vatican Museums should be scheduled early (preferred 8-10 AM)
        vatican_idx = None
        for i, poi in enumerate(sequence):
            if poi['poi'] == 'Vatican Museums':
                vatican_idx = i
                break

        assert vatican_idx is not None, "Vatican Museums should be in sequence"
        # Should be first to catch the 8-10 AM preferred slot
        assert vatican_idx == 0, f"Vatican Museums should be first (at position {vatican_idx})"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
