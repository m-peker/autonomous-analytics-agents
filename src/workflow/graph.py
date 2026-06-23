"""Pipeline orchestrating the 9-agent research flow.

Pipeline: Intake → Extraction → Quality → Strategy →
          Business Analyst → Data Scientist → Visualization →
          Insight → Report Generator → Output

Architecture notes:
  - Deterministic compute (parsing, stats, ML, charts) runs in plain Python.
  - LLM is used only for Strategy Agent (per-sheet decisions) and
    Insight Agent (executive summary + chart interpretation).
  - Every step is fault-isolated: errors in one agent don't crash the pipeline.
"""
from __future__ import annotations

import logging
from typing import Any

from config.settings import settings
from src.workflow.state import PipelineState

logger = logging.getLogger(__name__)


def run_pipeline(
    file_paths: list[str],
    urls: list[str],
    user_query: str = "",
    model: str | None = None,
    use_rag: bool = True,
    progress_callback: callable = None,
) -> dict[str, Any]:
    """Execute the full 9-agent research pipeline.

    Returns a dict with executive_summary, insights, charts, report_paths,
    confidence_score, quality_report, research_findings, and errors.
    """
    state = PipelineState(
        file_paths=file_paths,
        urls=urls,
        user_query=user_query,
        model=model,
        use_rag=use_rag,
    )

    logger.info("=" * 60)
    logger.info("AUTONOMOUS ANALYTICS AGENTS — Starting pipeline")
    logger.info("Files: %d | URLs: %d | Query: %s", len(file_paths), len(urls), user_query[:80])
    logger.info("=" * 60)

    # ── Step 1: Intake ──────────────────────────────────────────────────
    _step_intake(state)
    if progress_callback: progress_callback("intake", True)

    # ── Step 2: Data Extraction ──────────────────────────────────────────
    _step_extraction(state)
    if progress_callback: progress_callback("extraction", True)

    # ── Step 3: Data Quality ─────────────────────────────────────────────
    _step_quality(state)
    if progress_callback: progress_callback("quality", True)

    # ── Step 4: Strategy Agent (LLM decides what to analyze) ─────────────
    _step_strategy(state)
    if progress_callback: progress_callback("strategy", True)

    # ── Step 5: Research (conditional) ───────────────────────────────────
    if state.routing_plan.get("needs_research") or urls:
        _step_research(state)
        if progress_callback: progress_callback("research", True)

    # ── Step 6: Business Analyst (KPIs) ──────────────────────────────────
    _step_analyst(state)
    if progress_callback: progress_callback("analyst", True)

    # ── Step 7: Data Scientist (Stats + ML) ──────────────────────────────
    _step_scientist(state)
    if progress_callback: progress_callback("scientist", True)

    # ── Step 8: Visualization ────────────────────────────────────────────
    _step_visualization(state)
    if progress_callback: progress_callback("viz", True)

    # ── Step 9: Insight Agent ────────────────────────────────────────────
    _step_insights(state)
    if progress_callback: progress_callback("insight", True)

    # ── Step 10: Report Generator ────────────────────────────────────────
    _step_reporting(state)
    if progress_callback: progress_callback("report", True)

    # ── RAG indexing ─────────────────────────────────────────────────────
    if use_rag:
        _index_to_rag(state)

    # ── Build final output ───────────────────────────────────────────────
    return {
        "executive_summary": state.executive_summary,
        "insights": state.insights,
        "sheet_results": [
            {
                "sheet_name": sr.sheet_name,
                "source_file": sr.source_file,
                "row_count": sr.row_count,
                "col_count": sr.col_count,
                "quality_score": sr.quality_score,
                "quality_issues": sr.quality_issues,
                "analysis_plan": sr.analysis_plan,
                "findings": sr.insights.get("findings", []),
                "risks": sr.insights.get("risks", []),
                "ml_summary": list(sr.ml_report.keys()) if sr.ml_report else [],
                "forecast_trend": sr.forecast_report.get("trend", "") if sr.forecast_report else "",
            }
            for sr in state.sheet_results
        ],
        "charts": [
            {"title": c["title"], "insight": c["insight"], "sheet": c.get("sheet", ""),
             "png": f"data:image/png;base64,{c['png_base64']}"}
            for c in state.charts
        ],
        "report_paths": state.report_paths,
        "confidence_score": state.confidence_score,
        "quality_report": state.quality_report,
        "research_findings": state.research_findings,
        "errors": state.errors,
    }


# ── Pipeline steps ───────────────────────────────────────────────────────────

def _step_intake(state: PipelineState) -> None:
    """Step 1: Intake — classify inputs, build routing plan."""
    logger.info("[1/9] INTAKE — classifying inputs …")
    try:
        plan = {
            "data_types": [],
            "needs_research": bool(state.urls),
            "needs_ml": False,
            "needs_forecast": False,
            "recommended_steps": [
                "extract_files", "quality_check", "compute_kpis",
                "statistical_tests", "generate_charts", "synthesize_insights",
                "generate_report",
            ],
        }

        if state.file_paths:
            from src.ingestion.file_loaders import SUPPORTED_EXTENSIONS
            from pathlib import Path
            for fp in state.file_paths:
                ext = Path(fp).suffix.lower()
                if ext in (".xlsx", ".xlsm", ".xls", ".csv", ".tsv"):
                    plan["data_types"].append("tabular")
                    plan["needs_ml"] = True
                    plan["needs_forecast"] = True
                elif ext in (".pdf", ".docx", ".txt", ".md"):
                    plan["data_types"].append("document")

        if state.urls:
            plan["data_types"].append("web")
            plan["needs_research"] = True
            plan["recommended_steps"].insert(0, "scrape_web")

        state.routing_plan = plan
        logger.info("  → Plan: %s", plan.get("recommended_steps", []))
    except Exception as exc:
        state.errors.append(f"Intake failed: {exc}")
        logger.error("Intake error: %s", exc)


def _step_extraction(state: PipelineState) -> None:
    """Step 2: Load files & scrape URLs."""
    logger.info("[2/9] EXTRACTION — loading data …")
    try:
        if state.file_paths:
            from src.ingestion.file_loaders import load_files
            state.files_data = load_files(state.file_paths)
            logger.info("  → Loaded %d file(s)", len(state.files_data))

        if state.urls:
            from src.ingestion.web_scraper import scrape_urls
            pages = scrape_urls(state.urls)
            state.web_pages = [{"url": p.url, "title": p.title,
                                "text": p.text[:5000], "engine": p.engine}
                               for p in pages]
            logger.info("  → Scraped %d URL(s)", len(state.web_pages))
    except Exception as exc:
        state.errors.append(f"Extraction failed: {exc}")
        logger.error("Extraction error: %s", exc)


def _step_strategy(state: PipelineState) -> None:
    """LLM decides per-sheet analysis depth based on data characteristics."""
    logger.info("[4/10] STRATEGY — deciding analysis plan per sheet …")
    try:
        _ensure_sheet_results(state)

        for sr in state.sheet_results:
            numeric_cols = []
            for fd in state.files_data:
                if fd.get("sheets") and sr.sheet_name in fd["sheets"]:
                    df = fd["sheets"][sr.sheet_name]
                    numeric_cols = list(df.select_dtypes(include=["number"]).columns[:8])
                    break

            prompt = f"""You are a data strategy agent. Decide which analyses to run.

Sheet: {sr.sheet_name} | {sr.row_count} rows | {sr.col_count} cols
Quality: {sr.quality_score}/100
Numeric columns: {', '.join(numeric_cols) if numeric_cols else 'none'}

Reply with JSON only:
{{"run_kpi": true/false, "run_ml": true/false, "run_forecast": true/false, "run_charts": true/false, "reasoning": "one sentence"}}

Rules: KPI=always. ML needs 100+ rows + 3+ numeric + quality>70. Forecast needs 12+ rows + quality>80. Charts need 2+ numeric."""

            try:
                from src.llm.factory import llm
                resp = llm.generate(prompt, system="JSON only, no markdown.", max_tokens=300)
                import json
                txt = resp.content.strip().removeprefix("```json").removesuffix("```").strip()
                plan = json.loads(txt)
            except Exception:
                plan = {"run_kpi": True, "run_ml": sr.row_count>=100 and len(numeric_cols)>=3 and sr.quality_score>70,
                        "run_forecast": sr.row_count>=12 and len(numeric_cols)>=1 and sr.quality_score>80,
                        "run_charts": len(numeric_cols)>=2, "reasoning": "Deterministic fallback"}

            sr.analysis_plan = plan
            logger.info("  → %s: %s", sr.sheet_name, plan.get("reasoning",""))
    except Exception as exc:
        state.errors.append(f"Strategy failed: {exc}")
        logger.error("Strategy error: %s", exc)


def _step_quality(state: PipelineState) -> None:
    """Step 3: Data quality scoring & per-sheet tracking."""
    logger.info("[3/10] QUALITY — scoring per sheet …")
    try:
        from src.quality.scorer import score_dataframe

        scores: list[dict] = []
        for fd in state.files_data:
            if fd.get("sheets"):
                for name, df in fd["sheets"].items():
                    s = score_dataframe(df)
                    s["sheet_name"] = name
                    s["source"] = fd.get("path", "")
                    scores.append(s)

        # Set per-sheet quality on SheetResults
        _ensure_sheet_results(state)
        for sr in state.sheet_results:
            match = next((s for s in scores if s.get("sheet_name") == sr.sheet_name), None)
            if match:
                sr.quality_score = match["quality_score"]
                sr.quality_issues = match.get("issues", [])

        if scores:
            avg_score = sum(s["quality_score"] for s in scores) / len(scores)
            all_issues: list[str] = []
            for s in scores:
                all_issues.extend(s.get("issues", []))
            state.quality_report = {
                "quality_score": round(avg_score, 1),
                "issues": all_issues[:15],
                "per_sheet": {s["sheet_name"]: s["quality_score"] for s in scores},
            }
        else:
            state.quality_report = {"quality_score": 100, "issues": [], "per_sheet": {}}

        logger.info("  → Avg quality: %s/100", state.quality_report.get("quality_score"))
    except Exception as exc:
        state.errors.append(f"Quality check failed: {exc}")
        logger.error("Quality error: %s", exc)


def _step_research(state: PipelineState) -> None:
    """Step 4: Web research synthesis using LLM."""
    logger.info("[4/9] RESEARCH — synthesizing web content …")
    try:
        from src.llm.factory import llm

        web_texts = []
        for page in state.web_pages:
            web_texts.append(f"Source ({page['engine']}): {page['title']}\n{page['text'][:2000]}")
        context = "\n\n---\n\n".join(web_texts[:5])

        if context:
            prompt = (
                "You are a market research analyst. Based on the following web content, "
                "provide a concise synthesis covering: key trends, industry benchmarks, "
                "competitor mentions, and notable statistics.\n\n"
                f"WEB CONTENT:\n{context}\n\n"
                "SYNTHESIS (2-3 paragraphs):"
            )
            resp = llm.generate(prompt)
            state.research_findings = {
                "synthesis": resp.content,
                "sources": [{"title": p["title"], "url": p["url"]} for p in state.web_pages],
            }
        else:
            state.research_findings = {"synthesis": "No web content available.", "sources": []}

        logger.info("  → Research synthesis: %d chars", len(state.research_findings.get("synthesis", "")))
    except Exception as exc:
        state.errors.append(f"Research failed: {exc}")
        logger.error("Research error: %s", exc)


def _step_analyst(state: PipelineState) -> None:
    """Step 5: KPI computation — per sheet, each analyzed independently."""
    logger.info("[5/10] ANALYST — computing KPIs per sheet …")
    try:
        from src.analytics.kpi import compute_kpis
        _ensure_sheet_results(state)
        for sr in state.sheet_results:
            if not sr.analysis_plan.get("run_kpi", True):
                continue
            dfs = _get_sheet_dfs(state, sr.sheet_name)
            if not dfs:
                continue
            df = dfs[0]
            sr.kpi_report = compute_kpis(df)

        # Aggregate: build a cross-sheet summary
        total_rows = sum(sr.row_count for sr in state.sheet_results)
        summaries = []
        for sr in state.sheet_results:
            k = sr.kpi_report.get("summary", "")
            if k:
                summaries.append(f"[{sr.sheet_name}] {k}")
        state.kpi_report = {
            "kpis": {"total_rows": total_rows, "sheet_count": len(state.sheet_results)},
            "summary": " | ".join(summaries) if summaries else "No data.",
            "per_sheet": {sr.sheet_name: sr.kpi_report for sr in state.sheet_results},
        }
        logger.info("  → %d sheet(s) analyzed", len(state.sheet_results))
    except Exception as exc:
        state.errors.append(f"Analyst failed: {exc}")
        logger.error("Analyst error: %s", exc)


def _step_scientist(state: PipelineState) -> None:
    """Step 6: Statistics + AutoML + Forecasting — per sheet."""
    logger.info("[7/10] SCIENTIST — stats, ML, forecast per sheet …")
    try:
        _ensure_sheet_results(state)
        for sr in state.sheet_results:
            dfs = _get_sheet_dfs(state, sr.sheet_name)
            if not dfs:
                continue
            df = dfs[0]

            if sr.analysis_plan.get("run_ml", False):
                from src.analytics.statistics import correlation_matrix, hypothesis_tests
                sr.stats_report = {**correlation_matrix(df), **hypothesis_tests(df)}
                from src.analytics.automl import auto_cluster
                sr.ml_report = auto_cluster(df)

            if sr.analysis_plan.get("run_forecast", False):
                numeric = df.select_dtypes(include=["number"])
                if not numeric.empty:
                    from src.analytics.forecasting import forecast_series
                    sr.forecast_report = forecast_series(numeric.iloc[:, 0])

        # Aggregate for backward compatibility
        all_corr = {}
        for sr in state.sheet_results:
            for pair in sr.stats_report.get("top_pairs", []):
                key = f"{pair[0]}↔{pair[1]}"
                if key not in all_corr:
                    all_corr[key] = pair
        state.stats_report = {"top_pairs": list(all_corr.values())[:20]}
        state.ml_report = {"per_sheet": {sr.sheet_name: sr.ml_report for sr in state.sheet_results}}
        state.forecast_report = next(
            (sr.forecast_report for sr in state.sheet_results if sr.forecast_report), {}
        )
        logger.info("  → Stats+ML done for %d sheet(s)", len(state.sheet_results))
    except Exception as exc:
        state.errors.append(f"Scientist failed: {exc}")
        logger.error("Scientist error: %s", exc)

        # Forecasting
        if state.routing_plan.get("needs_forecast"):
            numeric = df.select_dtypes(include=["number"])
            if not numeric.empty:
                from src.analytics.forecasting import forecast_series
                sr.forecast_report = forecast_series(numeric.iloc[:, 0])


def _step_visualization(state: PipelineState) -> None:
    """Step 7: Auto-generate charts — per sheet."""
    logger.info("[8/10] VIZ — generating charts per sheet …")
    try:
        _ensure_sheet_results(state)
        all_charts: list[dict] = []
        for sr in state.sheet_results:
            if not sr.analysis_plan.get("run_charts", True):
                continue
            dfs = _get_sheet_dfs(state, sr.sheet_name)
            if not dfs:
                continue
            from src.viz.chart_engine import generate_charts
            charts = generate_charts(dfs[0], settings.output_dir)
            # Tag each chart with its sheet name
            for c in charts:
                c["sheet"] = sr.sheet_name
            sr.charts = charts
            all_charts.extend(charts)

        state.charts = all_charts
        logger.info("  → %d chart(s) across %d sheet(s)", len(all_charts), len(state.sheet_results))
    except Exception as exc:
        state.errors.append(f"Visualization failed: {exc}")
        logger.error("Viz error: %s", exc)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_sheet_results(state: PipelineState) -> None:
    """Populate state.sheet_results from files_data if not already done."""
    if state.sheet_results:
        return
    from src.workflow.state import SheetResult
    for fd in state.files_data:
        if fd.get("sheets"):
            for name, df in fd["sheets"].items():
                state.sheet_results.append(SheetResult(
                    sheet_name=name,
                    source_file=fd.get("path", ""),
                    row_count=len(df),
                    col_count=len(df.columns),
                ))


def _get_sheet_dfs(state: PipelineState, sheet_name: str) -> list:
    """Return the DataFrames for a given sheet name across all loaded files."""
    dfs = []
    for fd in state.files_data:
        if fd.get("sheets") and sheet_name in fd["sheets"]:
            dfs.append(fd["sheets"][sheet_name])
    return dfs


def _step_insights(state: PipelineState) -> None:
    """Step 8: Synthesize per-sheet insights + LLM executive summary."""
    logger.info("[9/10] INSIGHT — synthesizing per-sheet findings …")
    try:
        from src.insights.generator import generate_insights, generate_cross_sheet_insights

        # Per-sheet deterministic insights
        for sr in state.sheet_results:
            sr.insights = generate_insights(
                kpi_report=sr.kpi_report,
                stats_report=sr.stats_report,
                ml_report=sr.ml_report,
                forecast_report=sr.forecast_report,
                research_text="",
                sheet_name=sr.sheet_name,
            )

        # Cross-sheet synthesis
        state.insights = generate_cross_sheet_insights(state.sheet_results)
        state.confidence_score = state.insights.get("confidence_score", 70)

        # LLM executive summary
        from src.llm.factory import llm
        sheet_summaries = "\n".join(
            f"**{sr.sheet_name}** ({sr.row_count} rows): "
            + "; ".join(sr.insights.get("findings", [])[:3])
            for sr in state.sheet_results
        )
        summary_prompt = (
            "You are a Chief Data Officer. Write a 2-3 paragraph executive summary "
            "covering ALL of the following data sheets. Mention specific numbers where available. "
            "Be concise but insightful.\n\n"
            f"{sheet_summaries}\n\n"
            "EXECUTIVE SUMMARY:"
        )
        resp = llm.generate(summary_prompt)
        state.executive_summary = resp.content
        logger.info("  → Confidence: %d/100", state.confidence_score)
    except Exception as exc:
        import traceback
        logger.error("Insight error: %s\n%s", exc, traceback.format_exc())
        state.errors.append(f"Insight generation failed: {exc}")


def _step_reporting(state: PipelineState) -> None:
    """Step 9: Generate downloadable reports."""
    logger.info("[10/10] REPORT — generating documents …")
    try:
        from src.reporting.generator import generate_reports

        state.report_paths = generate_reports(
            executive_summary=state.executive_summary or "Analysis completed.",
            insights=state.insights,
            kpi_data=state.kpi_report,
            research_synthesis=state.research_findings.get("synthesis", ""),
            ml_results=state.ml_report.get("results", {}),
        )
        logger.info("  → Reports: %s", list(state.report_paths.keys()))
    except Exception as exc:
        state.errors.append(f"Report generation failed: {exc}")
        logger.error("Report error: %s", exc)


def _index_to_rag(state: PipelineState) -> None:
    """Index all outputs into ChromaDB for RAG Q&A."""
    logger.info("RAG — indexing to ChromaDB …")
    try:
        from src.rag.store import KnowledgeBase
        kb = KnowledgeBase()

        # Index executive summary
        if state.executive_summary:
            kb.index_text(state.executive_summary, source="executive_summary")

        # Index research synthesis
        if state.research_findings.get("synthesis"):
            kb.index_text(state.research_findings["synthesis"], source="web_research")

        # Index KPI summary
        if state.kpi_report.get("summary"):
            kb.index_text(state.kpi_report["summary"], source="kpi_analysis")

        # Index each file's text
        for fd in state.files_data:
            if fd.get("text"):
                kb.index_text(fd["text"], source=fd["path"])

        # Index scraped pages
        for page in state.web_pages:
            if page.get("text"):
                kb.index_text(page["text"], source=page.get("url", "web"))

        logger.info("  → Knowledge base: %d documents", kb.count())
    except Exception as exc:
        state.errors.append(f"RAG indexing failed: {exc}")
        logger.error("RAG error: %s", exc)
