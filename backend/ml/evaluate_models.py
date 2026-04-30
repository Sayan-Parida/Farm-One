"""
FarmOne ML Model Evaluation Script
===================================
Evaluates:
  1. Crop Recommendation Model  (RandomForestClassifier)
  2. Yield Prediction Model      (RandomForestRegressor)

Run from the project root:
    python backend/ml/evaluate_models.py
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    # Classification
    accuracy_score, f1_score, precision_score, recall_score,
    classification_report, confusion_matrix,
    # Regression
    r2_score, mean_absolute_error, mean_squared_error,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def section(title):
    width = 60
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)

def subsection(title):
    print(f"\n── {title} " + "─" * (55 - len(title)))


# ═════════════════════════════════════════════
# 1. CROP RECOMMENDATION MODEL (Classifier)
# ═════════════════════════════════════════════

def evaluate_crop_model():
    section("CROP RECOMMENDATION MODEL  (RandomForestClassifier)")

    data_path  = os.path.join(BASE_DIR, "data", "crop_recommendation.csv")
    model_path = os.path.join(BASE_DIR, "models", "crop_rf.pkl")
    le_path    = os.path.join(BASE_DIR, "models", "label_encoder.pkl")

    # ── Load data ──
    print("\n📂  Loading dataset …")
    df = pd.read_csv(data_path)
    df = df.drop(columns=["N", "P", "K"])

    X = df[["temperature", "humidity", "rainfall", "ph"]]
    y = df["label"]

    le = LabelEncoder()
    y_enc = le.fit_transform(y)
    num_classes = len(le.classes_)

    print(f"   Rows: {len(df):,}  |  Classes: {num_classes}")
    print(f"   Class labels: {list(le.classes_)}")

    # ── Split (same seed as training) ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42
    )

    # ── Load saved model ──
    print("\n🔄  Loading saved model …")
    model = joblib.load(model_path)

    # ── Predictions ──
    y_pred = model.predict(X_test)

    subsection("Core Metrics (held-out test set, 20 %)")

    acc       = accuracy_score(y_test, y_pred)
    f1_macro  = f1_score(y_test, y_pred, average="macro",    zero_division=0)
    f1_weight = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    prec      = precision_score(y_test, y_pred, average="weighted", zero_division=0)
    rec       = recall_score(y_test, y_pred, average="weighted",    zero_division=0)

    print(f"   Accuracy            : {acc * 100:.2f} %")
    print(f"   Precision (weighted): {prec:.4f}")
    print(f"   Recall    (weighted): {rec:.4f}")
    print(f"   F1-Score  (macro)   : {f1_macro:.4f}")
    print(f"   F1-Score  (weighted): {f1_weight:.4f}")

    subsection("Cross-Validation (5-fold, full dataset, F1 weighted)")
    cv_scores = cross_val_score(model, X, y_enc, cv=5,
                                scoring="f1_weighted", n_jobs=-1)
    print(f"   CV F1 scores : {[round(s, 4) for s in cv_scores]}")
    print(f"   Mean ± Std   : {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    subsection("Per-Class Classification Report")
    target_names = [str(c) for c in le.classes_]
    print(classification_report(y_test, y_pred,
                                target_names=target_names, zero_division=0))

    subsection("Feature Importances (RF)")
    importances = model.feature_importances_
    feat_names  = ["temperature", "humidity", "rainfall", "ph"]
    for feat, imp in sorted(zip(feat_names, importances),
                            key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"   {feat:<15} {imp:.4f}  {bar}")

    return {
        "accuracy":        round(acc, 4),
        "precision_w":     round(prec, 4),
        "recall_w":        round(rec, 4),
        "f1_macro":        round(f1_macro, 4),
        "f1_weighted":     round(f1_weight, 4),
        "cv_mean_f1":      round(cv_scores.mean(), 4),
        "cv_std_f1":       round(cv_scores.std(), 4),
    }


# ═════════════════════════════════════════════
# 2. YIELD PREDICTION MODEL (Regressor)
# ═════════════════════════════════════════════

def evaluate_yield_model():
    section("YIELD PREDICTION MODEL  (GradientBoostingRegressor v2)")

    data_path  = os.path.join(BASE_DIR, "data", "crop_yield.csv")
    model_path = os.path.join(BASE_DIR, "models", "yield_rf.pkl")

    # ── Load data ──
    print("\n📂  Loading dataset ...")
    df = pd.read_csv(data_path)
    df = df.drop(columns=["Unnamed: 0"], errors="ignore")
    print(f"   Rows: {len(df):,}  |  Columns: {list(df.columns)}")

    # Encode categoricals (same as training)
    from sklearn.preprocessing import LabelEncoder
    area_le = LabelEncoder()
    item_le = LabelEncoder()
    df["Area_enc"] = area_le.fit_transform(df["Area"])
    df["Item_enc"] = item_le.fit_transform(df["Item"])

    feature_cols = ["Temperature", "Rainfall", "pesticides_tonnes",
                    "Year", "Area_enc", "Item_enc"]
    target_col   = "Yield"

    X = df[feature_cols]
    y = df[target_col]

    # ── Split (same seed as training) ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ── Load saved model ──
    print("\n🔄  Loading saved model ...")
    model = joblib.load(model_path)

    # ── Predictions ──
    y_pred = model.predict(X_test)

    subsection("Core Metrics (held-out test set, 20 %)")

    r2   = r2_score(y_test, y_pred)
    mae  = mean_absolute_error(y_test, y_pred)
    mse  = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((y_test - y_pred) / np.where(y_test == 0, 1, y_test))) * 100

    y_mean   = y_test.mean()
    rel_rmse = (rmse / y_mean) * 100

    print(f"   R² Score            : {r2:.4f}   ({r2*100:.2f} % variance explained)")
    print(f"   MAE                 : {mae:,.2f} hg/ha  "
          f"({mae / 10000:.4f} ton/ha)")
    print(f"   RMSE                : {rmse:,.2f} hg/ha  "
          f"({rmse / 10000:.4f} ton/ha)")
    print(f"   MAPE                : {mape:.2f} %")
    print(f"   Relative RMSE       : {rel_rmse:.2f} %  (RMSE / mean_y × 100)")
    print(f"   Mean target (test)  : {y_mean:,.0f} hg/ha  "
          f"({y_mean / 10000:.2f} ton/ha)")

    subsection("Cross-Validation (5-fold, full dataset, R²)")
    cv_r2 = cross_val_score(model, X, y, cv=5, scoring="r2", n_jobs=-1)
    print(f"   CV R² scores : {[round(float(s), 4) for s in cv_r2]}")
    print(f"   Mean ± Std   : {cv_r2.mean():.4f} ± {cv_r2.std():.4f}")

    subsection("Residual Analysis")
    residuals  = y_test - y_pred
    print(f"   Max over-prediction  : {residuals.min():,.0f} hg/ha")
    print(f"   Max under-prediction : {residuals.max():,.0f} hg/ha")
    print(f"   Median residual      : {np.median(residuals):,.0f} hg/ha")

    subsection("Feature Importances (GBR)")
    importances = model.feature_importances_
    for feat, imp in sorted(zip(feature_cols, importances),
                            key=lambda x: -x[1]):
        bar = "█" * int(imp * 40)
        print(f"   {feat:<25} {imp:.4f}  {bar}")

    return {
        "r2":              round(r2, 4),
        "mae_hg_ha":       round(mae, 2),
        "rmse_hg_ha":      round(rmse, 2),
        "mape_pct":        round(mape, 2),
        "rel_rmse_pct":    round(rel_rmse, 2),
        "cv_mean_r2":      round(cv_r2.mean(), 4),
        "cv_std_r2":       round(cv_r2.std(), 4),
    }


# ═════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "★" * 60)
    print("   FarmOne  —  ML Model Evaluation Suite")
    print("★" * 60)

    crop_metrics  = evaluate_crop_model()
    yield_metrics = evaluate_yield_model()

    section("SUMMARY TABLE")
    print("\n  ┌─────────────────────────────────────────────────────┐")
    print("  │           CROP RECOMMENDATION (Classifier)          │")
    print("  ├─────────────────────────────────────────────────────┤")
    for k, v in crop_metrics.items():
        print(f"  │  {k:<28} {str(v):>20}  │")
    print("  ├─────────────────────────────────────────────────────┤")
    print("  │           YIELD PREDICTION (Regressor)              │")
    print("  ├─────────────────────────────────────────────────────┤")
    for k, v in yield_metrics.items():
        print(f"  │  {k:<28} {str(v):>20}  │")
    print("  └─────────────────────────────────────────────────────┘")
    print()
