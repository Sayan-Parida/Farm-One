import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


async def get_weather(lat: float, lon: float):
    """
    Fetch observed recent weather from Open-Meteo (free, no API key).

    Returns real values only — no simulated or extrapolated numbers:
        temperature    current air temperature (°C)
        humidity       current relative humidity (%)
        tmin_c/tmax_c  today's forecast min / max (°C)
        rain_7d_mm     total precipitation over the previous 7 days (mm)
    On failure returns {"error": ...}; callers must not substitute defaults.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "past_days": 7,
        "forecast_days": 1,
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            data = response.json()

        daily = data["daily"]
        # past_days=7 + forecast_days=1 → 8 entries; the last one is today.
        past_rain = [p for p in daily["precipitation_sum"][:-1] if p is not None]
        return {
            "temperature": data["current"]["temperature_2m"],
            "humidity": data["current"]["relative_humidity_2m"],
            "tmin_c": daily["temperature_2m_min"][-1],
            "tmax_c": daily["temperature_2m_max"][-1],
            "rain_7d_mm": round(sum(past_rain), 1) if len(past_rain) == 7 else None,
            "source": "Open-Meteo",
        }
    except Exception as e:
        return {"error": f"weather unavailable: {e}"}
