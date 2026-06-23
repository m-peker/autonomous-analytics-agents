"""Autonomous Analytics Agents — CLI entry point.

Examples:
    python main.py --files data/sales.xlsx --query "Analyze revenue trends"
    python main.py --urls https://example.com/report --files analysis.pdf
    python main.py --provider groq --files data.csv --query "Find anomalies"
    python main.py --ask "What were the key risks?"          # RAG follow-up
    python main.py --list-providers                            # Show available LLMs
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def cli() -> None:
    p = argparse.ArgumentParser(
        description="⚡ Autonomous Analytics Agents — Multi-Agent Data Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --files data/sales.xlsx --query "Analyze revenue"
  python main.py --urls https://example.com --provider anthropic
  python main.py --ask "What were the main risks?"
  python main.py --list-providers
        """,
    )
    p.add_argument("--files", nargs="*", default=[], help="xlsx/csv/pdf/docx/txt file paths")
    p.add_argument("--urls", nargs="*", default=[], help="URLs to scrape and research")
    p.add_argument("--query", default="", help="Business question or analysis objective")
    p.add_argument("--provider", default=None,
                   choices=["openai", "anthropic", "groq", "together", "google", "ollama"],
                   help="LLM provider override")
    p.add_argument("--no-rag", action="store_true", help="Disable ChromaDB RAG indexing")
    p.add_argument("--ask", default=None, help="RAG follow-up question (skips pipeline)")
    p.add_argument("--list-providers", action="store_true", help="Show available LLM providers")
    args = p.parse_args()

    # --list-providers
    if args.list_providers:
        from config.settings import settings as s
        print("Available LLM providers:")
        providers = [
            ("openai", s.openai_api_key),
            ("anthropic", s.anthropic_api_key),
            ("groq", s.groq_api_key),
            ("together", s.together_api_key),
            ("google", s.google_api_key),
            ("ollama", True),
        ]
        for name, configured in providers:
            status = "✅ configured" if configured else "❌ not configured"
            print(f"  {name:12s}  {status}")
        return

    # --ask (RAG mode)
    if args.ask:
        from src.rag.store import KnowledgeBase
        res = KnowledgeBase().ask(args.ask)
        print(res["answer"])
        return

    # Pipeline mode
    if not args.files and not args.urls:
        p.error("Provide --files and/or --urls (or use --ask for RAG Q&A).")

    if args.provider:
        import os
        os.environ["LLM_PROVIDER"] = args.provider

    from src.workflow.graph import run_pipeline

    print("\n⚡ Autonomous Analytics Agents — Running pipeline…\n")
    result = run_pipeline(args.files, args.urls, args.query, use_rag=not args.no_rag)

    print("\n" + "=" * 60)
    print("📋 EXECUTIVE SUMMARY")
    print("=" * 60)
    print(result.get("executive_summary", "No summary."))

    print("\n" + "=" * 60)
    print(f"🎯 CONFIDENCE SCORE: {result.get('confidence_score', 'N/A')}/100")
    print(f"📊 DATA QUALITY:   {result.get('quality_report', {}).get('quality_score', 'N/A')}/100")

    print("\n" + "=" * 60)
    print("📄 GENERATED REPORTS")
    print("=" * 60)
    for fmt, path in (result.get("report_paths") or {}).items():
        print(f"  {fmt.upper()}: {path}")

    print("\n" + "=" * 60)
    print(f"📈 CHARTS: {len(result.get('charts', []))} generated")
    print(f"💡 FINDINGS: {len(result.get('insights', {}).get('findings', []))} identified")
    print(f"⚠️  RISKS: {len(result.get('insights', {}).get('risks', []))} flagged")

    # Cost summary
    from src.llm.factory import cost_tracker
    cost = cost_tracker.snapshot()
    if cost["call_count"] > 0:
        print(f"\n💰 API COST: ${cost['total_cost_usd']:.6f} ({cost['call_count']} calls)")

    if result.get("errors"):
        print("\n⚠️  WARNINGS:")
        for e in result["errors"]:
            print(f"  - {e}")

    print("\n✅ Pipeline complete.\n")


if __name__ == "__main__":
    cli()
