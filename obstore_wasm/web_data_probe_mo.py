# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.0",
#     "aiohttp>=3.13",
#     "duckdb>=1.5",
#     "fsspec>=2026.3",
#     "geopandas>=1.1",
#     "pandas>=3.0",
#     "polars>=1.33",
#     "pyarrow>=22",
#     "requests>=2.33",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")

with app.setup:
    import asyncio
    import io
    import json
    import sys
    import time
    import traceback

    IS_WASM = sys.platform == "emscripten"
    TIMEOUT_S = 60
    # In WASM, creating fsspec's default (aiohttp) https filesystem leaves
    # marimo's event loop broken: later cells never finish. Off by default so
    # the rest of the probe can report; see README finding 6.
    TRY_AIOHTTP_FSSPEC = False
    # fiona's GeoPackage driver crashes Pyodide 314 ("null function or
    # function signature mismatch"), which kills the kernel. See finding 7.
    TRY_FIONA_GPKG = False

    # bedrock-ge tutorial data on GitHub: `Access-Control-Allow-Origin: *`,
    # `Accept-Ranges: bytes`.
    RAW = "https://raw.githubusercontent.com/bedrock-engineer/bedrock-ge/main/examples"
    CSV_URL = f"{RAW}/nz_weka_hills_leapfrog/WH_collar_all.csv"  # 5056 bytes
    GPKG_URL = f"{RAW}/nz_weka_hills_leapfrog/wekahills_gi.gpkg"  # 1.7 MB


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Getting web data into a WASM marimo notebook

    One cell per way of reading a URL. All URLs are cross-origin: the CSV and
    GeoPackage come from raw.githubusercontent.com, the Parquet file from a
    second local server with CORS and Range support (`run_wasm_probe.py`
    starts it and writes its address to `public/config.json`).

    Each check returns a row: name, status (`ok`, `fail`, `skip`), detail.
    The last cell shows them and a JSON block with id `probe-result`.
    """)
    return


@app.class_definition
class SkipCheck(Exception):
    """Raised by a check that does not apply in this runtime."""


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
    print(f"[probe] start {name}", file=sys.stderr)
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
        detail = "".join(traceback.format_exception_only(e)).strip()[-800:]
    row = {
        "name": name,
        "status": status,
        "detail": detail,
        "seconds": round(time.perf_counter() - t0, 3),
    }
    print(f"[probe] {status} {name}: {detail[:300]}", file=sys.stderr)
    return row


@app.function
def read_gpkg_layer(path, layer=None):
    """Read a GeoPackage feature layer with sqlite3 and shapely, without GDAL.

    Pyodide's fiona crashes on GeoPackages, so in WASM this is the way in.
    Handles the GeoPackage geometry header (no extended geometries) and takes
    the CRS from `gpkg_spatial_ref_sys.definition`.

    Args:
        path: Local path of the `.gpkg` file.
        layer: Table name of a feature layer. The first one if None.

    Returns:
        A GeoDataFrame with the layer's columns and geometry.
    """
    import sqlite3

    import geopandas as gpd
    import pandas as pd
    import shapely

    def _wkb(blob):
        envelope = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(blob[3] >> 1) & 0b111]
        return bytes(blob[8 + envelope :])

    with sqlite3.connect(path) as con:
        layers = con.execute(
            "select c.table_name, g.column_name, g.srs_id from gpkg_contents c "
            "join gpkg_geometry_columns g using (table_name) "
            "where c.data_type = 'features'"
        ).fetchall()
        table, geom_col, srs_id = next(
            (row for row in layers if layer in (None, row[0]))
        )
        (crs,) = con.execute(
            "select definition from gpkg_spatial_ref_sys where srs_id = ?",
            (srs_id,),
        ).fetchone()
        df = pd.read_sql(f'select * from "{table}"', con)
    geometry = shapely.from_wkb(df[geom_col].map(_wkb, na_action="ignore"))
    return gpd.GeoDataFrame(df.drop(columns=geom_col), geometry=geometry, crs=crs)


@app.cell
async def _(mo):
    async def _load_config():
        loc = str(mo.notebook_location())
        if not loc.startswith("http"):
            raise SkipCheck("not served over HTTP: no Parquet server")
        from pyodide.http import pyfetch

        resp = await pyfetch(loc.rstrip("/") + "/public/config.json")
        return json.loads(await resp.string())["parquet_url"]

    _row = await run_check("config", _load_config)
    parquet_url = _row["detail"] if _row["status"] == "ok" else None
    return (parquet_url,)


@app.cell
async def _():
    async def _patched():
        import urllib.request

        import requests

        return (
            f"urllib.request.urlopen from {urllib.request.urlopen.__module__}; "
            f"requests Session.request from {requests.Session.request.__module__}"
        )

    row_patched = await run_check("pyodide_http patch active?", _patched)
    return (row_patched,)


@app.cell
async def _(row_patched):
    async def _pyfetch():
        if not IS_WASM:
            raise SkipCheck("Pyodide only")
        from pyodide.http import pyfetch

        resp = await pyfetch(CSV_URL)
        return f"HTTP {resp.status}, {len(await resp.bytes())} bytes"

    def _open_url():
        if not IS_WASM:
            raise SkipCheck("Pyodide only")
        from pyodide.http import open_url

        return f"{len(open_url(CSV_URL).read())} chars"

    def _urllib():
        import urllib.request

        with urllib.request.urlopen(CSV_URL) as r:
            return f"{len(r.read())} bytes"

    def _requests():
        import requests

        r = requests.get(CSV_URL, timeout=30)
        rr = requests.get(GPKG_URL, headers={"Range": "bytes=0-15"}, timeout=30)
        return f"HTTP {r.status_code}, {len(r.content)} bytes; range HTTP {rr.status_code} -> {rr.content!r}"

    async def _aiohttp():
        import aiohttp

        async with aiohttp.ClientSession() as s:
            async with s.get(CSV_URL) as r:
                return f"HTTP {r.status}, {len(await r.read())} bytes"

    _ = row_patched
    row_pyfetch = await run_check("pyodide.http.pyfetch", _pyfetch)
    row_open_url = await run_check("pyodide.http.open_url", _open_url)
    row_urllib = await run_check("urllib.request.urlopen", _urllib)
    row_requests = await run_check("requests.get (+ Range)", _requests)
    row_aiohttp = await run_check("aiohttp.ClientSession", _aiohttp)
    rows_http = [row_pyfetch, row_open_url, row_urllib, row_requests, row_aiohttp]
    return (rows_http,)


@app.cell
async def _(parquet_url, rows_http):
    def _pandas_csv():
        import pandas as pd

        df = pd.read_csv(CSV_URL)
        return f"{df.shape}"

    def _pandas_parquet():
        if parquet_url is None:
            raise SkipCheck("no Parquet server")
        import pandas as pd

        return f"{pd.read_parquet(parquet_url + '?c=pandas').shape}"

    def _polars_csv():
        import polars as pl

        return f"{pl.read_csv(CSV_URL).shape}"

    def _polars_parquet():
        if parquet_url is None:
            raise SkipCheck("no Parquet server")
        import polars as pl

        return f"{pl.read_parquet(parquet_url + '?c=polars').shape}"

    def _duckdb():
        import duckdb

        n = duckdb.sql(f"select count(*) from read_csv('{CSV_URL}')").fetchone()[0]
        return f"{n} rows"

    def _duckdb_parquet():
        if parquet_url is None:
            raise SkipCheck("no Parquet server")
        import duckdb

        url = parquet_url + "?c=duckdb"
        n = duckdb.sql(f"select max(Depth) from read_parquet('{url}')").fetchone()[0]
        return f"max(Depth) = {n}"

    def _geopandas_url():
        if IS_WASM and not TRY_FIONA_GPKG:
            raise SkipCheck("fails: /vsicurl/ has no network in Pyodide (TRY_FIONA_GPKG)")
        import geopandas as gpd

        return f"{gpd.read_file(GPKG_URL).shape}"

    async def _download_gpkg():
        if IS_WASM:
            from pyodide.http import pyfetch

            data = await (await pyfetch(GPKG_URL)).bytes()
        else:
            import urllib.request

            data = urllib.request.urlopen(GPKG_URL).read()
        path = "/tmp/wekahills_gi.gpkg"
        with open(path, "wb") as f:
            f.write(data)
        return path

    async def _geopandas_file():
        if IS_WASM and not TRY_FIONA_GPKG:
            raise SkipCheck("crashes Pyodide: fiona GPKG driver (TRY_FIONA_GPKG)")
        import geopandas as gpd

        gdf = gpd.read_file(await _download_gpkg(), layer="Location")
        return f"Location: {gdf.shape}"

    async def _sqlite_gpkg():
        gdf = read_gpkg_layer(await _download_gpkg(), layer="Location")
        return f"Location: {gdf.shape}, {gdf.geom_type.iloc[0]}, CRS {gdf.crs.name}"

    _ = rows_http
    rows_libs = [
        await run_check("pandas.read_csv(url)", _pandas_csv),
        await run_check("pandas.read_parquet(url)", _pandas_parquet),
        await run_check("polars.read_csv(url)", _polars_csv),
        await run_check("polars.read_parquet(url)", _polars_parquet),
        await run_check("duckdb read_csv(url)", _duckdb),
        await run_check("duckdb read_parquet(url)", _duckdb_parquet),
        await run_check("geopandas.read_file(url)", _geopandas_url),
        await run_check("download -> geopandas.read_file", _geopandas_file),
        await run_check("download -> read_gpkg_layer (sqlite3)", _sqlite_gpkg),
    ]
    return (rows_libs,)


@app.cell
async def _(parquet_url, rows_libs):
    # Importing fsspec.implementations.http_sync re-registers "http" and
    # "https" globally, so this cell runs after the library checks.
    def _fs_checks():
        import fsspec
        import pyarrow.parquet as pq

        def info():
            fs = fsspec.filesystem("https")
            return f"fsspec {fsspec.__version__}: {type(fs).__module__}.{type(fs).__name__}"

        def cat():
            with fsspec.open(CSV_URL, "rb") as f:
                return f"{len(f.read())} bytes"

        def range_read():
            with fsspec.open(GPKG_URL, "rb", block_size=4096) as f:
                return f"size {f.size}, first 16 bytes {f.read(16)!r}"

        def parquet():
            if parquet_url is None:
                raise SkipCheck("no Parquet server")
            url = parquet_url + "?c=fsspec-pyarrow"
            with fsspec.open(url, "rb", block_size=64 * 1024) as f:
                pf = pq.ParquetFile(f)
                t = pf.read_row_group(0, columns=["Depth"])
                return (
                    f"{pf.metadata.num_rows} rows in {pf.metadata.num_row_groups} "
                    f"row groups; read 1 group, 1 column: {t.num_rows} rows; "
                    f"file {f.size} bytes"
                )

        return info, cat, range_read, parquet

    _info, _cat, _range, _parquet = _fs_checks()
    _ = rows_libs
    rows_fsspec = []
    if IS_WASM and TRY_AIOHTTP_FSSPEC:
        rows_fsspec.append(await run_check("fsspec https, default (aiohttp)", _info))
        rows_fsspec.append(await run_check("fsspec.open CSV, default", _cat))
    if IS_WASM:
        import fsspec.implementations.http_sync  # noqa: F401, registers https

    _sfx = ", http_sync" if IS_WASM else ", default"
    rows_fsspec += [
        await run_check("fsspec https filesystem" + _sfx, _info),
        await run_check("fsspec.open CSV" + _sfx, _cat),
        await run_check("fsspec.open GPKG range read" + _sfx, _range),
        await run_check("fsspec + pyarrow Parquet row group" + _sfx, _parquet),
    ]
    return (rows_fsspec,)


@app.cell
def _(mo, row_patched, rows_fsspec, rows_http, rows_libs):
    rows = [row_patched, *rows_http, *rows_fsspec, *rows_libs]
    if not IS_WASM:
        print(json.dumps(rows, indent=2))
    mo.vstack(
        [
            mo.ui.table(rows, selection=None, pagination=False),
            mo.Html(
                '<pre id="probe-result">'
                + json.dumps(rows).replace("&", "&amp;").replace("<", "&lt;")
                + "</pre>"
            ),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
