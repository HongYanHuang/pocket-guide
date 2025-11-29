"""
Test script for Itinerary Optimizer Agent

Tests Phase 2.2 implementation: End-to-end Selection → Optimization
"""

import yaml
import json
from src.trip_planner import POISelectorAgent, ItineraryOptimizerAgent, TourManager


def main():
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    print("=" * 60)
    print("Testing Trip Planning - Phase 2.2 (End-to-End)")
    print("=" * 60)
    print()

    # PHASE 2.1: POI Selection
    print("PHASE 2.1: POI SELECTION")
    print("-" * 60)

    selector = POISelectorAgent(config, provider='anthropic')

    selection = selector.select_pois(
        city='Athens',
        duration_days=3,
        interests=['architecture', 'history'],
        preferences={
            'walking_tolerance': 'moderate',
            'indoor_outdoor': 'balanced',
            'pace': 'relaxed'
        },
        must_see=['Acropolis']
    )

    print()
    print(f"✓ Selected {len(selection['starting_pois'])} Starting POIs")
    print(f"✓ Generated {selection['metadata']['total_backup_pois']} Back-up POIs")
    print()

    # PHASE 2.2: Itinerary Optimization
    print("PHASE 2.2: ITINERARY OPTIMIZATION")
    print("-" * 60)

    optimizer = ItineraryOptimizerAgent(config)

    itinerary_result = optimizer.optimize_itinerary(
        selected_pois=selection['starting_pois'],
        city='Athens',
        duration_days=3,
        start_time="09:00",
        preferences={
            'distance_weight': 0.5,
            'coherence_weight': 0.5
        }
    )

    # Display results
    print()
    print("=" * 60)
    print("OPTIMIZED ITINERARY")
    print("=" * 60)
    print()

    for day in itinerary_result['itinerary']:
        print(f"DAY {day['day']} (Start: {day['start_time']})")
        print(f"Total: {day['total_hours']}h activity, {day['total_walking_km']}km walking")
        print()

        for i, poi in enumerate(day['pois'], 1):
            print(f"  {i}. {poi['poi']} (~{poi.get('estimated_hours', '?')}h)")
            print(f"     {poi.get('reason', '')}")
            if poi.get('period'):
                print(f"     Period: {poi['period']}")
            print()

        print()

    # Optimization Scores
    print("=" * 60)
    print("OPTIMIZATION SCORES")
    print("=" * 60)
    scores = itinerary_result['optimization_scores']
    print(f"Distance Score:   {scores['distance_score']:.2f} (higher = less walking)")
    print(f"Coherence Score:  {scores['coherence_score']:.2f} (higher = better flow)")
    print(f"Overall Score:    {scores['overall_score']:.2f}")
    print(f"Total Walking:    {scores['total_distance_km']:.2f} km")
    print()

    # Constraint Violations
    if itinerary_result['constraints_violated']:
        print("=" * 60)
        print("⚠️  CONSTRAINT VIOLATIONS")
        print("=" * 60)
        for violation in itinerary_result['constraints_violated']:
            print(f"  • {violation}")
        print()
    else:
        print("✅ No constraint violations")
        print()

    # Selection Reasoning
    print("=" * 60)
    print("SELECTION REASONING")
    print("=" * 60)
    print(selection.get('reasoning_summary', 'No summary provided'))
    print()

    # Save tour with versioning
    print("=" * 60)
    print("SAVING TOUR WITH VERSIONING")
    print("=" * 60)

    tour_manager = TourManager(config)

    # Prepare input parameters for tracking
    input_parameters = {
        'city': 'Athens',
        'duration_days': 3,
        'interests': ['architecture', 'history'],
        'preferences': {
            'walking_tolerance': 'moderate',
            'indoor_outdoor': 'balanced',
            'pace': 'relaxed',
            'distance_weight': 0.5,
            'coherence_weight': 0.5
        },
        'must_see': ['Acropolis'],
        'start_time': "09:00"
    }

    # User info (optional)
    user_info = {
        'user_id': 'test_user',
        'username': 'Test User',
        'email': 'test@example.com'
    }

    # Save tour with full metadata
    save_result = tour_manager.save_tour(
        tour_data=itinerary_result,
        city='Athens',
        input_parameters=input_parameters,
        user_info=user_info
    )

    print(f"\n✓ Tour ID: {save_result['tour_id']}")
    print(f"✓ Version: {save_result['version_string']}")
    print(f"\nSaved files:")
    for file_type, path in save_result['files'].items():
        print(f"  • {file_type}: {path}")

    # Also save legacy test output
    output_file = 'test_itinerary_result.json'
    combined_result = {
        'selection': selection,
        'itinerary': itinerary_result
    }

    with open(output_file, 'w') as f:
        json.dump(combined_result, f, indent=2)

    print(f"\n✓ Legacy output saved to: {output_file}")
    print()


if __name__ == '__main__':
    main()
