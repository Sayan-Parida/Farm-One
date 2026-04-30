import http.client
import json

print("="*60)
print("Testing Farmone API - LIVE DATA VALIDATION")
print("="*60)

# Test 1: Health Check
print("\n1. Health Check (GET /)")
try:
    conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=5)
    conn.request("GET", "/")
    response = conn.getresponse()
    data = response.read().decode()
    print(f"   Status: {response.status}")
    if response.status == 200:
        print("   [OK] Health check passed")
    else:
        print(f"   [FAIL] Response: {data}")
    conn.close()
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 2: API Docs
print("\n2. API Documentation (GET /docs)")
try:
    conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=5)
    conn.request("GET", "/docs")
    response = conn.getresponse()
    print(f"   Status: {response.status}")
    if response.status == 200:
        print("   [OK] API docs available")
    else:
        print("   [FAIL] Docs not accessible")
    conn.close()
except Exception as e:
    print(f"   [ERROR] {e}")

# Test 3: Analyze Endpoint - LIVE DATA VALIDATION
print("\n3. Analyze Endpoint - LIVE DATA TEST")
print("   Testing with Kolkata coordinates (22.57, 88.36)")
try:
    conn = http.client.HTTPConnection("127.0.0.1", 8000, timeout=15)
    conn.request("GET", "/api/analyze?lat=22.57&lon=88.36")
    response = conn.getresponse()
    data = response.read().decode()
    print(f"   Status: {response.status}")
    
    if response.status == 200:
        parsed = json.loads(data)
        
        # Validate structure
        print("\n   Response Structure:")
        print(f"   {json.dumps(parsed, indent=6)}")
        
        print("\n   LIVE DATA VALIDATION:")
        print("   " + "-" * 50)
        
        # Check location
        if "location" in parsed:
            loc = parsed["location"]
            print(f"   [OK] Location: lat={loc.get('lat')}, lon={loc.get('lon')}")
        else:
            print("   [FAIL] Location missing")
        
        # Check weather - MUST be live data
        if "weather" in parsed:
            weather = parsed["weather"]
            if "error" in weather:
                print(f"   [WARN] Weather: {weather['error']}")
                print("          (API key may be missing or invalid)")
            else:
                # Validate it's NOT mock data
                temp = weather.get("temperature")
                humidity = weather.get("humidity")
                desc = weather.get("description")
                
                is_mock = (temp == 28 and humidity == 70 and desc == "clear sky")
                
                if is_mock:
                    print(f"   [FAIL] Weather: MOCK DATA DETECTED!")
                    print(f"          temp={temp}, humidity={humidity}, desc={desc}")
                else:
                    print(f"   [OK] Weather: LIVE DATA")
                    print(f"        temp={temp}C, humidity={humidity}%, desc={desc}")
        else:
            print("   [FAIL] Weather missing")
        
        # Check soil - May be unavailable for some locations
        if "soil" in parsed:
            soil = parsed["soil"]
            if "error" in soil:
                print(f"   [INFO] Soil: {soil['error']}")
                print("          (SoilGrids may not have data for this location)")
            else:
                # Validate it's NOT mock data
                ph = soil.get("ph")
                oc = soil.get("organic_carbon_pct")
                
                is_mock = (ph == 6.5 and oc == 0.9)
                
                if is_mock:
                    print(f"   [FAIL] Soil: MOCK DATA DETECTED!")
                    print(f"          pH={ph}, OC={oc}%")
                else:
                    print(f"   [OK] Soil: LIVE DATA")
                    print(f"        pH={ph}, OC={oc}%, texture={soil.get('texture')}")
        else:
            print("   [FAIL] Soil missing")
            
    else:
        print(f"   [FAIL] Response: {data}")
    conn.close()
except Exception as e:
    print(f"   [ERROR] {e}")

print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print("NOTE: Soil data may be unavailable for some locations")
print("      due to SoilGrids API coverage limitations.")
print("      This is expected behavior, not a bug.")
print("\nOpen these URLs in your browser:")
print("  - Health Check: http://127.0.0.1:8000/")
print("  - API Docs:     http://127.0.0.1:8000/docs")
print("  - Analyze:      http://127.0.0.1:8000/api/analyze?lat=22.57&lon=88.36")

