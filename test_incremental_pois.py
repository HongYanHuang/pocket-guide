"""
Incremental test: Add POIs one by one to find the breaking point
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

# Load the full tour POIs
tour_file = Path('tours/rome/rome-tour-20260227-102356-126fc9/tour_zh-tw.json')
with open(tour_file, 'r') as f:
    tour_data = json.load(f)

# Extract all POIs
all_pois = []
seen = set()
for day in tour_data['itinerary']:
    for poi_obj in day['pois']:
        poi_name = poi_obj['poi']
        if poi_name not in seen:
            seen.add(poi_name)
            all_pois.append({
                'poi': poi_name,
                'estimated_hours': poi_obj.get('estimated_hours', 2.0),
                'coordinates': poi_obj.get('coordinates', {'latitude': 41.9, 'longitude': 12.5}),
                'priority': 'high'
            })

print("=" * 80)
print("INCREMENTAL TEST: Finding the breaking point")
print("=" * 80)
print(f"Total POIs in tour: {len(all_pois)}")
print()

combo_loader = ComboTicketLoader()
combo_tickets = combo_loader.load_city_combo_tickets('Rome')

def build_distance_matrix(pois):
    """Build distance matrix for given POIs"""
    matrix = {}
    for i, poi_i in enumerate(pois):
        for j, poi_j in enumerate(pois):
            if i == j:
                matrix[(poi_i['poi'], poi_j['poi'])] = 0.0
            else:
                lat1 = radians(poi_i['coordinates']['latitude'])
                lon1 = radians(poi_i['coordinates']['longitude'])
                lat2 = radians(poi_j['coordinates']['latitude'])
                lon2 = radians(poi_j['coordinates']['longitude'])
                dlat, dlon = lat2 - lat1, lon2 - lon1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                matrix[(poi_i['poi'], poi_j['poi'])] = 2 * 6371 * asin(sqrt(a))
    return matrix

def test_poi_count(n_pois, duration_days=5):
    """Test with first n POIs"""
    pois = all_pois[:n_pois]
    pois_enriched = combo_loader.enrich_pois_with_combo_tickets(pois, combo_tickets)

    distance_matrix = build_distance_matrix(pois_enriched)
    coherence_scores = {(p1['poi'], p2['poi']): 0.5 for p1 in pois_enriched for p2 in pois_enriched}

    optimizer = ILPOptimizer(config)

    try:
        result = optimizer.optimize_sequence(
            pois=pois_enriched,
            distance_matrix=distance_matrix,
            coherence_scores=coherence_scores,
            duration_days=duration_days,
            preferences={'pace': 'normal', 'walking_tolerance': 'moderate'}
        )
        return result['solver_stats']['status']
    except Exception as e:
        return f"ERROR: {str(e)}"

# Test with increasing POI counts
test_sizes = [3, 5, 7, 10, 15, 20, 23]

print("Testing different POI counts:")
print("-" * 80)

for n in test_sizes:
    status = test_poi_count(n)
    total_hours = sum(all_pois[i]['estimated_hours'] for i in range(min(n, len(all_pois))))
    pois_subset = [p['poi'] for p in all_pois[:n]]

    # Count combo POIs in subset
    combo_pois = []
    for poi_name in pois_subset:
        if poi_name in ['Colosseum', 'Roman Forum', 'Palatine Hill', 'Vatican Museums', 'Sistine Chapel']:
            combo_pois.append(poi_name)

    result_icon = "✅" if status in ['OPTIMAL', 'FEASIBLE'] else "❌"

    print(f"{result_icon} {n:2d} POIs ({total_hours:4.1f}h total) → {status}")

    if combo_pois:
        print(f"   Combo POIs: {combo_pois}")

    if status == 'INFEASIBLE' and n > 3:
        print(f"\n⚠️  BREAKING POINT FOUND!")
        print(f"   Last working: {n-1} POIs")
        print(f"   First failure: {n} POIs")

        # Show what POI was added
        if n <= len(all_pois):
            new_poi = all_pois[n-1]
            print(f"   Added POI: {new_poi['poi']} ({new_poi['estimated_hours']}h)")

        break

print()
print("=" * 80)
print("Key insight:")
print("-" * 80)
print("The INFEASIBLE status is likely due to:")
print("1. Too many POIs for the available days/positions")
print("2. Combo ticket constraints reducing scheduling flexibility")
print("3. Position capacity limits (max_pois_per_day)")
