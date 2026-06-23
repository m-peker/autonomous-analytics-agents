"""Data quality scoring & auto-cleaning for ingested DataFrames."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def score_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Compute a data-quality score (0–100) and report issues.

    Dimensions: completeness, uniqueness, consistency, outlier ratio.
    """
    if df.empty:
        return {"quality_score": 0, "issues": ["Empty dataset"], "stats": {}}

    n = len(df)
    cols = list(df.columns)

    # Completeness
    missing = df.isnull().sum().sum()
    total_cells = n * len(cols)
    completeness = 100 * (1 - missing / max(total_cells, 1))

    # Uniqueness
    dup_rows = df.duplicated().sum()
    uniqueness = 100 * (1 - dup_rows / max(n, 1))

    # Consistency — mixed types per column
    mixed_cols = 0
    for c in cols:
        if df[c].dtype == object and df[c].nunique() > 0:
            sample = df[c].dropna().head(100)
            if sample.apply(type).nunique() > 2:
                mixed_cols += 1
    consistency = 100 * (1 - mixed_cols / max(len(cols), 1))

    # Outlier ratio (IQR on numeric columns)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    outlier_ratio = 0.0
    for c in numeric_cols:
        q1, q3 = df[c].quantile(0.25), df[c].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            outliers = ((df[c] < q1 - 1.5 * iqr) | (df[c] > q3 + 1.5 * iqr)).sum()
            outlier_ratio += outliers / max(n, 1)
    outlier_ratio = outlier_ratio / max(len(numeric_cols), 1)
    outlier_score = 100 * (1 - outlier_ratio)

    # Composite score
    quality_score = round(0.35 * completeness + 0.25 * uniqueness + 0.20 * consistency + 0.20 * outlier_score, 1)

    issues = []
    if completeness < 90:
        issues.append(f"Missing values: {missing}/{total_cells} cells ({100-completeness:.0f}%)")
    if dup_rows > 0:
        issues.append(f"Duplicate rows: {dup_rows}/{n}")
    if mixed_cols > 0:
        issues.append(f"Mixed-type columns: {mixed_cols}")
    if outlier_score < 80:
        issues.append(f"Potential outliers in {len(numeric_cols)} numeric columns")

    stats = {
        "rows": n,
        "columns": len(cols),
        "missing_cells": int(missing),
        "missing_pct": round(100 * missing / max(total_cells, 1), 1),
        "duplicate_rows": int(dup_rows),
        "numeric_columns": len(numeric_cols),
    }

    logger.info("Quality score: %.1f/100 — %d issues", quality_score, len(issues))
    return {"quality_score": quality_score, "issues": issues, "stats": stats}


def auto_clean(df: pd.DataFrame, fill_strategy: str = "median") -> pd.DataFrame:
    """Apply basic auto-cleaning: drop fully empty, fill numeric NaNs, forward-fill text."""
    df = df.copy()
    df.dropna(how="all", inplace=True)
    df.drop_duplicates(inplace=True)

    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for c in numeric_cols:
        if df[c].isnull().any():
            if fill_strategy == "median":
                df[c] = df[c].fillna(df[c].median())
            elif fill_strategy == "mean":
                df[c] = df[c].fillna(df[c].mean())
            else:
                df[c] = df[c].fillna(0)

    text_cols = df.select_dtypes(include=["object"]).columns
    for c in text_cols:
        df[c] = df[c].fillna("").ffill()

    logger.info("Auto-cleaned: %d rows, %d columns", len(df), len(df.columns))
    return df
