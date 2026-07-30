# Task 6 — Analytical Features: Forecasting (required)

## What it does

`GET /countries/{iso_code}/forecast?days=30` (30 default, 1-90 allowed):
predicts daily new confirmed cases for the requested number of days
ahead, plus a running projected cumulative total, computed **on-the-fly
per request** -- no pre-trained model file, no scheduled batch job. It's
consumed by a new chart in the Task 5 dashboard (historical new cases as
a solid line, forecast as a dashed continuation).

Clustering (Task 6's bonus half) was intentionally not built, to keep
scope realistic given the timeline -- noted here rather than left
unexplained.

## Method: Holt-Winters exponential smoothing

`analytics/forecasting.py` fits `statsmodels`'
`ExponentialSmoothing(trend="add", damped_trend=True, seasonal="add",
seasonal_periods=7)` on the country's daily *new* cases (derived by
differencing the Gold layer's cumulative `confirmed_cases`, clipped at
zero to absorb the reporting corrections already documented in Task 2's
EDA), using the most recent 180 days of history.

Why this over ARIMA or Prophet:

- **Weekly seasonality is real, not decorative.** COVID case reporting
  has a well-documented weekly rhythm (fewer cases logged on
  weekends/holidays -- a reporting-cadence artifact, not an
  epidemiological one). `seasonal_periods=7` captures exactly that, and
  it's visible in the synthetic-data test below: the model predicts a
  same-magnitude dip on the correct weekday without being told which
  day that is.
- **Damped trend** avoids the model naively projecting a straight line
  to infinity -- growth/decline trends flatten out, which is both more
  realistic and avoids wildly implausible 90-day forecasts.
- **No extra heavy dependency.** `statsmodels` is numpy/scipy-based,
  same family as pandas (already a dependency) -- no compiled
  Stan/PyStan toolchain like Prophet needs, which given this project's
  history of Python-version/build-dependency friction (Python
  3.14 -> 3.12, `ydata-profiling`/numba, `mashumaro`) was a real
  consideration, not just a style preference.
- **Fast enough to run live.** Fitting on 180 points takes a fraction of
  a second -- consistent with the rest of the API's "no pre-materialized
  latest table" on-the-fly design (Task 4's `/summary`, `/waves`).

## Known limitation (inherited from Task 4's `/summary` finding)

For countries JHU reports at state/province granularity in this
Marketplace mirror (the US being the clearest example), the underlying
daily `confirmed_cases` series is itself an undercount (see
`docs/tasks/task4_api_development.md`). The forecast is only as good as
that input -- it's forecasting the *reported* trend, not a corrected
one. Documented rather than silently inherited.

## Verified before handing off

- `analytics/forecasting.py` tested directly against synthetic data with
  a known linear trend (~100-200 cases/day) and a baked-in weekend dip:
  the model recovers both, forecast values are non-negative, and
  cumulative totals are strictly increasing across the horizon. Also
  confirmed the insufficient-history path raises a clear `ValueError`
  rather than crashing on too little data.
- The full `GET /forecast` endpoint tested through FastAPI's
  `TestClient` with `query_to_dataframe` mocked (same practice as
  Task 4): 200 for a normal request, 422 for `days` outside 1-90
  (FastAPI's own `Query(..., ge=1, le=90)` validation), 404 for a
  country with no data, 400 for a country with too little recent
  history.
- The dashboard's new forecast chart tested with mocked
  `dashboard.api_client` responses, same as the rest of Task 5:
  confirms it renders both the historical and forecast traces and
  computes the historical new-cases line correctly from the daily
  cumulative series.

## Try it

```bash
curl "http://localhost:8000/countries/US/forecast?days=14"
```

Or just open the dashboard (`http://localhost:8050`) -- the new "Daily
new cases: recent history + 30-day forecast" chart sits right below the
cases/deaths chart.
