"""Test without time window constraints"""
import sys
sys.path.insert(0, 'src')
import yaml
import json
from pathlib import Path
from trip_planner.ilp_optimizer import ILPOptimizer
from data.combo_ticket_loader import ComboTicketLoader
from math import radians, sin, cos, sqrt, asin

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

tour_file = Path('tours/rome/rome-tour-20260227-102356-126fc9/tour_zh-tw.json')
with open(tour_file, 'r') as f:
    tour_data = json.load(f)

# Extract POIs with metadata
pois = []
seen = set()
for day in tour_data['itinerary']:
    for poi_obj in day['pois']:
        poi_name = poi_obj['poi']
        if poi_name not in seen:
            seen.add(poi_name)
            pois.append({
                'poi': poi_name,
                'estimated_hours': poi_obj.get('estimated_hours', 2.0),
                'coordinates': poi_obj.get('coordinates', {'latitude': 41.9, 'longitude': 12.5}),
                'priority': 'high'
            })

# Enrich with combo tickets
combo_loader = ComboTicketLoader()
combo_tickets = combo_loader.load_city_combo_tickets('Rome')
pois = combo_loader.enrich_pois_with_combo_tickets(pois, combo_tickets)

# Build distance matrix
distance_matrix = {}
for i, poi_i in enumerate(pois):
    for j, poi_j in enumerate(pois):
        if i == j:
            distance_matrix[(poi_i['poi'], poi_j['poi'])] = 0.0
        else:
            lat1 = radians(poi_i['coordinates']['latitude'])
            lon1 = radians(poi_i['coordinates']['longitude'])
            lat2 = radians(poi_j['coordinates']['latitude'])
            lon2 = radians(poi_j['coordinates']['longitude'])
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            distance_matrix[(poi_i['poi'], poi_j['poi'])] = 2 * 6371 * asin(sqrt(a))

coherence_scores = {(p1['poi'], p2['poi']): 0.5 for p1 in pois for p2 in pois}

print(f"Testing {len(pois)} POIs WITHOUT time window constraints...")

optimizer = ILPOptimizer(config)

# Disable time windows
def noop(*args, **kwargs):
    print("  [DISABLED] Skipping time window constraints")
optimizer._add_time_window_constraints = noop

result = optimizer.optimize_sequence(
    pois=pois,
    distance_matrix=distance_matrix,
    coherence_scores=coherence_scores,
    duration_days=5,
    preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
)

print(f"\nStatus: {result['solver_stats']['status']}")

if result['solver_stats']['status'] in ['OPTIMAL', 'FEASIBLE']:
    print("✅ Solver found solution WITHOUT time windows!")
    
    # Check combo tickets
    day_assignments = result['day_assignments']
    arch_pois = ['Colosseum', 'Roman Forum', 'Palatine Hill']
    arch_days = {poi: day_assignments[poi] for poi in arch_pois if poi in day_assignments}
    
    if len(set(arch_days.values())) == 1:
        print(f"  ✅ Archaeological Pass: All 3 on day {list(arch_days.values())[0] + 1}")
    else:
        print(f"  ❌ Archaeological Pass: Split across days {set(arch_days.values())}")
else:
    print(f"❌ Still INFEASIBLE even without time windows!")
