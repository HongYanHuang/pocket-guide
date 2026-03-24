#!/usr/bin/env python3
"""
Test OAuth client detection logic
"""

# Test cases for redirect URI detection
test_cases = [
    # Web - localhost
    ("http://localhost:8000/auth/callback", "web"),
    ("http://localhost:65263/auth/callback", "web"),
    ("http://localhost:5173/auth/callback", "web"),

    # Web - HTTPS
    ("https://your-domain.com/auth/callback", "web"),
    ("https://app.example.com/callback", "web"),

    # iOS - custom scheme
    ("pocketguide://auth/callback", "ios"),
    ("pocketguide://callback", "ios"),

    # Edge cases
    ("http://192.168.1.100:8000/callback", "web"),
    ("https://tunnel-url.trycloudflare.com/callback", "web"),
]

def detect_client_type(redirect_uri: str) -> str:
    """Mock detection logic from oauth_handler.py"""
    if redirect_uri.startswith("pocketguide://"):
        return "ios"
    elif redirect_uri.startswith("http://") or redirect_uri.startswith("https://"):
        return "web"
    else:
        return "web"  # Default to web

print("OAuth Client Detection Test")
print("=" * 60)
print()

for redirect_uri, expected in test_cases:
    detected = detect_client_type(redirect_uri)
    status = "✅" if detected == expected else "❌"
    print(f"{status} {redirect_uri}")
    print(f"   Expected: {expected}, Got: {detected}")
    if detected != expected:
        print(f"   ⚠️  MISMATCH!")
    print()

print("=" * 60)
print("Detection logic test complete")
