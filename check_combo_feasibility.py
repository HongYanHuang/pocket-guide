"""Check if combo ticket POIs can fit in one day"""
import sys
sys.path.insert(0, 'src')
from math import radians, sin, cos, sqrt, asin

# Combo ticket POIs
pois = [
    {'poi': 'Colosseum', 'estimated_hours': 2.0, 'coordinates': {'latitude': 41.8902, 'longitude': 12.4922}},
    {'poi': 'Roman Forum', 'estimated_hours': 2.0, 'coordinates': {'latitude': 41.8925, 'longitude': 12.4853}},
    {'poi': 'Palatine Hill', 'estimated_hours': 1.5, 'coordinates': {'latitude': 41.8892, 'longitude': 12.4873}},
]

# Calculate distances
def distance(poi1, poi2):
    lat1 = radians(poi1['coordinates']['latitude'])
    lon1 = radians(poi1['coordinates']['longitude'])
    lat2 = radians(poi2['coordinates']['latitude'])
    lon2 = radians(poi2['coordinates']['longitude'])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return 2 * 6371 * asin(sqrt(a))

print("Combo Ticket POIs Time Analysis")
print("=" * 60)
print()

total_visit_hours = sum(p['estimated_hours'] for p in pois)
print(f"Visit times:")
for poi in pois:
    print(f"  {poi['poi']}: {poi['estimated_hours']}h")
print(f"  Total: {total_visit_hours}h")
print()

print(f"Walking distances:")
walking_speed_kmh = 4.0
total_walking_hours = 0
for i in range(len(pois) - 1):
    dist = distance(pois[i], pois[i+1])
    walking_hours = dist / walking_speed_kmh
    walking_minutes = walking_hours * 60
    total_walking_hours += walking_hours
    print(f"  {pois[i]['poi']} → {pois[i+1]['poi']}: {dist:.2f}km ({walking_minutes:.0f}min)")

print(f"  Total walking: {total_walking_hours:.2f}h ({total_walking_hours * 60:.0f}min)")
print()

total_hours = total_visit_hours + total_walking_hours
print(f"TOTAL TIME NEEDED: {total_hours:.2f}h")
print(f"Normal pace limit: 7.5h/day")
print()

if total_hours <= 7.5:
    slack = 7.5 - total_hours
    print(f"✓ FITS! {slack:.2f}h slack remaining")
else:
    over = total_hours - 7.5
    print(f"✗ TOO MUCH! {over:.2f}h over limit")
