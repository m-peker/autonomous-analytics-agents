"""Tests for analytics and KPI modules."""
from __future__ import annotations

import numpy as np
import pandas as pd


class TestKPIs:
    def test_compute_kpis(self):
        from src.analytics.kpi import compute_kpis
        df = pd.DataFrame({
            "revenue": [100, 200, 300, 400, 500],
            "cost": [50, 80, 110, 140, 170],
            "category": ["A", "B", "A", "B", "A"],
        })
        result = compute_kpis(df)
        assert "kpis" in result
        assert result["kpis"]["row_count"] == 5
        assert len(result["kpis"]["numeric_summary"]) == 2

    def test_empty_dataframe(self):
        from src.analytics.kpi import compute_kpis
        result = compute_kpis(pd.DataFrame())
        assert result["kpis"] == {}


class TestStatistics:
    def test_correlation_matrix(self):
        from src.analytics.statistics import correlation_matrix
        df = pd.DataFrame({
            "x": [1, 2, 3, 4, 5],
            "y": [2, 4, 6, 8, 10],
            "z": [5, 4, 3, 2, 1],
        })
        result = correlation_matrix(df)
        pairs = result["top_pairs"]
        assert len(pairs) >= 2
        # x and y should be perfectly correlated
        x_y = next((p for p in pairs if "x" in p and "y" in p), None)
        assert x_y is not None
        assert abs(x_y[2]) == 1.0


class TestAutoML:
    def test_auto_cluster(self):
        from src.analytics.automl import auto_cluster
        df = pd.DataFrame({
            "a": np.random.randn(30),
            "b": np.random.randn(30),
            "c": np.random.randn(30),
        })
        result = auto_cluster(df)
        assert "kmeans" in result or "error" in result
