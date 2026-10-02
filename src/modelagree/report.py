import html
import json
from pathlib import Path

from .scoring import score


def report(run_dir):
    path = Path(run_dir) / "report.html"
    payload = html.escape(json.dumps(score(run_dir), indent=2, ensure_ascii=False))
    path.write_text("<!doctype html><html lang='en'><meta charset='utf-8'>"
                    "<title>modelagree report</title><h1>modelagree report</h1>"
                    f"<pre>{payload}</pre></html>", encoding="utf-8")
    return path
