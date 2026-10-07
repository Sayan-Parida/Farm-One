"""
District-level crop yield prediction (live inference).

What a prediction means
-----------------------
"Expected average yield (t/ha) of <crop> in <district>, <state> for the
<season> season of crop year <Y>", with an 80% range.

It is a district average from official statistics — an individual farm can be
above or below it depending on irrigation, variety, inputs and management.

How it is computed (same features as training, see ml/yield_features.py)
------------------------------------------------------------------------
1. The clicked lat/lon is matched to the nearest district centroid.
2. District + state yield history comes from the official APY data, using the
   same publication lag the model was trained and tested with.
3. Season weather = observed months that have already passed in this season
   (rain: IMD gridded gauges, temperature: NASA POWER — the same sources as
   training) + the district's 1997-2014 normal for months still to come.
4. A gradient-boosting model trained on 1997-2022 and tested on unseen years
   2018-2022 predicts log-yield; the range comes from validation residuals.
"""

import json
import os
import threading
from datetime import date, timedelta
from functools import lru_cache

import httpx
import joblib
import numpy as np
import pandas as pd

from ml import imd_grid
from ml.yield_features import (
    ANOMALY_COLS, CATEGORICAL_COLS, CROP_ALIASES, CROPS, FEATURE_COLS, HIST_GAP, HIST_MIN_OBS,
    HIST_WINDOW, SEASONS, WEATHER_COLS, add_anomalies, aggregate_season_weather, ag_year_for,
    current_season_for_month, haversine_km, season_calendar,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE_DIR, "data")
MODELS = os.path.join(BASE_DIR, "models")

MAX_DISTRICT_DISTANCE_KM = 120  # further than this from any district centroid → outside coverage
POWER_DAILY = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_LAG_DAYS = 7               # NASA POWER daily data is published with a few days delay
IMD_ARCHIVE_DIR = os.path.join(DATA, "raw", "imd")

_res = None


def _load():
    global _res
    if _res is not None:
        return _res
    with open(os.path.join(MODELS, "yield_model_meta.json")) as f:
        meta = json.load(f)
    with open(os.path.join(MODELS, "yield_model_report.json")) as f:
        report = json.load(f)

    apy = pd.read_csv(os.path.join(DATA, "apy_clean.csv"))
    coords = pd.read_csv(os.path.join(DATA, "district_coords.csv")).dropna(subset=["lat", "lon"])
    coords = coords[coords["district_code"].isin(apy["district_code"].unique())].reset_index(drop=True)
    season_clim = pd.read_csv(os.path.join(DATA, "season_climatology.csv"))
    monthly = pd.read_csv(os.path.join(DATA, "district_monthly_weather.csv"))
    monthly_clim = (monthly[(monthly["year"] >= 1997) & (monthly["year"] <= 2014)]
                    .groupby(["district_code", "month"])[["rain_mm", "t_mean", "t_max", "t_min"]]
                    .mean())
    monthly_obs = monthly.dropna(subset=["rain_mm", "t_mean", "t_max", "t_min"]).set_index(
        ["district_code", "year", "month"])[["rain_mm", "t_mean", "t_max", "t_min"]]

    state_year = apy.groupby(["state", "crop", "season", "year"])[["production", "area"]].sum()
    state_year["log_yield"] = np.log(state_year["production"] / state_year["area"])

    _res = {
        "model": joblib.load(os.path.join(MODELS, "yield_district_model.pkl")),
        "meta": meta,
        "report": report,
        "apy": apy,
        "apy_idx": apy.set_index(["district_code", "crop", "season"]).sort_index(),
        "state_year": state_year["log_yield"].sort_index(),
        "coords": coords,
        "season_clim": season_clim.set_index(["district_code", "season"]).to_dict("index"),
        "monthly_clim": monthly_clim,
        "monthly_obs": monthly_obs,
        "imd_cells": imd_grid.district_cell_weights(coords),
    }
    return _res


# ── Lookups ─────────────────────────────────────────────────────────────────

def resolve_crop(name):
    if not name:
        return None
    key = str(name).strip()
    if key in CROPS:
        return key
    return CROP_ALIASES.get(key.lower())


def nearest_district(lat, lon):
    r = _load()
    c = r["coords"]
    d = haversine_km(lat, lon, c["lat"].values, c["lon"].values)
    i = int(np.argmin(d))
    row = c.iloc[i]
    return {
        "district_code": int(row["district_code"]),
        "district": row["district_name"],
        "state": row["state_name"],
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "distance_km": round(float(d[i]), 1),
    }


def _history(district_code, state, crop, season, ag_year):
    """Gap-aware history exactly as in training; falls back to the latest window if data runs out."""
    r = _load()
    latest = r["meta"]["latest_data_year"]
    hi = min(ag_year - HIST_GAP, latest)
    lo = hi - HIST_WINDOW + 1
    try:
        series = r["apy_idx"].loc[(district_code, crop, season)]
    except KeyError:
        return None
    window = series[(series["year"] >= lo) & (series["year"] <= hi)]
    if len(window) < HIST_MIN_OBS:
        return None
    logs = np.log(window["yield_t_ha"].values)
    try:
        st = r["state_year"].loc[(state, crop, season)]
        st = st[(st.index >= lo) & (st.index <= hi)]
        state_hist = float(st.mean()) if len(st) else float(np.mean(logs))
    except KeyError:
        state_hist = float(np.mean(logs))
    return {
        "hist_log_yield": float(np.mean(logs)),
        "hist_n": int(len(logs)),
        "hist_log_std": float(np.std(logs, ddof=1)) if len(logs) > 1 else np.nan,
        "state_hist_log_yield": state_hist,
        "years": f"{lo}-{hi}",
        "mean_yield_t_ha": round(float(np.mean(window["yield_t_ha"])), 2),
        "yearly": [{"year": f"{int(y)}-{str(int(y) + 1)[-2:]}", "yield_t_ha": round(float(v), 2)}
                   for y, v in zip(window["year"], window["yield_t_ha"])],
        "latest_area_ha": float(window.sort_values("year")["area"].iloc[-1]),
    }


@lru_cache(maxsize=4)
def _imd_archive_year(year):
    path = os.path.join(IMD_ARCHIVE_DIR, f"rain_{year}.grd")
    return imd_grid.read_imd_year(path, year) if os.path.exists(path) else None


def _imd_month_rain(district_code, year, month, today):
    """District rain total for a month: IMD archive year file if published, else real-time cache."""
    cells, w = _load()["imd_cells"][district_code]
    grid = _imd_archive_year(year)
    if grid is not None:
        start = date(year, 1, 1)
        idx = [i for i in range(grid.shape[0]) if (start + timedelta(days=i)).month == month]
        return float(np.sum(np.nansum(grid[idx], axis=0)[cells] * w))
    return imd_grid.realtime_month_total((cells, w), year, month, today)


def _power_month_temps(lat, lon, months):
    """{(y, m): {t_mean, t_max, t_min}} from NASA POWER daily data."""
    start = date(months[0][0], months[0][1], 1)
    ly, lm = months[-1]
    end = date(ly + (lm == 12), lm % 12 + 1, 1) - timedelta(days=1)
    try:
        resp = httpx.get(POWER_DAILY, params={
            "parameters": "T2M,T2M_MAX,T2M_MIN", "community": "AG",
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"), "format": "JSON",
        }, timeout=25)
        resp.raise_for_status()
        p = resp.json()["properties"]["parameter"]
    except Exception as e:
        print(f"NASA POWER daily fetch failed, using climate normals: {e}")
        return {}
    daily = pd.DataFrame({k: pd.Series(v) for k, v in p.items()}).replace(-999, np.nan)
    daily.index = pd.to_datetime(daily.index, format="%Y%m%d")
    out = {}
    for (y, m) in months:
        d = daily[(daily.index.year == y) & (daily.index.month == m)]
        if len(d) < 25 or d.isna().any().any():
            continue
        out[(y, m)] = {"t_mean": d["T2M"].mean(), "t_max": d["T2M_MAX"].max(), "t_min": d["T2M_MIN"].min()}
    return out


def _start_realtime_refresh(months, today):
    """Fill the IMD real-time cache for this season in the background (each day file is slow to fetch)."""
    first = date(months[0][0], months[0][1], 1)
    last = today - timedelta(days=2)
    if first > last or os.path.exists(os.path.join(IMD_ARCHIVE_DIR, f"rain_{first.year}.grd")) and \
            os.path.exists(os.path.join(IMD_ARCHIVE_DIR, f"rain_{last.year}.grd")):
        return
    threading.Thread(target=imd_grid.refresh_realtime_cache, args=(first, last), daemon=True).start()


def _fetch_observed_months(district, months, today):
    """Observed monthly weather for season months that are complete. Missing months → not observed."""
    r = _load()
    code = district["district_code"]
    cutoff = today - timedelta(days=POWER_LAG_DAYS)
    complete = [(y, m) for (y, m) in months
                if date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1) <= cutoff]
    if not complete:
        return {}

    out, need_live = {}, []
    for ym in complete:
        key = (code, *ym)
        if key in r["monthly_obs"].index:  # same table the model was trained on
            out[ym] = r["monthly_obs"].loc[key].to_dict()
        else:
            need_live.append(ym)
    if need_live:
        _start_realtime_refresh(months, today)
        temps = _power_month_temps(district["lat"], district["lon"], need_live)
        for ym in need_live:
            rain = _imd_month_rain(code, ym[0], ym[1], today)
            if rain is not None and ym in temps:
                out[ym] = {"rain_mm": rain, **temps[ym]}
    # Only a contiguous run from the season start counts as "observed" — a gap would mix sources oddly.
    observed = {}
    for ym in months:
        if ym not in out:
            break
        observed[ym] = out[ym]
    return observed


def season_weather(district, season, ag_year, today=None):
    """Season weather features: observed months + normals for the rest. Returns (features, basis)."""
    r = _load()
    today = today or date.today()
    code = district["district_code"]
    months = season_calendar(season, ag_year)
    clim = r["season_clim"].get((code, season))
    observed = _fetch_observed_months(district, months, today)

    if not observed:
        if clim is None:
            return None, None
        feats = {k: clim[k] for k in WEATHER_COLS}
        feats.update({k: 0.0 for k in ANOMALY_COLS})
    else:
        monthly = {}
        for ym in months:
            if ym in observed:
                monthly[ym] = observed[ym]
            else:
                try:
                    monthly[ym] = r["monthly_clim"].loc[(code, ym[1])].to_dict()
                except KeyError:
                    monthly[ym] = None
        feats = aggregate_season_weather(monthly)
        if feats is None:
            return None, None
        feats = add_anomalies(feats, clim)

    basis = {
        "months_in_season": len(months),
        "months_observed": len(observed),
        "observed_months": [f"{y}-{m:02d}" for (y, m) in sorted(observed)],
        "source": "IMD gridded rainfall + NASA POWER temperature (observed months); "
                  "1997-2014 district normals (remaining months)",
        "season_rain_mm": round(feats["w_rain_mm"], 1),
        "season_mean_temp_c": round(feats["w_t_mean"], 1),
        "rain_vs_normal_pct": None if np.isnan(feats.get("w_rain_anom_pct", np.nan))
        else round(feats["w_rain_anom_pct"], 1),
    }
    return feats, basis


def crops_in_district(district_code, season, min_years=HIST_MIN_OBS):
    """Crops with enough recent official records in this district & season."""
    r = _load()
    latest = r["meta"]["latest_data_year"]
    a = r["apy"]
    sub = a[(a["district_code"] == district_code) & (a["season"] == season)
            & (a["year"] > latest - HIST_WINDOW)]
    counts = sub.groupby("crop").agg(n=("year", "nunique"), area=("area", "mean"))
    counts = counts[counts["n"] >= min_years].sort_values("area", ascending=False)
    return [{"crop": c, "avg_area_ha": round(float(row["area"]))} for c, row in counts.iterrows()]


def seasons_for_crop(district_code, crop, min_years=HIST_MIN_OBS):
    """Seasons in which this crop has enough recent official records in the district, largest area first."""
    r = _load()
    latest = r["meta"]["latest_data_year"]
    a = r["apy"]
    sub = a[(a["district_code"] == district_code) & (a["crop"] == crop)
            & (a["year"] > latest - HIST_WINDOW)]
    counts = sub.groupby("season").agg(n=("year", "nunique"), area=("area", "mean"))
    counts = counts[counts["n"] >= min_years].sort_values("area", ascending=False)
    return [{"season": s, "avg_area_ha": round(float(row["area"]))} for s, row in counts.iterrows()]


def seasons_in_district(district_code):
    r = _load()
    a = r["apy"]
    return sorted(a.loc[a["district_code"] == district_code, "season"].unique().tolist())


# ── Core prediction ─────────────────────────────────────────────────────────

def _predict_one(district, crop, season, ag_year, weather_feats, basis):
    r = _load()
    hist = _history(district["district_code"], district["state"], crop, season, ag_year)
    if hist is None:
        return None
    row = {
        "crop": crop, "season": season, "state": district["state"],
        "lat": district["lat"], "lon": district["lon"], "year": ag_year,
        **{k: hist[k] for k in ("hist_log_yield", "hist_n", "hist_log_std", "state_hist_log_yield")},
        **weather_feats,
    }
    X = pd.DataFrame([row])[FEATURE_COLS]
    for c in CATEGORICAL_COLS:
        X[c] = pd.Categorical(X[c], categories=r["meta"]["categories"][c])
    # Blend the weather-aware model with the per-crop/season drift baseline (weight chosen in training).
    w = r["meta"].get("blend_model_weight", 1.0)
    drift = r["meta"].get("drift", {}).get(f"{crop}|{season}", 0.0)
    log_pred = hist["hist_log_yield"] + w * float(r["model"].predict(X)[0]) + (1 - w) * drift

    # Interval: blend pre-season and actual-weather residual quantiles by fraction of season observed.
    frac = basis["months_observed"] / basis["months_in_season"]
    pre = r["meta"]["interval_pre_season"]
    act = r["meta"]["interval_actual_weather"]
    qp = pre["per_crop"].get(crop, pre["all"])
    qa = act["per_crop"].get(crop, act["all"])
    q10 = (1 - frac) * qp["q10"] + frac * qa["q10"]
    q90 = (1 - frac) * qp["q90"] + frac * qa["q90"]

    pred = float(np.exp(log_pred))
    return {"pred": pred, "low": pred * np.exp(q10), "high": pred * np.exp(q90), "hist": hist,
            "rel_width": (np.exp(q90) - np.exp(q10))}


def _confidence(res, basis):
    """High/Medium/Low from interval width, history depth and how much of the season is observed."""
    score = 0
    if res["rel_width"] < 0.45:
        score += 1
    if res["hist"]["hist_n"] >= 4:
        score += 1
    if basis["months_observed"] >= basis["months_in_season"] / 2:
        score += 1
    return "High" if score >= 3 else "Medium" if score >= 1 else "Low"


def predict_yield(features: dict):
    """
    features:
        lat, lon         (required) farm location
        crop_name        optional; defaults to the district's main crop for the season
        season           optional; Kharif / Rabi / Summer / Autumn / Winter / Whole Year
                         (defaults to the season for the current month)
        today            optional date override (for testing)
    """
    try:
        r = _load()
    except FileNotFoundError as e:
        return {"error": f"Yield model artefacts missing — run the ml/pipeline steps first ({e})"}

    lat, lon = features.get("lat"), features.get("lon")
    if lat is None or lon is None:
        return {"error": "Location (lat, lon) is required for a district-level yield estimate.",
                "status": 400}

    district = nearest_district(float(lat), float(lon))
    if district["distance_km"] > MAX_DISTRICT_DISTANCE_KM:
        return {"error": "This location is outside the area covered by Indian district crop statistics.",
                "status": 422, "district": district}

    today = features.get("today") or date.today()
    season = features.get("season")
    if season and season not in SEASONS:
        return {"error": f"Unknown season '{season}'. Use one of {SEASONS}.", "status": 400}
    season_was_given = bool(season)
    season = season or current_season_for_month(today.month)
    available_seasons = seasons_in_district(district["district_code"])
    if season not in available_seasons and not season_was_given:
        # e.g. no Summer crop data recorded in this district — fall back to Kharif/Rabi
        for s in ("Kharif", "Rabi", "Whole Year"):
            if s in available_seasons:
                season = s
                break
    ag_year = ag_year_for(season, today.year, today.month)

    available = crops_in_district(district["district_code"], season)
    crop_requested = features.get("crop_name")
    crop = resolve_crop(crop_requested)
    if crop_requested and crop is None:
        return {"error": f"'{crop_requested}' is not one of the crops the yield model covers.",
                "status": 422, "supported_crops": sorted(CROPS), "available_crops": available,
                "district": district, "season": season}
    crop_seasons = seasons_for_crop(district["district_code"], crop) if crop else []
    season_defaulted = False
    if crop and crop not in {c["crop"] for c in available} and crop_seasons and not season_was_given:
        # e.g. rice in West Bengal is recorded as Autumn/Winter/Summer, not Kharif — use the crop's main season
        season = crop_seasons[0]["season"]
        season_defaulted = True
        ag_year = ag_year_for(season, today.year, today.month)
        available = crops_in_district(district["district_code"], season)
    crop_defaulted = False
    if crop is None:
        if not available:
            return {"error": f"No official {season} crop records for {district['district']} — "
                             f"cannot estimate yield here.", "status": 422, "district": district,
                    "available_seasons": available_seasons}
        crop = available[0]["crop"]
        crop_defaulted = True

    weather_feats, basis = season_weather(district, season, ag_year, today)
    if weather_feats is None:
        return {"error": "Weather data unavailable for this district.", "status": 503}

    res = _predict_one(district, crop, season, ag_year, weather_feats, basis)
    if res is None:
        hint = (f" It is recorded in {district['district']} as: "
                + ", ".join(x["season"] for x in crop_seasons) + "." if crop_seasons else "")
        return {"error": f"{crop} has too few official {season} records in {district['district']} "
                         f"to give a reliable estimate.{hint}", "status": 422,
                "district": district, "season": season, "available_crops": available,
                "crop_seasons": crop_seasons}

    test = r["report"]["test_by_crop"].get(crop, {})
    season_label = f"{season} {ag_year}-{str(ag_year + 1)[-2:]}"
    observed_txt = (f"{basis['months_observed']} of {basis['months_in_season']} season months use observed "
                    f"weather; the rest use the district's normal climate."
                    if basis["months_observed"] else
                    "The season hasn't started yet (or no complete month is available), so normal "
                    "climate for the district is assumed.")
    note = (f"District-average estimate for {crop}, {season_label}, {district['district']} "
            f"({district['state']}). Based on official yields {res['hist']['years']} "
            f"(avg {res['hist']['mean_yield_t_ha']} t/ha) and season weather. {observed_txt} "
            f"Your own field may differ with irrigation, variety and inputs.")
    if crop_defaulted:
        note = f"No crop selected — showing the district's main {season} crop. " + note
    if season_defaulted:
        note = f"{crop} is mainly recorded as a {season} crop in {district['district']}, so that season is shown. " + note

    return {
        "expected_yield_ton_per_hectare": round(res["pred"], 2),
        "range_ton_per_hectare": [round(res["low"], 2), round(res["high"], 2)],
        "range_level": "80%",
        "confidence": _confidence(res, basis),
        "note": note,
        "crop": crop,
        "crop_defaulted": crop_defaulted,
        "season_defaulted": season_defaulted,
        "season": season,
        "agricultural_year": f"{ag_year}-{str(ag_year + 1)[-2:]}",
        "district": district["district"],
        "state": district["state"],
        "district_distance_km": district["distance_km"],
        "history": {"years": res["hist"]["years"], "mean_yield_t_ha": res["hist"]["mean_yield_t_ha"],
                    "yearly": res["hist"]["yearly"]},
        "weather_basis": basis,
        "available_crops": available,
        "available_seasons": available_seasons,
        "model_accuracy": {
            "tested_on": r["report"]["split"]["test"],
            "crop_median_error_pct": test.get("model_pre_season_mAPE"),
            "overall_median_error_pct": r["report"]["test_overall"]["model_pre_season"]["median_APE_pct"],
        },
    }


def recommend_crops(features: dict, top_k: int = 5):
    """
    Data-driven crop suitability for a location and season.

    Candidates are crops that are actually grown (officially recorded) in the
    district in that season. Each is scored by its predicted yield relative to
    the national median for that crop & season — i.e. "how well does this crop
    do HERE compared to elsewhere in India". Nothing is invented: every crop
    shown has real recorded production in the district.
    """
    try:
        r = _load()
    except FileNotFoundError as e:
        return {"error": f"Model artefacts missing — run the ml/pipeline steps first ({e})"}

    lat, lon = features.get("lat"), features.get("lon")
    if lat is None or lon is None:
        return {"error": "Location (lat, lon) is required for crop recommendation.", "status": 400}
    district = nearest_district(float(lat), float(lon))
    if district["distance_km"] > MAX_DISTRICT_DISTANCE_KM:
        return {"error": "This location is outside the area covered by Indian district crop statistics.",
                "status": 422}

    today = features.get("today") or date.today()
    season = features.get("season") or current_season_for_month(today.month)
    available_seasons = seasons_in_district(district["district_code"])
    if season not in available_seasons:
        for s in ("Kharif", "Rabi", "Whole Year"):
            if s in available_seasons:
                season = s
                break
    ag_year = ag_year_for(season, today.year, today.month)

    candidates = crops_in_district(district["district_code"], season)
    if not candidates:
        return {"error": f"No official {season} crop records for {district['district']}.", "status": 422}

    weather_feats, basis = season_weather(district, season, ag_year, today)
    if weather_feats is None:
        return {"error": "Weather data unavailable for this district.", "status": 503}

    apy = r["apy"]
    latest = r["meta"]["latest_data_year"]
    recent = apy[(apy["season"] == season) & (apy["year"] > latest - HIST_WINDOW)]
    national_median = recent.groupby("crop")["yield_t_ha"].median()
    total_area = sum(c["avg_area_ha"] for c in candidates) or 1

    recs = []
    for c in candidates:
        res = _predict_one(district, c["crop"], season, ag_year, weather_feats, basis)
        if res is None or c["crop"] not in national_median:
            continue
        rel = res["pred"] / national_median[c["crop"]]
        recs.append({
            "crop": c["crop"],
            "expected_yield_t_ha": round(res["pred"], 2),
            "range_t_ha": [round(res["low"], 2), round(res["high"], 2)],
            "relative_to_national_pct": round(rel * 100),
            "district_area_share_pct": round(100 * c["avg_area_ha"] / total_area, 1),
            "confidence_level": _confidence(res, basis),
        })
    # Rank by relative performance, lightly favouring crops that are well established locally.
    recs.sort(key=lambda x: x["relative_to_national_pct"] * (1 + 0.5 * min(x["district_area_share_pct"], 40) / 40),
              reverse=True)
    return {
        "district": district["district"],
        "state": district["state"],
        "season": season,
        "agricultural_year": f"{ag_year}-{str(ag_year + 1)[-2:]}",
        "weather_basis": basis,
        "recommended_crops": recs[:top_k],
        "method": "Crops officially grown in this district in this season, ranked by predicted yield "
                  "relative to India's median for the same crop and season.",
    }
