import requests
import time
import json


def test_services():
    """Test both services and generate traces"""

    print("🎲 Testing Microservices with Distributed Tracing\n")

    # Test endpoints
    endpoints = [
        ("GET", "http://localhost:5000/", "Main service - dice roll + user"),
        ("GET", "http://localhost:5000/roll", "Dice roll only"),
        ("GET", "http://localhost:5001/health", "User service health"),
        ("GET", "http://localhost:5001/users/random", "Random user"),
        ("GET", "http://localhost:5000/user/1", "Get specific user via main service"),
        ("GET", "http://localhost:5000/user/999", "Get non-existent user (error case)"),
    ]

    for method, url, description in endpoints:
        print(f"📡 Testing: {description}")
        print(f"   URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            print(f"   ✅ Status: {response.status_code}")

            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                if 'tracking_id' in data:
                    print(f"   🔍 Tracking ID: {data['tracking_id']}")
                if 'user' in data:
                    print(f"   👤 User: {data['user']['name']} (ID: {data['user']['id']})")
                if 'dice_roll' in data:
                    print(f"   🎲 Dice Roll: {data['dice_roll']}")
                if 'rolls' in data:
                    print(f"   🎲 Multiple Rolls: {data['rolls']} (Total: {data['total']})")

        except requests.exceptions.RequestException as e:
            print(f"   ❌ Error: {e}")

        print()
        time.sleep(1)  # Small delay between requests

    print("🔍 Check Jaeger UI at http://localhost:16686")
    print("   Look for services:")
    print("   - dice-roller-service")
    print("   - user-service")
    print("\n💡 You should see distributed traces showing:")
    print("   - HTTP requests between services")
    print("   - Span relationships (parent-child)")
    print("   - Request propagation across service boundaries")


if __name__ == "__main__":
    test_services()