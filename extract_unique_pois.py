#!/usr/bin/env python3
"""
Extract unique POI names from research_candidates.json
Skips duplicates (entries with skip=true)
"""
import json
import sys
from pathlib import Path


def extract_unique_pois(city: str, output_file: str = None):
    """
    Extract unique POI names from research_candidates.json

    Args:
        city: City name (e.g., 'rome', 'paris')
        output_file: Output file path (default: unique_pois_{city}.txt)
    """
    # Find research_candidates.json
    project_root = Path(__file__).parent
    candidates_path = project_root / 'poi_research' / city / 'research_candidates.json'

    if not candidates_path.exists():
        print(f"❌ Error: {candidates_path} not found", file=sys.stderr)
        print(f"Run 'poi research {city}' or 'poi fulfill {city}' first", file=sys.stderr)
        sys.exit(1)

    # Load candidates
    with open(candidates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Filter unique POIs (skip=false or skip not present)
    unique_pois = []
    skipped_pois = []

    for poi in data['pois']:
        if poi.get('skip', False):
            skipped_pois.append(poi.get('name', 'Unknown'))
        else:
            unique_pois.append(poi.get('name', 'Unknown'))

    # Output file
    if not output_file:
        output_file = f"unique_pois_{city}.txt"

    # Write to file
    output_path = Path(output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        for poi in unique_pois:
            f.write(f"{poi}\n")

    # Print summary to stderr (so it doesn't interfere with stdout redirection)
    print(f"✅ Extracted unique POIs for {city}", file=sys.stderr)
    print(f"   📄 Output: {output_path}", file=sys.stderr)
    print(f"   ✓ Unique POIs: {len(unique_pois)}", file=sys.stderr)
    print(f"   ⊗ Skipped (duplicates): {len(skipped_pois)}", file=sys.stderr)

    if skipped_pois:
        print(f"\n📋 Skipped POIs (duplicates):", file=sys.stderr)
        for poi in skipped_pois[:10]:  # Show first 10
            print(f"   - {poi}", file=sys.stderr)
        if len(skipped_pois) > 10:
            print(f"   ... and {len(skipped_pois) - 10} more", file=sys.stderr)

    print(f"\n🚀 Next step:", file=sys.stderr)
    print(f"   ./pocket-guide poi batch-generate {output_file} --city {city}", file=sys.stderr)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_unique_pois.py <city> [output_file]")
        print()
        print("Examples:")
        print("  python3 extract_unique_pois.py rome")
        print("  python3 extract_unique_pois.py rome my_pois.txt")
        print("  python3 extract_unique_pois.py paris unique_paris.txt")
        sys.exit(1)

    city = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    extract_unique_pois(city, output_file)
