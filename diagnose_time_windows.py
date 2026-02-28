"""Diagnose which POIs have restrictive time windows"""
import sys
sys.path.insert(0, 'src')
import yaml
from pathlib import Path

# Check which POIs have early closing times
poi_dir = Path('poi_research/Rome')

print("POIs with early closing times (before 5:00 PM):")
print("=" * 80)

for poi_file in sorted(poi_dir.glob('*.yaml')):
    if poi_file.name in ['combo_tickets.yaml', 'city_info.yaml']:
        continue
    
    with open(poi_file, 'r') as f:
        data = yaml.safe_load(f)
    
    poi_name = data.get('poi', {}).get('name', poi_file.stem)
    op_hours = data.get('metadata', {}).get('operation_hours', {})
    periods = op_hours.get('periods', [])
    
    if periods:
        # Check closing time for weekdays (assume day 1 = Monday)
        monday_periods = [p for p in periods if p.get('open', {}).get('day') == 1]
        if monday_periods:
            close_time = int(monday_periods[0].get('close', {}).get('time', '2359'))
            if close_time < 1700:  # Before 5:00 PM
                close_hour = close_time // 100
                close_min = close_time % 100
                print(f"  {poi_name:45s} closes at {close_hour:02d}:{close_min:02d}")
                
                # Calculate which positions are blocked
                # Position arrival: 09:00 + (pos * 150 min)
                start_min = 540  # 9:00 AM
                for pos in range(10):
                    arrival_min = start_min + (pos * 150)
                    arrival_hhmm = (arrival_min // 60) * 100 + (arrival_min % 60)
                    if arrival_hhmm > close_time:
                        print(f"    └─ Position {pos}+ blocked (arrival {arrival_hhmm // 100:02d}:{arrival_hhmm % 100:02d} > closing)")
                        break

print()
print("Position timing breakdown (150 min/position assumption):")
print("-" * 80)
for pos in range(6):
    arrival_min = 540 + (pos * 150)
    h = arrival_min // 60
    m = arrival_min % 60
    print(f"  Position {pos}: arrival ~{h:02d}:{m:02d}")
