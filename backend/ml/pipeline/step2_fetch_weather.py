"""
Step 2 — Download real monthly weather for every district centroid.

Source : NASA POWER monthly point API (MERRA-2 / satellite derived, ~0.5° grid, free, no key)
         https://power.larc.nasa.gov/docs/services/api/temporal/monthly/
Output : ml/data/district_monthly_weather.csv
         one row per (district_code, year, month) with
         rain_mm (monthly total), t_mean, t_max (monthly max), t_min (monthly min), rh (mean %)

Raw JSON responses are cached in ml/data/raw/power/ so the script is re-runnable.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COORDS_PATH = os.path.join(BASE_DIR, "data", "district_coords.csv")
CACHE_DIR = os.path.join(BASE_DIR, "data", "raw", "power")
OUT_PATH = os.path.join(BASE_DIR, "data", "district_monthly_weather.csv")

START_YEAR, END_YEAR = 1997, 2024
PARAMS = {
    "PRECTOTCORR_SUM": "rain_mm",
    "T2M": "t_mean",
    "T2M_MAX": "t_max",
    "T2M_MIN": "t_min",
    "RH2M": "rh",
}
URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"


def fetch(code: int, lat: float, lon: float) -> str:
    path = os.path.join(CACHE_DIR, f"{code}.json")
    if os.path.exists(path):
        return path
    params = {
        "parameters": ",".join(PARAMS),
        "community": "AG",
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start": START_YEAR,
        "end": END_YEAR,
        "format": "JSON",
    }
    for attempt in range(4):
        try:
            r = httpx.get(URL, params=params, timeout=120)
            if r.status_code == 200:
                with open(path, "w") as f:
                    f.write(r.text)
                return path
        except httpx.HTTPError:
            pass
    raise RuntimeError(f"NASA POWER failed for district {code}")


def parse(code: int, path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)["properties"]["parameter"]
    rows = {}
    for p, col in PARAMS.items():
        for key, val in data[p].items():
            year, month = int(key[:4]), int(key[4:])
            if month == 13:  # annual aggregate
                continue
            rows.setdefault((year, month), {"district_code": code, "year": year, "month": month})
            rows[(year, month)][col] = None if val == -999 else val
    return list(rows.values())


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    coords = pd.read_csv(COORDS_PATH).dropna(subset=["lat", "lon"])
    print(f"Fetching NASA POWER monthly weather for {len(coords)} districts ({START_YEAR}-{END_YEAR})")

    all_rows, failed = [], []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fetch, int(c.district_code), c.lat, c.lon): int(c.district_code)
                   for c in coords.itertuples()}
        for i, fut in enumerate(as_completed(futures), 1):
            code = futures[fut]
            try:
                all_rows.extend(parse(code, fut.result()))
            except Exception as e:
                failed.append(code)
                print(f"  FAILED {code}: {e}")
            if i % 50 == 0:
                print(f"  {i}/{len(futures)}")

    out = pd.DataFrame(all_rows).sort_values(["district_code", "year", "month"])
    out.to_csv(OUT_PATH, index=False)
    print(f"Done. {out['district_code'].nunique()} districts, {len(out):,} monthly rows -> {OUT_PATH}")
    if failed:
        print(f"Failed districts (re-run to retry): {failed}")


if __name__ == "__main__":
    main()
