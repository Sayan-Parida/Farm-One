import asyncio
import httpx

async def test_multiple_locations():
    print("Testing SoilGrids API with multiple locations...")
    print("=" * 60)
    
    locations = [
        (22.57, 88.36, "Kolkata, India"),
        (40.7128, -74.0060, "New York, USA"),
        (51.5074, -0.1278, "London, UK"),
        (28.6139, 77.2090, "Delhi, India"),
    ]
    
    for lat, lon, name in locations:
        print(f"\n{name} ({lat}, {lon}):")
        print("-" * 40)
        
        url = (
            "https://rest.isric.org/soilgrids/v2.0/properties/query"
            f"?lat={lat}&lon={lon}"
            "&property=phh2o"
            "&property=ocd"
            "&depth=0-5cm"
            "&value=mean"
        )
        
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    layers = data["properties"]["layers"]
                    
                    # Note: API returns layers in different order sometimes
                    ph_layer = next((l for l in layers if l["name"] == "phh2o"), None)
                    oc_layer = next((l for l in layers if l["name"] == "ocd"), None)
                    
                    ph_raw = ph_layer["depths"][0]["values"]["mean"] if ph_layer else None
                    oc_raw = oc_layer["depths"][0]["values"]["mean"] if oc_layer else None
                    
                    if ph_raw is not None and oc_raw is not None:
                        # pH needs to be divided by 10 (it's stored as pH*10)
                        ph = ph_raw / 10
                        oc = oc_raw / 10
                        print(f"  [OK] pH: {round(ph, 2)}, OC: {round(oc, 2)}%")
                    else:
                        print(f"  [WARN] No data available (pH: {ph_raw}, OC: {oc_raw})")
                else:
                    print(f"  [ERROR] Status {response.status_code}")
                    
        except Exception as e:
            print(f"  [ERROR] {type(e).__name__}: {e}")

asyncio.run(test_multiple_locations())
