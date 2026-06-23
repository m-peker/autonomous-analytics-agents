"""Generate a realistic demo dataset for the Autonomous Agents platform.

Creates: data/uploads/demo_business_data.xlsx
  - Sheet 1: Sales — 500 rows of transactional sales data
  - Sheet 2: Customers — 200 customer profiles with segments
  - Sheet 3: Marketing — monthly marketing spend & channel performance
"""
import random
from pathlib import Path

import numpy as np
import pandas as pd

np.random.seed(42)
random.seed(42)

# ── Sheet 1: Sales Transactions ─────────────────────────────────────────
n = 500
dates = pd.date_range(start="2024-01-01", end="2025-06-01", freq="W")
products = ["Enterprise Suite", "Analytics Pro", "Starter Kit", "API Access", "Consulting"]
regions = ["North America", "Europe", "Asia Pacific", "Middle East", "Latin America"]
segments = ["Enterprise", "Mid-Market", "SMB", "Startup"]

sales = pd.DataFrame({
    "date": np.random.choice(dates, n),
    "product": np.random.choice(products, n, p=[0.15, 0.25, 0.30, 0.20, 0.10]),
    "region": np.random.choice(regions, n, p=[0.35, 0.25, 0.20, 0.10, 0.10]),
    "segment": np.random.choice(segments, n, p=[0.20, 0.30, 0.30, 0.20]),
    "units_sold": np.random.poisson(lam=50, size=n) + 1,
    "unit_price": np.random.uniform(50, 5000, n).round(2),
    "discount_pct": np.random.choice([0, 0, 0, 5, 10, 15, 20], n, p=[0.3, 0.2, 0.15, 0.1, 0.1, 0.1, 0.05]),
    "customer_id": np.random.randint(1000, 1201, n),
})
sales["revenue"] = (sales["units_sold"] * sales["unit_price"] * (1 - sales["discount_pct"] / 100)).round(2)
sales["cost_per_unit"] = (sales["unit_price"] * np.random.uniform(0.3, 0.7, n)).round(2)
sales["profit"] = (sales["revenue"] - sales["units_sold"] * sales["cost_per_unit"]).round(2)
sales = sales.sort_values("date")

# ── Sheet 2: Customer Profiles ──────────────────────────────────────────
customer_ids = sorted(sales["customer_id"].unique())
customer = pd.DataFrame({
    "customer_id": customer_ids,
    "company_name": [f"Company_{cid}" for cid in customer_ids],
    "industry": np.random.choice(
        ["Technology", "Finance", "Healthcare", "Retail", "Manufacturing", "Education"],
        len(customer_ids),
        p=[0.30, 0.20, 0.15, 0.15, 0.10, 0.10],
    ),
    "employee_count": np.random.poisson(lam=200, size=len(customer_ids)) + 5,
    "annual_revenue_m": np.random.exponential(scale=50, size=len(customer_ids)).round(1),
    "country": np.random.choice(
        ["US", "UK", "DE", "JP", "BR", "IN", "AE", "SG", "AU", "CA"],
        len(customer_ids),
        p=[0.30, 0.12, 0.10, 0.08, 0.08, 0.08, 0.06, 0.06, 0.06, 0.06],
    ),
    "acquisition_channel": np.random.choice(
        ["Organic", "Paid Search", "Partner", "Outbound", "Event"],
        len(customer_ids),
    ),
    "churn_risk": np.random.choice(
        ["Low", "Medium", "High", None],
        len(customer_ids),
        p=[0.50, 0.25, 0.10, 0.15],
    ),
})
customer["customer_since"] = pd.to_datetime(
    np.random.choice(pd.date_range("2020-01-01", "2024-12-01", freq="M"), len(customer_ids))
)

# ── Sheet 3: Marketing Spend ────────────────────────────────────────────
marketing = pd.DataFrame({
    "month": pd.date_range("2024-01-01", periods=18, freq="M"),
    "paid_search_spend": np.random.uniform(8000, 20000, 18).round(0),
    "social_media_spend": np.random.uniform(3000, 12000, 18).round(0),
    "content_marketing_spend": np.random.uniform(2000, 8000, 18).round(0),
    "event_spend": np.random.choice([0, 0, 5000, 10000, 15000], 18, p=[0.4, 0.2, 0.15, 0.15, 0.1]),
    "email_marketing_spend": np.random.uniform(500, 3000, 18).round(0),
})
marketing["total_spend"] = marketing.iloc[:, 1:].sum(axis=1)
marketing["leads_generated"] = (marketing["total_spend"] / np.random.uniform(20, 60, 18)).round(0).astype(int)
marketing["conversions"] = (marketing["leads_generated"] * np.random.uniform(0.02, 0.12, 18)).round(0).astype(int)
marketing["cac"] = (marketing["total_spend"] / marketing["conversions"].replace(0, 1)).round(2)
marketing["roi"] = ((marketing["conversions"] * 5000 - marketing["total_spend"]) / marketing["total_spend"] * 100).round(1)

# ── Write ───────────────────────────────────────────────────────────────
out_dir = Path("data/uploads")
out_dir.mkdir(parents=True, exist_ok=True)

filepath = out_dir / "demo_business_data.xlsx"
with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
    sales.to_excel(writer, sheet_name="Sales", index=False)
    customer.to_excel(writer, sheet_name="Customers", index=False)
    marketing.to_excel(writer, sheet_name="Marketing", index=False)

print(f"✅ Demo dataset created: {filepath}")
print(f"   Sales:      {len(sales)} rows × {len(sales.columns)} cols")
print(f"   Customers:  {len(customer)} rows × {len(customer.columns)} cols")
print(f"   Marketing:  {len(marketing)} rows × {len(marketing.columns)} cols")
print(f"\n   Total revenue: ${sales['revenue'].sum():,.0f}")
print(f"   Total profit:  ${sales['profit'].sum():,.0f}")
print(f"   Unique products: {sales['product'].nunique()}")
print(f"   Regions: {sales['region'].nunique()}")
