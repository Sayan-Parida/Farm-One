"""Re-geocode districts Nominatim missed, using corrected / alternate spellings. Re-runnable."""
import os, sys
import httpx
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from step1_geocode_districts import HEADERS, OUT_PATH, _query  # noqa: E402

ALIASES = {
    40: "Nawanshahr, Punjab", 181: "Shravasti, Uttar Pradesh", 327: "East Singhbhum, Jharkhand",
    376: "Dantewada, Chhattisgarh", 382: "Kabirdham, Chhattisgarh", 405: "Khandwa, Madhya Pradesh",
    463: "Daman", 464: "Diu", 465: "Silvassa", 602: "Port Blair", 603: "Car Nicobar",
    644: "Baloda Bazar, Chhattisgarh", 668: "Chhota Udaipur, Gujarat", 672: "Modasa, Gujarat",
    707: "Mankachar, Assam", 724: "Basar, Arunachal Pradesh", 760: "Manendragarh, Chhattisgarh",
    761: "Mohla, Chhattisgarh",
}

c = pd.read_csv(OUT_PATH)
with httpx.Client(headers=HEADERS, timeout=30) as client:
    for code, q in ALIASES.items():
        if c.loc[c.district_code == code, "lat"].notna().all():
            continue
        hit = _query(client, q + ", India")
        print(code, q, hit)
        if hit:
            c.loc[c.district_code == code, ["lat", "lon", "geocode_query"]] = [hit[0], hit[1], q + ", India (alias)"]
c.to_csv(OUT_PATH, index=False)
print("geocoded", int(c.lat.notna().sum()), "/", len(c))
