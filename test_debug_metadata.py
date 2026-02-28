"""
Debug what metadata is being passed to ILP optimizer
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

# Extract unique POIs (minimal structure like from selector)
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
print("METADATA DEBUG")
print("=" * 80)
print(f"Total POIs: {len(unique_pois)}")
print()

# Create optimizer and load metadata (same path as actual execution)
optimizer = ItineraryOptimizerAgent(config)

print("Loading and enriching POIs...")
enriched_pois = optimizer._enrich_pois_with_metadata(unique_pois, 'Rome')

print()
print("=" * 80)
print("ENRICHED POI METADATA")
print("=" * 80)

for poi in enriched_pois[:5]:  # Show first 5
    print(f"\nPOI: {poi['poi']}")
    print(f"  estimated_hours: {poi.get('estimated_hours')}")
    print(f"  coordinates: {poi.get('coordinates')}")
    print(f"  operation_hours: {poi.get('operation_hours')}")
    print(f"  metadata (if any): {poi.get('metadata', {})}")
    print(f"  combo_ticket_groups: {poi.get('metadata', {}).get('combo_ticket_groups', 'None')}")

print()
print("=" * 80)
print("KEY FINDING")
print("=" * 80)

# Check if ANY POI has operation_hours
has_operation_hours = any(bool(poi.get('operation_hours')) for poi in enriched_pois)
has_metadata_operation_hours = any(bool(poi.get('metadata', {}).get('operation_hours')) for poi in enriched_pois)

print(f"POIs with operation_hours at top level: {sum(1 for poi in enriched_pois if bool(poi.get('operation_hours')))}")
print(f"POIs with metadata.operation_hours: {sum(1 for poi in enriched_pois if bool(poi.get('metadata', {}).get('operation_hours')))}")

if not has_operation_hours and not has_metadata_operation_hours:
    print("\n⚠️  NO POIs have operation_hours data!")
    print("This means time window constraints are DISABLED.")
    print("So INFEASIBLE status must be caused by something else.")
