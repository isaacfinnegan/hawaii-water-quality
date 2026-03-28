import requests

print("Testing requests (synchronous)...")
try:
    response = requests.get("https://eha-cloud.doh.hawaii.gov/cwb/api/json/reply/GetEvents")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Data length: {len(data.get('list', []))}")
except Exception as e:
    print(f"Error: {e}")
