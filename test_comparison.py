"""
Comparison Test: Old Re-optimization vs New 3-Tier Strategy

This script compares:
- OLD: Full tour re-optimization every time (slow but thorough)
- NEW: Smart 3-tier strategy (fast and adaptive)

Shows side-by-side comparison of:
- Execution time
- Optimization scores
- Strategy used
- Tour changes
"""

import sys
sys.path.insert(0, 'src')

import json
import time
from pathlib import Path
import yaml
from copy import deepcopy
from typing import Dict, List


def list_available_tours() -> List[Dict]:
    """List all available tours for testing"""
    tours_dir = Path("tours")
    available_tours = []

    for city_dir in tours_dir.iterdir():
        if not city_dir.is_dir():
            continue

        for tour_dir in city_dir.iterdir():
            if not tour_dir.is_dir():
                continue

            # Check if tour has data
            tour_files = list(tour_dir.glob("tour_*.json"))
            if not tour_files:
                continue

            # Load tour to get info
            with open(tour_files[0], 'r', encoding='utf-8') as f:
                tour_data = json.load(f)

            # Check for backup POIs
            gen_record_files = list(tour_dir.glob("generation_record_*.json"))
            if gen_record_files:
                with open(gen_record_files[0], 'r', encoding='utf-8') as f:
                    gen_record = json.load(f)
                backup_pois = tour_data.get('backup_pois', {}) or gen_record.get('poi_selection', {}).get('backup_pois', {})
            else:
                backup_pois = {}

            num_pois = sum(len(day['pois']) for day in tour_data['itinerary'])
            num_days = len(tour_data['itinerary'])
            num_backups = len(backup_pois)

            available_tours.append({
                'id': tour_dir.name,
                'city': city_dir.name,
                'path': tour_dir,
                'num_days': num_days,
                'num_pois': num_pois,
                'num_backups': num_backups,
                'has_backups': num_backups > 0
            })

    return available_tours


def select_tour(tours: List[Dict]) -> Dict:
    """Interactive tour selection"""
    print("\n" + "="*70)
    print("Available Tours for Testing")
    print("="*70)

    # Filter tours with backups
    tours_with_backups = [t for t in tours if t['has_backups']]

    if not tours_with_backups:
        print("No tours with backup POIs found. Please generate a tour with backup POIs first.")
        return None

    for i, tour in enumerate(tours_with_backups, 1):
        print(f"\n{i}. {tour['id']}")
        print(f"   City: {tour['city'].title()}")
        print(f"   Days: {tour['num_days']}")
        print(f"   POIs: {tour['num_pois']}")
        print(f"   Backup POIs: {tour['num_backups']}")

    print("\n" + "="*70)

    while True:
        try:
            choice = input(f"\nSelect tour (1-{len(tours_with_backups)}) or 'q' to quit: ").strip()

            if choice.lower() == 'q':
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(tours_with_backups):
                return tours_with_backups[idx]
            else:
                print(f"Invalid choice. Please enter 1-{len(tours_with_backups)}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def load_tour_data(tour_path: Path):
    """Load tour data and generation record"""
    # Load tour
    tour_files = list(tour_path.glob("tour_*.json"))
    with open(tour_files[0], 'r', encoding='utf-8') as f:
        tour_data = json.load(f)

    # Load generation record
    gen_record_files = list(tour_path.glob("generation_record_*.json"))
    with open(gen_record_files[0], 'r', encoding='utf-8') as f:
        gen_record = json.load(f)

    return tour_data, gen_record


def find_test_replacement(tour_data: Dict, gen_record: Dict) -> Dict:
    """Find a suitable POI replacement for testing"""
    backup_pois = tour_data.get('backup_pois', {}) or gen_record.get('poi_selection', {}).get('backup_pois', {})

    # Find POI with backups
    for day in tour_data['itinerary']:
        for poi_obj in day['pois']:
            poi_name = poi_obj['poi']
            if poi_name in backup_pois and backup_pois[poi_name]:
                return {
                    'original_poi': poi_name,
                    'replacement_poi': backup_pois[poi_name][0]['poi'],
                    'day': day['day']
                }

    return None


def run_old_algorithm(tour_data: Dict, gen_record: Dict, replacement: Dict, city: str, config: Dict) -> Dict:
    """
    OLD Algorithm: Full tour re-optimization every time
    (What the code did before the 3-tier strategy)
    """
    from trip_planner.itinerary_optimizer import ItineraryOptimizerAgent

    # Deep copy to avoid modifying original
    test_tour = deepcopy(tour_data)

    # Start timing
    start_time = time.time()

    # Extract all POIs
    all_pois = []
    for day in test_tour['itinerary']:
        all_pois.extend(day['pois'])

    # Replace POI in list
    for i, poi_obj in enumerate(all_pois):
        if poi_obj['poi'] == replacement['original_poi']:
            # Load replacement POI metadata
            from utils import load_poi_metadata_from_research
            replacement_metadata = load_poi_metadata_from_research(city, replacement['replacement_poi'])

            all_pois[i] = {
                'poi': replacement['replacement_poi'],
                'reason': f'Replacement for {replacement["original_poi"]}',
                'suggested_day': day['day'],
                'estimated_hours': replacement_metadata.get('estimated_hours', 2.0),
                'priority': 'medium',
                'coordinates': replacement_metadata.get('coordinates', {}),
                'operation_hours': replacement_metadata.get('operation_hours', {}),
                'visit_info': replacement_metadata.get('visit_info', {}),
                'period': replacement_metadata.get('period'),
                'date_built': replacement_metadata.get('date_built')
            }
            break

    # Run full optimizer (OLD approach - always full optimization)
    optimizer = ItineraryOptimizerAgent(config)

    input_params = gen_record.get('input_parameters', {})
    preferences = input_params.get('preferences', {})
    duration_days = len(test_tour['itinerary'])
    start_time_str = test_tour['itinerary'][0].get('start_time', '09:00') if test_tour['itinerary'] else '09:00'

    result = optimizer.optimize_itinerary(
        selected_pois=all_pois,
        city=city,
        duration_days=duration_days,
        start_time=start_time_str,
        preferences=preferences
    )

    # End timing
    elapsed_time = time.time() - start_time

    # Update tour with results
    test_tour['itinerary'] = result['itinerary']
    test_tour['optimization_scores'] = result['optimization_scores']

    return {
        'tour_data': test_tour,
        'execution_time': elapsed_time,
        'strategy': 'full_tour_always',
        'scores': result['optimization_scores']
    }


def run_new_algorithm(tour_data: Dict, gen_record: Dict, replacement: Dict, city: str, config: Dict) -> Dict:
    """
    NEW Algorithm: Smart 3-tier strategy
    (Tier 1: Local swap, Tier 2: Day-level, Tier 3: Full tour)
    """
    from trip_planner.itinerary_reoptimizer import ItineraryReoptimizer

    # Deep copy to avoid modifying original
    test_tour = deepcopy(tour_data)

    # Start timing
    start_time = time.time()

    # Run smart reoptimizer
    reoptimizer = ItineraryReoptimizer(config)

    input_params = gen_record.get('input_parameters', {})
    preferences = input_params.get('preferences', {})

    replacements = [{
        'original_poi': replacement['original_poi'],
        'replacement_poi': replacement['replacement_poi'],
        'day': replacement['day']
    }]

    result = reoptimizer.reoptimize(
        tour_data=test_tour,
        replacements=replacements,
        city=city,
        preferences=preferences
    )

    # End timing
    elapsed_time = time.time() - start_time

    # Update tour with results
    test_tour['itinerary'] = result['itinerary']
    test_tour['optimization_scores'] = result['optimization_scores']

    return {
        'tour_data': test_tour,
        'execution_time': elapsed_time,
        'strategy': result['strategy_used'],
        'scores': result['optimization_scores'],
        'cache_size': len(result.get('distance_cache', {}))
    }


def compare_results(original: Dict, old_result: Dict, new_result: Dict, replacement: Dict):
    """Compare and display results side-by-side"""
    print("\n" + "="*70)
    print("COMPARISON RESULTS")
    print("="*70)

    print(f"\nTest Replacement:")
    print(f"  {replacement['original_poi']} → {replacement['replacement_poi']}")
    print(f"  Day: {replacement['day']}")

    # Original scores
    print(f"\n{'='*70}")
    print("ORIGINAL TOUR (Before Replacement)")
    print("="*70)
    orig_scores = original.get('optimization_scores', {})
    print(f"  Overall Score:    {orig_scores.get('overall_score', 'N/A')}")
    print(f"  Distance Score:   {orig_scores.get('distance_score', 'N/A')}")
    print(f"  Coherence Score:  {orig_scores.get('coherence_score', 'N/A')}")
    print(f"  Total Distance:   {orig_scores.get('total_distance_km', 'N/A')} km")

    # Old algorithm results
    print(f"\n{'='*70}")
    print("OLD ALGORITHM (Full Re-optimization Always)")
    print("="*70)
    print(f"  Strategy:         {old_result['strategy']}")
    print(f"  Execution Time:   {old_result['execution_time']:.3f}s")
    print(f"  Overall Score:    {old_result['scores'].get('overall_score', 'N/A')}")
    print(f"  Distance Score:   {old_result['scores'].get('distance_score', 'N/A')}")
    print(f"  Coherence Score:  {old_result['scores'].get('coherence_score', 'N/A')}")
    print(f"  Total Distance:   {old_result['scores'].get('total_distance_km', 'N/A')} km")

    # New algorithm results
    print(f"\n{'='*70}")
    print("NEW ALGORITHM (Smart 3-Tier Strategy)")
    print("="*70)
    print(f"  Strategy:         {new_result['strategy']} ← Auto-selected!")
    print(f"  Execution Time:   {new_result['execution_time']:.3f}s")
    print(f"  Overall Score:    {new_result['scores'].get('overall_score', 'N/A')}")
    print(f"  Distance Score:   {new_result['scores'].get('distance_score', 'N/A')}")
    print(f"  Coherence Score:  {new_result['scores'].get('coherence_score', 'N/A')}")
    print(f"  Total Distance:   {new_result['scores'].get('total_distance_km', 'N/A')} km")
    if 'cache_size' in new_result:
        print(f"  Distance Cache:   {new_result['cache_size']} entries")

    # Comparison summary
    print(f"\n{'='*70}")
    print("PERFORMANCE COMPARISON")
    print("="*70)

    # Time comparison
    speedup = old_result['execution_time'] / new_result['execution_time'] if new_result['execution_time'] > 0 else 1.0
    print(f"\n⏱️  Execution Time:")
    print(f"  Old: {old_result['execution_time']:.3f}s")
    print(f"  New: {new_result['execution_time']:.3f}s")
    print(f"  Speedup: {speedup:.1f}x faster! 🚀")

    # Score comparison
    old_score = old_result['scores'].get('overall_score', 0)
    new_score = new_result['scores'].get('overall_score', 0)

    print(f"\n📊 Overall Score:")
    print(f"  Old: {old_score}")
    print(f"  New: {new_score}")

    if new_score > old_score:
        improvement = ((new_score - old_score) / old_score) * 100
        print(f"  Result: {improvement:.1f}% better! ✅")
    elif new_score < old_score:
        decline = ((old_score - new_score) / old_score) * 100
        print(f"  Result: {decline:.1f}% worse ⚠️")
    else:
        print(f"  Result: Same score 🟰")

    # Distance comparison
    old_dist = old_result['scores'].get('total_distance_km', 0)
    new_dist = new_result['scores'].get('total_distance_km', 0)

    print(f"\n🚶 Total Walking Distance:")
    print(f"  Old: {old_dist} km")
    print(f"  New: {new_dist} km")

    if new_dist < old_dist:
        reduction = old_dist - new_dist
        print(f"  Result: {reduction:.2f} km shorter! 👍")
    elif new_dist > old_dist:
        increase = new_dist - old_dist
        print(f"  Result: {increase:.2f} km longer ⚠️")
    else:
        print(f"  Result: Same distance 🟰")

    # Strategy insights
    print(f"\n🎯 Strategy Insights:")
    print(f"  Old approach: Always runs full tour optimization")
    print(f"  New approach: Selected '{new_result['strategy']}' strategy")

    if new_result['strategy'] == 'local_swap':
        print(f"  Reason: Single POI replacement on small day → Fast optimization")
    elif new_result['strategy'] == 'day_level':
        print(f"  Reason: Few days affected → Day-level optimization sufficient")
    elif new_result['strategy'] == 'full_tour':
        print(f"  Reason: Multiple days affected → Full tour optimization needed")

    # Overall verdict
    print(f"\n{'='*70}")
    print("VERDICT")
    print("="*70)

    if speedup >= 2.0 and abs(new_score - old_score) < 0.1:
        print("✅ NEW algorithm is MUCH FASTER with similar quality!")
    elif speedup >= 1.5 and new_score >= old_score:
        print("✅ NEW algorithm is FASTER and BETTER quality!")
    elif new_score > old_score * 1.1:
        print("✅ NEW algorithm produces BETTER results!")
    elif speedup >= 1.2:
        print("✅ NEW algorithm is FASTER (quality similar)")
    else:
        print("⚠️  NEW algorithm shows mixed results")

    print()


def compare_tour_structures(old_tour: Dict, new_tour: Dict, replacement: Dict):
    """Compare the tour structures to see how POIs were reorganized"""
    print(f"\n{'='*70}")
    print("TOUR STRUCTURE COMPARISON")
    print("="*70)

    print("\nOLD Algorithm Tour Structure:")
    for day in old_tour['itinerary']:
        poi_names = [p['poi'] for p in day['pois']]
        print(f"  Day {day['day']}: {len(poi_names)} POIs")
        for poi in poi_names:
            marker = " ← NEW!" if poi == replacement['replacement_poi'] else ""
            print(f"    - {poi}{marker}")

    print("\nNEW Algorithm Tour Structure:")
    for day in new_tour['itinerary']:
        poi_names = [p['poi'] for p in day['pois']]
        print(f"  Day {day['day']}: {len(poi_names)} POIs")
        for poi in poi_names:
            marker = " ← NEW!" if poi == replacement['replacement_poi'] else ""
            print(f"    - {poi}{marker}")

    # Check if POI order changed
    old_order = []
    new_order = []

    for day in old_tour['itinerary']:
        old_order.extend([p['poi'] for p in day['pois']])

    for day in new_tour['itinerary']:
        new_order.extend([p['poi'] for p in day['pois']])

    if old_order == new_order:
        print("\n✓ POI order is IDENTICAL (both algorithms produced same sequence)")
    else:
        print("\n✗ POI order is DIFFERENT (algorithms reordered POIs differently)")


def main():
    """Main comparison test"""
    print("\n" + "="*70)
    print("POI Re-optimization Algorithm Comparison Test")
    print("OLD (Full Tour Always) vs NEW (Smart 3-Tier Strategy)")
    print("="*70)

    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # List available tours
    tours = list_available_tours()

    if not tours:
        print("\nNo tours found. Please generate a tour first.")
        return

    # Select tour
    selected_tour = select_tour(tours)

    if not selected_tour:
        print("\nTest cancelled.")
        return

    print(f"\n{'='*70}")
    print(f"Testing with tour: {selected_tour['id']}")
    print(f"City: {selected_tour['city'].title()}")
    print("="*70)

    # Load tour data
    tour_data, gen_record = load_tour_data(selected_tour['path'])
    city = selected_tour['city']

    # Find test replacement
    replacement = find_test_replacement(tour_data, gen_record)

    if not replacement:
        print("\nNo suitable replacement found in this tour.")
        return

    print(f"\nTest replacement selected:")
    print(f"  {replacement['original_poi']} → {replacement['replacement_poi']}")
    print(f"  Day: {replacement['day']}")

    # Save original tour
    original_tour = deepcopy(tour_data)

    # Run OLD algorithm
    print(f"\n{'='*70}")
    print("Running OLD algorithm (Full re-optimization)...")
    print("="*70)
    old_result = run_old_algorithm(tour_data, gen_record, replacement, city, config)
    print(f"✓ Completed in {old_result['execution_time']:.3f}s")

    # Run NEW algorithm
    print(f"\n{'='*70}")
    print("Running NEW algorithm (Smart 3-tier strategy)...")
    print("="*70)
    new_result = run_new_algorithm(tour_data, gen_record, replacement, city, config)
    print(f"✓ Completed in {new_result['execution_time']:.3f}s")
    print(f"✓ Selected strategy: {new_result['strategy']}")

    # Compare results
    compare_results(original_tour, old_result, new_result, replacement)

    # Compare tour structures
    compare_tour_structures(old_result['tour_data'], new_result['tour_data'], replacement)

    # Ask if user wants to test another replacement
    print(f"\n{'='*70}")
    another = input("\nTest another replacement? (y/n): ").strip().lower()

    if another == 'y':
        main()
    else:
        print("\n" + "="*70)
        print("Testing complete! Thank you.")
        print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
