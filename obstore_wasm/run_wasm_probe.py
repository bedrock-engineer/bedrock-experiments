# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.0",
#     "playwright>=1.55",
# ]
# ///
"""Export the probe notebook to WASM, open it in headless Chromium, print the result.

Usage (from obstore_wasm/):

    uv run run_wasm_probe.py                    # export + serve + run
    uv run run_wasm_probe.py --wheel path.whl   # also offer a locally built wheel

Needs a Playwright Chromium: `uv run --with playwright playwright install chromium`.
"""

import argparse
import functools
import http.server
import json
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
DIST = HERE / "dist"


def export(wheels: list[Path]) -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    subprocess.run(
        [
            sys.executable, "-m", "marimo", "export", "html-wasm",
            str(HERE / "obstore_probe_mo.py"), "-o", str(DIST), "--mode", "run",
        ],
        check=True,
    )
    public = DIST / "public"
    public.mkdir(exist_ok=True)
    shutil.copy(HERE / "public" / "sample.txt", public / "sample.txt")
    (public / "wheels").mkdir(exist_ok=True)
    for whl in wheels:
        shutil.copy(whl, public / "wheels" / whl.name)
    (public / "wheels.txt").write_text("".join(f"{w.name}\n" for w in wheels))


def serve() -> http.server.ThreadingHTTPServer:
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(DIST)
    )
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def run_in_browser(url: str, timeout_s: int) -> tuple[list[dict] | None, list[str]]:
    console: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda m: console.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: console.append(f"[pageerror] {e}"))
        page.goto(url)
        try:
            page.locator("#probe-result").wait_for(timeout=timeout_s * 1000)
            rows = json.loads(page.locator("#probe-result").inner_text())
        except Exception as e:  # noqa: BLE001
            console.append(f"[runner] no result: {e}")
            page.screenshot(path=str(HERE / "dist" / "timeout.png"), full_page=True)
            rows = None
        browser.close()
    return rows, console


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wheel", type=Path, action="append", default=[])
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    export(args.wheel)
    server = serve()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    rows, console = run_in_browser(url, args.timeout)
    server.shutdown()

    interesting = [c for c in console if any(
        k in c.lower() for k in ("obstore", "error", "panic", "wasm", "micropip", "runner")
    )]
    print("\n".join(interesting[-40:]))
    if rows is None:
        sys.exit("no probe result")
    for r in rows:
        print(f"{r['status']:5} {r['seconds']:7.2f}s  {r['name']}: {r['detail']}")


if __name__ == "__main__":
    main()
