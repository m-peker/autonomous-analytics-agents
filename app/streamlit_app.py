"""Autonomous Agents on GCP — Professional Dashboard."""
from __future__ import annotations
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from config.settings import settings
from src.workflow.graph import run_pipeline

st.set_page_config(page_title="Autonomous Analytics Agents", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*{font-family:Inter,system-ui,sans-serif}#MainMenu,footer,header{visibility:hidden}
section[data-testid="stSidebar"]>div:first-child{padding-top:0}
section[data-testid="stSidebar"]{background:#f8fafc;border-right:1px solid #e2e8f0}
.app-header{display:flex;align-items:center;justify-content:space-between;padding:.75rem 0;border-bottom:1px solid #e2e8f0;margin-bottom:1.5rem}
.app-header h1{font-size:1.3rem;font-weight:700;color:#1e293b;margin:0}
.pipeline-timeline{margin:1rem 0}.pipe-step{display:flex;align-items:center;gap:10px;padding:4px 0;font-size:.85rem;color:#94a3b8}
.pipe-step.done{color:#059669}.pipe-step.running{color:#4f46e5;font-weight:600}
.pipe-step .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;background:#e2e8f0}
.pipe-step.done .dot{background:#10b981}.pipe-step.running .dot{background:#4f46e5;animation:pulse 1.2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.metric-card{flex:1;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:1rem;text-align:center}
.metric-card .value{font-size:1.5rem;font-weight:700;color:#1e293b}
.metric-card .label{font-size:.75rem;color:#64748b;text-transform:uppercase;letter-spacing:.05em}
.insight-card{background:#f8fafc;border-radius:8px;padding:1rem;margin-bottom:.5rem;border-left:3px solid #4f46e5}
.insight-card.risk{border-left-color:#ef4444}.insight-card.opp{border-left-color:#f59e0b}
.chart-card{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:1rem;text-align:center}
.chart-card img{max-width:100%;border-radius:6px}
.chart-card .chart-caption{font-size:.8rem;color:#64748b;margin-top:.5rem;font-style:italic}
.stButton>button{background:#4f46e5;color:#fff;border:none;font-weight:600;border-radius:8px;padding:.6rem 2rem;transition:all .2s}
.stButton>button:hover{background:#4338ca;box-shadow:0 4px 12px rgba(79,70,229,.3)}
</style>""", unsafe_allow_html=True)

col_t, col_p = st.columns([6, 2])
with col_t:
    st.markdown("""
    <div class="app-header">
        <div>
            <h1>⚡ Autonomous Analytics Agents</h1>
            <span style="font-size:0.8rem;color:#64748b;font-weight:400">
            Upload any spreadsheet — 9 AI agents handle data quality, KPIs, statistics, 
            machine learning, forecasting, visualization, and professional reporting. Zero manual work.
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_p:
    provider = st.selectbox("Provider", ["openai","anthropic","groq","together","google","ollama"],
        format_func=lambda x: {"openai":"GPT-4o-mini","anthropic":"Claude 3","groq":"Groq","together":"Together","google":"Gemini","ollama":"Ollama"}.get(x,x),
        label_visibility="collapsed")
    # Show which providers are actually configured
    from src.llm.factory import LLMFactory
    factory = LLMFactory()
    configured = []
    for p in ["openai","anthropic","groq","together","google"]:
        prov = factory._get_or_load(p)
        if prov and prov.is_available(): configured.append(p)
    if not configured: configured.append("ollama")
    st.caption("🟢 " + " · ".join(configured) + " — if selected provider is unavailable, falls back automatically")

cf, ca = st.columns([5, 1])
with cf: files = st.file_uploader("Upload files", type=["xlsx","xlsm","xls","csv","tsv","pdf","docx","txt","md"], accept_multiple_files=True, label_visibility="collapsed", key="fu_main")
with ca: st.text(""); run_clicked = st.button("Run Analysis", type="primary", use_container_width=True)

if not files:
    st.info("👆 Upload one or more Excel, CSV, or PDF files. Each sheet will be analyzed independently by 9 specialized agents.")
    st.stop()

S = [
    ("intake","🔍","Intake Agent"),
    ("extraction","📥","Extraction Agent"),
    ("quality","✅","Quality Agent"),
    ("strategy","🧠","Strategy Agent"),
    ("analyst","📊","Business Analyst"),
    ("scientist","🔬","Data Scientist"),
    ("viz","📈","Visualization Agent"),
    ("insight","💡","Insight Agent"),
    ("report","📄","Report Generator"),
]
if "result" not in st.session_state: st.session_state.result = None

if run_clicked:
    ud = Path(settings.upload_dir); ud.mkdir(parents=True, exist_ok=True); paths = []
    for f in files or []:
        p = ud / f.name
        try:
            p.write_bytes(f.getbuffer())
        except PermissionError:
            # File locked by another process — add short suffix
            import time as _t
            p = ud / f"{Path(f.name).stem}_{int(_t.time())}{Path(f.name).suffix}"
            p.write_bytes(f.getbuffer())
        paths.append(str(p))
    if paths:
        sd = {}; ph = st.empty()
        def cb(n, ok):
            sd[n] = ok; ls = []
            for k, i, t in S:
                if k in sd: ls.append(f'<div class="pipe-step done"><span class="dot"></span> {i} {t}</div>')
                elif k == n: ls.append(f'<div class="pipe-step running"><span class="dot"></span> {i} {t}</div>')
                else: ls.append(f'<div class="pipe-step"><span class="dot"></span> {i} {t}</div>')
            ph.markdown('<div class="pipeline-timeline">' + "\n".join(ls) + '</div>', unsafe_allow_html=True)
        os.environ["LLM_PROVIDER"] = provider
        with st.spinner("Agents working…"):
            result = run_pipeline(paths, [], "", use_rag=False, progress_callback=cb)
        ls = []
        for k, i, t in S: ls.append(f'<div class="pipe-step done"><span class="dot"></span> {i} {t}</div>')
        ph.markdown('<div class="pipeline-timeline">' + "\n".join(ls) + '</div>', unsafe_allow_html=True)
        st.session_state.result = result

result = st.session_state.result
if not result: st.stop()

st.divider()
c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(f'<div class="metric-card"><div class="value">{result.get("confidence_score","—")}/100</div><div class="label">Confidence</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="value">{result.get("quality_report",{}).get("quality_score","—")}/100</div><div class="label">Data Quality</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card"><div class="value">{len(result.get("insights",{}).get("findings",[]))}</div><div class="label">Insights</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="metric-card"><div class="value">{len(result.get("charts",[]))}</div><div class="label">Charts</div></div>', unsafe_allow_html=True)
st.divider()

with st.expander("📋 Executive Summary", expanded=True):
    st.markdown(result.get("executive_summary", "_No summary._"))

qr = result.get("quality_report",{}).get("per_sheet",{})
if qr:
    qcols = st.columns(len(qr))
    for i,(n,s) in enumerate(qr.items()):
        e = "🟢" if s>=90 else ("🟡" if s>=70 else "🔴")
        with qcols[i]: st.markdown(f'<div class="metric-card"><div class="value">{e} {s}</div><div class="label">{n}</div></div>', unsafe_allow_html=True)

sr_list = result.get("sheet_results",[])
if sr_list:
    # ── Group sheets by source file ──────────────────────────────────────
    from collections import defaultdict
    by_file = defaultdict(list)
    for sr in sr_list:
        fname = Path(sr.get("source_file","")).name or "Uploaded Data"
        by_file[fname].append(sr)

    if len(by_file) > 1:
        st.subheader("📁 Cross-File Summary")
        xcols = st.columns(len(by_file))
        for i, (fname, sheets) in enumerate(by_file.items()):
            total_rows = sum(s["row_count"] for s in sheets)
            avg_q = round(sum(s.get("quality_score",0) for s in sheets) / max(len(sheets),1), 1)
            with xcols[i]:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="value">{len(sheets)} sheets</div>'
                    f'<div class="label">{fname}</div>'
                    f'<div style="font-size:0.75rem;color:#94a3b8;margin-top:4px">{total_rows} rows · quality {avg_q}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Per-file analysis ────────────────────────────────────────────────
    for fname, sheets in by_file.items():
        if len(by_file) > 1:
            st.subheader(f"📂 {fname}")
        file_tabs = st.tabs([s["sheet_name"] for s in sheets])
        for tab, sr in zip(file_tabs, sheets):
            with tab:
                st.caption(f"{sr['row_count']} rows · {sr['col_count']} cols · Quality: {sr.get('quality_score','—')}/100")
                fc, rc = st.columns(2)
                with fc:
                    for f in sr.get("findings",[])[:6]:
                        st.markdown(f'<div class="insight-card">{f}</div>', unsafe_allow_html=True)
                with rc:
                    for r in sr.get("risks",[])[:4]:
                        st.markdown(f'<div class="insight-card risk">{r}</div>', unsafe_allow_html=True)
                    if sr.get("forecast_trend"):
                        st.info(f"📉 Forecast: **{sr['forecast_trend']}**")
            # Show strategy decision
            plan = sr.get("analysis_plan", {})
            if plan:
                badges = []
                if plan.get("run_kpi"): badges.append("KPI")
                if plan.get("run_ml"): badges.append("ML")
                if plan.get("run_forecast"): badges.append("Forecast")
                if plan.get("run_charts"): badges.append("Charts")
                if badges:
                    st.caption("🧠 Strategy: " + " · ".join(badges) + f" — {plan.get('reasoning','')}")

ins = result.get("insights",{})
opps = ins.get("opportunities",{})
recs = ins.get("recommendations",{})
if any(opps.values()) or any(recs.values()):
    with st.expander("💡 Opportunities & Recommendations", expanded=False):
        o1,o2 = st.columns(2)
        with o1:
            for cat,items in opps.items():
                if items:
                    st.markdown(f"**{cat.replace('_',' ').title()}**")
                    for o in items[:3]: st.markdown(f'<div class="insight-card opp">{o}</div>', unsafe_allow_html=True)
        with o2:
            st.markdown("**⚡ Short-term**")
            for r in recs.get("short_term",[])[:4]: st.markdown(f"- {r}")
            st.markdown("**🎯 Long-term**")
            for r in recs.get("long_term",[])[:4]: st.markdown(f"- {r}")

charts = result.get("charts",[])
if charts:
    st.subheader("📈 Key Charts")
    # Group charts by file (derived from sheet name pattern)
    bs = {}
    for c in charts:
        sheet = c.get("sheet","General")
        # Find which file this sheet belongs to
        parent_file = "General"
        for sr in sr_list:
            if sr["sheet_name"] == sheet:
                parent_file = Path(sr.get("source_file","")).name or "Uploaded Data"
                break
        key = f"{parent_file} › {sheet}"
        bs.setdefault(key,[]).append(c)

    prio = ["Correlation Heatmap","Scatter Plot","Distribution","Line Chart","Bar Chart","Pie Chart"]
    for group_name, sc in bs.items():
        sc.sort(key=lambda c: prio.index(c["title"]) if c["title"] in prio else 99)
        sel = sc[:2]
        if not sel: continue
        st.markdown(f"**{group_name}**")
        cols = st.columns(len(sel))
        for i,ch in enumerate(sel):
            with cols[i]:
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.image(ch["png"], use_container_width=True)
                st.markdown(f'<div class="chart-caption">{ch.get("insight","")}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
        if len(sel) >= 1:
            try:
                from src.llm.factory import llm
                cd = "; ".join(f"{c['title']}: {c['insight']}" for c in sel)
                interp = llm.generate(
                    f"Analyze these charts and give 2-3 sentences of key business insights. "
                    f"Be specific, mention numbers and patterns. Do not just describe — interpret. "
                    f"Charts: {cd}",
                    system="You are a senior data analyst.",
                )
                st.info(f"💡 **Insight Agent:** {interp.content}")
            except Exception:
                st.caption("_Chart interpretation unavailable — check LLM provider connection._")

reps = result.get("report_paths",{})
if reps:
    with st.expander("⬇️ Download Reports", expanded=False):
        dcols = st.columns(len(reps))
        ico = {"md":"📝","html":"🌐","pdf":"📕","docx":"📄"}
        for i,(fmt,path) in enumerate(reps.items()):
            p = Path(path)
            if p.exists(): dcols[i].download_button(f"{ico.get(fmt,'📎')} {fmt.upper()}", p.read_bytes(), file_name=p.name, use_container_width=True)

if result.get("errors"):
    with st.expander("⚠️ Warnings"):
        for e in result["errors"]: st.warning(e)
