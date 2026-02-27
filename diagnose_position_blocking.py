"""
Diagnostic tool to show which POIs are blocked at which positions due to time window constraints
"""
import sys
sys.path.insert(0, 'src')
import yaml
import json
from pathlib import Path

# Load the tour POIs
tour_file = Path('tours/rome/rome-tour-20260227-102356-126fc9/tour_zh-tw.json')
with open(tour_file, 'r') as f:
    tour_data = json.load(f)

# Extract unique POIs
pois = []
seen = set()
for day in tour_data['itinerary']:
    for poi_obj in day['pois']:
        poi_name = poi_obj['poi']
        if poi_name not in seen:
            seen.add(poi_name)
            pois.append({
                'poi': poi_name,
                'estimated_hours': poi_obj.get('estimated_hours', 2.0)
            })

print("=" * 100)
print("POSITION BLOCKING ANALYSIS - Time Window Constraints")
print("=" * 100)
print(f"Total POIs: {len(pois)}")
print(f"Start time: 09:00 (540 minutes)")
print(f"Position timing: arrival = 09:00 + (position × 150 minutes)")
print()

# Load operation hours for each POI
poi_dir = Path('poi_research/Rome')
poi_hours = {}

def poi_name_to_filename(name):
    """Convert POI name to YAML filename"""
    return (name.lower()
            .replace(' ', '_')
            .replace('-', '_')
            .replace('(', '')
            .replace(')', '')
            .replace("'", '')
            .replace('.', '')
            .replace(',', ''))

for poi in pois:
    poi_name = poi['poi']
    filename = poi_name_to_filename(poi_name)
    poi_file = poi_dir / f"{filename}.yaml"

    if poi_file.exists():
        with open(poi_file, 'r') as f:
            data = yaml.safe_load(f)

        op_hours = data.get('metadata', {}).get('operation_hours', {})
        periods = op_hours.get('periods', [])

        if periods:
            # Get Monday hours (day 1)
            monday_periods = [p for p in periods if p.get('open', {}).get('day') == 1]
            if monday_periods:
                open_time = int(monday_periods[0].get('open', {}).get('time', '0900'))
                close_time = int(monday_periods[0].get('close', {}).get('time', '2359'))
                poi_hours[poi_name] = {
                    'open': open_time,
                    'close': close_time,
                    'open_str': f"{open_time // 100:02d}:{open_time % 100:02d}",
                    'close_str': f"{close_time // 100:02d}:{close_time % 100:02d}"
                }

# Analyze position blocking
print("Position Timing Breakdown:")
print("-" * 100)
start_minutes = 540  # 9:00 AM
positions = range(10)

position_arrivals = {}
for pos in positions:
    arrival_min = start_minutes + (pos * 150)
    h = arrival_min // 60
    m = arrival_min % 60
    arrival_hhmm = h * 100 + m
    position_arrivals[pos] = {
        'minutes': arrival_min,
        'hhmm': arrival_hhmm,
        'str': f"{h:02d}:{m:02d}"
    }
    print(f"  Position {pos}: {position_arrivals[pos]['str']} ({arrival_hhmm})")

print()
print("=" * 100)
print("POI POSITION RESTRICTIONS")
print("=" * 100)

# Track which POIs can go in which positions
position_restrictions = {}
archaeological_pass = ['Colosseum', 'Roman Forum', 'Palatine Hill']

for poi in pois:
    poi_name = poi['poi']

    if poi_name not in poi_hours:
        print(f"\n{poi_name}:")
        print(f"  ⚠️  No operation hours data - NO RESTRICTIONS")
        continue

    hours = poi_hours[poi_name]
    allowed_positions = []
    blocked_positions = []

    for pos in positions:
        arrival = position_arrivals[pos]

        # Check if arrival time is within opening hours
        if hours['open'] <= arrival['hhmm'] <= hours['close']:
            allowed_positions.append(pos)
        else:
            blocked_positions.append(pos)

    is_combo = "🎫 COMBO TICKET" if poi_name in archaeological_pass else ""
    print(f"\n{poi_name} {is_combo}:")
    print(f"  Opening hours: {hours['open_str']} - {hours['close_str']}")
    print(f"  ✅ Allowed positions: {allowed_positions}")
    print(f"  ❌ Blocked positions: {blocked_positions}")

    position_restrictions[poi_name] = {
        'allowed': allowed_positions,
        'blocked': blocked_positions,
        'num_allowed': len(allowed_positions)
    }

# Analyze combo ticket feasibility
print()
print("=" * 100)
print("COMBO TICKET ANALYSIS")
print("=" * 100)

combo_allowed = [position_restrictions.get(poi, {}).get('allowed', []) for poi in archaeological_pass]
print(f"\nArchaeological Pass POIs: {archaeological_pass}")

for poi in archaeological_pass:
    if poi in position_restrictions:
        print(f"  {poi}: positions {position_restrictions[poi]['allowed']}")
    else:
        print(f"  {poi}: NO RESTRICTIONS (no hours data)")

# Count how many POIs need early positions
early_position_demand = {}
for pos in positions:
    early_position_demand[pos] = 0

for poi_name, restrictions in position_restrictions.items():
    for pos in restrictions['allowed']:
        early_position_demand[pos] += 1

print()
print("Position Demand (how many POIs can use each position):")
print("-" * 100)
for pos in positions:
    demand = early_position_demand.get(pos, len(pois))
    print(f"  Position {pos}: {demand} POIs can arrive at {position_arrivals[pos]['str']}")

# Calculate scarcity
print()
print("SCARCITY ANALYSIS:")
print("-" * 100)
max_pois_per_day = 5  # From ILP config
print(f"Max POIs per day: {max_pois_per_day}")
print(f"Duration: 5 days")
print(f"Total position slots: {max_pois_per_day} × 5 = {max_pois_per_day * 5}")

# Count POIs with severe restrictions
restricted_pois = [poi for poi, res in position_restrictions.items() if res['num_allowed'] <= 3]
print(f"\nPOIs restricted to ≤3 positions: {len(restricted_pois)}")
for poi in restricted_pois:
    print(f"  - {poi}: {position_restrictions[poi]['num_allowed']} positions")

print()
print("⚠️  ROOT CAUSE:")
print("-" * 100)
print("The 150-minute-per-position approximation creates artificial position scarcity.")
print(f"Example: Colosseum (2.5h) + Roman Forum (1.5h) + Palatine Hill (1.5h) = 5.5h total")
print(f"Reality: Could easily fit in a single day with proper timing")
print(f"ILP model: Forces each to occupy separate 150-min slots (7.5h total)")
print()
print("When combo tickets force all 3 on same day, they occupy 3 early positions.")
print("Other POIs with early closing times ALSO need early positions.")
print("Result: INFEASIBLE due to artificial position scarcity, not actual time constraints!")
