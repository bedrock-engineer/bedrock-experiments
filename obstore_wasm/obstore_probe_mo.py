# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.0",
#     "obstore>=0.11.1",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")

with app.setup:
    import asyncio
    import json
    import sys
    import time
    import traceback

    IS_WASM = sys.platform == "emscripten"
    TIMEOUT_S = 30

    # Public S3-compatible endpoint with `Access-Control-Allow-Origin: *`.
    S3_ENDPOINT = "https://data.source.coop"
    S3_BUCKET = "cholmes"
    S3_SMALL_KEY = "eurocrops/README.md"  # 7311 bytes
    S3_RANGE_KEY = "eurocrops/eurocrops-all.pmtiles"  # 1.9 GB, read 7 bytes


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Does obstore work in a WASM marimo notebook?

    Each cell below runs one check and returns a row: name, status
    (`ok`, `fail`, `skip`) and a detail. The last cell shows the table and a
    JSON block with id `probe-result`, which `run_wasm_probe.py` reads from
    the browser.

    In WASM the notebook first tries `micropip.install("obstore")` (PyPI), then
    every wheel listed in `public/wheels.txt` next to the notebook. Natively,
    obstore comes from the PEP 723 header.
    """)
    return


@app.function
async def run_check(name, fn):
    """Run one check and turn its outcome into a result row.

    Args:
        name: Short check name, shown in the table.
        fn: Zero-argument callable returning a detail string, or a coroutine
            function. Raising `SkipCheck` marks the check as skipped.

    Returns:
        A dict with `name`, `status`, `detail` and `seconds`.
    """
    t0 = time.perf_counter()
    try:
        out = fn()
        if asyncio.iscoroutine(out):
            out = await asyncio.wait_for(out, TIMEOUT_S)
        status, detail = "ok", str(out)
    except SkipCheck as e:
        status, detail = "skip", str(e)
    except BaseException as e:  # noqa: BLE001, a probe must report everything
        status = "fail"
        detail = "".join(traceback.format_exception_only(e)).strip()[-1500:]
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "seconds": round(time.perf_counter() - t0, 3),
    }


@app.class_definition
class SkipCheck(Exception):
    """Raised by a check that does not apply in this runtime."""


@app.cell
def _(mo):
    notebook_location = str(mo.notebook_location())
    http_base = (
        notebook_location.rstrip("/") + "/public"
        if notebook_location.startswith("http")
        else None
    )
    return (http_base,)


@app.cell
async def _():
    async def _platform():
        if not IS_WASM:
            return f"native {sys.platform}, Python {sys.version.split()[0]}"
        import pyodide

        return f"pyodide {pyodide.__version__}, Python {sys.version.split()[0]}"

    row_platform = await run_check("platform", _platform)
    return (row_platform,)


@app.cell
async def _():
    async def _pypi_install():
        if not IS_WASM:
            raise SkipCheck("native: obstore comes from the PEP 723 header")
        import micropip

        await micropip.install("obstore")
        return "installed from PyPI"

    row_install_pypi = await run_check("micropip.install('obstore')", _pypi_install)
    return (row_install_pypi,)


@app.cell
async def _(http_base, row_install_pypi):
    async def _wheel_install():
        if not IS_WASM:
            raise SkipCheck("native")
        if row_install_pypi["status"] == "ok":
            raise SkipCheck("PyPI install already worked")
        from pyodide.http import pyfetch

        resp = await pyfetch(f"{http_base}/wheels.txt")
        if not resp.ok:
            raise SkipCheck(f"no public/wheels.txt (HTTP {resp.status})")
        names = [n.strip() for n in (await resp.string()).splitlines() if n.strip()]
        if not names:
            raise SkipCheck("public/wheels.txt is empty")
        import micropip

        urls = [f"{http_base}/wheels/{n}" for n in names]
        await micropip.install(urls, deps=False)
        return "installed " + ", ".join(names)

    row_install_wheel = await run_check("micropip.install(local wheel)", _wheel_install)
    return (row_install_wheel,)


@app.cell
async def _(row_install_pypi, row_install_wheel):
    async def _import():
        import obstore

        return f"obstore {obstore.__version__} from {obstore.__file__}"

    # Depend on both install rows so this runs after them.
    _ = (row_install_pypi, row_install_wheel)
    row_import = await run_check("import obstore", _import)
    return (row_import,)


@app.cell
async def _(row_import):
    def _memory_sync():
        import obstore as obs
        from obstore.store import MemoryStore

        store = MemoryStore()
        obs.put(store, "a.txt", b"hello")
        data = bytes(obs.get(store, "a.txt").bytes())
        listed = [m["path"] for m in obs.list(store).collect()]
        return f"get -> {data!r}, list -> {listed}"

    async def _memory_async():
        import obstore as obs
        from obstore.store import MemoryStore

        store = MemoryStore()
        await obs.put_async(store, "b.txt", b"world")
        resp = await obs.get_async(store, "b.txt")
        return f"get_async -> {bytes(await resp.bytes_async())!r}"

    _ = row_import
    row_memory_sync = await run_check("MemoryStore sync", _memory_sync)
    row_memory_async = await run_check("MemoryStore async", _memory_async)
    return row_memory_async, row_memory_sync


@app.cell
async def _(http_base, row_memory_async, row_memory_sync):
    async def _http_async():
        if http_base is None:
            raise SkipCheck("notebook is not served over HTTP")
        import obstore as obs
        from obstore.store import HTTPStore

        store = HTTPStore.from_url(http_base)
        resp = await obs.get_async(store, "sample.txt")
        return f"same-origin get_async -> {bytes(await resp.bytes_async())!r}"

    async def _s3_async():
        import obstore as obs
        from obstore.store import S3Store

        store = S3Store(
            S3_BUCKET,
            endpoint=S3_ENDPOINT,
            region="us-east-1",
            skip_signature=True,
        )
        resp = await obs.get_async(store, S3_SMALL_KEY)
        n = len(bytes(await resp.bytes_async()))
        head = bytes(await obs.get_range_async(store, S3_RANGE_KEY, start=0, length=7))
        return f"{S3_SMALL_KEY}: {n} bytes; pmtiles range 0-7 -> {head!r}"

    _ = (row_memory_sync, row_memory_async)
    row_http_async = await run_check("HTTPStore async (same origin)", _http_async)
    row_s3_async = await run_check("S3Store async (source.coop)", _s3_async)
    return row_http_async, row_s3_async


@app.cell
async def _():
    async def _pyfetch_fallback():
        # The fallback without obstore: plain HTTPS GET and Range requests
        # against the bucket's public URL, through the browser's fetch.
        if not IS_WASM:
            raise SkipCheck("native: pyodide.http only exists in Pyodide")
        from pyodide.http import pyfetch

        base = f"{S3_ENDPOINT}/{S3_BUCKET}"
        resp = await pyfetch(f"{base}/{S3_SMALL_KEY}")
        n = len(await resp.bytes())
        ranged = await pyfetch(
            f"{base}/{S3_RANGE_KEY}", headers={"Range": "bytes=0-6"}
        )
        head = await ranged.bytes()
        return (
            f"{S3_SMALL_KEY}: HTTP {resp.status}, {n} bytes; "
            f"range: HTTP {ranged.status} -> {head!r}"
        )

    row_pyfetch = await run_check("pyfetch GET + Range (fallback)", _pyfetch_fallback)
    return (row_pyfetch,)


@app.cell
async def _(http_base, row_http_async, row_s3_async):
    # Sync network calls go last: if they block the Pyodide worker, the
    # async results above are already on the page.
    def _http_sync():
        if http_base is None:
            raise SkipCheck("notebook is not served over HTTP")
        import obstore as obs
        from obstore.store import HTTPStore

        store = HTTPStore.from_url(http_base)
        return f"same-origin get -> {bytes(obs.get(store, 'sample.txt').bytes())!r}"

    _ = (row_http_async, row_s3_async)
    row_http_sync = await run_check("HTTPStore sync (same origin)", _http_sync)
    return (row_http_sync,)


@app.cell
def _(
    mo,
    row_http_async,
    row_http_sync,
    row_import,
    row_install_pypi,
    row_install_wheel,
    row_memory_async,
    row_memory_sync,
    row_platform,
    row_pyfetch,
    row_s3_async,
):
    rows = [
        row_platform,
        row_install_pypi,
        row_install_wheel,
        row_import,
        row_memory_sync,
        row_memory_async,
        row_http_async,
        row_s3_async,
        row_http_sync,
        row_pyfetch,
    ]
    if not IS_WASM:
        print(json.dumps(rows, indent=2))
    mo.vstack(
        [
            mo.ui.table(rows, selection=None, pagination=False),
            mo.Html(
                '<pre id="probe-result">'
                + mo.Html(json.dumps(rows)).text.replace("<", "&lt;")
                + "</pre>"
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
