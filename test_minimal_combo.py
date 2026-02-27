"""
Minimal test to isolate combo ticket INFEASIBLE issue
"""
import sys
sys.path.insert(0, 'src')
import yaml
from trip_planner.ilp_optimizer import ILPOptimizer
from data.combo_ticket_loader import ComboTicketLoader
from math import radians, sin, cos, sqrt, asin

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Minimal POI set: Just the 3 Archaeological Pass POIs
pois = [
    {
        'poi': 'Colosseum',
        'estimated_hours': 2.5,
        'coordinates': {'latitude': 41.8902, 'longitude': 12.4922},
        'priority': 'high'
    },
    {
        'poi': 'Roman Forum',
        'estimated_hours': 1.5,
        'coordinates': {'latitude': 41.8925, 'longitude': 12.4853},
        'priority': 'high'
    },
    {
        'poi': 'Palatine Hill',
        'estimated_hours': 1.5,
        'coordinates': {'latitude': 41.8894, 'longitude': 12.4875},
        'priority': 'high'
    }
]

print("=" * 80)
print("MINIMAL TEST: 3 Archaeological Pass POIs only")
print("=" * 80)
print(f"POIs: {[p['poi'] for p in pois]}")
print(f"Total hours: {sum(p['estimated_hours'] for p in pois)}")
print(f"Duration: 2 days")
print()

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

optimizer = ILPOptimizer(config)

# Test 1: Without combo ticket constraints
print("=" * 80)
print("TEST 1: No combo ticket constraints")
print("=" * 80)

result1 = optimizer.optimize_sequence(
    pois=[{'poi': p['poi'], 'estimated_hours': p['estimated_hours'], 'coordinates': p['coordinates'], 'priority': p['priority']} for p in pois],  # Strip combo ticket metadata
    distance_matrix=distance_matrix,
    coherence_scores=coherence_scores,
    duration_days=2,
    preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
)

print(f"Status: {result1['solver_stats']['status']}")
if result1['solver_stats']['status'] in ['OPTIMAL', 'FEASIBLE']:
    print("✅ Baseline works without combo tickets")
    print(f"Day assignments: {result1['day_assignments']}")
else:
    print("❌ FAILED - Problem is not with combo tickets!")

print()

# Test 2: With combo ticket constraints
print("=" * 80)
print("TEST 2: With combo ticket constraints (same-day requirement)")
print("=" * 80)

result2 = optimizer.optimize_sequence(
    pois=pois,  # Include combo ticket metadata
    distance_matrix=distance_matrix,
    coherence_scores=coherence_scores,
    duration_days=2,
    preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
)

print(f"Status: {result2['solver_stats']['status']}")
if result2['solver_stats']['status'] in ['OPTIMAL', 'FEASIBLE']:
    print("✅ Works WITH combo tickets")
    day_assignments = result2['day_assignments']
    print(f"Day assignments: {day_assignments}")

    # Check if all on same day
    days = set(day_assignments.values())
    if len(days) == 1:
        print(f"✅ All 3 POIs on day {list(days)[0] + 1}")
    else:
        print(f"❌ POIs split across days: {days}")
else:
    print("❌ INFEASIBLE with combo tickets")
    print("\n⚠️  ROOT CAUSE:")
    print("Combo ticket constraints are making the problem INFEASIBLE.")
    print("This means there's an issue with how combo ticket constraints interact with other constraints.")

print()
print("=" * 80)
print("ANALYSIS")
print("=" * 80)
print(f"Total POI hours: {sum(p['estimated_hours'] for p in pois)} hours")
print(f"Available time: 7.5 hours/day × 2 days = 15 hours")
print(f"Constraint: All 3 must be on same day")
print(f"Fits in 7.5h limit: {'✅ YES' if sum(p['estimated_hours'] for p in pois) <= 7.5 else '❌ NO'}")
