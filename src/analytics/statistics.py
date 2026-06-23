"""Statistical tests: correlation matrix, t-tests, ANOVA, OLS regression."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)


def correlation_matrix(df: pd.DataFrame) -> dict[str, Any]:
    """Pearson correlation matrix for numeric columns, with top pairs."""
    numeric = df.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return {"correlations": {}, "top_pairs": []}

    corr = numeric.corr()
    pairs = []
    for i in range(len(corr.columns)):
        for j in range(i + 1, len(corr.columns)):
            val = corr.iloc[i, j]
            if not np.isnan(val):
                pairs.append((corr.columns[i], corr.columns[j], round(val, 3)))

    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    return {"correlations": corr.round(3).to_dict(), "top_pairs": pairs[:15]}


def hypothesis_tests(df: pd.DataFrame, target_col: str | None = None) -> dict[str, Any]:
    """Run t-tests, ANOVA, and normality tests on numeric data."""
    numeric = df.select_dtypes(include=[np.number])
    results: dict[str, Any] = {"normality": {}, "groups": []}

    if numeric.empty:
        return results

    # Shapiro-Wilk normality test on each numeric column (sample)
    for col in numeric.columns[:5]:
        sample = numeric[col].dropna().sample(min(200, len(numeric)), random_state=42)
        if len(sample) >= 3:
            stat, p = scipy_stats.shapiro(sample.values)
            results["normality"][col] = {"statistic": round(stat, 4), "p_value": round(p, 6),
                                          "is_normal": p > 0.05}

    # If we have a categorical grouping column, run ANOVA/t-test
    if target_col and target_col in df.columns and df[target_col].nunique() <= 10:
        groups = df.groupby(target_col)
        if len(groups) > 1:
            for num_col in numeric.columns[:3]:
                group_data = [g[num_col].dropna().values for _, g in groups if len(g[num_col].dropna()) >= 3]
                if len(group_data) >= 2:
                    f_stat, p_val = scipy_stats.f_oneway(*group_data)
                    results["groups"].append({
                        "column": num_col,
                        "grouping": target_col,
                        "f_statistic": round(float(f_stat), 4),
                        "p_value": round(float(p_val), 6),
                        "significant": p_val < 0.05,
                    })

    return results


def regression_analysis(df: pd.DataFrame, target_col: str) -> dict[str, Any]:
    """OLS linear regression with statsmodels."""
    try:
        import statsmodels.api as sm
    except ImportError:
        return {"error": "statsmodels not installed"}

    numeric = df.select_dtypes(include=[np.number])
    if target_col not in numeric.columns or numeric.shape[1] < 2:
        return {"error": f"Need at least 2 numeric columns including '{target_col}'"}

    predictors = [c for c in numeric.columns if c != target_col]
    X = numeric[predictors].dropna()
    y = numeric.loc[X.index, target_col]

    # Encode any remaining categorical columns
    X = pd.get_dummies(X, drop_first=True)

    try:
        X = sm.add_constant(X)
        model = sm.OLS(y, X).fit()
        return {
            "r_squared": round(model.rsquared, 4),
            "adj_r_squared": round(model.rsquared_adj, 4),
            "f_statistic": round(float(model.fvalue), 4),
            "f_pvalue": round(float(model.f_pvalue), 6),
            "significant_predictors": [
                {"variable": v, "coef": round(float(model.params[v]), 4),
                 "p_value": round(float(model.pvalues[v]), 6)}
                for v in model.params.index if v != "const" and model.pvalues[v] < 0.05
            ],
        }
    except Exception as exc:
        logger.warning("Regression failed: %s", exc)
        return {"error": str(exc)}
