"""Insight synthesis: findings, risks, opportunities, recommendations, confidence."""
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.workflow.state import SheetResult

logger = logging.getLogger(__name__)


def generate_insights(
    kpi_report: dict,
    stats_report: dict,
    ml_report: dict,
    forecast_report: dict | None,
    research_text: str = "",
    sheet_name: str = "",
) -> dict[str, Any]:
    """Per-sheet insights: findings, risks, opportunities, recommendations.

    Now context-aware: uses sheet_name to generate meaningful labels
    (e.g., "Sales: $65M revenue, 500 transactions") instead of generic stats.
    """
    findings: list[str] = []
    risks: list[str] = []
    opportunities: dict[str, list[str]] = {"revenue": [], "cost_savings": [], "efficiency": []}
    recommendations: dict[str, list[str]] = {"short_term": [], "long_term": []}

    kpis = kpi_report.get("kpis", {})
    numeric_summary = kpis.get("numeric_summary", [])
    total_sums = kpis.get("total_sum", {})
    unique_counts = kpis.get("unique_counts", {})

    label = f"[{sheet_name}] " if sheet_name else ""

    # ── Contextual header ────────────────────────────────────────────────
    row_n = kpis.get("row_count", "?")
    col_n = kpis.get("column_count", "?")
    findings.append(f"{label}{row_n} rows, {col_n} columns analyzed.")

    # Financial metrics if present
    revenue_cols = [c for c in total_sums if any(kw in c.lower() for kw in ("revenue", "sales", "income"))]
    profit_cols = [c for c in total_sums if any(kw in c.lower() for kw in ("profit", "margin", "earnings"))]
    cost_cols = [c for c in total_sums if any(kw in c.lower() for kw in ("cost", "spend", "expense"))]

    for c in revenue_cols:
        val = total_sums[c]
        if val > 1000:
            findings.append(f"{label}Total {c}: ${val:,.0f}")
        else:
            findings.append(f"{label}Total {c}: {val:,.2f}")
    for c in profit_cols:
        val = total_sums[c]
        findings.append(f"{label}Total {c}: ${val:,.0f}" if val > 1000 else f"{label}Total {c}: {val:,.2f}")
    for c in cost_cols:
        val = total_sums[c]
        findings.append(f"{label}Total {c}: ${val:,.0f}" if val > 1000 else f"{label}Total {c}: {val:,.2f}")

    # Unique counts for categorical
    for c, n in list(unique_counts.items())[:5]:
        findings.append(f"{label}Unique {c}: {n}")

    # Top 3 numeric columns by mean
    for col_stats in numeric_summary[:3]:
        val = col_stats["mean"]
        if abs(val) > 1000:
            findings.append(f"{label}{col_stats['column']}: avg={val:,.0f}, trend={col_stats['trend']}")
        else:
            findings.append(f"{label}{col_stats['column']}: avg={val:.2f}, trend={col_stats['trend']}")

    # Correlation highlights (top 2)
    corr_pairs = stats_report.get("top_pairs", [])
    for a, b, val in corr_pairs[:2]:
        direction = "positive" if val > 0 else "negative"
        findings.append(f"{label}Correlation: {a} ↔ {b} = {val} ({direction})")

    # ML results
    ml_results = ml_report.get("results", {})
    for name, res in ml_results.items():
        if "silhouette" in res:
            findings.append(f"{label}Clustering ({name}): {res['silhouette']} silhouette, "
                            f"{res.get('clusters', '?')} groups")

    # Forecast — ONLY show if actual forecast was computed
    if forecast_report and forecast_report.get("method") and forecast_report.get("method") != "none":
        findings.append(f"{label}Forecast ({forecast_report['method']}): {forecast_report['trend']} trend")

    # Research
    if research_text and len(research_text) > 10:
        findings.append(f"Research: {research_text[:200]}...")

    # ── Risks ────────────────────────────────────────────────────────────
    if corr_pairs:
        for a, b, val in corr_pairs:
            if abs(val) > 0.85:
                risks.append(f"{label}High correlation ({val:.2f}) between {a} and {b} — check multicollinearity")

    for col_stats in numeric_summary:
        mean = abs(col_stats.get("mean", 0))
        std = col_stats.get("std", 0)
        if mean > 0 and std > 5 * mean:
            risks.append(f"{label}High volatility: {col_stats['column']} (σ={std:,.0f} vs μ={mean:,.0f})")

    if ml_results:
        acc_values = [r.get("accuracy", 0) for r in ml_results.values() if "accuracy" in r]
        r2_values = [r.get("r2_score", 0) for r in ml_results.values() if "r2_score" in r]
        if acc_values and max(acc_values) < 0.65:
            risks.append(f"{label}Low classification accuracy ({max(acc_values):.2f}) — feature engineering needed")
        if r2_values and max(r2_values) < 0.4:
            risks.append(f"{label}Low R² ({max(r2_values):.2f}) — weak predictive signal")

    # ── Opportunities ────────────────────────────────────────────────────
    for c in revenue_cols:
        opportunities["revenue"].append(f"{label}Optimize {c} — total ${total_sums[c]:,.0f}")
    for c in cost_cols:
        opportunities["cost_savings"].append(f"{label}Audit {c} (${total_sums[c]:,.0f}) for savings potential")
    if len(numeric_summary) >= 2:
        high_var = max(numeric_summary, key=lambda x: x.get("std", 0))
        opportunities["efficiency"].append(f"{label}Reduce variance in {high_var['column']} (σ={high_var['std']:,.0f})")

    # ── Recommendations ──────────────────────────────────────────────────
    recommendations["short_term"].append(f"{label}Validate data quality — check for missing values and outliers")
    if corr_pairs:
        top_corr = corr_pairs[0]
        recommendations["short_term"].append(
            f"{label}Investigate relationship between {top_corr[0]} and {top_corr[1]} (r={top_corr[2]})"
        )
    # ONLY recommend "declining intervention" if there's a REAL forecast showing decline
    if forecast_report and forecast_report.get("trend") == "decreasing" and forecast_report.get("method"):
        recommendations["short_term"].append(f"{label}Intervention needed: declining forecast trend detected")
        recommendations["long_term"].append(f"{label}Build early-warning system for declining {forecast_report.get('target', 'metrics')}")

    recommendations["long_term"].append(f"{label}Automate data refresh pipeline for {sheet_name or 'this dataset'}")
    recommendations["long_term"].append(f"{label}Deploy ML monitoring for anomaly detection")

    # ── Confidence ────────────────────────────────────────────────────────
    confidence = 70
    if kpis.get("row_count", 0) > 500:
        confidence += 10
    if kpis.get("row_count", 0) > 5000:
        confidence += 5
    if any("silhouette" in r and r["silhouette"] > 0.3 for r in ml_results.values()):
        confidence += 5
    if forecast_report and forecast_report.get("method") in ("prophet", "arima", "linear_extrapolation"):
        confidence += 5
    confidence = min(100, confidence)

    return {
        "findings": findings,
        "risks": risks,
        "opportunities": opportunities,
        "recommendations": recommendations,
        "confidence_score": confidence,
    }


def generate_cross_sheet_insights(sheet_results: list) -> dict[str, Any]:
    """Synthesize findings across all sheets into a unified insight report."""
    from src.workflow.state import SheetResult

    all_findings: list[str] = []
    all_risks: list[str] = []
    all_opps: dict[str, list[str]] = {"revenue": [], "cost_savings": [], "efficiency": []}
    all_recs: dict[str, list[str]] = {"short_term": [], "long_term": []}
    confidences: list[int] = []

    for sr in sheet_results:
        ins = sr.insights
        all_findings.extend(ins.get("findings", []))
        all_risks.extend(ins.get("risks", []))
        for cat in ["revenue", "cost_savings", "efficiency"]:
            all_opps[cat].extend(ins.get("opportunities", {}).get(cat, []))
        for cat in ["short_term", "long_term"]:
            all_recs[cat].extend(ins.get("recommendations", {}).get(cat, []))
        confidences.append(ins.get("confidence_score", 70))

    avg_conf = round(sum(confidences) / max(len(confidences), 1))

    return {
        "findings": all_findings,
        "risks": all_risks,
        "opportunities": all_opps,
        "recommendations": all_recs,
        "confidence_score": avg_conf,
    }
