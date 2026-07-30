"""Task 6 (required): time series forecasting.

Holt-Winters exponential smoothing on daily *new* cases (derived from the
cumulative confirmed_cases series), with weekly seasonality -- a real,
well-documented artifact of COVID reporting cadence (fewer cases get
logged on weekends/holidays; it's a reporting pattern, not an
epidemiological one) rather than a synthetic feature added just to make
the model look more sophisticated.

Deliberately not ARIMA/Prophet: exponential smoothing needs no extra
heavy dependencies beyond statsmodels (already numpy/scipy-based, same
family as pandas), fits fast enough to run on-the-fly per API request,
and its trend/seasonal/damping components are straightforward to explain
in the final report.
"""
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

MIN_HISTORY_DAYS = 60
TRAINING_WINDOW_DAYS = 180


def forecast_new_cases(dates: list, cumulative_cases: list, periods: int = 30) -> list[dict]:
    """dates/cumulative_cases: parallel lists, one row per (date, cumulative
    confirmed cases), any order. Returns `periods` days of forecast
    immediately following the last known date, as a list of
    {date, predicted_new_cases, predicted_cumulative_cases}.

    Raises ValueError if there isn't enough recent history to fit a
    seasonal model -- the caller (API layer) turns that into a 400.
    """
    series = pd.Series(cumulative_cases, index=pd.DatetimeIndex(dates)).sort_index()
    # Force a regular daily calendar so statsmodels can infer forecast
    # dates correctly, filling any missing days by interpolation --
    # cumulative counts are smooth enough that this is a safe, explainable
    # choice for a day or two of gaps.
    series = series.asfreq("D").interpolate(limit_direction="both")

    new_cases = series.diff().clip(lower=0).dropna()
    # Fit on recent behavior only -- three-plus years of pandemic history
    # isn't representative of "now," and keeps the fit fast.
    new_cases = new_cases.tail(TRAINING_WINDOW_DAYS)

    if len(new_cases) < MIN_HISTORY_DAYS:
        raise ValueError(
            f"Not enough recent daily history to forecast for this country "
            f"({len(new_cases)} days available, need at least {MIN_HISTORY_DAYS})"
        )

    model = ExponentialSmoothing(
        new_cases,
        trend="add",
        damped_trend=True,
        seasonal="add",
        seasonal_periods=7,
        initialization_method="estimated",
    ).fit()

    forecast = model.forecast(periods).clip(lower=0)

    running_total = float(series.iloc[-1])
    results = []
    for forecast_date, predicted_new in forecast.items():
        running_total += float(predicted_new)
        results.append(
            {
                "date": forecast_date.date(),
                "predicted_new_cases": float(predicted_new),
                "predicted_cumulative_cases": running_total,
            }
        )
    return results
