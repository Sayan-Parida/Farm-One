import os
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

async def get_weather(lat: float, lon: float):
    """
    Fetch weather data from OpenWeather API
    
    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        
    Returns:
        Dictionary with weather data or error message
    """
    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        
        return {
            "temperature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "rain_1h": data.get("rain", {}).get("1h", 0),
            "description": data["weather"][0]["description"]
        }
    
    except Exception:
        return {"error": "weather unavailable"}
