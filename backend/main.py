from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from global_land_mask import globe
from services.weather import get_weather
from services.soil import get_soil
app = FastAPI(title="Farmone API", version="1.0.3")
from ml.crop_recommendation import predict_crop
from ml.yield_prediction import predict_yield
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
    # Dataset means as defaults
    defaults = {
        "temperature": 25.62,
        "humidity": 71.48,
        "rainfall": 103.46,
        "ph": 6.47
    }
    
    # Extract values or use defaults
    weather = data.weather or WeatherData()
    soil = data.soil or SoilData()
    
    features = {
        "temperature": weather.temperature if weather.temperature is not None else defaults["temperature"],
        "humidity": weather.humidity if weather.humidity is not None else defaults["humidity"],
        "rainfall": weather.rainfall if weather.rainfall is not None else defaults["rainfall"],
        "ph": soil.ph if soil.ph is not None else defaults["ph"]
    }
    
    print(f"Backend: Received features: {features}")
    try:
        predictions = predict_crop(features)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Crop prediction failed: {e}"})
    print(f"Backend: Returning: {predictions}")
    
    return {
        "recommended_crops": predictions
    }

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
    weather: Optional[YieldWeather] = None
    soil: Optional[YieldSoil] = None
    crop_name: Optional[str] = None   # e.g. "rice", "maize" from crop recommendation
    country: Optional[str] = None     # e.g. "India" — improves regional accuracy

@app.get("/api/debug")
async def debug_endpoint():
    """Debug endpoint to verify server is running latest code"""
    return {"status": "ok", "version": "2.0", "timestamp": "2026-02-06T05:12:00"}

@app.post("/api/ml/yield")
async def estimate_yield(data: YieldPredictionRequest):
    """Estimate crop yield based on weather, soil, crop type and region."""
    weather = data.weather if data.weather else YieldWeather()
    soil    = data.soil    if data.soil    else YieldSoil()

    features = {
        "temp_min":             weather.temp_min,
        "temp_max":             weather.temp_max,
        "humidity":             weather.humidity,
        "rain_7d":              weather.rain_7d,
        "soil_ph":              soil.ph,
        "organic_carbon_pct":   soil.organic_carbon_pct,
        # New: crop type + country for improved accuracy
        "crop_name":            data.crop_name,
        "country":              data.country,
    }

    result = predict_yield(features)
    if isinstance(result, dict) and "error" in result:
        return JSONResponse(status_code=500, content=result)
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
    success_percentage: int

class CropRecommendation(BaseModel):
    recommended_crops: list[CropItem] | list[str]  # Accept both formats

class YieldPredictionData(BaseModel):
    expected_yield_ton_per_hectare: float
    confidence: str

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
    
    # Transform weather data to match frontend expectations
    # Frontend expects: tmin_c, tmax_c, rain_7d_mm, humidity_pct
    current_temp = weather_raw.get("temperature", 25)
    
    weather_transformed = {
        "tmin_c": round(current_temp - 3, 1), # Simulated min
        "tmax_c": round(current_temp + 3, 1), # Simulated max
        "rain_7d_mm": weather_raw.get("rain_1h", 0) * 24 * 7 if "rain_1h" in weather_raw else 0, # Rough estimate
        "humidity_pct": weather_raw.get("humidity", 50),
        "original_data": weather_raw
    }

    # Transform soil data if necessary (soil service seems to match mostly)
    # Frontend expects: ph, oc_pct, texture
    soil_transformed = {
        "ph": soil_raw.get("ph", 6.5),
        "oc_pct": soil_raw.get("organic_carbon_pct", 0.5), # Service returns organic_carbon_pct
        "texture": soil_raw.get("texture", "loam"),
        "original_data": soil_raw
    }

    return {
        "location": {"lat": lat, "lon": lon},
        "weather": weather_transformed,
        "soil": soil_transformed
    }
