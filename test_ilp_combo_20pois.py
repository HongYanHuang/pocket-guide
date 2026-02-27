"""
Test with actual 20 POIs from your tour to see which constraint causes INFEASIBLE
"""
import sys
sys.path.insert(0, 'src')

import yaml
from trip_planner.ilp_optimizer import ILPOptimizer
from data.combo_ticket_loader import ComboTicketLoader
from math import radians, sin, cos, sqrt, asin

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Your actual 20 POIs
test_pois = [
    {'poi': 'Colosseum', 'estimated_hours': 2.0, 'coordinates': {'latitude': 41.8902, 'longitude': 12.4922}},
    {'poi': 'Baths of Caracalla', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.8790, 'longitude': 12.4924}},
    {'poi': 'Arch of Constantine', 'estimated_hours': 0.3, 'coordinates': {'latitude': 41.8898, 'longitude': 12.4907}},
    {'poi': 'San Pietro in Vincoli', 'estimated_hours': 0.8, 'coordinates': {'latitude': 41.8931, 'longitude': 12.4972}},
    {'poi': 'Roman Forum', 'estimated_hours': 2.0, 'coordinates': {'latitude': 41.8925, 'longitude': 12.4853}},
    {'poi': 'Palatine Hill', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.8892, 'longitude': 12.4873}},
    {'poi': 'Pantheon', 'estimated_hours': 0.8, 'coordinates': {'latitude': 41.8986, 'longitude': 12.4769}},
    {'poi': 'Piazza Navona', 'estimated_hours': 0.8, 'coordinates': {'latitude': 41.8992, 'longitude': 12.4731}},
    {'poi': 'Ara Pacis', 'estimated_hours': 0.8, 'coordinates': {'latitude': 41.9064, 'longitude': 12.4761}},
    {'poi': 'Largo di Torre Argentina', 'estimated_hours': 0.5, 'coordinates': {'latitude': 41.8960, 'longitude': 12.4767}},
    {'poi': 'Galleria Doria Pamphilj', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.8987, 'longitude': 12.4807}},
    {'poi': 'Galleria Borghese', 'estimated_hours': 2.0, 'coordinates': {'latitude': 41.9142, 'longitude': 12.4922}},
    {'poi': 'National Roman Museum - Palazzo Massimo', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.9013, 'longitude': 12.4969}},
    {'poi': 'Basilica di San Clemente', 'estimated_hours': 1.2, 'coordinates': {'latitude': 41.8894, 'longitude': 12.4983}},
    {'poi': 'Capitoline Museums', 'estimated_hours': 2.0, 'coordinates': {'latitude': 41.8930, 'longitude': 12.4828}},
    {'poi': 'Vatican Museums', 'estimated_hours': 3.0, 'coordinates': {'latitude': 41.9064, 'longitude': 12.4534}},
    {'poi': 'Sistine Chapel', 'estimated_hours': 0.8, 'coordinates': {'latitude': 41.9030, 'longitude': 12.4545}},
    {'poi': 'Castel Sant\'Angelo', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.9031, 'longitude': 12.4663}},
    {'poi': 'St. Peter\'s Basilica', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.9022, 'longitude': 12.4539}},
    {'poi': 'Catacombs of San Callisto', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.8545, 'longitude': 12.5114}},
]

print(f"Testing with {len(test_pois)} POIs (your actual tour)")

# Enrich with combo tickets
combo_loader = ComboTicketLoader()
combo_tickets = combo_loader.load_city_combo_tickets('Rome')
test_pois = combo_loader.enrich_pois_with_combo_tickets(test_pois, combo_tickets)

# Build matrices
distance_matrix = {}
coherence_scores = {}
for i, poi_i in enumerate(test_pois):
    for j, poi_j in enumerate(test_pois):
        if i == j:
            distance_matrix[(poi_i['poi'], poi_j['poi'])] = 0.0
        else:
            lat1, lon1 = radians(poi_i['coordinates']['latitude']), radians(poi_i['coordinates']['longitude'])
            lat2, lon2 = radians(poi_j['coordinates']['latitude']), radians(poi_j['coordinates']['longitude'])
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            distance_matrix[(poi_i['poi'], poi_j['poi'])] = 2 * 6371 * asin(sqrt(a))
        coherence_scores[(poi_i['poi'], poi_j['poi'])] = 0.5

print("\nTest 1: WITH time window constraints (original)")
print("=" * 60)
try:
    optimizer = ILPOptimizer(config)
    result = optimizer.optimize_sequence(
        pois=test_pois,
        distance_matrix=distance_matrix,
        coherence_scores=coherence_scores,
        duration_days=5,
        preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
    )
    print(f"✓ SUCCESS: {result['solver_stats']['status']}")
except Exception as e:
    print(f"✗ FAILED: {e}")

print("\nTest 2: WITHOUT time window constraints")
print("=" * 60)
print("Temporarily disabling time window constraints...")

# Monkey patch to disable time windows
original_method = optimizer._add_time_window_constraints
def noop_time_windows(*args, **kwargs):
    print("  [DISABLED] Skipping time window constraints")
    pass
optimizer._add_time_window_constraints = noop_time_windows

try:
    result = optimizer.optimize_sequence(
        pois=test_pois,
        distance_matrix=distance_matrix,
        coherence_scores=coherence_scores,
        duration_days=5,
        preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
    )
    print(f"✓ SUCCESS: {result['solver_stats']['status']}")
    
    # Check combo tickets
    day_assignments = result['day_assignments']
    combo_pois = ['Colosseum', 'Roman Forum', 'Palatine Hill']
    combo_days = set(day_assignments[poi] for poi in combo_pois if poi in day_assignments)
    if len(combo_days) == 1:
        print(f"  ✓ COMBO TICKET OK: All 3 POIs on day {list(combo_days)[0] + 1}")
    else:
        print(f"  ✗ COMBO TICKET FAILED: {combo_days}")
except Exception as e:
    print(f"✗ FAILED: {e}")

