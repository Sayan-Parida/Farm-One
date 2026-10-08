"""
Step 1c — Validate district geocodes and fix wrong ones.

Problem found: step 1 took Nominatim's first hit, which can be a same-named village or town
(e.g. "Ferozepur" resolved to a point next to Ludhiana city, ~120 km from the real Ferozepur).
A wrong centroid silently gives a district the wrong weather, so every district is re-checked:

  accept a result only if it is an administrative boundary (district / state_district / county)
  AND its address.state matches the district's state.

Outputs:
  data/geocode_validation.csv   per-district audit trail (old point, verified point, distance, status)
  data/district_coords.csv      updated in place when a verified point is > MOVE_KM from the old one
  data/geocode_changed_codes.json   district_codes whose coordinates changed (their weather must be refetched)

Re-runnable: results are cached in data/raw/geocode_validation_cache.json.
"""

import json
import os
import re
import sys
import time

import httpx
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fix_missing_geocodes import ALIASES  # noqa: E402
from step1_geocode_districts import HEADERS, LAT_RANGE, LON_RANGE, NOMINATIM, OUT_PATH  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yield_features import haversine_km  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(BASE_DIR, "data", "raw", "geocode_validation_cache.json")
AUDIT = os.path.join(BASE_DIR, "data", "geocode_validation.csv")
CHANGED = os.path.join(BASE_DIR, "data", "geocode_changed_codes.json")

MOVE_KM = 25  # only replace when the verified point is clearly somewhere else
ADMIN_ADDRESSTYPES = {"state_district", "county", "district", "city", "municipality"}


def norm(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"\bthe\b|\band\b", " ", s)
    return re.sub(r"[^a-z]", "", s)


STATE_FIXES = {  # APY state label -> label(s) Nominatim uses
    norm("The Dadra And Nagar Haveli And Daman And Diu"): {norm("Dadra and Nagar Haveli and Daman and Diu")},
    norm("Delhi"): {norm("Delhi"), norm("NCT of Delhi")},
}


def state_matches(expected, got):
    e, g = norm(expected), norm(got)
    return g == e or g in STATE_FIXES.get(e, set())


def pick(results, state):
    """First strictly valid administrative hit in the right state, else None."""
    for want_boundary in (True, False):
        for r in results:
            addr = r.get("address", {})
            if not state_matches(state, addr.get("state") or addr.get("union_territory") or ""):
                continue
            is_boundary = r.get("class") == "boundary" and r.get("type") == "administrative"
            if want_boundary and is_boundary:
                return r
            if not want_boundary and r.get("addresstype") in ADMIN_ADDRESSTYPES:
                return r
    return None


def query(client, q):
    r = client.get(NOMINATIM, params={"q": q, "format": "json", "limit": 6, "addressdetails": 1,
                                      "countrycodes": "in"})
    time.sleep(1.1)
    return r.json() if r.status_code == 200 else []


def main():
    coords = pd.read_csv(OUT_PATH)
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}

    with httpx.Client(headers=HEADERS, timeout=30) as client:
        for i, d in enumerate(coords.itertuples(), 1):
            key = str(d.district_code)
            if key in cache:
                continue
            name = ALIASES.get(int(d.district_code), d.district_name).split(",")[0]
            tried, hit = [], None
            for q in (f"{name} district, {d.state_name}, India", f"{name}, {d.state_name}, India"):
                try:
                    res = query(client, q)
                except httpx.HTTPError:
                    res = []
                tried.append(q)
                r = pick(res, d.state_name)
                if r:
                    hit = {"lat": float(r["lat"]), "lon": float(r["lon"]), "type": r.get("type"),
                           "addresstype": r.get("addresstype"), "display": r.get("display_name")[:120], "q": q}
                    break
            cache[key] = hit
            if i % 25 == 0:
                json.dump(cache, open(CACHE, "w"))
                print(f"  {i}/{len(coords)}", flush=True)
    json.dump(cache, open(CACHE, "w"))

    rows, changed = [], []
    for d in coords.itertuples():
        hit = cache.get(str(d.district_code))
        row = {"district_code": d.district_code, "district": d.district_name, "state": d.state_name,
               "old_lat": d.lat, "old_lon": d.lon}
        if not hit:
            row.update(status="unverified (kept old point)", new_lat=None, new_lon=None, moved_km=None)
        else:
            nlat, nlon = hit["lat"], hit["lon"]
            ok_range = LAT_RANGE[0] <= nlat <= LAT_RANGE[1] and LON_RANGE[0] <= nlon <= LON_RANGE[1]
            moved = float(haversine_km(d.lat, d.lon, nlat, nlon))
            row.update(new_lat=nlat, new_lon=nlon, moved_km=round(moved, 1), match=hit["display"])
            if ok_range and moved > MOVE_KM:
                row["status"] = "REPLACED"
                changed.append(int(d.district_code))
                coords.loc[coords.district_code == d.district_code, ["lat", "lon", "geocode_query"]] = \
                    [nlat, nlon, hit["q"] + " (validated admin boundary)"]
            else:
                row["status"] = "verified"
        rows.append(row)

    audit = pd.DataFrame(rows)
    audit.to_csv(AUDIT, index=False)
    coords.to_csv(OUT_PATH, index=False)
    json.dump(changed, open(CHANGED, "w"))
    print(audit["status"].value_counts().to_string())
    print("replaced:", changed)


if __name__ == "__main__":
    main()
