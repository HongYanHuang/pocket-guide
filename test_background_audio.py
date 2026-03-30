#!/usr/bin/env python3
"""
Test Background Audio Generation

Tests the audio generation system without actually generating audio.
Verifies:
1. AudioGenerationTask initialization
2. Status file creation
3. Status retrieval
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from audio_background import AudioGenerationTask
from utils import load_config


def test_audio_task_manager():
    """Test AudioGenerationTask initialization and status tracking"""
    print("=" * 60)
    print("Testing Audio Background Generation System")
    print("=" * 60)
    print()

    # Test 1: Load config and initialize
    print("Test 1: Initialize AudioGenerationTask")
    try:
        config = load_config()
        audio_manager = AudioGenerationTask(config)
        print("✓ AudioGenerationTask initialized successfully")
        print(f"  Status directory: {audio_manager.status_dir}")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False

    # Test 2: Check status for non-existent tour
    print("\nTest 2: Get status for non-existent tour")
    try:
        status = audio_manager.get_status("test-tour-nonexistent")
        print("✓ Status retrieved for non-existent tour")
        print(f"  Status: {status['status']}")
        assert status['status'] == 'not_started', "Expected 'not_started' status"
        print("✓ Correct default status returned")
    except Exception as e:
        print(f"✗ Failed to get status: {e}")
        return False

    # Test 3: Create status file (simulate background task)
    print("\nTest 3: Simulate status file creation")
    try:
        test_tour_id = "test-tour-12345"
        test_status = {
            'tour_id': test_tour_id,
            'status': 'generating',
            'progress': 50,
            'total_pois': 5,
            'completed_pois': 2,
            'failed_pois': [],
            'error_message': None,
            'started_at': '2026-03-30T10:00:00',
            'completed_at': None,
            'provider': 'edge',
            'language': 'zh-tw',
            'city': 'Taipei'
        }
        audio_manager._save_status(test_tour_id, test_status)
        print(f"✓ Status file created for {test_tour_id}")

        # Verify we can retrieve it
        retrieved_status = audio_manager.get_status(test_tour_id)
        print("✓ Status retrieved successfully")
        print(f"  Status: {retrieved_status['status']}")
        print(f"  Progress: {retrieved_status['progress']}%")
        print(f"  Completed POIs: {retrieved_status['completed_pois']}/{retrieved_status['total_pois']}")

        # Cleanup
        status_file = audio_manager.status_dir / f"{test_tour_id}_audio.json"
        if status_file.exists():
            status_file.unlink()
            print("✓ Test status file cleaned up")

    except Exception as e:
        print(f"✗ Failed status file test: {e}")
        return False

    # Test 4: Test API models import
    print("\nTest 4: Verify API models")
    try:
        from api_models import TourAudioStatus
        test_model = TourAudioStatus(
            tour_id="test",
            status="completed",
            progress=100,
            total_pois=5,
            completed_pois=5,
            failed_pois=[],
            error_message=None,
            started_at="2026-03-30T10:00:00",
            completed_at="2026-03-30T10:05:00",
            provider="edge",
            language="en",
            city="Rome"
        )
        print("✓ TourAudioStatus model validated successfully")
        print(f"  Model: {test_model.tour_id}, {test_model.status}")
    except Exception as e:
        print(f"✗ Failed to validate model: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ All tests passed!")
    print("=" * 60)
    return True


if __name__ == '__main__':
    success = test_audio_task_manager()
    sys.exit(0 if success else 1)
