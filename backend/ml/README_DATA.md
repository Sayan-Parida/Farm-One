# FarmOne yield model — data, method and honest limits

## Why this replaced the old model
The previous yield model was trained on `crop_yield.csv` (FAO country-level data):
28,242 rows but only 13,130 unique (country, crop, year) combinations — the same
yield repeated up to 22 times with only temperature varying; rainfall was a single
number per country for all 24 years; no season, no district. A random train/test
split put copies of the same row on both sides, so its R² was inflated. The crop
recommender was trained on a synthetic-looking dataset (exactly 100 rows per crop,
non-overlapping value ranges). Neither could answer "which crop, where, when?".

## What a prediction means now
> Expected **district-average** yield (t/ha) of **one crop**, in **one district**,
> for **one season** of **one crop year**, with an 80% range.

It is not a prediction for an individual field.

## Data sources (all open)
| Data | Source | Use |
|---|---|---|
| District crop area / production / yield, 1997-2023 | Ministry of Agriculture & Farmers Welfare, via India Data Portal (ODC-BY) | target + history |
| Daily gridded rainfall 0.25° | IMD Pune (gauge-based) | rain features |
| Temperature | NASA POWER monthly | temperature features |
| District centroids | OpenStreetMap Nominatim | location |

NASA POWER rainfall was **not** used: its all-India June-Sept mean jumps from
~546 mm (1997-2007) to ~720 mm (2008-2024), a satellite-product artefact that
would create fake wet/dry "anomalies". NASA POWER humidity has a similar step
change after 2019 and is also excluded.

## Pipeline (`backend/ml/pipeline/`, run in order)
1. `step1_geocode_districts.py` (+ `fix_missing_geocodes.py`) — district → lat/lon
2. `step2_fetch_weather.py` — NASA POWER monthly weather per district
3. `step2b_fetch_imd_rain.py` — replace rainfall with IMD gridded rainfall
4. `step3_build_dataset.py` — clean yields, build season weather + history features
5. `step4_train_yield_model.py` — train, validate by time, write report

Raw downloads go to `data/raw/` (git-ignored, ~800 MB). Derived files needed at
inference (`apy_clean.csv`, `district_coords.csv`, `district_monthly_weather.csv`,
`season_climatology.csv`, `models/*`) are committed.

## Cleaning rules (counts in `data/cleaning_report.json`)
- drop "Total" season rows (they double-count other seasons)
- keep 23 major crops reported in tonnes (drop coconut, cotton, jute, mesta…)
- drop district-season area < 100 ha or zero production
- drop yields above an agronomic maximum per crop (e.g. rice > 8 t/ha)
- drop single years that are > 5x off the series median (entry/unit errors)

## Evaluation protocol
- **Split by time**: train ≤ 2014, validate 2015-17, test 2018-22. Never random.
- **History lag**: a prediction for year Y only uses yields up to Y-4, because
  official data is published with a multi-year delay. Training and testing use the
  same lag, so test numbers reflect real use.
- **Baselines the model must beat**: district's own recent mean; state mean;
  district mean + a per-crop trend.
- Two scenarios: *actual weather* (upper bound) and *pre-season* (climate normals
  only — what the app knows before a season starts).

Results are written to `models/yield_model_report.json` after every training run;
the app shows the per-crop test error next to each prediction.

## Known limits (say these out loud in a demo)
- District averages only; irrigation, variety and management dominate field yield.
- Most of the skill comes from the district's own history and trend. Season
  weather helps mainly in extreme years (e.g. drought) and is a small effect in
  normal years — this is expected for agronomic data.
- Official figures for the newest seasons are revised/published late; very recent
  seasons use older history by design.
- Crop recommendation ranks crops **already grown** in the district by predicted
  yield relative to India's median; it does not propose crops with no local record.
- Soil readings (SoilGrids) are displayed but not model inputs.
