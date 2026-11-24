"""Render the representative lip-sync frames with the three-vrm viewer (headless Chrome).

Usage:
    uv run python tools/render_mouth_frames.py OUT_DIR/summary.json [--vrm avatars/x.vrm]

Reads the frames chosen by tools/lipsync_check.py (mouth peak / closed / middle)
and saves OUT_DIR/<wav>_<frame>.png, rendered by the display web app in its
"still" mode. The web dev server must be running (cd app/web && npx vite).
Set CHROME to the Chrome binary if it is not in the default location.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlencode

DEFAULT_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def render(chrome: str, url: str, out: Path, size: tuple[int, int]) -> None:
    subprocess.run(
        [chrome, "--headless=new", "--hide-scrollbars", "--enable-unsafe-swiftshader",
         f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=15000",
         f"--screenshot={out}", url],
        check=True, capture_output=True, timeout=120,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("summary", type=Path)
    ap.add_argument("--url", default="http://127.0.0.1:5179/")
    ap.add_argument("--state", default="speaking")
    ap.add_argument("--size", default="420x640")
    ap.add_argument("--vrm", help="model under ADRIA_HOME/avatars (default: display.json)")
    args = ap.parse_args()
    chrome = os.environ.get("CHROME", DEFAULT_CHROME)
    size = tuple(int(v) for v in args.size.split("x"))
    summary = json.loads(args.summary.read_text())
    for result in summary["results"]:
        stem = Path(result["file"]).stem
        for name, frame in result["frames"].items():
            params = {"still": "", "checker": "", "state": args.state,
                      "mouth": f"{frame['mouth']:.3f}"}
            if args.vrm:
                params["vrm"] = args.vrm
            query = urlencode(params)
            out = args.summary.parent / f"{stem}_{name}.png"
            render(chrome, f"{args.url}?{query}", out, size)
            print(f"{out.name}: t={frame['time_sec']:.2f}s mouth={frame['mouth']:.2f}")


if __name__ == "__main__":
    main()
