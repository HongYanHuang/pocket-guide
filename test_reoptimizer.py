"""
Test script for ItineraryReoptimizer

This script tests the 3-tier optimization strategy with a sample tour.
"""

import sys
sys.path.insert(0, 'src')

import json
from pathlib import Path
import yaml


def test_reoptimizer():
    """Test the reoptimizer with a real tour"""

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Find a test tour
    tours_dir = Path("tours")
    test_tour = None
    test_city = None

    for city_dir in tours_dir.iterdir():
        if not city_dir.is_dir():
            continue

        # Find first tour in this city
        for tour_dir in city_dir.iterdir():
            if tour_dir.is_dir():
                # Try to load tour
                tour_files = list(tour_dir.glob("tour_*.json"))
                if tour_files:
                    test_tour = tour_dir
                    test_city = city_dir.name
                    break

        if test_tour:
            break

    if not test_tour:
        print("No test tours found. Please generate a tour first.")
        return

    print(f"Testing with tour: {test_tour.name} in {test_city}")

    # Load tour data
    tour_files = list(test_tour.glob("tour_*.json"))
    with open(tour_files[0], 'r', encoding='utf-8') as f:
        tour_data = json.load(f)

    # Load generation record
    gen_record_files = list(test_tour.glob("generation_record_*.json"))
    if not gen_record_files:
        print("No generation record found")
        return

    with open(gen_record_files[0], 'r', encoding='utf-8') as f:
        gen_record = json.load(f)

    print(f"\nOriginal tour:")
    print(f"  Days: {len(tour_data['itinerary'])}")
    print(f"  Total POIs: {sum(len(day['pois']) for day in tour_data['itinerary'])}")
    print(f"  Current score: {tour_data.get('optimization_scores', {}).get('overall_score', 'N/A')}")

    # Get backup POIs
    backup_pois = tour_data.get('backup_pois', {}) or gen_record.get('poi_selection', {}).get('backup_pois', {})

    if not backup_pois:
        print("No backup POIs found in this tour")
        return

    # Find a POI with backups to test replacement
    test_original_poi = None
    test_replacement_poi = None
    test_day = None

    for day in tour_data['itinerary']:
        for poi_obj in day['pois']:
            poi_name = poi_obj['poi']
            if poi_name in backup_pois and backup_pois[poi_name]:
                test_original_poi = poi_name
                test_replacement_poi = backup_pois[poi_name][0]['poi']
                test_day = day['day']
                break
        if test_original_poi:
            break

    if not test_original_poi:
        print("No POIs with backups found for testing")
        return

    print(f"\nTest replacement:")
    print(f"  Original POI: {test_original_poi}")
    print(f"  Replacement POI: {test_replacement_poi}")
    print(f"  Day: {test_day}")

    # Test Tier 1: Local swap
    print("\n" + "="*60)
    print("TEST 1: Local Swap (Tier 1)")
    print("="*60)

    from trip_planner.itinerary_reoptimizer import ItineraryReoptimizer

    reoptimizer = ItineraryReoptimizer(config)

    # Make a copy of tour data
    test_tour_data = json.loads(json.dumps(tour_data))

    replacements = [{
        'original_poi': test_original_poi,
        'replacement_poi': test_replacement_poi,
        'day': test_day
    }]

    result = reoptimizer.reoptimize(
        tour_data=test_tour_data,
        replacements=replacements,
        city=test_city,
        preferences={}
    )

    print(f"\nResult:")
    print(f"  Strategy used: {result['strategy_used']}")
    print(f"  New score: {result['optimization_scores']['overall_score']}")
    print(f"  Distance score: {result['optimization_scores']['distance_score']}")
    print(f"  Coherence score: {result['optimization_scores']['coherence_score']}")
    print(f"  Total distance: {result['optimization_scores']['total_distance_km']} km")
    print(f"  Cache entries: {len(result['distance_cache'])}")

    # Verify replacement was made
    replacement_found = False
    for day in result['itinerary']:
        for poi_obj in day['pois']:
            if poi_obj['poi'] == test_replacement_poi:
                replacement_found = True
                print(f"\n✓ Replacement POI found in day {day['day']}")
                break

    if not replacement_found:
        print("\n✗ ERROR: Replacement POI not found in itinerary!")

    # Test Tier 2: Day-level optimization
    print("\n" + "="*60)
    print("TEST 2: Day-level Optimization (Tier 2)")
    print("="*60)

    # Make multiple replacements on 1-2 days to trigger Tier 2
    test_tour_data_2 = json.loads(json.dumps(tour_data))

    # Find another replacement on same or adjacent day
    replacements_2 = [replacements[0]]

    for day in tour_data['itinerary']:
        if day['day'] in [test_day, test_day + 1]:
            for poi_obj in day['pois']:
                poi_name = poi_obj['poi']
                if poi_name != test_original_poi and poi_name in backup_pois and backup_pois[poi_name]:
                    replacements_2.append({
                        'original_poi': poi_name,
                        'replacement_poi': backup_pois[poi_name][0]['poi'],
                        'day': day['day']
                    })
                    break
        if len(replacements_2) >= 2:
            break

    if len(replacements_2) >= 2:
        print(f"Testing with {len(replacements_2)} replacements:")
        for r in replacements_2:
            print(f"  - {r['original_poi']} → {r['replacement_poi']} (Day {r['day']})")

        result_2 = reoptimizer.reoptimize(
            tour_data=test_tour_data_2,
            replacements=replacements_2,
            city=test_city,
            preferences={}
        )

        print(f"\nResult:")
        print(f"  Strategy used: {result_2['strategy_used']}")
        print(f"  New score: {result_2['optimization_scores']['overall_score']}")
        print(f"  Total distance: {result_2['optimization_scores']['total_distance_km']} km")
    else:
        print("Not enough POIs to test Tier 2 (need 2+ replacements)")

    # Test Tier 3: Full tour optimization
    print("\n" + "="*60)
    print("TEST 3: Full Tour Optimization (Tier 3)")
    print("="*60)

    # Make replacements across multiple days to trigger Tier 3
    test_tour_data_3 = json.loads(json.dumps(tour_data))

    replacements_3 = []
    for day in tour_data['itinerary'][:3]:  # First 3 days
        for poi_obj in day['pois'][:1]:  # First POI of each day
            poi_name = poi_obj['poi']
            if poi_name in backup_pois and backup_pois[poi_name]:
                replacements_3.append({
                    'original_poi': poi_name,
                    'replacement_poi': backup_pois[poi_name][0]['poi'],
                    'day': day['day']
                })
                break

    if len(replacements_3) >= 3:
        print(f"Testing with {len(replacements_3)} replacements across multiple days:")
        for r in replacements_3:
            print(f"  - {r['original_poi']} → {r['replacement_poi']} (Day {r['day']})")

        result_3 = reoptimizer.reoptimize(
            tour_data=test_tour_data_3,
            replacements=replacements_3,
            city=test_city,
            preferences={}
        )

        print(f"\nResult:")
        print(f"  Strategy used: {result_3['strategy_used']}")
        print(f"  New score: {result_3['optimization_scores']['overall_score']}")
        print(f"  Total distance: {result_3['optimization_scores']['total_distance_km']} km")
    else:
        print("Not enough POIs to test Tier 3 (need 3+ days with backups)")

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    test_reoptimizer()
