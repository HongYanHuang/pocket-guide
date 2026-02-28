"""
Diagnose EXACT constraint conflict for Archaeological Pass POIs
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

# Extract all POIs with operation hours
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
                'operation_hours': poi_obj.get('operation_hours', {})
            })

print("=" * 100)
print("EXACT CONSTRAINT CONFLICT ANALYSIS")
print("=" * 100)

# Calculate average position duration (same as ILP)
avg_visit_minutes = sum(poi.get('estimated_hours', 2.0) for poi in pois) / len(pois) * 60
avg_travel_minutes = 30
avg_position_duration = int(avg_visit_minutes + avg_travel_minutes)

print(f"Average position duration: {avg_position_duration} minutes ({avg_position_duration/60:.2f} hours)")
print()

# Position timing
start_minutes = 540  # 09:00
max_pois_per_day = 6  # From ILP calculation
duration_days = 5

print("Position timing (based on average 110 min/position):")
print("-" * 100)
position_times = []
for pos in range(max_pois_per_day):
    arrival_min = start_minutes + (pos * avg_position_duration)
    h = arrival_min // 60
    m = arrival_min % 60
    hhmm = h * 100 + m
    position_times.append({'pos': pos, 'minutes': arrival_min, 'hhmm': hhmm, 'str': f"{h:02d}:{m:02d}"})
    print(f"  Position {pos}: {position_times[pos]['str']} ({position_times[pos]['hhmm']} in HHMM)")

print()
print("=" * 100)
print("ARCHAEOLOGICAL PASS POI CONSTRAINTS")
print("=" * 100)

arch_pois = ['Colosseum', 'Roman Forum', 'Palatine Hill']
arch_constraints = {}

for poi_name in arch_pois:
    poi_data = next((p for p in pois if p['poi'] == poi_name), None)
    if not poi_data:
        print(f"\n{poi_name}: NOT FOUND")
        continue

    hours = poi_data.get('estimated_hours', 2.0)
    op_hours = poi_data.get('operation_hours', {})
    periods = op_hours.get('periods', [])

    print(f"\n{poi_name}:")
    print(f"  Estimated duration: {hours} hours ({hours * 60:.0f} minutes)")

    if not periods:
        print(f"  ⚠️  NO OPERATION HOURS DATA")
        arch_constraints[poi_name] = {'allowed_positions': list(range(max_pois_per_day)), 'hours': hours}
        continue

    # Check Monday (day 1)
    monday_periods = [p for p in periods if p.get('open', {}).get('day') == 1]
    if not monday_periods:
        print(f"  ⚠️  CLOSED ON MONDAY")
        continue

    period = monday_periods[0]
    open_time = int(period.get('open', {}).get('time', '0000'))
    close_time = int(period.get('close', {}).get('time', '2359'))

    open_h = open_time // 100
    open_m = open_time % 100
    close_h = close_time // 100
    close_m = close_time % 100

    print(f"  Opening hours: {open_h:02d}:{open_m:02d} - {close_h:02d}:{close_m:02d} ({open_time} - {close_time} in HHMM)")

    # Check which positions are allowed
    allowed_positions = []
    blocked_positions = []

    for pos in range(max_pois_per_day):
        arrival_hhmm = position_times[pos]['hhmm']

        # Check if arrival time is within opening hours
        if open_time <= arrival_hhmm <= close_time:
            allowed_positions.append(pos)
        else:
            blocked_positions.append(pos)

    print(f"  ✅ Allowed positions: {allowed_positions}")
    print(f"  ❌ Blocked positions: {blocked_positions}")

    arch_constraints[poi_name] = {
        'allowed_positions': allowed_positions,
        'blocked_positions': blocked_positions,
        'hours': hours,
        'open_time': open_time,
        'close_time': close_time
    }

print()
print("=" * 100)
print("CONSTRAINT CONFLICT ANALYSIS")
print("=" * 100)

# Calculate total hours
total_hours = sum(c['hours'] for c in arch_constraints.values())
print(f"\nTotal duration for 3 POIs: {total_hours} hours")
print(f"Available time per day: 7.5 hours (based on 'normal' pace)")
print(f"Duration check: {total_hours} ≤ 7.5? {'✅ YES' if total_hours <= 7.5 else '❌ NO'}")

print()
print("Position-based constraint check:")
print("-" * 100)

# Find common allowed positions
if len(arch_constraints) == 3:
    common_positions = set(arch_constraints['Colosseum']['allowed_positions'])
    for poi_name in ['Roman Forum', 'Palatine Hill']:
        common_positions &= set(arch_constraints[poi_name]['allowed_positions'])

    print(f"Common allowed positions (all 3 can use): {sorted(common_positions)}")
    print(f"Number of common positions: {len(common_positions)}")

    print()
    if len(common_positions) >= 3:
        print("✅ There are enough common positions (3+) for all 3 POIs on same day")
        print("   → Position constraint should NOT cause INFEASIBLE")
    else:
        print(f"❌ Only {len(common_positions)} common positions available")
        print("   → Cannot fit all 3 POIs on same day with current constraints")
        print("   → THIS IS WHY IT'S INFEASIBLE!")

print()
print("=" * 100)
print("ROOT CAUSE")
print("=" * 100)

# Check if the issue is the position-based arrival time
print("\nThe problem with position-based timing:")
print("-" * 100)
print("ILP model assumes:")
print(f"  - Position 0 POI arrives at 09:00 and stays until next position")
print(f"  - Position 1 POI arrives at 10:50 and stays until next position")
print(f"  - Position 2 POI arrives at 12:40 and stays until next position")
print(f"  - etc.")
print()
print("Reality:")
print(f"  - Colosseum (2.0h): 09:00-11:00")
print(f"  - Roman Forum (2.0h): 11:30-13:30")
print(f"  - Palatine Hill (1.5h): 14:00-15:30")
print(f"  - Total: 09:00-15:30 (6.5h including travel) ✅ Fits before 16:30 closing!")
print()
print("The position-based model doesn't know the actual visit duration,")
print("so it can't accurately determine if a POI fits in the opening hours.")
