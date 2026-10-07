from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from global_land_mask import globe
from services.weather import get_weather
from services.soil import get_soil
from ml.yield_prediction import predict_yield, recommend_crops
from ml.advisory_llm import generate_advice
from ml.farmbot_chat import get_chat_response

app = FastAPI(title="Farmone API", version="1.0.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.16.0.2:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Input models for ML endpoint
class WeatherData(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None

class SoilData(BaseModel):
    ph: Optional[float] = None

class CropPredictionRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    season: Optional[str] = None      # Kharif / Rabi / Summer / ... (default: current season)
    # Accepted for backwards compatibility; the district model does not use point weather/soil.
    weather: Optional[WeatherData] = None
    soil: Optional[SoilData] = None

@app.get("/")
async def health_check():
    return {
        "status": "healthy",
        "message": "Farmone API is running",
        "version": "1.0.0"
    }

@app.post("/api/ml/crop")
async def recommend_crop(data: CropPredictionRequest):
    """
    Crops officially grown in the farm's district for the season, ranked by predicted
    district yield relative to India's median for that crop. Requires lat/lon.
    """
    result = recommend_crops({"lat": data.lat, "lon": data.lon, "season": data.season})
    if "error" in result:
        return JSONResponse(status_code=result.pop("status", 500), content=result)
    return result

# Input models for Yield endpoint
class YieldWeather(BaseModel):
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    humidity: Optional[float] = None
    rain_7d: Optional[float] = None

class YieldSoil(BaseModel):
    ph: Optional[float] = None
    organic_carbon_pct: Optional[float] = None

class YieldPredictionRequest(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    crop_name: Optional[str] = None   # e.g. "Rice", "wheat", "chickpea"; default = district's main crop
    season: Optional[str] = None      # Kharif / Rabi / Summer / Autumn / Winter / Whole Year
    # Accepted for backwards compatibility; not used by the district model.
    weather: Optional[YieldWeather] = None
    soil: Optional[YieldSoil] = None
    country: Optional[str] = None

@app.get("/api/debug")
async def debug_endpoint():
    """Debug endpoint to verify server is running latest code"""
    return {"status": "ok", "version": "2.0", "timestamp": "2026-02-06T05:12:00"}

@app.post("/api/ml/yield")
async def estimate_yield(data: YieldPredictionRequest):
    """District-level yield estimate for a crop, season and location (see ml/yield_prediction.py)."""
    result = predict_yield({
        "lat": data.lat,
        "lon": data.lon,
        "crop_name": data.crop_name,
        "season": data.season,
    })
    if "error" in result:
        return JSONResponse(status_code=result.pop("status", 500), content=result)
    return result

# Input models for Advisory endpoint
class AdvisoryWeather(BaseModel):
    temperature: Optional[float] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    humidity: Optional[float] = None
    rainfall: Optional[float] = None
    rain_7d: Optional[float] = None

class AdvisorySoil(BaseModel):
    ph: Optional[float] = None
    organic_carbon_pct: Optional[float] = None
    texture: Optional[str] = None

class CropItem(BaseModel):
    crop: str
    expected_yield_t_ha: Optional[float] = None
    relative_to_national_pct: Optional[float] = None

class CropRecommendation(BaseModel):
    recommended_crops: list[CropItem] | list[str]  # Accept both formats

class YieldPredictionData(BaseModel):
    expected_yield_ton_per_hectare: Optional[float] = None
    confidence: str
    crop: Optional[str] = None
    season: Optional[str] = None
    district: Optional[str] = None

class AdvisoryRequest(BaseModel):
    weather: AdvisoryWeather
    soil: AdvisorySoil
    crop_recommendation: CropRecommendation
    yield_prediction: YieldPredictionData
    question: Optional[str] = None

@app.post("/api/ml/advice")
async def get_advice(data: AdvisoryRequest):
    advisory_text = generate_advice(
        weather=data.weather.model_dump(),
        soil=data.soil.model_dump(),
        crop_recommendation=data.crop_recommendation.model_dump(),
        yield_prediction=data.yield_prediction.model_dump(),
        question=data.question
    )
    
    return {
        "advisory": advisory_text
    }

# Input model for Chat endpoint
class ChatRequest(BaseModel):
    question: str

@app.post("/api/ml/chat")
async def chat_farmbot(data: ChatRequest):
    answer = get_chat_response(data.question)
    # If the chat module returned its internal fallback message, propagate
    # a 503 so the frontend treats it as a failure and shows the connection
    # error UI instead of embedding a stale fallback string as content.
    if isinstance(answer, str) and answer.strip().startswith("FarmBot is temporarily unavailable"):
        return JSONResponse(status_code=503, content={"error": answer})

    return {"answer": answer}

@app.get("/api/analyze")
async def analyze(lat: float, lon: float):
    # Restrict analysis to land points only.
    if not globe.is_land(lat, lon):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Selected point is over water. Please click on land to fetch soil and weather insights.",
                "code": "WATER_POINT",
                "location": {"lat": lat, "lon": lon},
            },
        )

    # Call weather service - won't crash if it fails
    weather_raw = await get_weather(lat, lon)
    
    # Call soil service - won't crash if it fails
    soil_raw = await get_soil(lat, lon)
    
    # Only real measurements are passed on. Missing values stay None (shown as N/A) —
    # never substituted with defaults, because downstream models would treat them as real.
    weather_ok = "error" not in weather_raw
    weather_transformed = {
        "tmin_c": weather_raw.get("tmin_c") if weather_ok else None,
        "tmax_c": weather_raw.get("tmax_c") if weather_ok else None,
        "rain_7d_mm": weather_raw.get("rain_7d_mm") if weather_ok else None,
        "humidity_pct": weather_raw.get("humidity") if weather_ok else None,
        "available": weather_ok,
        "source": weather_raw.get("source"),
    }

    soil_ok = "error" not in soil_raw
    soil_transformed = {
        "ph": soil_raw.get("ph") if soil_ok else None,
        "oc_pct": soil_raw.get("organic_carbon_pct") if soil_ok else None,
        "texture": soil_raw.get("texture") if soil_ok else None,
        "available": soil_ok,
        "source": soil_raw.get("source") if soil_ok else None,
    }

    return {
        "location": {"lat": lat, "lon": lon},
        "weather": weather_transformed,
        "soil": soil_transformed
    }
