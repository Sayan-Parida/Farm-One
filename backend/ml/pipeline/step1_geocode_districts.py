"""
Step 1 — Geocode every district in the APY dataset to a (lat, lon) centroid.

Source : OpenStreetMap Nominatim (free, 1 request/second usage policy).
Output : ml/data/district_coords.csv  (district_code, district_name, state_name, lat, lon, geocode_query)

Re-runnable: districts already present in the output are skipped.
"""

import os
import time

import httpx
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APY_PATH = os.path.join(BASE_DIR, "data", "raw", "apy_district.csv")
OUT_PATH = os.path.join(BASE_DIR, "data", "district_coords.csv")

NOMINATIM = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "FarmOne-academic-project/1.0 (district geocoding for crop yield research)"}

# India bounding box — reject any geocode result outside it.
LAT_RANGE = (6.0, 37.5)
LON_RANGE = (68.0, 97.5)


def _query(client: httpx.Client, q: str):
    r = client.get(NOMINATIM, params={"q": q, "format": "json", "limit": 1, "countrycodes": "in"})
    time.sleep(1.1)  # respect Nominatim's 1 req/s policy
    if r.status_code != 200:
        return None
    hits = r.json()
    if not hits:
        return None
    lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LON_RANGE[0] <= lon <= LON_RANGE[1]):
        return None
    return lat, lon


def main():
    apy = pd.read_csv(APY_PATH, usecols=["district_code", "district_name", "state_name"], low_memory=False)
    districts = apy.drop_duplicates("district_code").sort_values("district_code")

    done = pd.read_csv(OUT_PATH) if os.path.exists(OUT_PATH) else pd.DataFrame(columns=["district_code"])
    done_codes = set(done["district_code"])
    rows = done.to_dict("records")

    todo = districts[~districts["district_code"].isin(done_codes)]
    print(f"{len(done_codes)} already geocoded, {len(todo)} to go")

    with httpx.Client(headers=HEADERS, timeout=30) as client:
        for i, d in enumerate(todo.itertuples(), 1):
            queries = [
                f"{d.district_name} district, {d.state_name}, India",
                f"{d.district_name}, {d.state_name}, India",
            ]
            hit, used = None, None
            for q in queries:
                try:
                    hit = _query(client, q)
                except httpx.HTTPError:
                    hit = None
                if hit:
                    used = q
                    break
            rows.append({
                "district_code": d.district_code,
                "district_name": d.district_name,
                "state_name": d.state_name,
                "lat": hit[0] if hit else None,
                "lon": hit[1] if hit else None,
                "geocode_query": used,
            })
            if i % 25 == 0 or i == len(todo):
                pd.DataFrame(rows).to_csv(OUT_PATH, index=False)
                print(f"  {i}/{len(todo)}  last: {d.district_name}, {d.state_name} -> {hit}")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    print(f"Done. {out['lat'].notna().sum()}/{len(out)} districts geocoded -> {OUT_PATH}")


if __name__ == "__main__":
    main()
