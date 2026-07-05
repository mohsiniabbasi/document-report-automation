"""Generate a synthetic monthly-performance spreadsheet for the demo.

Fictional company, fabricated figures — no real financials or private data.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SAMPLE_CSV = Path(__file__).parent / "sample_monthly_performance.csv"
DEMO_COMPANY = "Northwind Trading Co. (demo)"


def build_sample(seed: int = 7) -> Path:
    rng = random.Random(seed)
    rows = []
    revenue = 42000
    for m in MONTHS:
        revenue = int(revenue * rng.uniform(1.01, 1.12))          # gentle growth
        costs = int(revenue * rng.uniform(0.55, 0.72))
        new_customers = rng.randint(18, 46)
        rows.append({"Month": m, "Revenue": revenue,
                     "Costs": costs, "New Customers": new_customers})
    with open(SAMPLE_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Month", "Revenue", "Costs", "New Customers"])
        w.writeheader()
        w.writerows(rows)
    return SAMPLE_CSV


if __name__ == "__main__":
    print("wrote", build_sample())
