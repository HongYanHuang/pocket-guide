#!/usr/bin/env python3
"""
Lightweight script to update visit_info for Rome POIs using AI estimation.
Only researches visit duration/accessibility, not full historical content.
"""

import sys
sys.path.insert(0, 'src')

import yaml
from pathlib import Path
from utils import load_config
from content_generator import ContentGenerator

def estimate_visit_info(poi_name: str, city: str, description: str, config: dict, provider: str = "anthropic") -> dict:
    """
    Use AI to estimate visit information for a POI.

    Args:
        poi_name: POI name
        city: City name
        description: POI description from research
        config: Application config
        provider: AI provider

    Returns:
        Dictionary with typical_duration_minutes, indoor_outdoor, accessibility
    """
    prompt = f"""
You are a travel planning expert. Estimate realistic visit information for this POI.

POI: {poi_name}
City: {city}
Description: {description}

Based on this POI's characteristics, estimate:

1. typical_duration_minutes: How long do visitors typically spend here?
   - Consider: Size of site, what there is to see, queue times, walking distance
   - Examples:
     * Vatican Museums (large museum, 50+ rooms): 150 minutes
     * Colosseum (large archaeological site): 120 minutes
     * Pantheon (single building, impressive interior): 60 minutes
     * Trevi Fountain (small fountain, photo stop): 15 minutes
     * Small church: 30 minutes
     * Large basilica: 60 minutes

2. indoor_outdoor: Is this primarily indoor, outdoor, or mixed?
   - "indoor": Museums, churches, palaces (mostly covered)
   - "outdoor": Fountains, ruins, squares, parks
   - "mixed": Palaces with gardens, sites with both elements

3. accessibility: Wheelchair accessibility level
   - "full": Flat, elevator access, ramps available
   - "partial": Some areas accessible, may have limitations
   - "limited": Stairs, uneven ground, difficult access

Output ONLY valid YAML in this exact format (no markdown, no extra text):

typical_duration_minutes: 120
indoor_outdoor: indoor
accessibility: partial
"""

    # Create content generator (uses existing AI calling logic)
    generator = ContentGenerator(config)

    # Call AI using the appropriate provider method
    if provider == 'anthropic':
        response = generator._generate_anthropic(prompt)
    elif provider == 'openai':
        response = generator._generate_openai(prompt)
    elif provider == 'google':
        response = generator._generate_google(prompt)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Parse YAML response
    try:
        # Strip markdown code fences if present
        content = response.strip()
        if content.startswith('```'):
            lines = content.split('\n')
            lines = [l for l in lines if not l.strip().startswith('```')]
            content = '\n'.join(lines)

        visit_info = yaml.safe_load(content)

        # Validate required fields
        if not isinstance(visit_info, dict):
            raise ValueError("Response is not a dictionary")
        if 'typical_duration_minutes' not in visit_info:
            raise ValueError("Missing typical_duration_minutes")

        return visit_info
    except Exception as e:
        print(f"  ⚠ Failed to parse AI response for {poi_name}: {e}")
        print(f"  Raw response: {response[:100]}...")
        return {
            'typical_duration_minutes': 60,
            'indoor_outdoor': 'unknown',
            'accessibility': 'unknown'
        }

def update_rome_pois_with_provider(provider: str = "anthropic"):
    """Update visit_info for all Rome POIs.

    Args:
        provider: AI provider to use (anthropic, openai, google)
    """
    # Load config
    config = load_config()

    rome_dir = Path("poi_research/Rome")

    if not rome_dir.exists():
        print("Error: poi_research/Rome directory not found")
        return

    yaml_files = list(rome_dir.glob("*.yaml"))
    yaml_files = [f for f in yaml_files if f.stem != "research_candidates"]

    print(f"Found {len(yaml_files)} Rome POIs")
    print("=" * 60)

    updated = 0
    skipped = 0

    for yaml_file in sorted(yaml_files):
        poi_name = yaml_file.stem.replace('_', ' ').title()

        try:
            # Load existing data
            with open(yaml_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            poi_data = data.get('poi', {})

            # Check if visit_info already exists (from research, not metadata)
            if 'visit_info' in poi_data and poi_data['visit_info']:
                print(f"⊘ {poi_name}: Already has visit_info, skipping")
                skipped += 1
                continue

            # Get description
            basic_info = poi_data.get('basic_info', {})
            description = basic_info.get('description', '')

            if not description:
                print(f"⚠ {poi_name}: No description found, skipping")
                skipped += 1
                continue

            # Estimate visit info using AI
            print(f"🔍 {poi_name}: Estimating visit info...")
            visit_info = estimate_visit_info(
                poi_name=poi_data.get('name', poi_name),
                city="Rome",
                description=description,
                config=config,
                provider=provider
            )

            # Update POI data
            poi_data['visit_info'] = visit_info

            # Write back to file
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            duration = visit_info.get('typical_duration_minutes', 0)
            indoor_outdoor = visit_info.get('indoor_outdoor', 'unknown')
            print(f"  ✓ {duration}min, {indoor_outdoor}")
            updated += 1

        except Exception as e:
            print(f"  ✗ Error processing {poi_name}: {e}")
            continue

    print("=" * 60)
    print(f"✓ Updated: {updated} POIs")
    print(f"⊘ Skipped: {skipped} POIs")
    print(f"Total: {len(yaml_files)} POIs")

# Backward compatibility
def update_rome_pois():
    """Update visit_info for all Rome POIs using default provider (anthropic)."""
    update_rome_pois_with_provider("anthropic")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Update Rome POI visit info using AI')
    parser.add_argument(
        '--provider',
        choices=['anthropic', 'openai', 'google'],
        default='anthropic',
        help='AI provider to use (default: anthropic/Claude)'
    )
    args = parser.parse_args()

    provider_names = {
        'anthropic': 'Claude (Anthropic)',
        'openai': 'ChatGPT (OpenAI)',
        'google': 'Gemini (Google)'
    }

    print("Rome POI Visit Info Updater")
    print("=" * 60)
    print(f"AI Provider: {provider_names[args.provider]}")
    print("This script uses AI to estimate visit duration and accessibility")
    print("for Rome POIs. It only updates POIs that don't have visit_info yet.")
    print("=" * 60)
    print()

    try:
        # Pass provider to update function
        update_rome_pois_with_provider(args.provider)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
