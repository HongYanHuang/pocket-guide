"""
Test: Only Archaeological Pass combo tickets, no Vatican Combo
"""
import sys
sys.path.insert(0, 'src')
import yaml
import json
from pathlib import Path
from trip_planner.itinerary_optimizer import ItineraryOptimizerAgent
from data.combo_ticket_loader import ComboTicketLoader

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
print("Test: ONLY Archaeological Pass (remove Vatican Combo constraint)")
print("=" * 80)

# Monkey-patch the combo ticket loader to only return Archaeological Pass
original_load = ComboTicketLoader.load_city_combo_tickets

def load_only_arch_pass(self, city):
    all_combos = original_load(self, city)
    # Only return archaeological_pass_rome
    return {k: v for k, v in all_combos.items() if k == 'archaeological_pass_rome'}

ComboTicketLoader.load_city_combo_tickets = load_only_arch_pass

try:
    optimizer = ItineraryOptimizerAgent(config)

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
        print("✅ Works with ONLY Archaeological Pass!")

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
        print(f"❌ INFEASIBLE even with ONLY Archaeological Pass")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Restore
    ComboTicketLoader.load_city_combo_tickets = original_load
