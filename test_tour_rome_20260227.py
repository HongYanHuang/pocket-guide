"""
Test script that replicates the exact ILP optimization for tour rome-tour-20260227-102356-126fc9
"""
import sys
sys.path.insert(0, 'src')

import yaml
import json
from pathlib import Path
from trip_planner.itinerary_optimizer import ItineraryOptimizerAgent

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Load the exact POI list from the tour
tour_file = Path('tours/rome/rome-tour-20260227-102356-126fc9/tour_zh-tw.json')
with open(tour_file, 'r') as f:
    tour_data = json.load(f)

# Extract unique POIs
unique_pois = []
seen = set()
for day in tour_data['itinerary']:
    for poi_obj in day['pois']:
        poi_name = poi_obj['poi']
        if poi_name not in seen:
            seen.add(poi_name)
            unique_pois.append({
                'poi': poi_name,
                'estimated_hours': poi_obj.get('estimated_hours', 2.0),
                'priority': 'high'
            })

print("=" * 80)
print("ILP Test - Exact Replication of rome-tour-20260227-102356-126fc9")
print("=" * 80)
print(f"POIs: {len(unique_pois)}")
print(f"Duration: 5 days")
print(f"Mode: ILP")
print()

# Print POI list
print("POIs in tour:")
for i, poi in enumerate(unique_pois, 1):
    print(f"  {i:2d}. {poi['poi']}")
print()

# Check which POIs are part of combo tickets
combo_pois = {
    'archaeological_pass_rome': ['Colosseum', 'Roman Forum', 'Palatine Hill'],
    'vatican_combo': ['Vatican Museums', 'Sistine Chapel']
}

print("Expected combo ticket groupings:")
for ticket_name, members in combo_pois.items():
    in_tour = [p for p in members if p in seen]
    if len(in_tour) > 0:
        print(f"  {ticket_name}: {in_tour} ({len(in_tour)}/{len(members)} present)")
print()

# Run ILP optimization
print("=" * 80)
print("Running ILP optimization...")
print("=" * 80)

optimizer = ItineraryOptimizerAgent(config)

try:
    result = optimizer.optimize_itinerary(
        selected_pois=unique_pois,
        city='Rome',
        duration_days=5,
        mode='ilp',
        preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
    )
    
    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    solver_status = result.get('solver_stats', {}).get('status', 'UNKNOWN')
    print(f"Solver Status: {solver_status}")
    print()
    
    if solver_status in ['OPTIMAL', 'FEASIBLE']:
        # Show day-by-day breakdown
        print("Day-by-day itinerary:")
        for day in result['itinerary']:
            pois = [p['poi'] for p in day['pois']]
            print(f"  Day {day['day']}: {pois}")
        print()
        
        # Check combo ticket constraints
        print("Combo Ticket Validation:")
        print("-" * 80)
        
        # Archaeological Pass check
        arch_pois = ['Colosseum', 'Roman Forum', 'Palatine Hill']
        arch_days = {}
        for day in result['itinerary']:
            for poi_obj in day['pois']:
                if poi_obj['poi'] in arch_pois:
                    arch_days[poi_obj['poi']] = day['day']
        
        if len(arch_days) > 0:
            unique_days = set(arch_days.values())
            print(f"Archaeological Pass POIs:")
            for poi, day in arch_days.items():
                print(f"  - {poi}: Day {day}")
            if len(unique_days) == 1:
                print(f"  ✅ PASS: All on Day {list(unique_days)[0]}")
            else:
                print(f"  ❌ FAIL: Spread across days {unique_days}")
        print()
        
        # Vatican combo check
        vatican_pois = ['Vatican Museums', 'Sistine Chapel']
        vatican_days = {}
        for day in result['itinerary']:
            for poi_obj in day['pois']:
                if poi_obj['poi'] in vatican_pois:
                    vatican_days[poi_obj['poi']] = day['day']
        
        if len(vatican_days) > 0:
            unique_days = set(vatican_days.values())
            print(f"Vatican Combo POIs:")
            for poi, day in vatican_days.items():
                print(f"  - {poi}: Day {day}")
            if len(unique_days) == 1:
                print(f"  ✅ PASS: All on Day {list(unique_days)[0]}")
            else:
                print(f"  ❌ FAIL: Spread across days {unique_days}")
                
    else:
        print(f"❌ Solver failed with status: {solver_status}")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Test Complete")
print("=" * 80)
