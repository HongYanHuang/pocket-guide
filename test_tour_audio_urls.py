"""
Test script to verify tour API includes audio URLs
"""
import requests
import json

BASE_URL = "http://localhost:8000"
TOUR_ID = "rome-tour-20260320-175540-6b0704"
LANGUAGE = "zh-tw"

def test_tour_audio_urls():
    """Test that tour API returns audio URLs for POIs"""

    # Note: This tour is private, so we need auth token
    # For testing, we'll try without auth first to see the error,
    # then with a valid token

    print("=" * 60)
    print("Testing Tour API with Audio URLs")
    print("=" * 60)
    print()

    # Test 1: Try to get tour (will fail if private and no auth)
    url = f"{BASE_URL}/tours/{TOUR_ID}?language={LANGUAGE}"
    print(f"Request URL: {url}")
    print()

    response = requests.get(url)

    if response.status_code == 403:
        print("⚠️  Tour is private - requires authentication")
        print("   This is expected for client-created tours")
        print()
        print("To test with authentication:")
        print("1. Login via backstage to get token")
        print("2. Run: curl -H 'Authorization: Bearer <token>' \\")
        print(f"        '{url}'")
        print()
        return

    if response.status_code != 200:
        print(f"✗ Error: {response.status_code}")
        print(f"  {response.json()}")
        return

    # Success - parse response
    tour = response.json()

    print("✓ Tour loaded successfully")
    print()

    # Check first POI in first day
    if 'itinerary' in tour and len(tour['itinerary']) > 0:
        first_day = tour['itinerary'][0]
        print(f"Day {first_day['day']}:")
        print(f"  POIs: {len(first_day['pois'])}")
        print()

        for i, poi in enumerate(first_day['pois'][:3], 1):  # Show first 3 POIs
            print(f"POI #{i}:")
            print(f"  Name: {poi['poi']}")
            print(f"  POI ID: {poi.get('poi_id', 'NOT PROVIDED')}")
            print(f"  Audio Available: {poi.get('audio_available', 'NOT PROVIDED')}")
            print(f"  Audio URL: {poi.get('audio_url', 'NOT PROVIDED')}")

            # Test if audio URL works
            if poi.get('audio_url'):
                audio_url = BASE_URL + poi['audio_url']
                print(f"  Testing audio URL...")
                audio_response = requests.head(audio_url)
                if audio_response.status_code == 200:
                    size = audio_response.headers.get('Content-Length', 'unknown')
                    print(f"    ✓ Audio accessible (Size: {int(size)/1024/1024:.1f} MB)")
                else:
                    print(f"    ✗ Audio not accessible ({audio_response.status_code})")

            print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)

    total_pois = sum(len(day['pois']) for day in tour['itinerary'])
    pois_with_audio = sum(
        1 for day in tour['itinerary']
        for poi in day['pois']
        if poi.get('audio_available')
    )

    print(f"Total POIs: {total_pois}")
    print(f"POIs with audio: {pois_with_audio}")
    print(f"Coverage: {pois_with_audio/total_pois*100:.0f}%")


if __name__ == "__main__":
    test_tour_audio_urls()
