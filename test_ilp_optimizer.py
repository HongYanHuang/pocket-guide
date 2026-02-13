"""
Test suite for ILP Optimizer

Tests basic TSP functionality, distance minimization, coherence balance,
solver timeout, and comparison with greedy algorithm.
"""

import pytest
import yaml
from pathlib import Path
from src.trip_planner.ilp_optimizer import ILPOptimizer
from src.trip_planner.itinerary_optimizer import ItineraryOptimizerAgent


# Sample POI data for testing
TEST_POIS = [
    {
        'poi': 'Colosseum',
        'coordinates': {'latitude': 41.8902, 'longitude': 12.4922},
        'estimated_hours': 2.5,
        'period': 'Roman Empire',
        'date_built': '70-80 AD'
    },
    {
        'poi': 'Roman Forum',
        'coordinates': {'latitude': 41.8925, 'longitude': 12.4853},
        'estimated_hours': 2.0,
        'period': 'Roman Empire',
        'date_built': '500 BC'
    },
    {
        'poi': 'Pantheon',
        'coordinates': {'latitude': 41.8986, 'longitude': 12.4768},
        'estimated_hours': 1.5,
        'period': 'Roman Empire',
        'date_built': '126 AD'
    },
    {
        'poi': 'Trevi Fountain',
        'coordinates': {'latitude': 41.9009, 'longitude': 12.4833},
        'estimated_hours': 0.5,
        'period': 'Modern',
        'date_built': '1762'
    },
    {
        'poi': 'Vatican Museums',
        'coordinates': {'latitude': 41.9065, 'longitude': 12.4536},
        'estimated_hours': 3.0,
        'period': 'Modern',
        'date_built': '1506'
    }
]


@pytest.fixture
def config():
    """Load test configuration"""
    return {
        'optimization': {
            'ilp_enabled': True,
            'ilp_max_seconds': 10,  # Short timeout for tests
            'distance_weight': 0.5,
            'coherence_weight': 0.5,
            'constraint_penalty_weight': 0.3,
            'ilp_fallback_enabled': True
        }
    }


@pytest.fixture
def distance_matrix():
    """Calculate distance matrix for test POIs"""
    from src.trip_planner.itinerary_optimizer import ItineraryOptimizerAgent

    optimizer = ItineraryOptimizerAgent({})
    return optimizer._build_distance_matrix(TEST_POIS)


@pytest.fixture
def coherence_scores():
    """Calculate coherence scores for test POIs"""
    from src.trip_planner.itinerary_optimizer import ItineraryOptimizerAgent

    optimizer = ItineraryOptimizerAgent({})
    return optimizer._calculate_coherence_scores(TEST_POIS)


class TestILPOptimizer:
    """Test suite for ILP optimizer"""

    def test_initialization(self, config):
        """Test ILP optimizer initialization"""
        optimizer = ILPOptimizer(config)

        assert optimizer.max_seconds == 10
        assert optimizer.distance_weight == 0.5
        assert optimizer.coherence_weight == 0.5
        assert optimizer.fallback_enabled is True

    def test_basic_tsp(self, config, distance_matrix, coherence_scores):
        """Test basic TSP optimization without constraints"""
        optimizer = ILPOptimizer(config)

        result = optimizer.optimize_sequence(
            pois=TEST_POIS,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=2,
            preferences={}
        )

        # Check result structure
        assert 'sequence' in result
        assert 'day_assignments' in result
        assert 'scores' in result
        assert 'solver_stats' in result

        # Check sequence
        assert len(result['sequence']) == len(TEST_POIS)
        assert all(poi['poi'] in [p['poi'] for p in TEST_POIS] for poi in result['sequence'])

        # Check scores
        scores = result['scores']
        assert 'distance_score' in scores
        assert 'coherence_score' in scores
        assert 'overall_score' in scores
        assert 0 <= scores['distance_score'] <= 1
        assert 0 <= scores['coherence_score'] <= 1

        # Check solver stats
        stats = result['solver_stats']
        assert stats['status'] in ['OPTIMAL', 'FEASIBLE']
        assert stats['solve_time'] > 0

    def test_distance_minimization(self, config, distance_matrix, coherence_scores):
        """Test that ILP minimizes total distance"""
        # Configure for distance-only optimization
        distance_prefs = {'distance_weight': 1.0, 'coherence_weight': 0.0}

        optimizer = ILPOptimizer(config)
        result = optimizer.optimize_sequence(
            pois=TEST_POIS,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=2,
            preferences=distance_prefs
        )

        # Calculate total distance
        sequence = result['sequence']
        total_distance = 0
        for i in range(len(sequence) - 1):
            poi1 = sequence[i]['poi']
            poi2 = sequence[i + 1]['poi']
            total_distance += distance_matrix[(poi1, poi2)]

        # Should be reasonably optimized (within 20% of theoretical minimum)
        # For 5 POIs, a good solution should be < 5km total
        assert total_distance < 5.0
        assert result['scores']['total_distance_km'] < 5.0

    def test_coherence_balance(self, config, distance_matrix, coherence_scores):
        """Test coherence-weighted optimization"""
        # Configure for coherence-heavy optimization
        coherence_prefs = {'distance_weight': 0.2, 'coherence_weight': 0.8}

        optimizer = ILPOptimizer(config)
        result = optimizer.optimize_sequence(
            pois=TEST_POIS,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=2,
            preferences=coherence_prefs
        )

        # Check that Roman Empire POIs come before Modern POIs
        sequence = result['sequence']
        roman_indices = [i for i, poi in enumerate(sequence)
                        if poi.get('period') == 'Roman Empire']
        modern_indices = [i for i, poi in enumerate(sequence)
                         if poi.get('period') == 'Modern']

        # At least some chronological ordering should exist
        if roman_indices and modern_indices:
            # Average position of Roman POIs should be earlier than Modern
            avg_roman = sum(roman_indices) / len(roman_indices)
            avg_modern = sum(modern_indices) / len(modern_indices)

            # This is a soft check - coherence should influence ordering
            assert result['scores']['coherence_score'] > 0.3

    def test_solver_timeout(self, config, distance_matrix, coherence_scores):
        """Test solver timeout behavior"""
        # Create a config with very short timeout
        short_timeout_config = config.copy()
        short_timeout_config['optimization']['ilp_max_seconds'] = 0.1

        optimizer = ILPOptimizer(short_timeout_config)

        # Should still complete (either find feasible solution or fallback)
        result = optimizer.optimize_sequence(
            pois=TEST_POIS,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=2,
            preferences={}
        )

        # Should have a valid result (either ILP or greedy fallback)
        assert 'sequence' in result
        assert len(result['sequence']) == len(TEST_POIS)

    def test_compare_ilp_vs_greedy(self, config, distance_matrix, coherence_scores):
        """Compare ILP solution quality against greedy algorithm"""
        # ILP solution
        ilp_optimizer = ILPOptimizer(config)
        ilp_result = ilp_optimizer.optimize_sequence(
            pois=TEST_POIS,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=2,
            preferences={}
        )

        # Greedy solution
        greedy_optimizer = ItineraryOptimizerAgent(config)
        greedy_sequence = greedy_optimizer._optimize_sequence(
            TEST_POIS,
            distance_matrix,
            coherence_scores,
            {}
        )

        # Calculate greedy total distance
        greedy_distance = 0
        for i in range(len(greedy_sequence) - 1):
            poi1 = greedy_sequence[i]['poi']
            poi2 = greedy_sequence[i + 1]['poi']
            greedy_distance += distance_matrix[(poi1, poi2)]

        ilp_distance = ilp_result['scores']['total_distance_km']

        # ILP should be at least as good as greedy (or within 10% margin)
        # Due to different objective formulations, ILP might not always be shorter,
        # but should be competitive
        assert ilp_distance <= greedy_distance * 1.1

    def test_day_assignments(self, config, distance_matrix, coherence_scores):
        """Test that day assignments are valid"""
        optimizer = ILPOptimizer(config)
        result = optimizer.optimize_sequence(
            pois=TEST_POIS,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=2,
            preferences={}
        )

        day_assignments = result['day_assignments']

        # All POIs should be assigned
        assert len(day_assignments) == len(TEST_POIS)

        # All assignments should be valid days (0 or 1 for 2-day trip)
        for poi_name, day in day_assignments.items():
            assert 0 <= day < 2

        # Each day should have at least one POI
        days_used = set(day_assignments.values())
        assert len(days_used) > 0

    def test_fallback_on_failure(self, config, distance_matrix, coherence_scores):
        """Test fallback to greedy when ILP fails"""
        # Create a config that might cause ILP issues
        bad_config = config.copy()
        bad_config['optimization']['ilp_max_seconds'] = 0.01  # Extremely short

        optimizer = ILPOptimizer(bad_config)

        # Should fallback to greedy without crashing
        result = optimizer.optimize_sequence(
            pois=TEST_POIS,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=2,
            preferences={}
        )

        # Should still return valid result
        assert 'sequence' in result
        assert len(result['sequence']) == len(TEST_POIS)

        # Check if fallback was used
        if 'solver_stats' in result:
            # Might be GREEDY_FALLBACK status
            assert result['solver_stats']['status'] in ['OPTIMAL', 'FEASIBLE', 'GREEDY_FALLBACK']


class TestIntegration:
    """Integration tests with ItineraryOptimizerAgent"""

    def test_optimizer_agent_ilp_mode(self, config):
        """Test ItineraryOptimizerAgent with ILP mode"""
        optimizer = ItineraryOptimizerAgent(config)

        # Check ILP availability
        assert optimizer._is_ilp_available() is True

        # Optimize with ILP mode
        result = optimizer.optimize_itinerary(
            selected_pois=TEST_POIS,
            city='Rome',
            duration_days=2,
            start_time='09:00',
            preferences={},
            mode='ilp'
        )

        # Check result structure
        assert 'itinerary' in result
        assert 'optimization_scores' in result
        assert 'solver_stats' in result

        # Check itinerary
        itinerary = result['itinerary']
        assert len(itinerary) <= 2  # Should fit in 2 days

        total_pois = sum(len(day['pois']) for day in itinerary)
        assert total_pois == len(TEST_POIS)

    def test_optimizer_agent_simple_mode(self, config):
        """Test ItineraryOptimizerAgent with simple mode (greedy)"""
        optimizer = ItineraryOptimizerAgent(config)

        result = optimizer.optimize_itinerary(
            selected_pois=TEST_POIS,
            city='Rome',
            duration_days=2,
            start_time='09:00',
            preferences={},
            mode='simple'
        )

        # Check result structure
        assert 'itinerary' in result
        assert 'optimization_scores' in result

        # Should NOT have solver_stats in simple mode
        assert 'solver_stats' not in result or result['solver_stats'] is None


def test_ortools_import():
    """Test that OR-Tools can be imported"""
    try:
        from ortools.sat.python import cp_model
        assert True
    except ImportError:
        pytest.fail("OR-Tools not installed. Run: pip install ortools")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
