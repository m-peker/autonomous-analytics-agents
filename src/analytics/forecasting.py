"""Time-series forecasting: ARIMA + Prophet."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def forecast_series(series: pd.Series, periods: int = 12) -> dict[str, Any]:
    """Forecast using ARIMA first, Prophet as fallback."""
    clean = series.dropna()
    if len(clean) < 6:
        return {"error": "Need at least 6 data points for forecasting"}

    # Try Prophet first (more robust)
    try:
        return _prophet_forecast(clean, periods)
    except Exception as exc:
        logger.warning("Prophet failed: %s — trying ARIMA", exc)

    try:
        return _arima_forecast(clean, periods)
    except Exception as exc:
        logger.warning("ARIMA failed: %s", exc)
        return _simple_forecast(clean, periods)


def _prophet_forecast(series: pd.Series, periods: int) -> dict[str, Any]:
    from prophet import Prophet
    df = pd.DataFrame({"ds": pd.to_datetime(series.index) if hasattr(series.index, "to_series")
                       else pd.date_range(end=pd.Timestamp.now(), periods=len(series), freq="D"),
                       "y": series.values})
    model = Prophet(yearly_seasonality="auto", weekly_seasonality="auto", daily_seasonality="auto")
    model.fit(df)
    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)
    predicted = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)
    return {
        "method": "prophet",
        "forecast": predicted.rename(columns={"ds": "period", "yhat": "value",
                                               "yhat_lower": "lower", "yhat_upper": "upper"}).to_dict(orient="records"),
        "trend": "increasing" if predicted["yhat"].iloc[-1] > predicted["yhat"].iloc[0] else "decreasing",
    }


def _arima_forecast(series: pd.Series, periods: int) -> dict[str, Any]:
    from statsmodels.tsa.arima.model import ARIMA
    model = ARIMA(series.values, order=(2, 1, 2))
    fitted = model.fit()
    forecast = fitted.forecast(steps=periods)
    conf = fitted.get_forecast(periods).conf_int()
    return {
        "method": "arima",
        "forecast": [{"period": i + 1, "value": round(float(forecast[i]), 2),
                       "lower": round(float(conf[i, 0]), 2), "upper": round(float(conf[i, 1]), 2)}
                      for i in range(len(forecast))],
        "trend": "increasing" if forecast[-1] > forecast[0] else "decreasing",
    }


def _simple_forecast(series: pd.Series, periods: int) -> dict[str, Any]:
    """Linear extrapolation fallback."""
    x = np.arange(len(series))
    slope, intercept = np.polyfit(x, series.values, 1)
    future_x = np.arange(len(series), len(series) + periods)
    predicted = slope * future_x + intercept
    return {
        "method": "linear_extrapolation",
        "forecast": [{"period": i + 1, "value": round(float(predicted[i]), 2)}
                      for i in range(len(predicted))],
        "trend": "increasing" if slope > 0 else "decreasing",
    }
