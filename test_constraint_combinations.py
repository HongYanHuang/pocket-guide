"""
Test different constraint combinations to find exactly what causes INFEASIBLE
"""
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

# Load the tour POIs
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
                'operation_hours': poi_obj.get('operation_hours', {}),
                'priority': 'high'
            })

# Enrich with combo tickets
combo_loader = ComboTicketLoader()
combo_tickets = combo_loader.load_city_combo_tickets('Rome')
pois_with_combo = combo_loader.enrich_pois_with_combo_tickets(pois, combo_tickets)

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

print("=" * 100)
print("CONSTRAINT COMBINATION TESTING - Finding the Exact Conflict")
print("=" * 100)
print(f"Testing {len(pois)} POIs")
print()

# Test different combinations
tests = [
    {
        'name': 'Test 1: TSP + Combo Tickets ONLY',
        'disable_time_windows': True,
        'disable_precedence': True,
        'use_combo': True
    },
    {
        'name': 'Test 2: TSP + Time Windows ONLY (no combo)',
        'disable_time_windows': False,
        'disable_precedence': True,
        'use_combo': False
    },
    {
        'name': 'Test 3: TSP + Precedence ONLY (no combo)',
        'disable_time_windows': True,
        'disable_precedence': False,
        'use_combo': False
    },
    {
        'name': 'Test 4: TSP + Time Windows + Combo Tickets',
        'disable_time_windows': False,
        'disable_precedence': True,
        'use_combo': True
    },
    {
        'name': 'Test 5: TSP + Precedence + Combo Tickets',
        'disable_time_windows': True,
        'disable_precedence': False,
        'use_combo': True
    },
    {
        'name': 'Test 6: TSP + Time Windows + Precedence (no combo)',
        'disable_time_windows': False,
        'disable_precedence': False,
        'use_combo': False
    },
    {
        'name': 'Test 7: ALL CONSTRAINTS (TSP + Time Windows + Precedence + Combo)',
        'disable_time_windows': False,
        'disable_precedence': False,
        'use_combo': True
    }
]

results = []

for test in tests:
    print("=" * 100)
    print(test['name'])
    print("=" * 100)

    optimizer = ILPOptimizer(config)

    # Monkey-patch to disable specific constraints
    original_time_window = optimizer._add_time_window_constraints
    original_precedence = optimizer._add_precedence_constraints

    if test['disable_time_windows']:
        def noop_time(*args, **kwargs):
            print("  [DISABLED] Time window constraints", flush=True)
        optimizer._add_time_window_constraints = noop_time

    if test['disable_precedence']:
        def noop_prec(*args, **kwargs):
            print("  [DISABLED] Precedence constraints", flush=True)
        optimizer._add_precedence_constraints = noop_prec

    # Choose POIs (with or without combo enrichment)
    test_pois = pois_with_combo if test['use_combo'] else pois

    try:
        result = optimizer.optimize_sequence(
            pois=test_pois,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=5,
            preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
        )

        status = result['solver_stats']['status']
        results.append({
            'test': test['name'],
            'status': status,
            'success': status in ['OPTIMAL', 'FEASIBLE']
        })

        if status in ['OPTIMAL', 'FEASIBLE']:
            print(f"✅ {status}")
        else:
            print(f"❌ {status}")

    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        results.append({
            'test': test['name'],
            'status': 'ERROR',
            'success': False,
            'error': str(e)
        })

    # Restore
    optimizer._add_time_window_constraints = original_time_window
    optimizer._add_precedence_constraints = original_precedence

    print()

# Summary
print("=" * 100)
print("SUMMARY - Finding the Culprit")
print("=" * 100)
print()

for r in results:
    icon = "✅" if r['success'] else "❌"
    print(f"{icon} {r['test']}: {r['status']}")

print()
print("=" * 100)
print("ANALYSIS")
print("=" * 100)

# Determine which constraint causes the issue
if results[3]['success']:  # Time Windows + Combo
    print("✅ Time Windows + Combo Tickets = FEASIBLE")
    print("   → Time windows are NOT the problem")
else:
    print("❌ Time Windows + Combo Tickets = INFEASIBLE")
    print("   → Time windows CONFLICT with combo tickets")

print()

if results[4]['success']:  # Precedence + Combo
    print("✅ Precedence + Combo Tickets = FEASIBLE")
    print("   → Precedence is NOT the problem")
else:
    print("❌ Precedence + Combo Tickets = INFEASIBLE")
    print("   → Precedence CONFLICTS with combo tickets")

print()

if results[5]['success']:  # Time Windows + Precedence (no combo)
    print("✅ Time Windows + Precedence (no combo) = FEASIBLE")
    print("   → These two constraints are compatible")
else:
    print("❌ Time Windows + Precedence (no combo) = INFEASIBLE")
    print("   → These two constraints conflict even without combo")

print()
print("ROOT CAUSE:")
if not results[3]['success'] and not results[4]['success']:
    print("  Both Time Windows AND Precedence conflict with combo tickets individually")
elif not results[3]['success']:
    print("  Time Windows conflict with combo tickets (Precedence is fine)")
elif not results[4]['success']:
    print("  Precedence conflicts with combo tickets (Time Windows are fine)")
else:
    print("  Time Windows and Precedence are individually OK with combo tickets,")
    print("  but the THREE-WAY interaction causes INFEASIBLE")
