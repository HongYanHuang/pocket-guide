#!/usr/bin/env python3
"""
Migrate combo ticket metadata from POI files to city-level registry.

This script:
1. Scans all POI files in a city for combo_ticket metadata
2. Extracts unique combo tickets
3. Creates combo_tickets.yaml with deduplicated data
4. Updates POI files to use simple references instead of full metadata

Usage:
    python scripts/migrate_combo_tickets.py --city rome
    python scripts/migrate_combo_tickets.py --city rome --dry-run
    python scripts/migrate_combo_tickets.py --all-cities
"""

import argparse
import yaml
import sys
from pathlib import Path
from collections import defaultdict
from datetime import date
from typing import Dict, List, Any, Set

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.combo_ticket_loader import ComboTicketLoader


class ComboTicketMigrator:
    """Migrates combo ticket data from POI files to city-level registry"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.base_path = Path("poi_research")
        self.loader = ComboTicketLoader()

    def extract_combo_tickets_from_pois(self, city: str) -> Dict[str, Dict[str, Any]]:
        """
        Scan all POI files and extract combo ticket definitions.

        Args:
            city: City name

        Returns:
            Dictionary of combo tickets indexed by group_id
        """
        poi_dir = self.base_path / city
        if not poi_dir.exists():
            print(f"❌ City directory not found: {city}")
            return {}

        combo_tickets = {}
        conflicts = []

        print(f"\n📂 Scanning POI files in {city}...")

        for poi_file in sorted(poi_dir.glob("*.yaml")):
            if poi_file.name in ['combo_tickets.yaml', 'city_info.yaml']:
                continue

            try:
                with open(poi_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                if not data:
                    continue

                poi_name = data.get('poi', {}).get('name') or data.get('poi', 'unknown')
                combo = data.get('metadata', {}).get('combo_ticket', {})

                if not combo or not combo.get('group_id'):
                    continue

                group_id = combo['group_id']

                # Build combo ticket object
                ticket = {
                    'id': group_id,
                    'name': combo.get('name', f"Combo Ticket {group_id}"),
                    'type': combo.get('type', 'same_day_consecutive'),
                    'members': combo.get('members', []),
                    'constraints': {
                        'must_visit_together': combo.get('must_visit_together', True),
                        'max_separation_hours': combo.get('max_separation_hours', 4),
                        'visit_order': combo.get('visit_order', 'flexible'),
                        'same_day_required': combo.get('same_day_required', True),
                    }
                }

                # Add pricing if present
                if 'pricing' in combo:
                    ticket['pricing'] = combo['pricing']

                # Add booking info if present
                if 'booking_info' in combo:
                    ticket['booking_info'] = combo['booking_info']

                # Check for conflicts with existing data
                if group_id in combo_tickets:
                    existing = combo_tickets[group_id]

                    # Check if data matches
                    if existing != ticket:
                        conflicts.append({
                            'group_id': group_id,
                            'poi_file': poi_file.name,
                            'existing_from': combo_tickets[group_id].get('_source'),
                            'differences': self._find_differences(existing, ticket)
                        })

                else:
                    ticket['_source'] = poi_file.name  # Track where it came from
                    combo_tickets[group_id] = ticket
                    print(f"  ✓ Found combo ticket '{group_id}' in {poi_file.name}")

            except Exception as e:
                print(f"  ⚠️  Error reading {poi_file.name}: {e}")

        # Report conflicts
        if conflicts:
            print(f"\n⚠️  Found {len(conflicts)} conflicts:")
            for conflict in conflicts:
                print(f"\n  Combo ticket: {conflict['group_id']}")
                print(f"    First seen in: {conflict['existing_from']}")
                print(f"    Conflict in: {conflict['poi_file']}")
                print(f"    Differences: {conflict['differences']}")

            if not self.dry_run:
                response = input("\nContinue with migration? First occurrence will be used. (y/n): ")
                if response.lower() != 'y':
                    print("Migration cancelled.")
                    return {}

        # Remove internal _source field
        for ticket in combo_tickets.values():
            ticket.pop('_source', None)

        print(f"\n✓ Extracted {len(combo_tickets)} unique combo tickets")
        return combo_tickets

    def _find_differences(self, dict1: Dict, dict2: Dict) -> List[str]:
        """Find differences between two dictionaries"""
        differences = []

        all_keys = set(dict1.keys()) | set(dict2.keys())
        for key in all_keys:
            if key == '_source':
                continue

            if key not in dict1:
                differences.append(f"Missing in first: {key}")
            elif key not in dict2:
                differences.append(f"Missing in second: {key}")
            elif dict1[key] != dict2[key]:
                differences.append(f"{key}: {dict1[key]} != {dict2[key]}")

        return differences

    def create_combo_tickets_file(
        self,
        city: str,
        combo_tickets: Dict[str, Dict[str, Any]]
    ) -> bool:
        """
        Create combo_tickets.yaml for the city.

        Args:
            city: City name
            combo_tickets: Combo ticket data

        Returns:
            True if successful
        """
        output_path = self.base_path / city / "combo_tickets.yaml"

        if output_path.exists():
            print(f"\n⚠️  File already exists: {output_path}")
            if not self.dry_run:
                response = input("Overwrite? (y/n): ")
                if response.lower() != 'y':
                    print("Skipped creating combo_tickets.yaml")
                    return False

        data = {
            'combo_tickets': list(combo_tickets.values()),
            'metadata': {
                'city': city.title(),
                'last_updated': date.today().isoformat(),
                'migrated_from': 'individual POI files'
            }
        }

        if self.dry_run:
            print(f"\n[DRY RUN] Would create: {output_path}")
            print(f"  Content: {len(combo_tickets)} combo tickets")
            return True

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True
                )

            print(f"\n✓ Created {output_path}")
            print(f"  Wrote {len(combo_tickets)} combo tickets")
            return True

        except Exception as e:
            print(f"\n❌ Error creating combo_tickets.yaml: {e}")
            return False

    def update_poi_files(self, city: str, combo_tickets: Dict[str, Dict[str, Any]]) -> int:
        """
        Update POI files to use simple combo ticket references.

        Args:
            city: City name
            combo_tickets: Combo ticket data

        Returns:
            Number of POI files updated
        """
        poi_dir = self.base_path / city
        updated_count = 0

        print(f"\n📝 Updating POI files...")

        for poi_file in sorted(poi_dir.glob("*.yaml")):
            if poi_file.name in ['combo_tickets.yaml', 'city_info.yaml']:
                continue

            try:
                with open(poi_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                if not data:
                    continue

                combo = data.get('metadata', {}).get('combo_ticket', {})

                if not combo or not combo.get('group_id'):
                    continue

                group_id = combo['group_id']

                # Replace full combo_ticket with simple reference
                if 'metadata' not in data:
                    data['metadata'] = {}

                # Remove old format
                del data['metadata']['combo_ticket']

                # Add new format (simple reference)
                data['metadata']['combo_tickets'] = [group_id]

                if self.dry_run:
                    print(f"  [DRY RUN] Would update: {poi_file.name}")
                else:
                    with open(poi_file, 'w', encoding='utf-8') as f:
                        yaml.dump(
                            data,
                            f,
                            default_flow_style=False,
                            sort_keys=False,
                            allow_unicode=True
                        )
                    print(f"  ✓ Updated {poi_file.name}")

                updated_count += 1

            except Exception as e:
                print(f"  ⚠️  Error updating {poi_file.name}: {e}")

        return updated_count

    def migrate_city(self, city: str) -> bool:
        """
        Migrate combo tickets for a single city.

        Args:
            city: City name

        Returns:
            True if successful
        """
        print(f"\n{'='*60}")
        print(f"Migrating combo tickets for: {city.upper()}")
        print(f"{'='*60}")

        # Step 1: Extract combo tickets from POI files
        combo_tickets = self.extract_combo_tickets_from_pois(city)

        if not combo_tickets:
            print(f"\n✓ No combo tickets found in {city}")
            return True

        # Step 2: Create combo_tickets.yaml
        success = self.create_combo_tickets_file(city, combo_tickets)

        if not success:
            return False

        # Step 3: Update POI files
        updated_count = self.update_poi_files(city, combo_tickets)

        print(f"\n{'='*60}")
        print(f"Migration Summary for {city}:")
        print(f"  Combo tickets created: {len(combo_tickets)}")
        print(f"  POI files updated: {updated_count}")
        if self.dry_run:
            print(f"  Status: DRY RUN (no files were modified)")
        else:
            print(f"  Status: COMPLETED")
        print(f"{'='*60}")

        return True

    def migrate_all_cities(self) -> Dict[str, bool]:
        """
        Migrate all cities with POI data.

        Returns:
            Dictionary of city -> success status
        """
        results = {}

        # Find all city directories
        if not self.base_path.exists():
            print(f"❌ POI research directory not found: {self.base_path}")
            return results

        cities = [d.name for d in self.base_path.iterdir() if d.is_dir()]

        print(f"\nFound {len(cities)} cities to migrate:")
        for city in cities:
            print(f"  - {city}")

        if not self.dry_run:
            response = input("\nProceed with migration? (y/n): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return results

        for city in cities:
            results[city] = self.migrate_city(city)

        # Print overall summary
        print(f"\n{'='*60}")
        print(f"OVERALL MIGRATION SUMMARY")
        print(f"{'='*60}")
        for city, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {city}")
        print(f"{'='*60}")

        return results


def main():
    parser = argparse.ArgumentParser(
        description="Migrate combo ticket metadata to city-level registry"
    )
    parser.add_argument(
        '--city',
        type=str,
        help='City to migrate (e.g., rome, paris)'
    )
    parser.add_argument(
        '--all-cities',
        action='store_true',
        help='Migrate all cities'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    if not args.city and not args.all_cities:
        parser.error("Either --city or --all-cities must be specified")

    migrator = ComboTicketMigrator(dry_run=args.dry_run)

    if args.all_cities:
        migrator.migrate_all_cities()
    else:
        migrator.migrate_city(args.city)


if __name__ == '__main__':
    main()
