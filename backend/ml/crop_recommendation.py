import joblib
import os
import pandas as pd
import numpy as np
import logging

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "crop_rf.pkl")
LABEL_ENCODER_PATH = os.path.join(BASE_DIR, "models", "label_encoder.pkl")

# Global variables to hold model and encoder
_model = None
_le = None

def load_model():
    """Load model and label encoder if not already loaded."""
    global _model, _le
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _model = joblib.load(MODEL_PATH)
                print(f"Model loaded from {MODEL_PATH}")
            except Exception as e:
                _model = None
                print(f"Failed to load model at {MODEL_PATH}: {e}")
        else:
            print(f"Model not found at {MODEL_PATH}")

    if _le is None:
        if os.path.exists(LABEL_ENCODER_PATH):
            try:
                _le = joblib.load(LABEL_ENCODER_PATH)
                print(f"Label Encoder loaded from {LABEL_ENCODER_PATH}")
            except Exception as e:
                _le = None
                print(f"Failed to load label encoder at {LABEL_ENCODER_PATH}: {e}")
        else:
            print(f"Label Encoder not found at {LABEL_ENCODER_PATH}")

def predict_crop(features: dict):
    """
    Predict suitable crops with heuristic adjustments for model bias.
    """
    try:
        load_model()
    except Exception as e:
        logger = logging.getLogger("uvicorn")
        logger.error(f"Model loading failed, using heuristic fallback: {e}")
    
    # 1. Run ML Model
    ml_results = []
    logger = logging.getLogger("uvicorn")
    logger.warning(f"DEBUG_LOG: features={features}")

    if _model and _le:
        try:
            feature_order = ['temperature', 'humidity', 'rainfall', 'ph']
            # Create DataFrame to ensure correct column names and order
            input_data = pd.DataFrame([features])
            for col in feature_order:
                if col not in input_data.columns:
                    input_data[col] = 0 # Default if missing
            
            input_data = input_data[feature_order]
            
            proba = _model.predict_proba(input_data)[0]
            top3_idx = np.argsort(proba)[-3:][::-1]
            for idx in top3_idx:
                crop = _le.inverse_transform([idx])[0]
                conf = float(proba[idx])
                if conf > 0.01:
                    ml_results.append({
                        "crop": crop,
                        "success_percentage": round(conf * 100),
                        "confidence_level": "High" if conf > 0.6 else "Medium" if conf > 0.3 else "Low"
                    })
        except Exception as e:
            logger.error(f"ML Model Error: {e}")

    # 2. Heuristic Overrides (Fixing Bias)
    
    adjusted_results = ml_results
    
    try:
        temp = float(features.get("temperature", 25))
        rain = float(features.get("rainfall", 100))
        humidity = float(features.get("humidity", 70))
        ph = float(features.get("ph", 6.5))
        
        logger.warning(f"DEBUG_LOG: Parsed - Temp={temp} Rain={rain} Hum={humidity} pH={ph}")

        # Rule 1: High Rainfall -> Rice/Jute
        if rain > 150:
            logger.warning("DEBUG_LOG: Triggering Rule 1 (High Rain)")
            if not any(r['crop'] == 'rice' for r in adjusted_results):
                adjusted_results.insert(0, {"crop": "rice", "success_percentage": 92, "confidence_level": "High"})
            if not any(r['crop'] == 'jute' for r in adjusted_results):
                adjusted_results.append({"crop": "jute", "success_percentage": 85, "confidence_level": "High"})

        # Rule 2: Low Temp & Low Rain -> Wheat/Chickpea (Rabi crops)
        elif temp < 20 and rain < 50:
            logger.warning("DEBUG_LOG: Triggering Rule 2 (Winter)")
            # Override Maize if it appears for cold weather
            adjusted_results = [r for r in adjusted_results if r['crop'] != 'maize']
            adjusted_results.insert(0, {"crop": "chickpea", "success_percentage": 88, "confidence_level": "High"})
            adjusted_results.insert(1, {"crop": "kidneybeans", "success_percentage": 82, "confidence_level": "Medium"})

        # Rule 3: Dry/Arid -> Mothbeans/Lentil
        elif rain < 40 and temp > 25:
             logger.warning("DEBUG_LOG: Triggering Rule 3 (Dry)")
             if not any(r['crop'] == 'mothbeans' for r in adjusted_results):
                 adjusted_results.insert(0, {"crop": "mothbeans", "success_percentage": 90, "confidence_level": "High"})

        # Rule 4: Fruit Logic (Banana needs water + heat)
        if temp > 25 and rain > 100:
             logger.warning("DEBUG_LOG: Triggering Rule 4 (Banana)")
             if not any(r['crop'] == 'banana' for r in adjusted_results):
                 adjusted_results.insert(1, {"crop": "banana", "success_percentage": 85, "confidence_level": "Medium"})

        # Rule 5: Cotton (Black soil conditions approx) -> High Temp, Medium Rain
        if temp > 28 and 50 < rain < 100:
            logger.warning("DEBUG_LOG: Triggering Rule 5 (Cotton)")
            if not any(r['crop'] == 'cotton' for r in adjusted_results):
                 adjusted_results.insert(0, {"crop": "cotton", "success_percentage": 89, "confidence_level": "High"})
                 
    except Exception as e:
        logger.error(f"Heuristic Logic Error: {e}")

    # Ensure correct format and max 3 items
    final_output = adjusted_results[:3]
    
    # Fallback if empty
    if not final_output:
         final_output = [{"crop": "maize", "success_percentage": 75, "confidence_level": "Medium"}]
         
    return final_output
