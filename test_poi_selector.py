"""
Test script for POI Selector Agent

Tests Phase 2.1 implementation with Athens POIs.
"""

import yaml
import json
from src.trip_planner import POISelectorAgent


def main():
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Initialize selector with Anthropic
    print("=" * 60)
    print("Testing POI Selector Agent - Phase 2.1")
    print("=" * 60)
    print()

    selector = POISelectorAgent(config, provider='anthropic')

    # Test case: 3-day Athens trip with architecture & history interests
    print("TEST CASE: 3-day Athens trip")
    print("Interests: architecture, history")
    print("Preferences: moderate walking, balanced indoor/outdoor")
    print()

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

    # Display results
    print()
    print("=" * 60)
    print("SELECTION RESULTS")
    print("=" * 60)
    print()

    print(f"Starting POIs ({len(selection['starting_pois'])}):")
    for i, poi in enumerate(selection['starting_pois'], 1):
        print(f"  {i}. {poi['poi']}")
        print(f"     Reason: {poi['reason']}")
        print(f"     Day {poi.get('suggested_day', '?')}, ~{poi.get('estimated_hours', '?')} hours")
        print()

    print(f"Total Estimated Time: {selection['total_estimated_hours']} hours")
    print()

    print("Back-up POIs:")
    for starting_poi, backups in selection['backup_pois'].items():
        print(f"\n  For '{starting_poi}':")
        for backup in backups:
            print(f"    → {backup['poi']} (similarity: {backup['similarity_score']})")
            print(f"      {backup['reason']}")

    print()
    print("=" * 60)
    print("REASONING SUMMARY")
    print("=" * 60)
    print(selection.get('reasoning_summary', 'No summary provided'))
    print()

    # Save to file
    output_file = 'test_poi_selection_result.json'
    with open(output_file, 'w') as f:
        json.dump(selection, f, indent=2)

    print(f"\n✓ Full results saved to: {output_file}")


if __name__ == '__main__':
    main()
