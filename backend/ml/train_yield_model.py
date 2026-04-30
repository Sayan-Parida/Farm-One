"""
FarmOne — Yield Model Training (v2)
====================================
Improvements over v1:
  - Uses ALL dataset features: Item (crop), Area (country), Year,
    Temperature, Rainfall, pesticides_tonnes
  - Label-encodes categorical columns so the model knows what crop/country
  - Switches from RandomForest to GradientBoostingRegressor
  - Saves label encoders for Area and Item alongside the model
  - Expected R² jump: from ~-0.15 → 0.85+
"""

import pandas as pd
import joblib
import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "crop_yield.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")

MODEL_PATH      = os.path.join(MODEL_DIR, "yield_rf.pkl")          # Keep same filename for drop-in compatibility
MEANS_PATH      = os.path.join(MODEL_DIR, "yield_means.pkl")
AREA_LE_PATH    = os.path.join(MODEL_DIR, "yield_area_encoder.pkl")
ITEM_LE_PATH    = os.path.join(MODEL_DIR, "yield_item_encoder.pkl")

# Feature order MUST match predict_yield inference
FEATURE_COLS = [
    "Temperature",
    "Rainfall",
    "pesticides_tonnes",
    "Year",
    "Area_enc",
    "Item_enc",
]
TARGET_COL = "Yield"


def train_model():
    print("=" * 60)
    print("  FarmOne Yield Model Training  (v2 — GradientBoosting)")
    print("=" * 60)

    # ── Load ───────────────────────────────────────────────────────────────
    print("\n[1/5] Loading data ...")
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: Data file not found at {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")
    print(f"      Loaded {len(df):,} rows x {df.shape[1]} cols")

    # ── Encode categoricals ────────────────────────────────────────────────
    print("\n[2/5] Encoding categoricals ...")
    area_le = LabelEncoder()
    item_le = LabelEncoder()

    df["Area_enc"] = area_le.fit_transform(df["Area"])
    df["Item_enc"] = item_le.fit_transform(df["Item"])

    print(f"      Areas  : {len(area_le.classes_)} unique  {list(area_le.classes_[:5])} ...")
    print(f"      Items  : {len(item_le.classes_)} unique  {list(item_le.classes_)}")

    # ── Prepare X / y ──────────────────────────────────────────────────────
    print("\n[3/5] Preparing features ...")
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    print(f"      Features: {FEATURE_COLS}")
    print(f"      Target  : {TARGET_COL}  (mean={y.mean():,.0f}, std={y.std():,.0f})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"      Train: {len(X_train):,}  |  Test: {len(X_test):,}")

    # ── Train ──────────────────────────────────────────────────────────────
    print("\n[4/5] Training GradientBoostingRegressor ...")
    print("      (n_estimators=500, lr=0.05, max_depth=5) — may take ~2 min ...")

    model = GradientBoostingRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.8,
        min_samples_leaf=5,
        random_state=42,
        verbose=0,
    )
    model.fit(X_train, y_train)

    # ── Evaluate ───────────────────────────────────────────────────────────
    print("\n[5/5] Evaluating ...")
    y_pred = model.predict(X_test)
    r2   = r2_score(y_test, y_pred)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    print(f"\n  R2 Score : {r2:.4f}  ({r2*100:.2f}% variance explained)")
    print(f"  MAE      : {mae:,.0f} hg/ha  ({mae/10000:.3f} ton/ha)")
    print(f"  RMSE     : {rmse:,.0f} hg/ha  ({rmse/10000:.3f} ton/ha)")

    # Feature importances
    print("\n  Feature Importances:")
    for feat, imp in sorted(zip(FEATURE_COLS, model.feature_importances_),
                            key=lambda x: -x[1]):
        bar = "#" * int(imp * 40)
        print(f"    {feat:<22} {imp:.4f}  {bar}")

    # ── Save ───────────────────────────────────────────────────────────────
    os.makedirs(MODEL_DIR, exist_ok=True)

    joblib.dump(model,   MODEL_PATH)
    joblib.dump(area_le, AREA_LE_PATH)
    joblib.dump(item_le, ITEM_LE_PATH)

    # Save inference means/defaults (for filling missing values at runtime)
    means = {
        "Temperature":       float(df["Temperature"].mean()),
        "Rainfall":          float(df["Rainfall"].mean()),
        "pesticides_tonnes": float(df["pesticides_tonnes"].median()),  # median: less skewed
        "Year":              2024,   # default: recent year
        "Area_enc":          int(area_le.transform(["India"])[0]) if "India" in area_le.classes_ else 0,
        "Item_enc":          int(item_le.transform(["Wheat"])[0]),
        # For inference unit conversions:
        "_rainfall_annual_mean": float(df["Rainfall"].mean()),
        "_temp_mean":            float(df["Temperature"].mean()),
        # Expose encoder class lists so yield_prediction.py can map names
        "_area_classes":    list(area_le.classes_),
        "_item_classes":    list(item_le.classes_),
        # Item name normalization map  (lowercase → exact dataset label)
        "_item_name_map": {
            "rice":                 "Rice, paddy",
            "paddy":                "Rice, paddy",
            "rice, paddy":          "Rice, paddy",
            "maize":                "Maize",
            "corn":                 "Maize",
            "wheat":                "Wheat",
            "potato":               "Potatoes",
            "potatoes":             "Potatoes",
            "soybean":              "Soybeans",
            "soybeans":             "Soybeans",
            "sorghum":              "Sorghum",
            "cassava":              "Cassava",
            "yam":                  "Yams",
            "yams":                 "Yams",
            "sweet potato":         "Sweet potatoes",
            "sweet potatoes":       "Sweet potatoes",
            "plantain":             "Plantains and others",
            "plantains":            "Plantains and others",
            "banana":               "Maize",      # fallback: not in dataset
            "chickpea":             "Wheat",      # fallback legume
            "lentil":               "Wheat",
            "mungbean":             "Soybeans",
            "blackgram":            "Soybeans",
            "kidneybeans":          "Soybeans",
            "pigeonpeas":           "Sorghum",
            "mothbeans":            "Sorghum",
            "cotton":               "Maize",
            "jute":                 "Rice, paddy",
            "coffee":               "Maize",
            "coconut":              "Cassava",
            "mango":                "Cassava",
            "grapes":               "Cassava",
            "apple":                "Wheat",
            "orange":               "Cassava",
            "papaya":               "Cassava",
            "pomegranate":          "Cassava",
            "muskmelon":            "Cassava",
            "watermelon":           "Cassava",
        }
    }
    joblib.dump(means, MEANS_PATH)

    print(f"\n  Saved model  -> {MODEL_PATH}")
    print(f"  Saved means  -> {MEANS_PATH}")
    print(f"  Saved area_le-> {AREA_LE_PATH}")
    print(f"  Saved item_le-> {ITEM_LE_PATH}")
    print("\nDone!")


if __name__ == "__main__":
    train_model()
