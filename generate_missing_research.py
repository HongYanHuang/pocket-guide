#!/usr/bin/env python3
"""
Generate research YAML files for existing POIs that were created with --skip-research
"""
import sys
import yaml
from pathlib import Path
from src.research_agent import ResearchAgent
from src.utils import load_config

def generate_research_for_poi(city: str, poi_name: str, provider: str = 'anthropic'):
    """Generate and save research YAML for a single POI"""
    config = load_config()

    # Initialize research agent
    agent = ResearchAgent(config)

    # Create research directory
    research_dir = Path("poi_research") / city
    research_dir.mkdir(parents=True, exist_ok=True)

    # Create filename (kebab-case to snake_case)
    safe_name = poi_name.lower().replace(' ', '_').replace('-', '_')
    research_path = research_dir / f"{safe_name}.yaml"

    # Check if already exists
    if research_path.exists():
        print(f"⚠️  Research already exists: {research_path}")
        return False

    print(f"🔍 Researching: {poi_name} in {city}...")

    # Perform research
    research_data = agent.research_poi_recursive(
        poi_name=poi_name,
        city=city,
        user_description="",
        provider=provider
    )

    # Save research
    with open(research_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(research_data, f, allow_unicode=True, sort_keys=False)

    print(f"✅ Saved research to: {research_path}")
    return True

def main():
    """Generate research for all Istanbul POIs that are missing it"""
    city = "Istanbul"

    # POIs that need research (based on content directory)
    pois_to_research = [
        "Süleymaniye Mosque",
        "Blue Mosque (Sultan Ahmed Mosque)",
        "Topkapı Palace",
        "Basilica Cistern",
        "Grand Bazaar",
        "Dolmabahçe Palace",
        "Galata Tower",
        "Hippodrome of Constantinople (Sultanahmet Square)",
        "Chora Church (Kariye Museum)"
    ]

    print(f"\n🎯 Generating research for {len(pois_to_research)} Istanbul POIs\n")

    succeeded = []
    failed = []
    skipped = []

    for poi_name in pois_to_research:
        try:
            result = generate_research_for_poi(city, poi_name, provider='anthropic')
            if result:
                succeeded.append(poi_name)
            else:
                skipped.append(poi_name)
        except Exception as e:
            print(f"❌ Failed for {poi_name}: {e}")
            failed.append(poi_name)
        print()  # Blank line between POIs

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"✅ Successfully generated: {len(succeeded)}")
    print(f"⏭️  Skipped (already exists): {len(skipped)}")
    print(f"❌ Failed: {len(failed)}")

    if succeeded:
        print(f"\n✨ Generated research files:")
        for poi in succeeded:
            print(f"   • {poi}")

    if failed:
        print(f"\n⚠️  Failed POIs:")
        for poi in failed:
            print(f"   • {poi}")

if __name__ == "__main__":
    main()
