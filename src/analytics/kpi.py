"""KPI extraction: growth, variance, trends, top/bottom performers."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_kpis(df: pd.DataFrame) -> dict[str, Any]:
    """Extract a rich set of KPIs from a DataFrame."""
    if df.empty:
        return {"kpis": {}, "summary": "No data available."}

    numeric = df.select_dtypes(include=[np.number])
    categorical = df.select_dtypes(exclude=[np.number])

    kpis: dict[str, Any] = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "numeric_columns": list(numeric.columns),
        "categorical_columns": list(categorical.columns),
    }

    if not numeric.empty:
        stats_rows = []
        for col in numeric.columns:
            col_data = numeric[col].dropna()
            if len(col_data) < 2:
                continue
            stats_rows.append({
                "column": col,
                "mean": round(col_data.mean(), 2),
                "median": round(col_data.median(), 2),
                "std": round(col_data.std(), 2),
                "min": round(col_data.min(), 2),
                "max": round(col_data.max(), 2),
                "trend": _detect_trend(col_data),
            })
        kpis["numeric_summary"] = stats_rows

        # Top/bottom
        if len(numeric.columns) >= 1:
            first = numeric.columns[0]
            if len(numeric) >= 5:
                kpis["top_5"] = df.nlargest(5, first)[list(df.columns)].to_dict(orient="records")
                kpis["bottom_5"] = df.nsmallest(5, first)[list(df.columns)].to_dict(orient="records")

        # Total sum for something financial-like
        kpis["total_sum"] = {c: round(float(numeric[c].sum()), 2) for c in numeric.columns[:10]}

    if not categorical.empty:
        kpis["unique_counts"] = {c: int(categorical[c].nunique()) for c in categorical.columns[:20]}

    # Simple summary text
    parts = [f"Dataset has {len(df)} rows and {len(df.columns)} columns."]
    if len(numeric.columns) > 0:
        parts.append(f"{len(numeric.columns)} numeric columns found.")
    if len(categorical.columns) > 0:
        parts.append(f"{len(categorical.columns)} categorical columns found.")
    kpis["summary"] = " ".join(parts)

    return {"kpis": kpis, "summary": kpis["summary"]}


def _detect_trend(series: pd.Series) -> str:
    """Quick linear-trend direction."""
    if len(series) < 3:
        return "insufficient_data"
    x = np.arange(len(series))
    slope = np.polyfit(x, series.values, 1)[0]
    if slope > 0.01 * series.std():
        return "increasing"
    elif slope < -0.01 * series.std():
        return "decreasing"
    return "stable"
