# 🚀 Quick Start Guide - Farmone Backend

## Server is Running! ✅

Your FastAPI backend is live at: **http://127.0.0.1:8000**

## 📍 Available Endpoints

### 1. Health Check
```
http://127.0.0.1:8000/
```
Returns API status and version info.

### 2. Interactive API Documentation  
```
http://127.0.0.1:8000/docs
```
Swagger UI - test all endpoints directly in your browser!

### 3. Alternative Documentation
```
http://127.0.0.1:8000/redoc
```
ReDoc - clean, readable API documentation.

### 4. Analyze Location
```
http://127.0.0.1:8000/api/analyze?lat=22.57&lon=88.36
```
Get weather and soil data for any coordinates.

**Example (Kolkata):**
- Latitude: 22.57
- Longitude: 88.36

**Example (New Delhi):**
```
http://127.0.0.1:8000/api/analyze?lat=28.6139&lon=77.2090
```

## 🔑 Get Real Weather Data

1. Visit https://openweathermap.org/api
2. Sign up for a free account
3. Copy your API key
4. Open `backend/.env`
5. Replace `demo_key_replace_with_real_key` with your actual key
6. Server will auto-reload!

## 🛠️ Useful Commands

**Start Server:**
```powershell
cd backend
.\start.ps1
```

**Or manually:**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload
```

**Stop Server:**
Press `Ctrl+C` in the terminal

**Test Endpoints:**
```powershell
python test_api.py
```

## ✅ Everything is Working!

All endpoints tested and confirmed:
- ✅ Health check responding
- ✅ API docs accessible  
- ✅ Analyze endpoint working
- ✅ CORS enabled for frontend

**Next:** Open http://127.0.0.1:8000/docs in your browser to explore the API!
