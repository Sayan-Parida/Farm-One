"""
Step 2b — Replace NASA POWER rainfall with IMD gridded rainfall.

Why: NASA POWER's PRECTOTCORR has a structural break around 2008 — the all-India
June-September mean jumps from ~546 mm (1997-2007) to ~720 mm (2008-2024), which
did not happen in reality. Comparing a season's rain to "normal" across that
break produces fake wet/dry anomalies. IMD's 0.25° gridded product (Pai et al.,
built from ~7000 rain gauges) is the official, homogeneous record.

Source : IMD Pune, daily gridded rainfall 0.25° (https://imdpune.gov.in/cmpg/Griddata/)
Output : data/raw/imd/rain_<year>.grd (cached), and rewrites rain_mm in
         data/district_monthly_weather.csv with IMD values (column rain_source = "IMD").
         Temperature columns stay from NASA POWER (no comparable break found).
"""

import datetime as dt
import os
import sys

import httpx
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from imd_grid import IMD_LAT, IMD_LON, district_cell_weights, read_imd_year  # noqa: E402

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")
IMD_DIR = os.path.join(DATA, "raw", "imd")
URL = "https://imdpune.gov.in/cmpg/Griddata/rainfall.php"
START_YEAR, END_YEAR = 1997, 2025


def download(year):
    path = os.path.join(IMD_DIR, f"rain_{year}.grd")
    days = (dt.date(year + 1, 1, 1) - dt.date(year, 1, 1)).days
    expected = days * len(IMD_LAT) * len(IMD_LON) * 4
    if os.path.exists(path) and os.path.getsize(path) == expected:
        return path
    for attempt in range(4):
        try:
            with httpx.stream("POST", URL, data={"rain": str(year)}, timeout=600) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
            if os.path.getsize(path) == expected:
                return path
            print(f"  {year}: wrong size {os.path.getsize(path)} (expected {expected}), retrying")
        except httpx.HTTPError as e:
            print(f"  {year}: {e}, retrying")
    raise RuntimeError(f"IMD download failed for {year}")


def main():
    os.makedirs(IMD_DIR, exist_ok=True)
    coords = pd.read_csv(os.path.join(DATA, "district_coords.csv")).dropna(subset=["lat", "lon"])
    weights = district_cell_weights(coords)

    rows = []
    for year in range(START_YEAR, END_YEAR + 1):
        path = download(year)
        daily = read_imd_year(path, year)  # (days, lat, lon), NaN outside India
        start = dt.date(year, 1, 1)
        month_idx = np.array([(start + dt.timedelta(days=i)).month for i in range(daily.shape[0])])
        for m in range(1, 13):
            monthly = np.nansum(daily[month_idx == m], axis=0)  # mm per cell
            for code, (cells, w) in weights.items():
                rows.append({"district_code": code, "year": year, "month": m,
                             "rain_mm": float(np.sum(monthly[cells] * w))})
        print(f"  {year} done")

    imd = pd.DataFrame(rows)
    wpath = os.path.join(DATA, "district_monthly_weather.csv")
    w = pd.read_csv(wpath)
    if "rain_mm_power" not in w.columns:
        w = w.rename(columns={"rain_mm": "rain_mm_power"})
    w = w.drop(columns=["rain_mm", "rain_source"], errors="ignore")
    w = w.merge(imd, on=["district_code", "year", "month"], how="left")
    w["rain_source"] = np.where(w["rain_mm"].notna(), "IMD", None)
    w.to_csv(wpath, index=False)

    jjas = w[w["month"].between(6, 9)].groupby(["district_code", "year"])["rain_mm"].sum()
    print("All-district mean JJAS rain by year (IMD):",
          jjas.groupby("year").mean().round(0).to_dict())


if __name__ == "__main__":
    main()
