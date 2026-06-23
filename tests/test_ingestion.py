"""Tests for ingestion and quality modules."""
from __future__ import annotations

import io

import pandas as pd
import pytest


class TestFileLoaders:
    def test_load_csv_from_buffer(self):
        from src.ingestion.file_loaders import load_file
        import tempfile
        import os

        csv_content = "name,value\nA,10\nB,20\nC,30"
        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
            f.write(csv_content)
            tmp = f.name

        try:
            result = load_file(tmp)
            assert result["type"] == "tabular"
            assert result["sheets"]["data"].shape == (3, 2)
        finally:
            os.unlink(tmp)

    def test_unsupported_extension(self):
        from src.ingestion.file_loaders import load_file
        with pytest.raises(ValueError, match="Unsupported"):
            load_file("/tmp/test.xyz")


class TestQualityScorer:
    def test_perfect_dataframe(self):
        from src.quality.scorer import score_dataframe
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = score_dataframe(df)
        assert result["quality_score"] == 100.0
        assert len(result["issues"]) == 0

    def test_missing_values(self):
        from src.quality.scorer import score_dataframe
        df = pd.DataFrame({"a": [1, None, 3], "b": [4, 5, None]})
        result = score_dataframe(df)
        assert result["quality_score"] < 100.0
        assert any("Missing" in i for i in result["issues"])
