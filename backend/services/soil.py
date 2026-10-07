import httpx

def get_texture(sand, silt, clay):
    """Determine USDA soil texture class"""
    if sand + silt + clay == 0:
        return "Unknown"
    
    # Simple classification logic based on USDA triangle
    if clay >= 40:
        return "Clay"
    elif sand >= 50:
        if clay >= 27:
            return "Sandy Clay Loam"
        return "Sandy Loam"
    elif silt >= 50:
        if clay >= 27:
            return "Silty Clay Loam"
        return "Silty Loam"
    elif clay >= 27:
        return "Clay Loam"
    else:
        return "Loam"

async def get_soil(lat: float, lon: float):
    """
    Fetch soil data from SoilGrids API
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Dictionary with soil data or error message
    """
    try:
        url = (
            "https://rest.isric.org/soilgrids/v2.0/properties/query"
            f"?lat={lat}&lon={lon}"
            "&property=phh2o"
            "&property=soc"
            "&property=sand"
            "&property=silt"
            "&property=clay"
            "&depth=0-5cm"
            "&value=mean"
        )

        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        layers = data["properties"]["layers"]
        
        # Find layers by name
        ph_layer = next((l for l in layers if l["name"] == "phh2o"), None)
        oc_layer = next((l for l in layers if l["name"] == "soc"), None)
        sand_layer = next((l for l in layers if l["name"] == "sand"), None)
        silt_layer = next((l for l in layers if l["name"] == "silt"), None)
        clay_layer = next((l for l in layers if l["name"] == "clay"), None)
        
        if not ph_layer or not oc_layer:
            return {"error": "soil unavailable"}
        
        # Extract values (mean of 0-5cm)
        ph_raw = ph_layer["depths"][0]["values"]["mean"]
        oc_raw = oc_layer["depths"][0]["values"]["mean"]
        sand_raw = sand_layer["depths"][0]["values"]["mean"] if sand_layer else None
        silt_raw = silt_layer["depths"][0]["values"]["mean"] if silt_layer else None
        clay_raw = clay_layer["depths"][0]["values"]["mean"] if clay_layer else None
        
        # Check for null values
        if ph_raw is None or oc_raw is None:
            return {"error": "soil unavailable"}
        
        # Conversions
        # pH: stored as pH*10 -> divide by 10
        ph = ph_raw / 10
        # SOC: dg/kg -> % by mass (1 % = 10 g/kg = 100 dg/kg)
        oc = oc_raw / 100
        # Texture parts: g/kg -> percentage (divide by 10)
        if None in (sand_raw, silt_raw, clay_raw):
            sand = silt = clay = None
            texture_class = "Unknown"
        else:
            sand, silt, clay = sand_raw / 10, silt_raw / 10, clay_raw / 10
            texture_class = get_texture(sand, silt, clay)

        return {
            "ph": round(ph, 2),
            "organic_carbon_pct": round(oc, 2),
            "texture": texture_class,
            "sand_pct": None if sand is None else round(sand, 1),
            "silt_pct": None if silt is None else round(silt, 1),
            "clay_pct": None if clay is None else round(clay, 1),
            "source": "SoilGrids 0-5 cm"
        }
    
    except Exception as e:
        print(f"Soil API Error: {e}")
        return {"error": "soil unavailable"}

