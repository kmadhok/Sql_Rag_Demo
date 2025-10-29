"""
Test Browser Simulation

Simulates exactly what the browser does to debug CORS and network issues.
"""

import requests
import json
from urllib.parse import urlparse

# Configuration
test_urls = [
    "http://127.0.0.1:80/api/chat/",      # Through nginx
    "http://localhost:80/api/chat/",       # Through nginx alternative
    "http://127.0.0.1:8000/api/chat/",    # Direct backend
]

payload = {
    "message": "Browser simulation test",
    "agent_type": "normal"
}

def test_endpoint(url, description):
    """Test a specific endpoint with browser-like headers"""
    print(f"\n{'='*60}")
    print(f"🌐 TESTING: {description}")
    print(f"🔗 URL: {url}")
    print(f"{'='*60}")
    
    # Browser-like headers
    headers = {
        "Content-Type": "application/json",
        "Origin": "http://127.0.0.1:80",
        "Referer": "http://127.0.0.1:80/"
    }
    
    try:
        # First try OPTIONS (CORS preflight)
        print(f"\n📡 1. Testing CORS preflight (OPTIONS)...")
        options_response = requests.options(
            url, 
            headers=headers,
            timeout=10
        )
        print(f"   Status: {options_response.status_code}")
        if options_response.status_code == 200 or options_response.status_code == 204:
            print(f"   ✅ CORS preflight successful")
            print(f"   CORS Headers: {dict(options_response.headers)}")
        else:
            print(f"   ❌ CORS preflight failed: {options_response.text}")
        
        # Then try actual POST
        print(f"\n📤 2. Testing actual POST request...")
        post_response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=10
        )
        print(f"   Status: {post_response.status_code}")
        print(f"   Headers: {dict(post_response.headers)}")
        
        if post_response.status_code == 200:
            result = post_response.json()
            print(f"   ✅ SUCCESS! Chat response:")
            print(f"     🤖 Message: {result.get('message', 'No message')[:80]}...")
            print(f"     🆔 Session: {result.get('session_id', 'No session')}")
            print(f"     🔍 SQL: {result.get('sql_query', 'No SQL')[:60]}...")
            return True
        else:
            print(f"   ❌ FAILED! Response: {post_response.text}")
            return False
            
    except requests.exceptions.ConnectTimeout:
        print(f"   ⏰ CONNECTION TIMEOUT")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"   🔌 CONNECTION ERROR: {e}")
        return False
    except requests.exceptions.Timeout:
        print(f"   ⏰ REQUEST TIMEOUT")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def test_different_origins():
    """Test different origins to find CORS issues"""
    origins_to_test = [
        "http://127.0.0.1:80",
        "http://localhost:80",
        "http://127.0.0.1:3000",
        "http://localhost:3000"
    ]
    
    url = "http://127.0.0.1:80/api/chat/"
    payload = {"message": "Origin test", "agent_type": "normal"}
    
    print(f"\n{'='*60}")
    print(f"🌍 TESTING DIFFERENT ORIGINS")
    print(f"{'='*60}")
    
    for origin in origins_to_test:
        print(f"\n--- Testing Origin: {origin} ---")
        headers = {
            "Content-Type": "application/json",
            "Origin": origin,
        }
        
        # Test just POST to see if it works
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=5)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ {origin} works!")
            else:
                print(f"   ❌ {origin} failed: {response.text[:100]}")
        except Exception as e:
            print(f"   ❌ {origin} error: {e}")

def main():
    """Main test function"""
    print("🧪 BROWSER SIMULATION TESTING")
    print("Testing chat endpoints with browser-like behavior")
    
    results = {}
    
    # Test 1: Different URLs
    results["nginx"] = test_endpoint(
        "http://127.0.0.1:80/api/chat/",
        "NGINX Proxy (127.0.0.1:80)"
    )
    
    results["direct_backend"] = test_endpoint(
        "http://127.0.0.1:8000/api/chat/",
        "Direct Backend (127.0.0.1:8000)"
    )
    
    # Test 2: Different origins
    test_different_origins()
    
    # Results
    print(f"\n{'='*60}")
    print("🏆 RESULTS SUMMARY")
    print(f"{'='*60}")
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20}: {status}")
    
    if results.get("nginx"):
        print(f"\n🎉 SUCCESS! The chat interface should work through nginx.")
        print(f"🌐 Open your browser: http://127.0.0.1:80")
        print(f"💬 Go to Chat page and try sending messages.")
    else:
        print(f"\n❌ Issues remain. Check nginx configuration and CORS settings.")
        print(f"💡 Try the direct backend URL if nginx continues to fail.")

if __name__ == "__main__":
    main()