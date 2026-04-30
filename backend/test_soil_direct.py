import asyncio
import sys
sys.path.insert(0, 'c:/Users/Sayan/Downloads/Farmone-main/Farmone-main/backend')

from services.soil import get_soil

async def test_soil():
    print("Testing soil API directly...")
    print("=" * 60)
    
    # Test with Kolkata coordinates
    lat, lon = 22.57, 88.36
    print(f"Coordinates: lat={lat}, lon={lon}")
    
    result = await get_soil(lat, lon)
    print(f"\nResult: {result}")
    
    if "error" in result:
        print("\n[WARN] Soil API returned error - this could be:")
        print("  - API rate limiting")
        print("  - Network timeout")
        print("  - Invalid coordinates")
        print("  - API endpoint issue")
    else:
        print("\n[OK] Soil API returned live data successfully!")

asyncio.run(test_soil())
