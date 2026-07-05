"""Document & Report Automation — upload a spreadsheet, get a branded PDF report."""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse

from . import report as R
from .render import html_to_pdf
from .sample_data import build_sample, DEMO_COMPANY

app = FastAPI(title="Document & Report Automation", version="1.0.0")

OUT = Path(tempfile.gettempdir()) / "dra-out"
OUT.mkdir(exist_ok=True)

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Document &amp; Report Automation</title>
<style>
  body{font-family:-apple-system,"Segoe UI",Roboto,Arial,sans-serif;background:#f1f5f9;color:#1f2937;margin:0}
  header{background:#1e1b4b;color:#fff;padding:20px 26px}
  header h1{margin:0;font-size:19px} header p{margin:4px 0 0;color:#c4b5fd;font-size:13px}
  .wrap{max-width:640px;margin:32px auto;padding:0 20px}
  .card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;margin-bottom:18px}
  .step{display:flex;gap:12px;align-items:flex-start;margin:10px 0;font-size:14px}
  .step b{background:#6d28d9;color:#fff;border-radius:50%;width:24px;height:24px;display:inline-flex;
          align-items:center;justify-content:center;font-size:12px;flex:none}
  .drop{border:2px dashed #c4b5fd;border-radius:10px;padding:26px;text-align:center;background:#faf5ff;margin:12px 0}
  input[type=file]{font-size:13px}
  button{background:#6d28d9;color:#fff;border:0;border-radius:8px;padding:11px 18px;font-size:14px;font-weight:600;cursor:pointer}
  button:hover{background:#5b21b6} .muted{color:#64748b;font-size:12.5px}
  .or{ text-align:center;color:#94a3b8;margin:10px 0;font-size:12px }
</style></head><body>
<header><h1>Document &amp; Report Automation</h1>
<p>Spreadsheet in → branded PDF report out · demonstration build (synthetic data)</p></header>
<div class="wrap">
  <div class="card">
    <div class="step"><b>1</b><div>Upload a spreadsheet with columns <code>Month, Revenue, Costs, New Customers</code>.</div></div>
    <div class="step"><b>2</b><div>It's parsed, the numbers are analysed, and an executive summary is written.</div></div>
    <div class="step"><b>3</b><div>A branded PDF — summary, KPIs, chart and table — is generated and downloaded.</div></div>
  </div>
  <div class="card">
    <form action="/generate" method="post" enctype="multipart/form-data">
      <div class="drop">
        <input type="file" name="file" accept=".csv,.xlsx,.xls" required>
        <p class="muted">CSV or Excel</p>
      </div>
      <button type="submit">Generate report</button>
    </form>
    <div class="or">— or —</div>
    <form action="/generate-sample" method="post">
      <button type="submit" style="background:#0369a1">Generate from sample data</button>
      <span class="muted">&nbsp;uses a synthetic monthly dataset</span>
    </form>
  </div>
</div></body></html>"""


def _make_pdf(df, company: str) -> Path:
    metrics = R.compute_metrics(df)
    summary = R.narrative(metrics)          # set use_llm=True for a Claude-written summary
    html = R.build_html(metrics, summary, company)
    out = OUT / f"report-{uuid.uuid4().hex}.pdf"
    return html_to_pdf(html, out)


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.post("/generate")
async def generate(file: UploadFile = File(...)):
    suffix = Path(file.filename or "upload.csv").suffix or ".csv"
    tmp = OUT / f"in-{uuid.uuid4().hex}{suffix}"
    tmp.write_bytes(await file.read())
    df = R.parse(tmp)
    tmp.unlink(missing_ok=True)
    pdf = _make_pdf(df, Path(file.filename or "Report").stem.title())
    return FileResponse(pdf, media_type="application/pdf", filename="report.pdf")


@app.post("/generate-sample")
def generate_sample():
    df = R.parse(build_sample())
    pdf = _make_pdf(df, DEMO_COMPANY)
    return FileResponse(pdf, media_type="application/pdf", filename="sample-report.pdf")
