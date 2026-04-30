import requests
import json

print("Testing /api/analyze endpoint with live data...")
print("=" * 60)

# Test with Kolkata coordinates
url = "http://127.0.0.1:8000/api/analyze?lat=22.57&lon=88.36"
print(f"\nRequest: {url}")

try:
    response = requests.get(url, timeout=15)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\nResponse Data:")
        print(json.dumps(data, indent=2))
        
        # Verify structure
        print("\n" + "=" * 60)
        print("VERIFICATION:")
        print("=" * 60)
        
        # Check location
        if "location" in data:
            print(f"[OK] Location: lat={data['location']['lat']}, lon={data['location']['lon']}")
        else:
            print("[FAIL] Location missing")
        
        # Check weather
        if "weather" in data:
            weather = data['weather']
            if "error" in weather:
                print(f"[WARN] Weather: {weather['error']}")
            else:
                print(f"[OK] Weather: temp={weather.get('temperature')}C, humidity={weather.get('humidity')}%, desc={weather.get('description')}")
        else:
            print("[FAIL] Weather missing")
        
        # Check soil
        if "soil" in data:
            soil = data['soil']
            if "error" in soil:
                print(f"[WARN] Soil: {soil['error']}")
            else:
                print(f"[OK] Soil: pH={soil.get('ph')}, organic_carbon={soil.get('organic_carbon_pct')}%, texture={soil.get('texture')}")
        else:
            print("[FAIL] Soil missing")
            
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"ERROR: {e}")
