"""
Step 3 — Build the modelling dataset.

Inputs : data/raw/apy_district.csv          (Ministry of Agriculture district APY, 1997-2023)
         data/district_coords.csv            (step 1)
         data/district_monthly_weather.csv   (step 2)
Outputs: data/apy_clean.csv                  cleaned yield records (also used at inference for history)
         data/season_weather.csv             weather aggregated per (district, season, ag year)
         data/season_climatology.csv         1997-2014 normal weather per (district, season)
         data/yield_dataset.csv              one row per (district, crop, season, year) with features + target
         data/cleaning_report.json           how many rows each cleaning rule removed
"""

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yield_features import (  # noqa: E402
    CLIMATOLOGY_YEARS, CROPS, WEATHER_COLS, HIST_GAP, HIST_MIN_OBS, HIST_WINDOW, SEASONS,
    add_anomalies, aggregate_season_weather, season_calendar,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")

MIN_AREA_HA = 100        # district-season totals below this are too small / noisy
SERIES_JUMP_FACTOR = 5   # drop a year whose yield is >5x or <1/5 of its series median (unit/entry errors)


def clean_apy():
    raw = pd.read_csv(os.path.join(DATA, "raw", "apy_district.csv"), low_memory=False)
    report = {"raw_rows": len(raw)}

    df = raw[raw["season"] != "Total"]
    report["drop_total_season_rows"] = len(raw) - len(df)

    n = len(df); df = df[df["crop_name"].isin(CROPS)]
    report["drop_not_modelled_crop"] = n - len(df)

    n = len(df); df = df[(df["area"] >= MIN_AREA_HA) & (df["production"] > 0)]
    report["drop_small_area_or_zero_production"] = n - len(df)

    df = df.assign(
        year=df["year"].str[:4].astype(int),
        yield_t_ha=df["production"] / df["area"],
    )

    n = len(df)
    bound = df["crop_name"].map(CROPS)
    df = df[df["yield_t_ha"] <= bound]
    report["drop_above_agronomic_max"] = n - len(df)

    n = len(df)
    key = ["district_code", "crop_name", "season"]
    med = df.groupby(key)["yield_t_ha"].transform("median")
    ratio = df["yield_t_ha"] / med
    df = df[(ratio <= SERIES_JUMP_FACTOR) & (ratio >= 1 / SERIES_JUMP_FACTOR)]
    report["drop_series_jump_outlier"] = n - len(df)

    df = df.rename(columns={"crop_name": "crop", "state_name": "state", "district_name": "district"})
    df = df[["district_code", "district", "state", "crop", "season", "year", "area", "production", "yield_t_ha"]]
    report["clean_rows"] = len(df)
    return df.reset_index(drop=True), report


def build_season_weather(coords):
    w = pd.read_csv(os.path.join(DATA, "district_monthly_weather.csv"))
    if "rain_source" not in w.columns:
        raise SystemExit("Run step2b_fetch_imd_rain.py first (NASA POWER rainfall is not homogeneous).")
    lookup = {
        (r.district_code, r.year, r.month): {"rain_mm": r.rain_mm, "t_mean": r.t_mean,
                                             "t_max": r.t_max, "t_min": r.t_min}
        for r in w.itertuples()
        if not pd.isna(r.rain_mm)
    }
    max_year = int(w["year"].max())
    rows = []
    for code in coords["district_code"]:
        for season in SEASONS:
            for ag_year in range(1997, max_year):
                months = season_calendar(season, ag_year)
                agg = aggregate_season_weather({ym: lookup.get((code, *ym)) for ym in months})
                if agg:
                    rows.append({"district_code": code, "season": season, "year": ag_year, **agg})
    sw = pd.DataFrame(rows)
    lo, hi = CLIMATOLOGY_YEARS
    clim = (sw[(sw["year"] >= lo) & (sw["year"] <= hi)]
            .groupby(["district_code", "season"])[WEATHER_COLS]
            .mean().reset_index())
    return sw, clim


def add_history(df):
    """Gap-aware trailing history of log-yield at district and state level."""
    df = df.copy()
    df["log_yield"] = np.log(df["yield_t_ha"])
    key = ["district_code", "crop", "season"]

    base = df[key + ["year", "log_yield"]]
    lags = []
    for k in range(HIST_GAP, HIST_GAP + HIST_WINDOW):
        lagged = base.assign(year=base["year"] + k).rename(columns={"log_yield": f"lag{k}"})
        df = df.merge(lagged, on=key + ["year"], how="left")
        lags.append(f"lag{k}")
    df["hist_n"] = df[lags].notna().sum(axis=1)
    df["hist_log_yield"] = df[lags].mean(axis=1)
    df["hist_log_std"] = df[lags].std(axis=1)
    df.loc[df["hist_n"] < HIST_MIN_OBS, ["hist_log_yield", "hist_log_std"]] = np.nan
    df = df.drop(columns=lags)

    # State-level history (area-weighted state yield in the same lag window)
    st = (df.groupby(["state", "crop", "season", "year"])[["production", "area"]].sum().reset_index())
    st["state_log_yield"] = np.log(st["production"] / st["area"])
    st = st[["state", "crop", "season", "year", "state_log_yield"]]
    skey = ["state", "crop", "season"]
    slags = []
    for k in range(HIST_GAP, HIST_GAP + HIST_WINDOW):
        lagged = st.assign(year=st["year"] + k).rename(columns={"state_log_yield": f"slag{k}"})
        df = df.merge(lagged, on=skey + ["year"], how="left")
        slags.append(f"slag{k}")
    df["state_hist_log_yield"] = df[slags].mean(axis=1)
    return df.drop(columns=slags)


def main():
    apy, report = clean_apy()
    print("Cleaning:", json.dumps(report, indent=2))
    apy.to_csv(os.path.join(DATA, "apy_clean.csv"), index=False)

    coords = pd.read_csv(os.path.join(DATA, "district_coords.csv")).dropna(subset=["lat", "lon"])
    print(f"Aggregating seasonal weather for {len(coords)} districts ...")
    sw, clim = build_season_weather(coords)
    sw.to_csv(os.path.join(DATA, "season_weather.csv"), index=False)
    clim.to_csv(os.path.join(DATA, "season_climatology.csv"), index=False)

    df = add_history(apy)
    df = df.merge(coords[["district_code", "lat", "lon"]], on="district_code", how="inner")
    df = df.merge(sw, on=["district_code", "season", "year"], how="inner")

    clim_map = clim.set_index(["district_code", "season"]).to_dict("index")
    df = pd.DataFrame([add_anomalies(r, clim_map.get((r["district_code"], r["season"])))
                       for r in df.to_dict("records")])

    report["rows_with_coords_and_weather"] = len(df)
    report["rows_with_district_history"] = int(df["hist_log_yield"].notna().sum())
    out = os.path.join(DATA, "yield_dataset.csv")
    df.to_csv(out, index=False)
    with open(os.path.join(DATA, "cleaning_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {len(df):,} rows -> {out}")
    print("Dup check on (district, crop, season, year):",
          int(df.duplicated(["district_code", "crop", "season", "year"]).sum()))


if __name__ == "__main__":
    main()
