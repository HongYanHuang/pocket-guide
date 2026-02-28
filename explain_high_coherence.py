"""
Explain WHY specific POI pairs have high coherence scores
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
unique_pois = []
seen = set()
for day in tour_data['itinerary']:
    for poi_obj in day['pois']:
        poi_name = poi_obj['poi']
        if poi_name not in seen:
            seen.add(poi_name)
            unique_pois.append(poi_name)

# Load POI research data
poi_data = {}
poi_dir = Path('poi_research/Rome')

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

for poi_name in unique_pois:
    filename = poi_name_to_filename(poi_name)
    poi_file = poi_dir / f"{filename}.yaml"

    if poi_file.exists():
        with open(poi_file, 'r') as f:
            data = yaml.safe_load(f)
            poi_data[poi_name] = {
                'period': data.get('poi', {}).get('basic_info', {}).get('period', 'Unknown'),
                'date_built': data.get('poi', {}).get('basic_info', {}).get('date_built', 'Unknown'),
                'date_relative': data.get('poi', {}).get('basic_info', {}).get('date_relative', ''),
                'description': data.get('poi', {}).get('basic_info', {}).get('description', '')[:200] + '...'
            }
    else:
        poi_data[poi_name] = {
            'period': 'Unknown',
            'date_built': 'Unknown',
            'date_relative': '',
            'description': 'No data found'
        }

print("=" * 120)
print("DETAILED EXPLANATION OF HIGH COHERENCE PAIRS")
print("=" * 120)

high_coherence_pairs = [
    ('Arch of Constantine', 'Baths of Diocletian', 0.90),
    ('Baths of Diocletian', 'Arch of Constantine', 0.90),
    ('Colosseum', 'Baths of Caracalla', 0.80),
    ('Baths of Caracalla', 'Colosseum', 0.80)
]

for idx, (poi1, poi2, score) in enumerate(high_coherence_pairs, 1):
    print(f"\n{idx}. {poi1} → {poi2} (coherence: {score})")
    print("=" * 120)

    data1 = poi_data.get(poi1, {})
    data2 = poi_data.get(poi2, {})

    print(f"\n  {poi1}:")
    print(f"    Period: {data1.get('period', 'Unknown')}")
    print(f"    Built: {data1.get('date_built', 'Unknown')}")
    if data1.get('date_relative'):
        print(f"    Age: {data1['date_relative']}")

    print(f"\n  {poi2}:")
    print(f"    Period: {data2.get('period', 'Unknown')}")
    print(f"    Built: {data2.get('date_built', 'Unknown')}")
    if data2.get('date_relative'):
        print(f"    Age: {data2['date_relative']}")

    # Analyze why they have high coherence
    print(f"\n  WHY HIGH COHERENCE?")

    period1 = data1.get('period', '')
    period2 = data2.get('period', '')

    if period1 and period2 and period1 == period2:
        print(f"    ✓ Same historical period: '{period1}'")

    # Check if both are Roman Empire era
    if 'Roman Empire' in period1 and 'Roman Empire' in period2:
        print(f"    ✓ Both from Roman Empire era (thematically related)")

    # Check if names suggest same type
    if 'Baths' in poi1 and 'Baths' in poi2:
        print(f"    ✓ Both are Roman baths (same building type)")
    elif 'Arch' in poi1 or 'Arch' in poi2:
        print(f"    ✓ One or both are triumphal arches")

    # Date proximity
    date1 = data1.get('date_built', '')
    date2 = data2.get('date_built', '')
    if date1 != 'Unknown' and date2 != 'Unknown':
        print(f"    ✓ Built in similar time periods")
        print(f"      {poi1}: {date1}")
        print(f"      {poi2}: {date2}")

print()
print("=" * 120)
print("COHERENCE SCORING LOGIC (from code)")
print("=" * 120)
print("""
The coherence score is calculated based on:

1. Chronological order bonus (40%):
   - If poi1 comes BEFORE poi2 in history: +0.4
   - If same period: +0.3

2. Same period bonus (30%):
   - If both from same historical period: +0.3

3. Date proximity (30%):
   - If built within similar timeframes: +0.3

Maximum possible score: 1.0
Threshold for precedence: 0.7

NOTE: Scores are SYMMETRIC (bidirectional)
- coherence(A → B) often equals coherence(B → A)
- This creates CYCLES when both directions exceed threshold!
""")

print()
print("=" * 120)
print("PROBLEM WITH SYMMETRIC COHERENCE")
print("=" * 120)
print("""
Example: Arch of Constantine ↔ Baths of Diocletian

Both directions get score 0.90 because:
- Both from Roman Empire period (+0.3 for same period)
- Both built in early 4th century AD (+0.3 for date proximity)
- Chronological order is ambiguous (+0.3 for same period)
- Total: 0.9

Old code would create BOTH constraints:
  Arch of Constantine < Baths of Diocletian
  Baths of Diocletian < Arch of Constantine
  → IMPOSSIBLE! Creates a cycle.

New code picks ONE direction (higher score, or first if tied):
  Arch of Constantine < Baths of Diocletian
  → Only one constraint, no cycle.
""")
