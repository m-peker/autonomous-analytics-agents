"""Auto-chart engine: bar, line, pie, scatter, heatmap, distribution, forecast.

Produces PNG (matplotlib/seaborn) and SVG/HTML (plotly) charts.
"""
from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # non-interactive backend

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

logger = logging.getLogger(__name__)


def generate_charts(df: pd.DataFrame, output_dir: str | Path = "./data/outputs") -> list[dict[str, Any]]:
    """Auto-generate all relevant charts for a DataFrame."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    charts: list[dict[str, Any]] = []

    numeric = df.select_dtypes(include=[np.number])
    categorical = df.select_dtypes(exclude=[np.number])

    if not numeric.empty:
        # Bar chart: first numeric column
        charts.append(_bar_chart(df, numeric.columns[0], out))

        # Distribution: histogram of first numeric
        charts.append(_distribution(df, numeric.columns[0], out))

        # Correlation heatmap
        if len(numeric.columns) >= 2:
            charts.append(_heatmap(numeric, out))

        # Scatter plot
        if len(numeric.columns) >= 2:
            charts.append(_scatter(df, numeric.columns[0], numeric.columns[1], out))

    if not categorical.empty:
        top_cat = categorical.iloc[:, 0].value_counts().head(10)
        charts.append(_pie_chart(top_cat, out))

    # Line chart if index is datetime-like
    if _is_time_series(df) and len(numeric.columns) >= 1:
        charts.append(_line_chart(df, numeric.columns[0], out))

    return charts


# ── Individual chart generators ──────────────────────────────────────────────

def _bar_chart(df: pd.DataFrame, col: str, out: Path) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(10, 5))
    data = df[col].dropna().head(30)
    ax.bar(range(len(data)), data.values, color="#4f46e5", alpha=0.85)
    ax.set_title(f"{col} — Bar Chart", fontweight="bold")
    ax.set_xlabel("Index")
    ax.set_ylabel(col)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    mean_v = data.mean()
    max_v, min_v = data.max(), data.min()
    return _encode("Bar Chart", buf,
        f"{col}: avg={mean_v:,.1f}, range [{min_v:,.1f} – {max_v:,.1f}]. "
        f"Top value is {max_v/mean_v:.1f}x the average.")


def _line_chart(df: pd.DataFrame, col: str, out: Path) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(range(len(df)), df[col].values, color="#0891b2", linewidth=2)
    ax.set_title(f"{col} — Trend", fontweight="bold")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    vals = df[col].dropna().values
    if len(vals) >= 2:
        change = (vals[-1] - vals[0]) / max(abs(vals[0]), 1) * 100
        direction = "increased" if change > 0 else "decreased"
        return _encode("Line Chart", buf,
            f"{col}: {direction} by {abs(change):.1f}% over {len(vals)} periods. "
            f"Current value: {vals[-1]:,.1f}")
    return _encode("Line Chart", buf, f"Trend line for {col}.")


def _pie_chart(series: pd.Series, out: Path) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(8, 8))
    top = series.head(10)
    colors = sns.color_palette("pastel", len(top))
    wedges, texts, autotexts = ax.pie(
        top.values, labels=top.index, autopct="%1.1f%%",
        colors=colors, startangle=140, pctdistance=0.85,
    )
    for t in autotexts: t.set_fontsize(9)
    ax.set_title("Category Distribution", fontweight="bold")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    top_name = top.index[0]
    top_pct = top.values[0] / top.values.sum() * 100
    return _encode("Pie Chart", buf,
        f"Top category is '{top_name}' at {top_pct:.1f}% of total. "
        f"{len(top)} categories shown, total {len(series)} unique values.")


def _scatter(df: pd.DataFrame, x_col: str, y_col: str, out: Path) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(10, 6))
    sample = df[[x_col, y_col]].dropna().head(200)
    ax.scatter(sample[x_col], sample[y_col], alpha=0.5, c="#4f46e5", edgecolors="none")
    ax.set_xlabel(x_col); ax.set_ylabel(y_col)
    ax.set_title(f"{x_col} vs {y_col}", fontweight="bold")
    corr = sample.corr().iloc[0, 1]
    if len(sample) >= 3:
        z = np.polyfit(sample[x_col], sample[y_col], 1)
        p = np.poly1d(z)
        x_range = np.linspace(sample[x_col].min(), sample[x_col].max(), 100)
        ax.plot(x_range, p(x_range), "--", color="#dc2626", linewidth=2, alpha=0.7)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    direction = "positive" if corr > 0 else "negative"
    strength = "strong" if abs(corr) > 0.7 else ("moderate" if abs(corr) > 0.4 else "weak")
    return _encode("Scatter Plot", buf,
        f"{x_col} vs {y_col}: {strength} {direction} correlation (r={corr:.3f}). "
        f"Each point represents one record from {len(sample)} samples.")


def _heatmap(numeric: pd.DataFrame, out: Path) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(numeric.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0,
                square=True, linewidths=0.5, ax=ax)
    ax.set_title("Correlation Heatmap", fontweight="bold")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    corr_mat = numeric.corr()
    # Find strongest correlation pair
    pairs = []
    for i in range(len(corr_mat.columns)):
        for j in range(i+1, len(corr_mat.columns)):
            pairs.append((corr_mat.columns[i], corr_mat.columns[j], corr_mat.iloc[i,j]))
    pairs.sort(key=lambda x: abs(x[2]), reverse=True)
    if pairs:
        a,b,v = pairs[0]
        direction = "positive" if v>0 else "negative"
        return _encode("Correlation Heatmap", buf,
            f"Strongest link: {a} ↔ {b} (r={v:.2f}, {direction}). "
            f"Red cells = positive correlation, blue = negative. {len(numeric.columns)} variables compared.")
    return _encode("Correlation Heatmap", buf, f"Correlation matrix of {len(numeric.columns)} numeric variables.")


def _distribution(df: pd.DataFrame, col: str, out: Path) -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(df[col].dropna(), kde=True, bins=30, color="#7c3aed", ax=ax)
    ax.set_title(f"{col} — Distribution", fontweight="bold")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    vals = df[col].dropna()
    skew = vals.skew()
    shape = "right-skewed" if skew > 0.5 else ("left-skewed" if skew < -0.5 else "roughly symmetric")
    return _encode("Distribution", buf,
        f"{col}: {shape} distribution (skew={skew:.2f}), "
        f"mean={vals.mean():,.1f}, median={vals.median():,.1f}. "
        f"Range: [{vals.min():,.1f} – {vals.max():,.1f}]")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _encode(title: str, buf: io.BytesIO, insight: str) -> dict[str, Any]:
    buf.seek(0)
    return {
        "title": title,
        "insight": insight,
        "png_base64": base64.b64encode(buf.read()).decode(),
        "svg": None,
        "html": None,
    }


def _is_time_series(df: pd.DataFrame) -> bool:
    if isinstance(df.index, pd.DatetimeIndex):
        return True
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return True
    return False
