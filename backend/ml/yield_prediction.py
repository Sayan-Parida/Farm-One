import joblib
import os
import pandas as pd
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "yield_rf.pkl")
MEANS_PATH = os.path.join(BASE_DIR, "models", "yield_means.pkl")

# Global cache
_model = None
_means = None


def load_resources():
    """Load model and inference config if not already loaded."""
    global _model, _means
    if _model is None:
        if os.path.exists(MODEL_PATH):
            try:
                _model = joblib.load(MODEL_PATH)
                print(f"Yield Model loaded from {MODEL_PATH}")
            except Exception as e:
                _model = None
                print(f"Failed to load yield model at {MODEL_PATH}: {e}")
        else:
            print(f"Yield Model not found at {MODEL_PATH}")

    if _means is None:
        if os.path.exists(MEANS_PATH):
            try:
                _means = joblib.load(MEANS_PATH)
                print(f"Yield Means loaded from {MEANS_PATH}")
            except Exception as e:
                _means = None
                print(f"Failed to load yield means at {MEANS_PATH}: {e}")
        else:
            print(f"Yield Means not found at {MEANS_PATH}")


def _resolve_item_enc(crop_name: str, means: dict) -> int:
    """Map a crop recommendation name to a dataset Item label and encode it."""
    if not crop_name:
        return means.get("Item_enc", 0)

    name_map   = means.get("_item_name_map", {})
    item_classes = means.get("_item_classes", [])

    # Try direct lookup in normalisation map
    normalised = name_map.get(crop_name.lower().strip())

    if normalised and normalised in item_classes:
        return item_classes.index(normalised)

    # Try case-insensitive match against dataset labels directly
    for i, cls in enumerate(item_classes):
        if cls.lower() == crop_name.lower().strip():
            return i

    # Fallback to saved default (Wheat)
    return means.get("Item_enc", 0)


def _resolve_area_enc(country: str, means: dict) -> int:
    """Map a country name to its encoded integer (defaults to India)."""
    if not country:
        return means.get("Area_enc", 0)

    area_classes = means.get("_area_classes", [])
    for i, cls in enumerate(area_classes):
        if cls.lower() == country.lower().strip():
            return i

    return means.get("Area_enc", 0)


def predict_yield(features: dict):
    """
    Predict crop yield.

    Args:
        features (dict): May contain:
            - temp_min, temp_max          (°C)   from live weather
            - rain_7d                     (mm)   7-day rainfall
            - humidity                    (%)    unused by model but kept for API compat
            - soil_ph                            unused by model (no soil in training data)
            - organic_carbon_pct                 unused by model
            - crop_name    (str, optional) e.g. "rice", "maize"
            - country      (str, optional) e.g. "India"
            - year         (int, optional) defaults to 2024

    Returns:
        dict: { expected_yield_ton_per_hectare, confidence, note }
    """
    try:
        load_resources()
    except Exception as e:
        return {"error": f"Failed loading yield resources: {e}"}

    if _model is None or _means is None:
        return {"error": "Model or config not loaded"}

    # ── 1. Derive Temperature (°C) ─────────────────────────────────────────
    temp_min = features.get("temp_min")
    temp_max = features.get("temp_max")

    if temp_min is not None and temp_max is not None:
        temperature = (temp_min + temp_max) / 2.0
    elif temp_max is not None:
        temperature = temp_max
    elif temp_min is not None:
        temperature = temp_min
    else:
        temperature = _means["Temperature"]

    # ── 2. Derive Annual Rainfall (mm/year) ────────────────────────────────
    # Training data uses annual rainfall; rain_7d is 7-day accumulation.
    # Scale: 7d → annual by multiplying by 52 weeks.
    rain_7d = features.get("rain_7d")
    if rain_7d is not None:
        rainfall = rain_7d * 52.0
        # Clamp to dataset range [51, 3240]
        rainfall = float(np.clip(rainfall, 51, 3240))
    else:
        rainfall = _means["Rainfall"]

    # ── 3. Pesticides (default: dataset median) ────────────────────────────
    pesticides = _means["pesticides_tonnes"]

    # ── 4. Year ────────────────────────────────────────────────────────────
    year = int(features.get("year", _means["Year"]))

    # ── 5. Crop (Item) encoding ────────────────────────────────────────────
    crop_name = features.get("crop_name", "")
    item_enc  = _resolve_item_enc(crop_name, _means)

    # ── 6. Country (Area) encoding ─────────────────────────────────────────
    country  = features.get("country", "")
    area_enc = _resolve_area_enc(country, _means)

    # ── 7. Confidence logic ────────────────────────────────────────────────
    has_weather = (temp_min is not None or temp_max is not None) and rain_7d is not None
    has_crop    = bool(crop_name)

    if has_weather and has_crop:
        confidence = "High"
    elif has_weather or has_crop:
        confidence = "Medium"
    else:
        confidence = "Low"

    # ── 8. Predict ─────────────────────────────────────────────────────────
    try:
        feature_order = [
            "Temperature",
            "Rainfall",
            "pesticides_tonnes",
            "Year",
            "Area_enc",
            "Item_enc",
        ]

        input_dict = {
            "Temperature":       temperature,
            "Rainfall":          rainfall,
            "pesticides_tonnes": pesticides,
            "Year":              year,
            "Area_enc":          area_enc,
            "Item_enc":          item_enc,
        }

        input_df = pd.DataFrame([input_dict])[feature_order]
        raw_yield = float(_model.predict(input_df)[0])

        # Convert hg/ha → ton/ha
        yield_ton = round(raw_yield / 10000, 2)

        # Agronomic soft cap — very high-yielding crops (potatoes) can legitimately
        # exceed 25 ton/ha but general field crops rarely exceed 15.
        yield_ton = min(yield_ton, 25.0)
        yield_ton = max(yield_ton, 0.1)

        crop_display = crop_name if crop_name else "selected crop"
        note = (
            f"Estimated for {crop_display} using climate, crop type, and regional data. "
            f"Annual rainfall estimated from 7-day reading."
        )

        return {
            "expected_yield_ton_per_hectare": yield_ton,
            "confidence": confidence,
            "note": note,
        }

    except Exception as e:
        print(f"Yield Prediction error: {e}")
        return {"error": str(e)}
