"""
Analyze ALL coherence scores and show which ones create precedence constraints
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
            unique_pois.append({
                'poi': poi_name,
                'estimated_hours': poi_obj.get('estimated_hours', 2.0),
                'priority': 'high'
            })

optimizer = ItineraryOptimizerAgent(config)

# Load metadata
enriched_pois = optimizer._enrich_pois_with_metadata(unique_pois, 'Rome')

# Calculate coherence scores
coherence_scores = optimizer._calculate_coherence_scores(enriched_pois)

print("=" * 120)
print("COMPLETE COHERENCE SCORE ANALYSIS")
print("=" * 120)
print(f"Total POIs: {len(enriched_pois)}")
print(f"Total pairs: {len(enriched_pois) * (len(enriched_pois) - 1)}")
print()

# Get threshold from config
threshold = config.get('optimization', {}).get('precedence_soft_threshold', 0.7)
print(f"Precedence threshold: {threshold}")
print(f"Pairs with coherence >= {threshold} will create precedence constraints")
print()

# Collect all scores
all_scores = []
for (poi1, poi2), score in coherence_scores.items():
    if poi1 != poi2:  # Skip self-pairs
        all_scores.append({
            'from': poi1,
            'to': poi2,
            'score': score
        })

# Sort by score descending
all_scores.sort(key=lambda x: x['score'], reverse=True)

# Show high coherence pairs
print("=" * 120)
print(f"HIGH COHERENCE PAIRS (score >= {threshold})")
print("=" * 120)

high_coherence = [s for s in all_scores if s['score'] >= threshold]
print(f"Found {len(high_coherence)} pairs with coherence >= {threshold}")
print()

if high_coherence:
    for idx, pair in enumerate(high_coherence, 1):
        print(f"{idx:3d}. {pair['from']:45s} → {pair['to']:45s} score: {pair['score']:.2f}")

print()
print("=" * 120)
print("CHECKING FOR BIDIRECTIONAL PAIRS (potential cycles)")
print("=" * 120)

# Find bidirectional high coherence
bidirectional = []
for pair in high_coherence:
    # Check if reverse pair also has high coherence
    reverse_score = coherence_scores.get((pair['to'], pair['from']), 0)
    if reverse_score >= threshold:
        # Check if we haven't already added the reverse
        if not any(b['poi1'] == pair['to'] and b['poi2'] == pair['from'] for b in bidirectional):
            bidirectional.append({
                'poi1': pair['from'],
                'poi2': pair['to'],
                'score_12': pair['score'],
                'score_21': reverse_score
            })

if bidirectional:
    print(f"Found {len(bidirectional)} BIDIRECTIONAL pairs (would create cycles in old code):")
    print()
    for idx, pair in enumerate(bidirectional, 1):
        print(f"{idx}. {pair['poi1']:45s} ↔ {pair['poi2']:45s}")
        print(f"   {pair['poi1']:45s} → {pair['poi2']:45s} score: {pair['score_12']:.2f}")
        print(f"   {pair['poi2']:45s} → {pair['poi1']:45s} score: {pair['score_21']:.2f}")
        print()
else:
    print("No bidirectional high-coherence pairs found")

print()
print("=" * 120)
print("MEDIUM COHERENCE PAIRS (0.5 <= score < 0.7)")
print("=" * 120)

medium_coherence = [s for s in all_scores if 0.5 <= s['score'] < threshold]
print(f"Found {len(medium_coherence)} pairs with medium coherence")
print("(Showing first 20):")
print()

for idx, pair in enumerate(medium_coherence[:20], 1):
    print(f"{idx:3d}. {pair['from']:45s} → {pair['to']:45s} score: {pair['score']:.2f}")

if len(medium_coherence) > 20:
    print(f"\n... and {len(medium_coherence) - 20} more medium coherence pairs")

print()
print("=" * 120)
print("ANALYSIS SUMMARY")
print("=" * 120)
print(f"Total POI pairs: {len(all_scores)}")
print(f"High coherence (>= {threshold}): {len(high_coherence)} pairs")
print(f"Medium coherence (0.5-{threshold}): {len(medium_coherence)} pairs")
print(f"Low coherence (< 0.5): {len(all_scores) - len(high_coherence) - len(medium_coherence)} pairs")
print()
print(f"Bidirectional high-coherence pairs: {len(bidirectional)}")
print()
print("With OLD code: Would create", len(high_coherence), "precedence constraints")
print("              Including", len(bidirectional), "cycles (impossible!)")
print()
print("With NEW code: Creates", len(high_coherence) - len(bidirectional), "precedence constraints")
print("              No cycles (uses stronger direction for bidirectional pairs)")
