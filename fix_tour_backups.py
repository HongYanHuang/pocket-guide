#!/usr/bin/env python3
"""
Retroactively fix backup_pois for a tour that was created before the fix.
This adds backup_pois entries for all POIs that don't have them.
"""

import json
import sys
from pathlib import Path

def fix_tour_backups(tour_path: str):
    """Fix backup_pois for a tour"""
    tour_dir = Path(tour_path)

    # Load current tour
    tour_file = tour_dir / "tour_zh-cn.json"
    with open(tour_file, 'r') as f:
        tour = json.load(f)

    # Load generation record to get original backup_pois
    gen_files = list(tour_dir.glob("generation_record_v1_*_zh-cn.json"))
    if not gen_files:
        print("ERROR: No generation record found")
        return

    with open(gen_files[0], 'r') as f:
        gen_record = json.load(f)

    original_backup_pois = gen_record.get('poi_selection', {}).get('backup_pois', {})

    # Get all POIs currently in tour
    current_pois = []
    for day in tour['itinerary']:
        for poi_obj in day['pois']:
            current_pois.append(poi_obj['poi'])

    print(f"Tour has {len(current_pois)} POIs:")
    for poi in current_pois:
        print(f"  - {poi}")

    # Initialize backup_pois if not present
    if 'backup_pois' not in tour:
        tour['backup_pois'] = {}

    print(f"\nCurrent backup_pois entries: {list(tour['backup_pois'].keys())}")

    # For each POI in tour, ensure it has backup_pois
    for poi in current_pois:
        if poi in tour['backup_pois']:
            print(f"\n✓ {poi} already has {len(tour['backup_pois'][poi])} backups")
            continue

        print(f"\n✗ {poi} missing backup_pois, creating...")

        # Check if this POI was in the original tour (has backup_pois in gen_record)
        if poi in original_backup_pois:
            # Use original backups
            tour['backup_pois'][poi] = original_backup_pois[poi]
            print(f"  Added {len(original_backup_pois[poi])} original backups")
        else:
            # This was a replacement POI - get backups from ALL original POIs
            # (since we don't know which one it replaced, add backups from all)
            all_backups = []
            seen = set()

            for orig_poi, backups in original_backup_pois.items():
                if orig_poi not in current_pois:  # This original POI was replaced
                    # Add it as a swap option
                    if orig_poi not in seen:
                        all_backups.append({
                            'poi': orig_poi,
                            'similarity_score': 0.8,
                            'reason': f'Original POI from tour generation',
                            'substitute_scenario': 'Swap with original POI'
                        })
                        seen.add(orig_poi)

                    # Add its backups
                    for backup in backups:
                        if backup['poi'] not in seen and backup['poi'] not in current_pois:
                            all_backups.append(backup)
                            seen.add(backup['poi'])

            if all_backups:
                tour['backup_pois'][poi] = all_backups
                print(f"  Added {len(all_backups)} backups from original POIs")
            else:
                print(f"  No backups available")

    # Save updated tour
    with open(tour_file, 'w') as f:
        json.dump(tour, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Tour updated successfully!")
    print(f"backup_pois now has {len(tour['backup_pois'])} entries")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python fix_tour_backups.py <tour_directory>")
        print("Example: python fix_tour_backups.py tours/rome/rome-tour-20260206-172207-14adcf")
        sys.exit(1)

    fix_tour_backups(sys.argv[1])
