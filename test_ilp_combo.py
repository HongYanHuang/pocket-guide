"""
Test script for ILP combo ticket constraints
Minimal test case to debug why solver returns INFEASIBLE
"""
import sys
sys.path.insert(0, 'src')

import yaml
from pathlib import Path
from trip_planner.ilp_optimizer import ILPOptimizer
from data.combo_ticket_loader import ComboTicketLoader

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Test POIs - minimal set with combo ticket
test_pois = [
    {
        'poi': 'Colosseum',
        'estimated_hours': 2.0,
        'coordinates': {'latitude': 41.8902, 'longitude': 12.4922},
        'priority': 'high'
    },
    {
        'poi': 'Roman Forum',
        'estimated_hours': 2.0,
        'coordinates': {'latitude': 41.8925, 'longitude': 12.4853},
        'priority': 'high'
    },
    {
        'poi': 'Palatine Hill',
        'estimated_hours': 1.5,
        'coordinates': {'latitude': 41.8892, 'longitude': 12.4873},
        'priority': 'high'
    },
    {
        'poi': 'Pantheon',
        'estimated_hours': 0.8,
        'coordinates': {'latitude': 41.8986, 'longitude': 12.4769},
        'priority': 'medium'
    },
    {
        'poi': 'Piazza Navona',
        'estimated_hours': 0.8,
        'coordinates': {'latitude': 41.8992, 'longitude': 12.4731},
        'priority': 'medium'
    }
]

print("=" * 60)
print("ILP Combo Ticket Test")
print("=" * 60)
print(f"Testing with {len(test_pois)} POIs")
print(f"POIs: {[p['poi'] for p in test_pois]}")
print()

# Enrich with combo tickets
print("Enriching POIs with combo tickets...")
combo_loader = ComboTicketLoader()
combo_tickets = combo_loader.load_city_combo_tickets('Rome')
print(f"Loaded {len(combo_tickets)} combo ticket(s)")
test_pois = combo_loader.enrich_pois_with_combo_tickets(test_pois, combo_tickets)

# Check enrichment
for poi in test_pois:
    combo_groups = poi.get('metadata', {}).get('combo_ticket_groups', [])
    if combo_groups:
        print(f"  ✓ {poi['poi']}: {len(combo_groups)} combo ticket(s)")
print()

# Build distance matrix
print("Building distance matrix...")
from math import radians, sin, cos, sqrt, asin

distance_matrix = {}
for i, poi_i in enumerate(test_pois):
    for j, poi_j in enumerate(test_pois):
        if i == j:
            distance_matrix[(poi_i['poi'], poi_j['poi'])] = 0.0
        else:
            lat1 = radians(poi_i['coordinates']['latitude'])
            lon1 = radians(poi_i['coordinates']['longitude'])
            lat2 = radians(poi_j['coordinates']['latitude'])
            lon2 = radians(poi_j['coordinates']['longitude'])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            distance = 2 * 6371 * asin(sqrt(a))
            
            distance_matrix[(poi_i['poi'], poi_j['poi'])] = distance

# Build coherence scores (simple: all neutral)
coherence_scores = {}
for i, poi_i in enumerate(test_pois):
    for j, poi_j in enumerate(test_pois):
        coherence_scores[(poi_i['poi'], poi_j['poi'])] = 0.5

print("Distance matrix ready")
print()

# Test with different day counts
for duration_days in [2, 3]:
    print("=" * 60)
    print(f"Testing with {duration_days} days")
    print("=" * 60)
    
    try:
        optimizer = ILPOptimizer(config)
        
        result = optimizer.optimize_sequence(
            pois=test_pois,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=duration_days,
            preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
        )
        
        print(f"✓ SUCCESS: {result['solver_stats']['status']}")
        print(f"  Solve time: {result['solver_stats']['solve_time']}s")
        
        # Show day assignments
        print("\nDay assignments:")
        day_assignments = result['day_assignments']
        for day in range(duration_days):
            pois_on_day = [poi for poi, d in day_assignments.items() if d == day]
            print(f"  Day {day + 1}: {pois_on_day}")
        
        # Check combo ticket constraint
        combo_pois = ['Colosseum', 'Roman Forum', 'Palatine Hill']
        combo_days = set(day_assignments[poi] for poi in combo_pois if poi in day_assignments)
        if len(combo_days) == 1:
            print(f"\n✓ COMBO TICKET OK: All 3 POIs on day {list(combo_days)[0] + 1}")
        else:
            print(f"\n✗ COMBO TICKET FAILED: POIs on different days: {combo_days}")
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
    
    print()

print("=" * 60)
print("Test complete")
print("=" * 60)
