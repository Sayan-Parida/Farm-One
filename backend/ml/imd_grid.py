"""
Helpers for IMD 0.25° gridded rainfall (.grd binary files).

File layout: little-endian float32, shape (days, 129 lat, 135 lon), C order,
lat 6.5..38.5 N, lon 66.5..100.0 E, -999 outside India.

Used by the training pipeline (archive, year files) and by live inference
(real-time daily files), with the same district cell weights in both.
"""

import datetime as dt
import os
import threading

import httpx
import numpy as np

IMD_LAT = np.linspace(6.5, 38.5, 129)
IMD_LON = np.linspace(66.5, 100.0, 135)
DISTRICT_RADIUS_DEG = 0.3  # average all valid cells within ~30 km of the district centroid

REALTIME_URL = "https://imdpune.gov.in/cmpg/Realtimedata/Rainfall/rain.php"


def _to_grid(raw, days):
    a = raw.reshape(days, len(IMD_LAT), len(IMD_LON)).astype(np.float32)
    a[a < -998] = np.nan
    return a


def read_imd_year(path, year):
    days = (dt.date(year + 1, 1, 1) - dt.date(year, 1, 1)).days
    return _to_grid(np.fromfile(path, dtype="<f4"), days)


def district_cell_weights(coords):
    """{district_code: (flat cell indices, weights)} — equal weights over valid cells near the centroid."""
    # Any archive year gives the land mask; build it from the grid definition lazily via a sample year.
    mask = _land_mask()
    lat2, lon2 = np.meshgrid(IMD_LAT, IMD_LON, indexing="ij")
    out = {}
    for c in coords.itertuples():
        near = (np.abs(lat2 - c.lat) <= DISTRICT_RADIUS_DEG) & (np.abs(lon2 - c.lon) <= DISTRICT_RADIUS_DEG) & mask
        if not near.any():
            d = (lat2 - c.lat) ** 2 + (lon2 - c.lon) ** 2
            d[~mask] = np.inf
            near = np.zeros_like(mask)
            near[np.unravel_index(np.argmin(d), d.shape)] = True
        idx = np.flatnonzero(near)
        out[int(c.district_code)] = (np.unravel_index(idx, mask.shape), np.full(len(idx), 1.0 / len(idx)))
    return out


_MASK = None


def _land_mask():
    global _MASK
    if _MASK is None:
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        path = os.path.join(base, "imd_land_mask.npy")
        if os.path.exists(path):
            _MASK = np.load(path)
        else:
            sample = os.path.join(base, "raw", "imd", "rain_2009.grd")
            _MASK = ~np.isnan(read_imd_year(sample, 2009)[0])
            np.save(path, _MASK)
    return _MASK


# ── Real-time daily files (live inference) ──────────────────────────────────

_rt_lock = threading.Lock()


def realtime_dir():
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw", "imd_realtime")
    os.makedirs(d, exist_ok=True)
    return d


def realtime_path(day: dt.date):
    return os.path.join(realtime_dir(), f"rain_{day:%Y%m%d}.grd")


def fetch_realtime_day(day: dt.date, timeout=60):
    """Download one provisional daily IMD file into the cache. Returns True if cached."""
    path = realtime_path(day)
    expected = len(IMD_LAT) * len(IMD_LON) * 4
    if os.path.exists(path) and os.path.getsize(path) == expected:
        return True
    try:
        r = httpx.post(REALTIME_URL, data={"rain": day.strftime("%d%m%Y")}, timeout=timeout)
        if r.status_code == 200 and len(r.content) == expected:
            with open(path, "wb") as f:
                f.write(r.content)
            return True
    except httpx.HTTPError:
        pass
    return False


def realtime_month_total(cells_weights, year, month, today):
    """District rain total for a calendar month from cached real-time files, or None if incomplete."""
    cells, w = cells_weights
    first = dt.date(year, month, 1)
    last = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    if last >= today:
        return None
    total = 0.0
    day = first
    while day <= last:
        path = realtime_path(day)
        if not os.path.exists(path):
            return None
        grid = _to_grid(np.fromfile(path, dtype="<f4"), 1)[0]
        v = grid[cells]
        if np.isnan(v).all():
            return None
        total += float(np.nansum(v * w) / w[~np.isnan(v)].sum())
        day += dt.timedelta(days=1)
    return total


def refresh_realtime_cache(start: dt.date, end: dt.date):
    """Background job: fill the real-time cache for [start, end]. Safe to call repeatedly."""
    if not _rt_lock.acquire(blocking=False):
        return  # another refresh is running
    try:
        day = start
        while day <= end:
            fetch_realtime_day(day)
            day += dt.timedelta(days=1)
    finally:
        _rt_lock.release()
