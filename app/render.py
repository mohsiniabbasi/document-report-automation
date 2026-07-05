"""HTML -> PDF rendering.

Primary path: WeasyPrint (pure-Python, no browser) — reliable and deterministic
in containers. The chart is rendered server-side by matplotlib and embedded as an
image, so no JavaScript engine is needed.

Fallback: if WeasyPrint isn't installed (e.g. a Windows dev box without its GTK
libs), fall back to headless Chrome so local development still works.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path


def _weasyprint_pdf(html: str, out_path: Path) -> None:
    from weasyprint import HTML
    HTML(string=html, base_url=".").write_pdf(str(out_path))


_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "google-chrome", "chromium", "chromium-browser",
]


def _find_chrome() -> str:
    env = os.getenv("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for c in _CHROME_CANDIDATES:
        if Path(c).exists() or shutil.which(c):
            return c
    raise RuntimeError("Neither WeasyPrint nor Chrome available for PDF rendering.")


def _chrome_pdf(html: str, out_path: Path) -> None:
    tmp = Path(tempfile.gettempdir()) / f"report-{uuid.uuid4().hex}.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        subprocess.run(
            [_find_chrome(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
             "--no-sandbox", "--disable-dev-shm-usage",
             "--virtual-time-budget=6000", f"--print-to-pdf={out_path}", tmp.as_uri()],
            capture_output=True, timeout=60,
        )
    finally:
        tmp.unlink(missing_ok=True)


def html_to_pdf(html: str, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    try:
        _weasyprint_pdf(html, out_path)
    except ImportError:
        _chrome_pdf(html, out_path)     # local dev fallback
    if not out_path.exists() or out_path.stat().st_size < 200 or out_path.read_bytes()[:4] != b"%PDF":
        raise RuntimeError("PDF render produced no valid output.")
    return out_path
