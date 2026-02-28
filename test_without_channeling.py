"""
Test: Disable channeling constraints to see if they're over-constraining
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

print("Testing WITHOUT channeling constraints...")
print(f"POIs: {len(unique_pois)}")

optimizer = ItineraryOptimizerAgent(config)

# Temporarily disable channeling
from trip_planner import ilp_optimizer
original_method = ilp_optimizer.ILPOptimizer._add_tsp_constraints

def no_channeling_constraints(self, model, visit_vars, pois, duration_days, day_vars=None):
    """Call original but without day_vars (disables channeling)"""
    return original_method(self, model, visit_vars, pois, duration_days, day_vars=None)

ilp_optimizer.ILPOptimizer._add_tsp_constraints = no_channeling_constraints

try:
    result = optimizer.optimize_itinerary(
        selected_pois=unique_pois,
        city='Rome',
        duration_days=5,
        mode='ilp',
        preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
    )

    solver_status = result.get('solver_stats', {}).get('status', 'UNKNOWN')
    print(f"\nStatus: {solver_status}")

    if solver_status in ['OPTIMAL', 'FEASIBLE']:
        print("✅ Works WITHOUT channeling constraints!")
        print("   This means channeling constraints are over-constraining")

        # Check combo tickets
        arch_pois = ['Colosseum', 'Roman Forum', 'Palatine Hill']
        arch_days = {}
        for day in result['itinerary']:
            for poi_obj in day['pois']:
                if poi_obj['poi'] in arch_pois:
                    arch_days[poi_obj['poi']] = day['day']

        if len(arch_days) > 0:
            unique_days = set(arch_days.values())
            print(f"\nArchaeological Pass POIs:")
            for poi, day in arch_days.items():
                print(f"  - {poi}: Day {day}")
            if len(unique_days) == 1:
                print(f"  ✅ All on Day {list(unique_days)[0]}")
            else:
                print(f"  ❌ Split across days {unique_days}")
    else:
        print(f"❌ Still INFEASIBLE without channeling constraints")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Restore original method
    ilp_optimizer.ILPOptimizer._add_tsp_constraints = original_method
