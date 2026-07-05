"""Parse a spreadsheet, compute metrics, write a narrative, build a branded HTML report."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


def parse(path: str | Path) -> pd.DataFrame:
    path = str(path)
    if path.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce").fillna(0)


def compute_metrics(df: pd.DataFrame) -> dict:
    label_col = df.columns[0]
    rev = _num(df, "Revenue")
    cost = _num(df, "Costs")
    profit = rev - cost
    total_rev, total_cost = float(rev.sum()), float(cost.sum())
    total_profit = total_rev - total_cost
    best_i = int(rev.idxmax())
    first, last = float(rev.iloc[0]), float(rev.iloc[-1])
    growth = (last - first) / first * 100 if first else 0.0
    margin = total_profit / total_rev * 100 if total_rev else 0.0
    return {
        "label_col": label_col,
        "labels": [str(x) for x in df[label_col].tolist()],
        "revenue": [round(x, 2) for x in rev.tolist()],
        "costs": [round(x, 2) for x in cost.tolist()],
        "profit": [round(x, 2) for x in profit.tolist()],
        "total_revenue": round(total_rev, 2),
        "total_costs": round(total_cost, 2),
        "total_profit": round(total_profit, 2),
        "margin_pct": round(margin, 1),
        "growth_pct": round(growth, 1),
        "best_period": str(df[label_col].iloc[best_i]),
        "best_revenue": round(float(rev.iloc[best_i]), 2),
        "periods": len(df),
        "new_customers": int(_num(df, "New Customers").sum()) if "New Customers" in df.columns else None,
    }


def _rule_narrative(m: dict) -> str:
    trend = "grew" if m["growth_pct"] >= 0 else "declined"
    cust = (f" The business added {m['new_customers']} new customers over the period."
            if m["new_customers"] is not None else "")
    return (
        f"Over {m['periods']} periods, revenue {trend} {abs(m['growth_pct'])}% from first to last, "
        f"totalling £{m['total_revenue']:,.0f} against £{m['total_costs']:,.0f} of costs — "
        f"a net profit of £{m['total_profit']:,.0f} at a {m['margin_pct']}% margin. "
        f"The strongest period was {m['best_period']} (£{m['best_revenue']:,.0f}).{cust}"
    )


def narrative(m: dict, use_llm: bool = False) -> str:
    if use_llm and os.getenv("ANTHROPIC_API_KEY"):
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=180,
                messages=[{"role": "user", "content":
                    "Write a concise, professional 3-4 sentence executive summary of this "
                    "monthly performance data. British English, no bullet points, no preamble.\n"
                    + json.dumps({k: m[k] for k in
                        ("total_revenue", "total_costs", "total_profit", "margin_pct",
                         "growth_pct", "best_period", "best_revenue", "periods", "new_customers")})}],
            )
            return msg.content[0].text.strip()
        except Exception:
            pass
    return _rule_narrative(m)


def chart_png_data_uri(m: dict) -> str:
    """Render the revenue-vs-costs chart to a base64 PNG (server-side, no browser)."""
    import base64
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels, rev, cost = m["labels"], m["revenue"], m["costs"]
    x = range(len(labels))
    w = 0.4
    fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=140)
    ax.bar([i - w / 2 for i in x], rev, width=w, label="Revenue", color="#6d28d9")
    ax.bar([i + w / 2 for i in x], cost, width=w, label="Costs", color="#c4b5fd")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.6)
    ax.set_axisbelow(True)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def build_html(m: dict, summary: str, company: str) -> str:
    def money(x): return f"£{x:,.0f}"
    rows = "".join(
        f"<tr><td>{lbl}</td><td>{money(r)}</td><td>{money(c)}</td>"
        f"<td class='{'pos' if p>=0 else 'neg'}'>{money(p)}</td></tr>"
        for lbl, r, c, p in zip(m["labels"], m["revenue"], m["costs"], m["profit"])
    )
    chart = chart_png_data_uri(m)
    growth = f"{'+' if m['growth_pct']>=0 else ''}{m['growth_pct']}%"
    # WeasyPrint-friendly CSS: no flex/grid — KPI cards use inline-block.
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  @page {{ size:A4; margin:16mm 15mm; }}
  body {{ font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; color:#1f2937; font-size:10.5pt; margin:0; }}
  .cover {{ background:#1e1b4b; color:#fff; padding:24px 26px; border-radius:12px; }}
  .cover .k {{ font-size:8.5pt; letter-spacing:2px; text-transform:uppercase; color:#c4b5fd; margin:0 0 6px; }}
  .cover h1 {{ font-size:22pt; margin:0 0 4px; }}
  .cover p {{ margin:0; color:#ddd6fe; }}
  h2 {{ font-size:12.5pt; color:#1e1b4b; border-bottom:2px solid #c4b5fd; padding-bottom:3px; margin:20px 0 8px; }}
  .summary {{ background:#f5f3ff; border:1px solid #e9e5ff; border-radius:8px; padding:12px 15px; font-size:11pt; }}
  .kpis {{ margin:12px 0; }}
  .kpi {{ display:inline-block; width:23%; margin-right:1.5%; vertical-align:top;
          background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px; padding:11px 6px; text-align:center; }}
  .kpi .n {{ font-size:15pt; font-weight:700; color:#6d28d9; }}
  .kpi .l {{ font-size:8pt; color:#64748b; text-transform:uppercase; }}
  .chart {{ width:100%; margin-top:6px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
  th,td {{ border:1px solid #e2e8f0; padding:6px 10px; font-size:9.5pt; text-align:right; }}
  th {{ background:#f1f5f9; color:#1e1b4b; }} td:first-child, th:first-child {{ text-align:left; }}
  .pos {{ color:#059669; }} .neg {{ color:#dc2626; }}
  .foot {{ margin-top:18px; padding-top:8px; border-top:1px solid #e2e8f0; font-size:8pt; color:#94a3b8; }}
</style></head><body>
  <div class="cover">
    <p class="k">Monthly Performance Report · Auto-generated</p>
    <h1>{company}</h1>
    <p>Generated automatically from an uploaded spreadsheet — narrative, chart and layout.</p>
  </div>

  <h2>Executive summary</h2>
  <div class="summary">{summary}</div>

  <div class="kpis">
    <div class="kpi"><div class="n">{money(m['total_revenue'])}</div><div class="l">Total revenue</div></div>
    <div class="kpi"><div class="n">{money(m['total_profit'])}</div><div class="l">Net profit</div></div>
    <div class="kpi"><div class="n">{m['margin_pct']}%</div><div class="l">Margin</div></div>
    <div class="kpi"><div class="n">{growth}</div><div class="l">Revenue growth</div></div>
  </div>

  <h2>Revenue vs costs</h2>
  <img class="chart" src="{chart}" alt="Revenue vs costs chart">

  <h2>Detail</h2>
  <table><thead><tr><th>{m['label_col']}</th><th>Revenue</th><th>Costs</th><th>Profit</th></tr></thead>
  <tbody>{rows}</tbody></table>

  <div class="foot">Demonstration build — not a paid client engagement. All figures are synthetic and fictional; no real or private data is used.</div>
</body></html>"""
