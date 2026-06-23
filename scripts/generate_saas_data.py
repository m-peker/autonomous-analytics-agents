"""Generate a second demo dataset: SaaS Startup Metrics.

Creates: data/uploads/demo_saas_metrics.xlsx
  - Sheet 1: Subscription Revenue — MRR, churn, upgrades over 24 months
  - Sheet 2: Product Usage — DAU, feature adoption, session time, NPS
  - Sheet 3: Customer Support — tickets, resolution time, satisfaction
"""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(123)

# ── Sheet 1: Subscription Revenue (24 months) ───────────────────────────
months = pd.date_range("2024-01-01", periods=24, freq="ME")
n = 24
base_mrr = 50_000
growth = np.cumsum(np.random.normal(0.05, 0.02, n))
mrr = (base_mrr * (1 + growth)).round(0)
new_mrr = np.random.poisson(lam=5000, size=n) + 2000
expansion_mrr = np.random.poisson(lam=3000, size=n) + 1000
churned_mrr = np.random.poisson(lam=2000, size=n) + 500
downgrade_mrr = np.random.poisson(lam=1000, size=n) + 200

subscription = pd.DataFrame({
    "month": months,
    "mrr": mrr.astype(int),
    "new_mrr": new_mrr,
    "expansion_mrr": expansion_mrr,
    "churned_mrr": churned_mrr,
    "downgrade_mrr": downgrade_mrr,
    "total_customers": (np.cumsum(np.random.poisson(lam=30, size=n)) + 200).astype(int),
    "arpu": (mrr / (np.cumsum(np.random.poisson(lam=30, size=n)) + 200)).round(2),
})
subscription["net_new_mrr"] = subscription["new_mrr"] + subscription["expansion_mrr"] - subscription["churned_mrr"] - subscription["downgrade_mrr"]
subscription["churn_rate_pct"] = (subscription["churned_mrr"] / subscription["mrr"] * 100).round(2)

# ── Sheet 2: Product Usage (24 months) ──────────────────────────────────
product = pd.DataFrame({
    "month": months,
    "dau": np.random.randint(800, 3500, n),
    "wau": np.random.randint(3000, 12000, n),
    "mau": np.random.randint(10000, 40000, n),
    "avg_session_minutes": np.random.uniform(12, 28, n).round(1),
    "feature_a_adoption_pct": np.clip(np.cumsum(np.random.normal(0.8, 0.3, n)), 10, 85).round(1),
    "feature_b_adoption_pct": np.clip(np.cumsum(np.random.normal(0.5, 0.4, n)), 2, 55).round(1),
    "feature_c_adoption_pct": np.clip(np.cumsum(np.random.normal(0.3, 0.5, n)), 1, 35).round(1),
    "nps_score": np.clip(np.random.normal(42, 8, n).round(0), 20, 65).astype(int),
})
product["dau_mau_ratio"] = (product["dau"] / product["mau"] * 100).round(1)
product["engagement_score"] = (
    product["dau_mau_ratio"] * 0.4 + product["feature_a_adoption_pct"] * 0.3 + product["nps_score"] / 65 * 30
).round(1)

# ── Sheet 3: Customer Support (24 months) ───────────────────────────────
support = pd.DataFrame({
    "month": months,
    "tickets_opened": np.random.poisson(lam=200, size=n) + 100,
    "tickets_resolved": np.random.poisson(lam=190, size=n) + 100,
    "avg_resolution_hours": np.clip(np.random.normal(8, 3, n).round(1), 2, 48),
    "csat_score": np.clip(np.random.normal(4.2, 0.4, n).round(1), 3.0, 5.0),
    "tier_1_pct": np.random.uniform(40, 65, n).round(1),
    "tier_2_pct": np.random.uniform(20, 35, n).round(1),
    "tier_3_pct": np.random.uniform(5, 20, n).round(1),
    "backlog": (np.random.poisson(lam=10, size=n) + 5).astype(int),
})
support["resolution_rate_pct"] = (support["tickets_resolved"] / support["tickets_opened"] * 100).round(1)
support["avg_resolution_cost"] = (support["avg_resolution_hours"] * np.random.uniform(15, 35, n)).round(2)

# ── Write ───────────────────────────────────────────────────────────────
out_dir = Path("data/uploads")
out_dir.mkdir(parents=True, exist_ok=True)

filepath = out_dir / "demo_saas_metrics.xlsx"
with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
    subscription.to_excel(writer, sheet_name="Subscription", index=False)
    product.to_excel(writer, sheet_name="Product Usage", index=False)
    support.to_excel(writer, sheet_name="Support", index=False)

print(f"✅ SaaS metrics dataset: {filepath}")
print(f"   Subscription: {len(subscription)} rows × {len(subscription.columns)} cols")
print(f"   Product:      {len(product)} rows × {len(product.columns)} cols")
print(f"   Support:      {len(support)} rows × {len(support.columns)} cols")
print(f"\n   Final MRR: ${subscription['mrr'].iloc[-1]:,}")
print(f"   Final ARPU: ${subscription['arpu'].iloc[-1]:.2f}")
print(f"   Final NPS:   {product['nps_score'].iloc[-1]}")
print(f"   Avg CSAT:    {support['csat_score'].mean():.1f}/5.0")
