"""Pipeline workflow state definition."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SheetResult:
    """Per-sheet analysis result."""
    sheet_name: str = ""
    source_file: str = ""
    row_count: int = 0
    col_count: int = 0
    quality_score: float = 100.0
    quality_issues: list[str] = field(default_factory=list)
    analysis_plan: dict[str, Any] = field(default_factory=dict)
    kpi_report: dict[str, Any] = field(default_factory=dict)
    stats_report: dict[str, Any] = field(default_factory=dict)
    ml_report: dict[str, Any] = field(default_factory=dict)
    forecast_report: dict[str, Any] = field(default_factory=dict)
    charts: list[dict[str, Any]] = field(default_factory=list)
    insights: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineState:
    """Shared state that flows through the agent pipeline."""

    # Inputs
    file_paths: list[str] = field(default_factory=list)
    urls: list[str] = field(default_factory=list)
    user_query: str = ""
    model: str | None = None
    use_rag: bool = True

    # Routing plan (from Intake Agent)
    routing_plan: dict[str, Any] = field(default_factory=dict)

    # Loaded data
    files_data: list[dict[str, Any]] = field(default_factory=list)
    web_pages: list[dict[str, Any]] = field(default_factory=list)

    # Quality (aggregate across all sheets)
    quality_report: dict[str, Any] = field(default_factory=dict)

    # Web research
    research_findings: dict[str, Any] = field(default_factory=dict)

    # Per-sheet results (NEW — replaces monolithic analytics)
    sheet_results: list[SheetResult] = field(default_factory=list)

    # Aggregate analytics (computed from sheet_results)
    kpi_report: dict[str, Any] = field(default_factory=dict)
    stats_report: dict[str, Any] = field(default_factory=dict)
    ml_report: dict[str, Any] = field(default_factory=dict)
    forecast_report: dict[str, Any] = field(default_factory=dict)

    # Charts (aggregated across all sheets)
    charts: list[dict[str, Any]] = field(default_factory=list)

    # Insights
    insights: dict[str, Any] = field(default_factory=dict)
    executive_summary: str = ""

    # Outputs
    report_paths: dict[str, str] = field(default_factory=dict)
    confidence_score: int = 0

    # Error tracking
    errors: list[str] = field(default_factory=list)
