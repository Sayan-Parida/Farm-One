"""
Step 4 — Train and honestly evaluate the district yield model.

Split is by TIME, never random:
    train : agricultural years 1997-2014
    valid : 2015-2017   (early stopping + prediction-interval calibration)
    test  : 2018-2022   (touched once, for the reported numbers)

The model is compared against two baselines it must beat to be worth using:
    B1 "district history" : the district's own average yield in the lag window
    B2 "state history"    : the state's average yield in the lag window

Two test scenarios are reported:
    actual-weather  : season weather as it actually happened (upper bound; e.g. end-of-season estimate)
    pre-season      : weather replaced by the district's normal climate — what the app knows before
                      the season starts. This is the number that reflects live use.

Outputs: models/yield_district_model.pkl, models/yield_model_meta.json, models/yield_model_report.json
"""

import json
import os
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from yield_features import (  # noqa: E402
    ANOMALY_COLS, CATEGORICAL_COLS, FEATURE_COLS, HIST_GAP, HIST_WINDOW, WEATHER_COLS,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE_DIR, "data")
MODELS = os.path.join(BASE_DIR, "models")

TRAIN_END, VALID_END = 2014, 2017


def prepare(df, categories=None):
    X = df[FEATURE_COLS].copy()
    for c in CATEGORICAL_COLS:
        cats = categories[c] if categories else sorted(X[c].dropna().unique())
        X[c] = pd.Categorical(X[c], categories=cats)
    return X


GRID = [
    {"learning_rate": 0.05, "max_leaf_nodes": 63, "min_samples_leaf": 40, "l2_regularization": 1.0},
    {"learning_rate": 0.02, "max_leaf_nodes": 31, "min_samples_leaf": 100, "l2_regularization": 1.0},
    {"learning_rate": 0.02, "max_leaf_nodes": 15, "min_samples_leaf": 200, "l2_regularization": 5.0},
    {"learning_rate": 0.01, "max_leaf_nodes": 15, "min_samples_leaf": 400, "l2_regularization": 10.0},
]


def make_model(**params):
    return HistGradientBoostingRegressor(
        loss="absolute_error",  # L1 in log space: optimises the median % error we report
        max_iter=1500,
        categorical_features="from_dtype",
        early_stopping=False,  # iterations are chosen on our own time-based validation years
        random_state=42,
        **params,
    )


def metrics(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    ape = np.abs(y_pred - y_true) / y_true
    return {
        "n": int(len(y_true)),
        "MAE_t_ha": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "median_APE_pct": round(float(np.median(ape) * 100), 1),
        "within_20pct": round(float(np.mean(ape <= 0.20) * 100), 1),
        "R2_log": round(float(r2_score(np.log(y_true), np.log(y_pred))), 3),
    }


def to_climatology(df, clim):
    """Replace actual season weather with the district-season normal (pre-season scenario)."""
    out = df.drop(columns=WEATHER_COLS).merge(clim, on=["district_code", "season"], how="left")
    out[ANOMALY_COLS] = 0.0
    return out


def main():
    df = pd.read_csv(os.path.join(DATA, "yield_dataset.csv"))
    clim = pd.read_csv(os.path.join(DATA, "season_climatology.csv"))
    df = df.dropna(subset=["hist_log_yield"])  # need some history to make a district-specific estimate
    # Target = change vs the district's own (lagged) history. Trees cannot extrapolate a
    # time trend past the training years, but they can learn "how much higher/lower than
    # its history does a district end up, given trend, state context and season weather".
    df["target"] = df["log_yield"] - df["hist_log_yield"]

    train = df[df["year"] <= TRAIN_END]
    valid = df[(df["year"] > TRAIN_END) & (df["year"] <= VALID_END)]
    test = df[df["year"] > VALID_END]
    print(f"train {len(train):,} ({train.year.min()}-{train.year.max()})  "
          f"valid {len(valid):,}  test {len(test):,} ({test.year.min()}-{test.year.max()})")

    categories = {c: sorted(df[c].unique()) for c in CATEGORICAL_COLS}
    Xtr, Xva, Xte = prepare(train, categories), prepare(valid, categories), prepare(test, categories)

    # ── Choose hyper-parameters + number of iterations on the time-based validation years ──
    best = None
    for params in GRID:
        probe = make_model(**params).fit(Xtr, train["target"])
        curve = [np.mean(np.abs(p - valid["target"])) for p in probe.staged_predict(Xva)]
        i = int(np.argmin(curve))
        print(f"  {params} -> best iter {i + 1}, valid MAE(log) {curve[i]:.5f}")
        if best is None or curve[i] < best[0]:
            best = (curve[i], params, i + 1)
    _, best_params, best_iter = best
    print(f"chosen: {best_params}, n_iter={best_iter}")

    model = make_model(**best_params).set_params(max_iter=best_iter)
    model.fit(Xtr, train["target"])

    # ── Blend with the per-crop/season drift baseline ──
    # The drift baseline (district history + the typical change seen in training years) is very hard
    # to beat on median error; the weather-aware model adds sensitivity to extreme years. The blend
    # weight is chosen on the validation years only.
    def drift_table(frame):
        return frame.groupby(["crop", "season"])["target"].median().to_dict()

    def drift_of(frame, table):
        return np.array([table.get((c, s), 0.0) for c, s in zip(frame["crop"], frame["season"])])

    drift_train = drift_table(train)
    valid_pre = to_climatology(valid, clim)
    Xva_pre = prepare(valid_pre, categories)
    delta_va_pre = model.predict(Xva_pre)

    def median_ape(frame, delta):
        yt = frame["yield_t_ha"].values
        return float(np.median(np.abs(np.exp(frame["hist_log_yield"].values + delta) - yt) / yt) * 100)

    blend_scores = {}
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        blend_scores[w] = median_ape(valid, w * delta_va_pre + (1 - w) * drift_of(valid, drift_train))
    blend_w = min(blend_scores, key=blend_scores.get)
    print("blend weight on model -> valid median APE:", {k: round(v, 2) for k, v in blend_scores.items()},
          "chosen", blend_w)

    def blended(frame, X):
        return blend_w * model.predict(X) + (1 - blend_w) * drift_of(frame, drift_train)

    # ── Prediction intervals: empirical residual quantiles on validation, per crop ──
    def residual_quantiles(frame, X):
        res = frame["target"].values - blended(frame, X)  # residual in log space
        q = pd.DataFrame({"crop": frame["crop"].values, "res": res}).groupby("crop")["res"]
        per_crop = q.quantile(0.1).to_frame("q10").join(q.quantile(0.9).to_frame("q90")).to_dict("index")
        return per_crop, {"q10": float(np.quantile(res, 0.1)), "q90": float(np.quantile(res, 0.9))}

    pi_actual, pi_actual_all = residual_quantiles(valid, Xva)
    pi_pre, pi_pre_all = residual_quantiles(valid_pre, Xva_pre)

    # ── Test evaluation ──
    y = test["yield_t_ha"].values
    base = test["hist_log_yield"].values
    pred_actual = np.exp(base + blended(test, Xte))
    test_pre = to_climatology(test, clim)
    pred_pre = np.exp(base + blended(test, prepare(test_pre, categories)))
    b1 = np.exp(test["hist_log_yield"].values)
    b2 = np.exp(test["state_hist_log_yield"].fillna(test["hist_log_yield"]).values)
    # B3: district history + typical per-crop/season drift learnt on train years (trend only, no weather)
    b3 = np.exp(base + drift_of(test, drift_train))

    q10 = test["crop"].map(lambda c: pi_pre.get(c, pi_pre_all)["q10"]).values
    q90 = test["crop"].map(lambda c: pi_pre.get(c, pi_pre_all)["q90"]).values
    lo, hi = pred_pre * np.exp(q10), pred_pre * np.exp(q90)
    coverage = float(np.mean((y >= lo) & (y <= hi)) * 100)

    report = {
        "data_source": "Ministry of Agriculture & Farmers Welfare, district-wise Area-Production-Yield "
                       "(via India Data Portal, ODC-BY) + NASA POWER monthly weather",
        "unit": "one crop x one district x one season x one agricultural year",
        "split": {"train": f"1997-{TRAIN_END}", "valid": f"{TRAIN_END+1}-{VALID_END}",
                  "test": f"{VALID_END+1}-{int(test.year.max())}"},
        "history_lag_years": f"years Y-{HIST_GAP+HIST_WINDOW-1} .. Y-{HIST_GAP} (matches data publication lag)",
        "n_iter": best_iter,
        "hyperparameters": best_params,
        "target": "log(yield) - district hist_log_yield",
        "blend": {"model_weight": blend_w, "valid_median_APE_by_weight": {str(k): round(v, 2) for k, v in blend_scores.items()}},
        "test_overall": {
            "model_actual_weather": metrics(y, pred_actual),
            "model_pre_season": metrics(y, pred_pre),
            "baseline_district_history": metrics(y, b1),
            "baseline_state_history": metrics(y, b2),
            "baseline_district_history_plus_trend": metrics(y, b3),
        },
        "pre_season_80pct_interval_coverage_pct": round(coverage, 1),
        "test_by_crop": {},
    }
    for crop in sorted(test["crop"].unique()):
        m = (test["crop"] == crop).values
        if m.sum() < 100:
            continue
        report["test_by_crop"][crop] = {
            "n": int(m.sum()),
            "model_pre_season_mAPE": metrics(y[m], pred_pre[m])["median_APE_pct"],
            "model_actual_weather_mAPE": metrics(y[m], pred_actual[m])["median_APE_pct"],
            "baseline_district_mAPE": metrics(y[m], b1[m])["median_APE_pct"],
            "baseline_history_plus_trend_mAPE": metrics(y[m], b3[m])["median_APE_pct"],
        }

    print(json.dumps(report["test_overall"], indent=2))
    print("80% interval coverage on test:", round(coverage, 1))

    # ── Refit on ALL years (same hyper-parameters) for deployment ──
    full = df
    final = make_model(**best_params).set_params(max_iter=best_iter)
    final.fit(prepare(full, categories), full["target"])

    os.makedirs(MODELS, exist_ok=True)
    joblib.dump(final, os.path.join(MODELS, "yield_district_model.pkl"))
    meta = {
        "feature_cols": FEATURE_COLS,
        "target": "log_yield_minus_hist",
        "categories": categories,
        "interval_pre_season": {"per_crop": pi_pre, "all": pi_pre_all},
        "interval_actual_weather": {"per_crop": pi_actual, "all": pi_actual_all},
        "blend_model_weight": blend_w,
        "drift": {f"{c}|{se}": float(v) for (c, se), v in drift_table(full).items()},
        "latest_data_year": int(df["year"].max()),
        "trained_on_years": f"{int(df.year.min())}-{int(df.year.max())}",
    }
    with open(os.path.join(MODELS, "yield_model_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(MODELS, "yield_model_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print("Saved model + meta + report to", MODELS)


if __name__ == "__main__":
    main()
