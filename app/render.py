"""HTML -> PDF via headless Chrome (the same render pipeline used across the projects)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

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
    raise RuntimeError("Chrome/Chromium not found. Set CHROME_PATH.")


def html_to_pdf(html: str, out_path: str | Path) -> Path:
    out_path = Path(out_path)
    tmp = Path(tempfile.gettempdir()) / f"report-{uuid.uuid4().hex}.html"
    tmp.write_text(html, encoding="utf-8")
    try:
        proc = subprocess.run(
            [_find_chrome(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
             # --no-sandbox / --disable-dev-shm-usage: required to run Chromium headless
             # as root inside a container; harmless on a normal desktop.
             "--no-sandbox", "--disable-dev-shm-usage",
             "--virtual-time-budget=6000", f"--print-to-pdf={out_path}", tmp.as_uri()],
            capture_output=True, timeout=60,
        )
    finally:
        tmp.unlink(missing_ok=True)
    # Trust the output file, not the exit code: some headless Chromium builds write a
    # valid PDF then exit non-zero on shutdown (harmless crashpad noise in containers).
    if not out_path.exists() or out_path.stat().st_size < 200 or out_path.read_bytes()[:4] != b"%PDF":
        raise RuntimeError(
            f"PDF render failed (exit {proc.returncode}): "
            f"{proc.stderr.decode(errors='ignore')[-500:]}"
        )
    return out_path
