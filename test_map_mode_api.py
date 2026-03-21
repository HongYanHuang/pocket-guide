"""
Test script for Map Mode API endpoints

Tests all 4 endpoints:
- POST /tours/{tour_id}/progress
- GET /tours/{tour_id}/progress
- POST /tours/{tour_id}/trail
- GET /tours/{tour_id}/trail
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TOUR_ID = "rome-tour-20260320-175540-6b0704"  # Private tour by henry48124@gmail.com

# Mock JWT token (for testing - in real scenario, get from /auth/login)
# This is a placeholder - you'll need a real token from the auth system
MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJoZW5yeTQ4MTI0QGdtYWlsLmNvbSIsImVtYWlsIjoiaGVucnk0ODEyNEBnbWFpbC5jb20iLCJuYW1lIjoiSGVucnkgSHVhbmciLCJyb2xlIjoiY2xpZW50X3VzZXIiLCJzY29wZXMiOlsicmVhZF90b3VycyIsIndyaXRlX3RvdXJzIl0sImV4cCI6OTk5OTk5OTk5OX0.placeholder"

headers = {
    "Authorization": f"Bearer {MOCK_TOKEN}",
    "Content-Type": "application/json"
}


def test_update_poi_progress():
    """Test POST /tours/{tour_id}/progress"""
    print("\n=== Test 1: Update POI Progress ===")

    payload = {
        "poi_id": "colosseum",
        "day": 1,
        "completed": True
    }

    response = requests.post(
        f"{BASE_URL}/tours/{TOUR_ID}/progress",
        headers=headers,
        json=payload
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        print("✅ POI progress update successful")
    else:
        print(f"❌ Failed: {response.text}")


def test_get_tour_progress():
    """Test GET /tours/{tour_id}/progress"""
    print("\n=== Test 2: Get Tour Progress ===")

    response = requests.get(
        f"{BASE_URL}/tours/{TOUR_ID}/progress?language=zh-tw",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tour ID: {data['tour_id']}")
        print(f"Total POIs: {data['total_pois']}")
        print(f"Completed: {data['completed_count']}")
        print(f"Completion %: {data['completion_percentage']}%")
        print(f"\nFirst 3 POIs:")
        for poi in data['completions'][:3]:
            status = "✅" if poi['completed'] else "❌"
            print(f"  {status} Day {poi['day']}: {poi['poi_name']} ({poi['poi_id']})")
        print("✅ Get progress successful")
    else:
        print(f"❌ Failed: {response.text}")


def test_upload_gps_trail():
    """Test POST /tours/{tour_id}/trail"""
    print("\n=== Test 3: Upload GPS Trail ===")

    # Simulate GPS points near Colosseum
    payload = {
        "points": [
            {
                "lat": 41.8902,
                "lng": 12.4922,
                "timestamp": datetime.utcnow().isoformat(),
                "accuracy": 15.5
            },
            {
                "lat": 41.8905,
                "lng": 12.4925,
                "timestamp": datetime.utcnow().isoformat(),
                "accuracy": 12.0
            },
            {
                "lat": 41.8908,
                "lng": 12.4928,
                "timestamp": datetime.utcnow().isoformat(),
                "accuracy": 10.5
            }
        ]
    }

    response = requests.post(
        f"{BASE_URL}/tours/{TOUR_ID}/trail",
        headers=headers,
        json=payload
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    if response.status_code == 200:
        print("✅ GPS trail upload successful")
    else:
        print(f"❌ Failed: {response.text}")


def test_get_gps_trail():
    """Test GET /tours/{tour_id}/trail"""
    print("\n=== Test 4: Get GPS Trail ===")

    response = requests.get(
        f"{BASE_URL}/tours/{TOUR_ID}/trail",
        headers=headers
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tour ID: {data['tour_id']}")
        print(f"Total Points: {data['total_points']}")
        if data['points']:
            print(f"\nFirst 3 points:")
            for point in data['points'][:3]:
                print(f"  - {point['lat']}, {point['lng']} at {point['timestamp']}")
        print("✅ Get trail successful")
    else:
        print(f"❌ Failed: {response.text}")


def test_without_auth():
    """Test endpoints without authentication"""
    print("\n=== Test 5: Without Authentication ===")

    response = requests.get(
        f"{BASE_URL}/tours/{TOUR_ID}/progress",
        headers={"Content-Type": "application/json"}
    )

    print(f"Status: {response.status_code}")
    if response.status_code in [401, 403]:
        print("✅ Correctly rejected unauthenticated request")
    else:
        print(f"❌ Should have rejected: {response.text}")


if __name__ == "__main__":
    print("=" * 60)
    print("Map Mode API Test Suite")
    print("=" * 60)

    # Note: These tests will fail with 401 because we don't have a real token
    # To run properly, you need to:
    # 1. Get a real JWT token from /auth/google/login
    # 2. Replace MOCK_TOKEN with the real token

    test_update_poi_progress()
    test_get_tour_progress()
    test_upload_gps_trail()
    test_get_gps_trail()
    test_without_auth()

    print("\n" + "=" * 60)
    print("Test Suite Complete")
    print("=" * 60)
