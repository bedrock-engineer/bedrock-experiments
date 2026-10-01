# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.0",
#     "pandas>=3.0",
#     "playwright>=1.55",
#     "pyarrow>=22",
# ]
# ///
"""Export the probe notebook to WASM, open it in headless Chromium, print the result.

Usage (from obstore_wasm/):

    uv run run_wasm_probe.py                    # export + serve + run obstore_probe_mo.py
    uv run run_wasm_probe.py --wheel path.whl   # also offer a locally built wheel
    uv run run_wasm_probe.py --notebook web_data_probe_mo.py

A second server on another port (so: cross-origin) serves a Parquet file with
CORS and Range support. Its URL goes into `public/config.json`.

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
CPT_CSV = (
    "https://raw.githubusercontent.com/bedrock-engineer/bedrock-ge/main/examples/"
    "nz_weka_hills_leapfrog/WH_cpt_Alluvial.csv"
)


def export(notebook: Path, wheels: list[Path]) -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    subprocess.run(
        [
            sys.executable, "-m", "marimo", "export", "html-wasm",
            str(notebook), "-o", str(DIST), "--mode", "run",
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


def write_parquet(path: Path) -> None:
    """CPT table from bedrock-ge as Parquet, 10 row groups."""
    import pandas as pd

    df = pd.read_csv(CPT_CSV)
    df.to_parquet(path, row_group_size=len(df) // 10 + 1)


class RangeCORSHandler(http.server.SimpleHTTPRequestHandler):
    """Static files with `Access-Control-Allow-Origin: *` and single Range requests.

    Every request is appended to `requests` as (method, path with query, Range
    header, body bytes sent), so the runner can show what each reader fetched.
    """

    requests: list[tuple[str, str, str, int]] = []
    log_message = lambda *a: None  # noqa: E731

    def send_header(self, key, value):
        if key.lower() == "content-length":
            self._sent_length = int(value)
        super().send_header(key, value)

    def handle_one_request(self):
        self._sent_length = 0
        super().handle_one_request()
        if getattr(self, "command", None):
            body = 0 if self.command in ("HEAD", "OPTIONS") else self._sent_length
            self.requests.append(
                (self.command, self.path, self.headers.get("Range", ""), body)
            )

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "Content-Range, Content-Length, Accept-Ranges, ETag")
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        rng = self.headers.get("Range")
        path = Path(self.translate_path(self.path))
        if not rng or not path.is_file():
            return super().do_GET()
        size = path.stat().st_size
        start_s, end_s = rng.removeprefix("bytes=").split(",")[0].split("-")
        if start_s == "":
            start, end = max(size - int(end_s), 0), size - 1
        else:
            start = int(start_s)
            end = min(int(end_s), size - 1) if end_s else size - 1
        with open(path, "rb") as f:
            f.seek(start)
            body = f.read(end - start + 1)
        self.send_response(206)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(directory: Path, handler_cls=http.server.SimpleHTTPRequestHandler):
    handler = functools.partial(handler_cls, directory=str(directory))
    if handler_cls is http.server.SimpleHTTPRequestHandler:
        http.server.SimpleHTTPRequestHandler.log_message = lambda *a: None
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
    ap.add_argument("--notebook", type=Path, default=HERE / "obstore_probe_mo.py")
    ap.add_argument("--wheel", type=Path, action="append", default=[])
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()

    export(args.notebook, args.wheel)
    data_dir = DIST / "cross_origin"
    data_dir.mkdir()
    write_parquet(data_dir / "cpt.parquet")
    data_server = serve(data_dir, RangeCORSHandler)
    parquet_url = f"http://127.0.0.1:{data_server.server_port}/cpt.parquet"
    (DIST / "public" / "config.json").write_text(json.dumps({"parquet_url": parquet_url}))
    server = serve(DIST)
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    rows, console = run_in_browser(url, args.timeout)
    server.shutdown()
    data_server.shutdown()

    by_check: dict[str, list[tuple[str, str, int]]] = {}
    for method, path, rng, n in RangeCORSHandler.requests:
        tag = path.partition("?c=")[2] or "(untagged)"
        by_check.setdefault(tag, []).append((method, rng, n))
    size = (DIST / "cross_origin" / "cpt.parquet").stat().st_size
    print(f"\nParquet server, file {size} bytes:")
    for tag, reqs in by_check.items():
        methods = ", ".join(sorted({m for m, _, _ in reqs}))
        ranged = sum(1 for _, r, _ in reqs if r)
        total = sum(n for _, _, n in reqs)
        print(f"  {tag:16} {len(reqs):3} requests ({methods}), {ranged} with Range, {total} bytes")

    interesting = [c for c in console if any(
        k in c.lower() for k in ("[probe]", "obstore", "error", "panic", "wasm", "micropip", "runner")
    )]
    print("\n".join(interesting[-80:]))
    if rows is None:
        sys.exit("no probe result")
    for r in rows:
        print(f"{r['status']:5} {r['seconds']:7.2f}s  {r['name']}: {r['detail']}")


if __name__ == "__main__":
    main()
