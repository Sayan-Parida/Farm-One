"""
Shared feature definitions for the district yield model.

Imported by BOTH the training pipeline (ml/pipeline/*) and live inference
(ml/yield_prediction.py) so the features the model is trained on are computed
exactly the same way as the features it receives in production.

Unit of prediction: one crop, in one district, in one season, of one
agricultural year.  An agricultural year "Y" means the Indian crop year that
starts in June of Y (e.g. Y=2022 is the "2022-2023" crop year).
"""

import numpy as np

# ── Crops kept for modelling ────────────────────────────────────────────────
# Major field crops reported in tonnes. Excluded on purpose: Coconut (reported
# in nuts), Cotton/Jute/Mesta (reported in bales in many states), and minor
# "Other ..." groupings whose composition changes between states.
# Values are an upper plausibility bound in t/ha for a *district average*;
# rows above it are data-entry errors (e.g. rice at 223 t/ha) and are dropped.
CROPS = {
    "Rice": 8.0,
    "Wheat": 7.5,
    "Maize": 12.0,
    "Jowar": 6.0,
    "Bajra": 5.0,
    "Ragi": 5.0,
    "Barley": 6.0,
    "Small Millets": 3.0,
    "Gram": 3.5,
    "Arhar/Tur": 3.5,
    "Moong(Green Gram)": 2.5,
    "Urad": 2.5,
    "Masoor": 3.0,
    "Groundnut": 5.0,
    "Rapeseed &Mustard": 3.5,
    "Soyabean": 4.0,
    "Sesamum": 2.0,
    "Sunflower": 3.5,
    "Linseed": 2.5,
    "Castor Seed": 4.0,
    "Potato": 50.0,
    "Onion": 50.0,
    "Sugarcane": 150.0,
}

# Friendly names users / other modules may send → dataset crop name.
CROP_ALIASES = {
    "rice": "Rice", "paddy": "Rice", "wheat": "Wheat", "maize": "Maize", "corn": "Maize",
    "jowar": "Jowar", "sorghum": "Jowar", "bajra": "Bajra", "pearl millet": "Bajra",
    "ragi": "Ragi", "finger millet": "Ragi", "barley": "Barley", "small millets": "Small Millets",
    "gram": "Gram", "chickpea": "Gram", "chana": "Gram",
    "arhar": "Arhar/Tur", "tur": "Arhar/Tur", "pigeonpea": "Arhar/Tur", "pigeon pea": "Arhar/Tur",
    "moong": "Moong(Green Gram)", "mungbean": "Moong(Green Gram)", "green gram": "Moong(Green Gram)",
    "urad": "Urad", "blackgram": "Urad", "black gram": "Urad",
    "masoor": "Masoor", "lentil": "Masoor",
    "groundnut": "Groundnut", "peanut": "Groundnut",
    "mustard": "Rapeseed &Mustard", "rapeseed": "Rapeseed &Mustard", "rapeseed & mustard": "Rapeseed &Mustard",
    "soyabean": "Soyabean", "soybean": "Soyabean", "sesamum": "Sesamum", "sesame": "Sesamum", "til": "Sesamum",
    "sunflower": "Sunflower", "linseed": "Linseed", "castor": "Castor Seed", "castor seed": "Castor Seed",
    "potato": "Potato", "onion": "Onion", "sugarcane": "Sugarcane",
}

# ── Season → calendar months ────────────────────────────────────────────────
# (year_offset, month) pairs relative to agricultural year Y.
# Standard Indian crop calendar (DES / IMD conventions).
SEASON_MONTHS = {
    "Kharif":     [(0, m) for m in (6, 7, 8, 9, 10)],                      # Jun–Oct Y
    "Rabi":       [(0, 11), (0, 12), (1, 1), (1, 2), (1, 3)],              # Nov Y – Mar Y+1
    "Summer":     [(1, m) for m in (3, 4, 5, 6)],                          # Mar–Jun Y+1 (zaid)
    "Autumn":     [(0, m) for m in (4, 5, 6, 7, 8)],                       # Apr–Aug Y (aus / bhadoi)
    "Winter":     [(0, m) for m in (7, 8, 9, 10, 11)],                     # Jul–Nov Y (aman)
    "Whole Year": [(0, m) for m in range(6, 13)] + [(1, m) for m in range(1, 6)],  # Jun Y – May Y+1
}
SEASONS = list(SEASON_MONTHS)

# ── History features ────────────────────────────────────────────────────────
# Official district statistics are published with a multi-year lag (the latest
# in our data is 2022-23). When the app predicts the current season, the most
# recent yield it knows is ~4 years old. To make offline evaluation honest, the
# model is trained and tested with the SAME lag: history for year Y uses only
# years Y-HIST_GAP-HIST_WINDOW+1 … Y-HIST_GAP.
HIST_GAP = 4
HIST_WINDOW = 5
HIST_MIN_OBS = 2

# Weather normals (climatology) are computed from these years only, which are
# all inside the training period, so test years never leak into features.
CLIMATOLOGY_YEARS = (1997, 2014)

# Rainfall: IMD gridded gauges. Temperature: NASA POWER. Humidity is deliberately NOT used —
# NASA POWER RH2M has a step change around 2019 that would look like a fake climate signal.
WEATHER_COLS = ["w_rain_mm", "w_t_mean", "w_t_max", "w_t_min"]
ANOMALY_COLS = ["w_rain_anom_pct", "w_t_mean_anom"]

CATEGORICAL_COLS = ["crop", "season", "state"]
NUMERIC_COLS = (
    ["lat", "lon", "year", "hist_log_yield", "hist_n", "hist_log_std", "state_hist_log_yield"]
    + WEATHER_COLS
    + ANOMALY_COLS
)
FEATURE_COLS = CATEGORICAL_COLS + NUMERIC_COLS


def season_calendar(season: str, ag_year: int):
    """List of (calendar_year, month) covered by a season of agricultural year ag_year."""
    return [(ag_year + dy, m) for dy, m in SEASON_MONTHS[season]]


def aggregate_season_weather(monthly: dict):
    """
    Aggregate monthly weather into season features.

    monthly: {(year, month): {"rain_mm", "t_mean", "t_max", "t_min"}} for
             exactly the months of the season (missing months → returns None).
    """
    vals = list(monthly.values())
    if not vals or any(v is None for v in vals):
        return None
    try:
        return {
            "w_rain_mm": float(sum(v["rain_mm"] for v in vals)),
            "w_t_mean": float(np.mean([v["t_mean"] for v in vals])),
            "w_t_max": float(max(v["t_max"] for v in vals)),
            "w_t_min": float(min(v["t_min"] for v in vals)),
        }
    except (TypeError, KeyError):
        return None


def add_anomalies(row: dict, clim: dict):
    """Rain % anomaly and temperature anomaly versus the district-season normal."""
    if clim is None:
        row["w_rain_anom_pct"] = np.nan
        row["w_t_mean_anom"] = np.nan
        return row
    normal_rain = clim["w_rain_mm"]
    row["w_rain_anom_pct"] = (
        100.0 * (row["w_rain_mm"] - normal_rain) / normal_rain if normal_rain and normal_rain > 1 else np.nan
    )
    row["w_t_mean_anom"] = row["w_t_mean"] - clim["w_t_mean"]
    return row


def current_season_for_month(month: int):
    """Most likely season a farmer is planning for in a given calendar month."""
    if month in (6, 7, 8, 9, 10):
        return "Kharif"
    if month in (11, 12, 1, 2):
        return "Rabi"
    return "Summer"  # Mar–May


def ag_year_for(season: str, year: int, month: int):
    """Agricultural year a season belongs to, given today's calendar date."""
    if season in ("Rabi", "Whole Year"):
        # Rabi Nov–Mar: Jan–May belong to the crop year that began the previous June.
        return year - 1 if month <= 5 else year
    if season == "Summer":
        # Summer (Mar–Jun Y+1) belongs to crop year Y.
        return year - 1 if month <= 6 else year
    return year


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))
