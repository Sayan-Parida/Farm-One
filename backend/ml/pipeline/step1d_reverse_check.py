"""
Step 1d — Independent check of districts step 1c could not verify.

For every district in data/geocode_validation.csv with status "unverified", reverse-geocode the stored
point (Nominatim /reverse, zoom 8 = district level) and compare the district name OpenStreetMap says the
point lies in with the expected district name.

Output: data/geocode_reverse_check.csv  (district, state, point, osm_district, osm_state, name_match)
A name mismatch means the stored point is probably in the wrong district (e.g. Ferozepur -> Ludhiana).
"""

import difflib
import os
import re
import sys
import time

import httpx
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from step1_geocode_districts import HEADERS  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")

REVERSE = "https://nominatim.openstreetmap.org/reverse"
STOP = re.compile(r"\b(district|division|metropolitan|city|urban|rural|zila|tehsil)\b")


def clean(s):
    s = (s or "").lower().replace("&", "and")
    s = STOP.sub(" ", s)
    return re.sub(r"[^a-z]", "", s)


def similar(a, b):
    a, b = clean(a), clean(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def main():
    val = pd.read_csv(os.path.join(DATA, "geocode_validation.csv"))
    todo = val[val["status"].str.startswith("unverified")]
    rows = []
    with httpx.Client(headers=HEADERS, timeout=30) as client:
        for i, d in enumerate(todo.itertuples(), 1):
            osm = {}
            try:
                r = client.get(REVERSE, params={"lat": d.old_lat, "lon": d.old_lon, "format": "json",
                                                "zoom": 8, "addressdetails": 1})
                osm = r.json().get("address", {}) if r.status_code == 200 else {}
            except httpx.HTTPError:
                pass
            time.sleep(1.1)
            names = [osm.get(k) for k in ("state_district", "county", "city", "district") if osm.get(k)]
            best = max((similar(d.district, n) for n in names), default=0.0)
            rows.append({"district_code": d.district_code, "district": d.district, "state": d.state,
                         "lat": d.old_lat, "lon": d.old_lon, "osm_places": " | ".join(names),
                         "osm_state": osm.get("state"), "similarity": round(best, 2),
                         "name_match": best >= 0.7})
            if i % 25 == 0:
                print(f"  {i}/{len(todo)}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(DATA, "geocode_reverse_check.csv"), index=False)
    print(out["name_match"].value_counts().to_string())


if __name__ == "__main__":
    main()
