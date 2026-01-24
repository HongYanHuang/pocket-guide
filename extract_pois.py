#!/usr/bin/env python3
"""
Extract POI names from research_candidates.json

Usage:
    python3 extract_pois.py <city>
    python3 extract_pois.py Rome
    python3 extract_pois.py Rome --include-skipped

Output:
    Prints POI names (one per line) to stdout
    Use redirection to save to file: python3 extract_pois.py Rome > rome_pois.txt
"""

import json
import sys
from pathlib import Path
import argparse


def extract_poi_names(city: str, include_skipped: bool = False) -> list:
    """Extract POI names from research_candidates.json"""

    # Build path to research_candidates.json
    project_root = Path(__file__).parent
    candidates_path = project_root / "poi_research" / city / "research_candidates.json"

    if not candidates_path.exists():
        print(f"Error: No research_candidates.json found for {city}", file=sys.stderr)
        print(f"Expected path: {candidates_path}", file=sys.stderr)
        print(f"\nRun this first:", file=sys.stderr)
        print(f"  ./pocket-guide poi research {city} --count 30", file=sys.stderr)
        sys.exit(1)

    # Load JSON
    with open(candidates_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    pois = data.get('pois', [])

    if not pois:
        print(f"Error: No POIs found in research_candidates.json", file=sys.stderr)
        sys.exit(1)

    # Extract names (filter out skipped POIs unless requested)
    names = []
    skipped_count = 0

    for poi in pois:
        is_skipped = poi.get('skip', False)

        if is_skipped:
            skipped_count += 1
            if include_skipped:
                names.append(poi['name'])
        else:
            names.append(poi['name'])

    # Print stats to stderr (won't be included in redirected output)
    print(f"Found {len(names)} POIs for {city}", file=sys.stderr)
    if skipped_count > 0 and not include_skipped:
        print(f"Skipped {skipped_count} duplicate POIs (use --include-skipped to include them)", file=sys.stderr)
    print(f"---", file=sys.stderr)

    return names


def main():
    parser = argparse.ArgumentParser(
        description='Extract POI names from research_candidates.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Print to screen
  python3 extract_pois.py Rome

  # Save to file
  python3 extract_pois.py Rome > rome_pois.txt

  # Include duplicates/skipped POIs
  python3 extract_pois.py Athens --include-skipped > athens_all_pois.txt
        """
    )

    parser.add_argument('city', help='City name (e.g., Rome, Athens, Istanbul)')
    parser.add_argument('--include-skipped', action='store_true',
                        help='Include POIs marked as duplicates (skip:true)')

    args = parser.parse_args()

    # Extract names
    names = extract_poi_names(args.city, args.include_skipped)

    # Print names to stdout (one per line)
    for name in names:
        print(name)


if __name__ == '__main__':
    main()
