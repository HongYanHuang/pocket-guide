#!/usr/bin/env python3
"""
Test script for tour saving and transcript linking functionality.
This allows testing the tour save logic without generating transcripts.
"""

import sys
import yaml
from pathlib import Path
from src.trip_planner.tour_manager import TourManager

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Mock tour data (similar to what trip planner generates)
mock_tour_data = {
    'itinerary': [
        {
            'day': 1,
            'pois': [
                {'poi': 'Colosseum', 'duration': 2.0, 'order': 1},
                {'poi': 'Roman Forum', 'duration': 1.5, 'order': 2},
                {'poi': 'Palatine Hill', 'duration': 1.5, 'order': 3}
            ],
            'total_time': 5.0,
            'total_distance': 1.2
        }
    ],
    'optimization_scores': {
        'distance_score': 0.85,
        'coherence_score': 0.90,
        'overall_score': 0.875
    }
}

# Mock selection result (matching POI selector structure)
mock_selection_result = {
    'starting_pois': [
        {'poi': 'Colosseum', 'reason': 'Iconic'},
        {'poi': 'Roman Forum', 'reason': 'Historical'},
        {'poi': 'Palatine Hill', 'reason': 'Archaeological'}
    ],
    'backup_pois': {
        'Colosseum': [
            {'poi': 'Trevi Fountain', 'reason': 'Nearby alternative'}
        ],
        'Roman Forum': [
            {'poi': 'Spanish Steps', 'reason': 'Alternative site'}
        ]
    },
    'rejected_pois': [
        {'poi': 'Other POI 1', 'reason': 'Too far'},
        {'poi': 'Other POI 2', 'reason': 'Not relevant'}
    ]
}

# Input parameters
input_parameters = {
    'city': 'Rome',
    'duration_days': 1,
    'interests': ['history'],
    'preferences': {'pace': 'normal', 'walking_tolerance': 'moderate'},
    'must_see': [],
    'provider': 'anthropic',
    'language': 'zh-cn'
}

def test_tour_save():
    """Test tour saving with transcript linking"""
    print("=" * 60)
    print("Testing Tour Save with Transcript Linking")
    print("=" * 60)

    # Initialize TourManager
    tour_manager = TourManager(
        config=config,
        tours_dir='tours',
        content_dir='content'
    )

    print("\n[1/3] Initializing TourManager...")
    print(f"  Tours dir: {tour_manager.tours_dir}")
    print(f"  Content dir: {tour_manager.content_dir}")

    print("\n[2/3] Saving tour...")
    try:
        result = tour_manager.save_tour(
            tour_data=mock_tour_data,
            city='rome',
            input_parameters=input_parameters,
            selection_result=mock_selection_result,
            language='zh-cn'
        )

        print("  ✓ Tour saved successfully!")
        print(f"\n  Tour ID: {result['tour_id']}")
        print(f"  Version: v{result['version']}")
        print(f"  Language: {result['language']}")
        print(f"  Tour file: {result['files']['tour']}")

        # Check transcript links
        if 'transcript_links_file' in result:
            print(f"  Links file: {result['transcript_links_file']}")

            # Read and display links
            import json
            links_path = Path(result['transcript_links_file'])
            if links_path.exists():
                with open(links_path, 'r') as f:
                    links_data = json.load(f)

                print(f"\n[3/3] Transcript Links Created:")
                print(f"  Tour ID: {links_data['tour_id']}")
                print(f"  Language: {links_data['language']}")
                print(f"  Total links: {len(links_data['links'])}")

                for i, link in enumerate(links_data['links'], 1):
                    print(f"\n  Link {i}:")
                    print(f"    POI: {link['poi']}")
                    print(f"    Path: {link['transcript_path']}")
                    print(f"    Version: {link['transcript_version']}")
                    print(f"    Type: {link['transcript_type']}")
            else:
                print("  ⚠️  Links file not found on disk")
        else:
            print("  ⚠️  No transcript links file in result")

        print("\n" + "=" * 60)
        print("✅ TEST PASSED - Tour saved successfully")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ TEST FAILED")
        print(f"Error: {e}")
        import traceback
        print(f"\nTraceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    test_tour_save()
