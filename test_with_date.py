"""Test with trip_start_date to trigger opening hours"""
import sys
sys.path.insert(0, 'src')
from datetime import datetime
import yaml
from trip_planner.itinerary_optimizer import ItineraryOptimizerAgent

with open('config.yaml') as f:
    config = yaml.safe_load(f)

# Minimal POI set with combo ticket
selected_pois = [
    {'poi': 'Colosseum', 'estimated_hours': 2.0, 'priority': 'high'},
    {'poi': 'Roman Forum', 'estimated_hours': 2.0, 'priority': 'high'},
    {'poi': 'Palatine Hill', 'estimated_hours': 1.5, 'priority': 'high'},
    {'poi': 'Pantheon', 'estimated_hours': 0.8, 'priority': 'medium'},
    {'poi': 'Piazza Navona', 'estimated_hours': 0.8, 'priority': 'medium'},
]

optimizer = ItineraryOptimizerAgent(config)

print("Testing ILP with trip_start_date (triggers opening hours)...")
try:
    result = optimizer.optimize_itinerary(
        selected_pois=selected_pois,
        city='Rome',
        duration_days=3,
        mode='ilp',
        trip_start_date=datetime(2026, 3, 15)  # Saturday
    )
    print(f"✓ SUCCESS: {result.get('solver_stats', {}).get('status', 'N/A')}")
    
    # Check combo
    for day in result['itinerary']:
        pois = [p['poi'] for p in day['pois']]
        combo_count = sum(1 for p in pois if p in ['Colosseum', 'Roman Forum', 'Palatine Hill'])
        if combo_count > 0:
            print(f"  Day {day['day']}: {pois} ({combo_count}/3 combo POIs)")
            
except Exception as e:
    print(f"✗ FAILED: {e}")
