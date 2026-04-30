# Farmone Backend API

FastAPI backend for the Farmone agricultural platform.

## Setup

### 1. Create Virtual Environment
```bash
python -m venv venv
```

### 2. Activate Virtual Environment
```bash
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Windows CMD
.\venv\Scripts\activate.bat
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys
Create a `.env` file in the backend directory and add your OpenWeather API key:
```bash
OPENWEATHER_API_KEY=your_api_key_here
```

Get a free API key from [OpenWeather](https://openweathermap.org/api)

## Running the Server

### Development Mode (with auto-reload)
```bash
python -m uvicorn main:app --reload
```

### Production Mode
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

## Endpoints

### Health Check
- **GET** `/` - Returns API health status

### Analysis
- **GET** `/api/analyze?lat={latitude}&lon={longitude}` - Get weather and soil data for a location
  - **Parameters:**
    - `lat` (float): Latitude coordinate
    - `lon` (float): Longitude coordinate
  - **Returns:** Combined weather and soil analysis data

## Project Structure

```
backend/
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
├── services/           # Business logic services
│   ├── weather.py      # Weather service
│   └── soil.py         # Soil analysis service
└── venv/               # Virtual environment (not in git)
```

## Features

- ✅ FastAPI framework
- ✅ CORS enabled for all origins
- ✅ Auto-reload in development
- ✅ Interactive API documentation
- ✅ Modular service architecture
