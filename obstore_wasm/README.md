# obstore in WASM marimo notebooks

Experiment: does [obstore](https://github.com/developmentseed/obstore) work in a marimo notebook that runs in the browser (Pyodide)?

Why: the bedrock-geo tutorials should keep their example data on Cloudflare R2 and read it through an obstore store, as in marimo's [Drive storage](https://marimo.io/blog/drive-storage) post. The same tutorials should also run as WASM notebooks. obstore is a Rust extension, so it needs a wheel built for Pyodide.

A second notebook asks the follow-up: if not obstore, what does work for getting web data into a WASM notebook? fsspec, pandas, polars, DuckDB, geopandas and the plain HTTP clients, each tested in the browser. See [Part 2](#part-2-other-ways-to-read-web-data-in-wasm).

Short answer for obstore: **no.** There is no Pyodide wheel, and building one from source fails. The cause is not a missing build flag. obstore's HTTP stack (object_store, reqwest, hyper, tokio) only switches to the browser's `fetch` on `wasm32-unknown-unknown`. Pyodide is `wasm32-unknown-emscripten`, so those crates take the native socket path, which cannot compile there. Making it work means a fork with a fetch-based HTTP connector. Plain HTTPS reads through `pyodide.http.pyfetch` do work, including Range requests.

## Layout

```
obstore_wasm/
├── obstore_probe_mo.py       # notebook: obstore checks, result table + JSON
├── web_data_probe_mo.py      # notebook: fsspec, pandas, polars, DuckDB, geopandas, HTTP clients
├── run_wasm_probe.py         # export to html-wasm, serve, run in headless Chromium
├── build_pyodide_wheel.sh    # try to build an obstore wheel with pyodide-build
└── public/sample.txt         # same-origin file for the HTTPStore check
```

## How to run

From `obstore_wasm/`:

```bash
uv run obstore_probe_mo.py                       # native baseline, prints JSON
uv run --with playwright playwright install chromium
uv run run_wasm_probe.py                         # WASM: export, serve, run in Chromium
uv run web_data_probe_mo.py                      # part 2, native baseline
uv run run_wasm_probe.py --notebook web_data_probe_mo.py   # part 2 in Chromium
uv run run_wasm_probe.py --wheel path/to/obstore-*.whl   # offer a locally built wheel
./build_pyodide_wheel.sh                         # toolchains go into .build/ (git-ignored)
uv run marimo edit obstore_probe_mo.py           # interactive
```

On a headless machine without `libasound.so.2`, Chromium does not start. Without sudo: `apt-get download libasound2t64`, `dpkg-deb -x` it somewhere, and point `LD_LIBRARY_PATH` at its `usr/lib/x86_64-linux-gnu`.

## Checks

The notebook runs the same checks natively and in WASM. Remote reads go to `s3://cholmes/eurocrops/` on source.coop (`https://data.source.coop`), a public S3-compatible endpoint that sends `Access-Control-Allow-Origin: *`. That is the setup an R2 bucket with a public URL and a CORS policy would have. The range check reads the 7-byte `PMTiles` magic from a 1.9 GB file.

| Check | Native (Linux) | WASM (Chromium) |
|---|---|---|
| platform | Python 3.13.15 | Pyodide 314.0.0, Python 3.14.2 |
| `micropip.install("obstore")` | skip | **fail**: `Can't find a pure Python 3 wheel for 'obstore'` |
| `import obstore` | ok, 0.11.1 | fail, `ModuleNotFoundError` |
| `MemoryStore` sync and async | ok | fail (not installed) |
| `S3Store` async: GET 7311 bytes + range read | ok, 1.7 s | fail (not installed) |
| `HTTPStore` same origin | skip (no server) | fail (not installed) |
| `pyfetch` GET + `Range: bytes=0-6` | skip | **ok**: HTTP 200, 7311 bytes; HTTP 206, `b'PMTiles'`, 2.7 s |

## Versions

marimo 0.25.0 (its WASM export loads Pyodide 314.0.0 from jsDelivr), obstore 0.11.1 (latest on PyPI), Pyodide 314.0.7 (latest), pyodide-build with Emscripten 5.0.3 and Rust 1.93.0 (`pyodide config get rust_toolchain`), Playwright Chromium headless shell 153. Linux (homelab), 2026-10-01.

## FINDINGS

### 1. No wheel to install

PyPI has only the sdist for obstore 0.11.1 and no `pyemscripten`/`pyodide` wheel. The Pyodide distribution does not include obstore either: neither the 314.0.7 lock file (357 packages) nor the 0.29.5 one (379 packages) lists it. They do include `pyarrow`, `polars`, `duckdb` and `fsspec`. None of the 775 issues and PRs in `developmentseed/obstore` mention Pyodide, WASM or Emscripten, so nobody upstream is working on it.

In the browser, marimo cannot install it:

```
ValueError: Can't find a pure Python 3 wheel for 'obstore'.
```

### 2. Native baseline works

`uv run obstore_probe_mo.py` passes every check that applies natively, including the anonymous `S3Store` read from source.coop. So the test target and the notebook are sound, and the WASM failures come from the runtime.

### 3. Building a Pyodide wheel fails, and not because of a flag

`build_pyodide_wheel.sh` runs `pyodide build` on the unmodified 0.11.1 sdist. It fails after 13 s while compiling `mio`:

```
error: This wasm target is unsupported by mio. If using Tokio, disable the net feature.
error: could not compile `mio` (lib) due to 27 previous errors
```

`cargo tree -i mio --target wasm32-unknown-emscripten -e features` shows who pulls it in. object_store's `aws`/`azure`/`gcp`/`http` features use reqwest. reqwest uses hyper and hyper-util, which use tokio `net`, which uses mio. `pyo3-async-runtimes` with `tokio-runtime` and obstore's own `rt-multi-thread` add a threaded tokio runtime on top.

Both crates do have a browser backend, but they gate it on the wrong target for Pyodide:

- reqwest 0.13.4 uses `fetch` via wasm-bindgen only under `cfg(all(target_arch = "wasm32", any(target_os = "unknown", target_os = "none")))`.
- object_store 0.14.1 gates its wasm dependencies (`wasm-bindgen-futures`, `web-time`) on `target_os = "unknown"` too.

Pyodide extensions must be built for `wasm32-unknown-emscripten`, so both crates fall back to native sockets. TLS is a second problem: obstore picks rustls with `aws-lc-rs`, a C/assembly crypto library. In a browser, TLS belongs to `fetch`.

What a port would take: an object_store `HttpConnector` (the trait exists in `object_store::client::HttpConnector`) that calls JavaScript `fetch` through Pyodide, no reqwest, a single-threaded tokio runtime (or no tokio) hooked into Pyodide's event loop, and a decision about the sync API (`obs.get`), which would have to block on a `fetch` promise. That is a fork of obstore and pyo3-object_store, not a build recipe. I did not try it.

### 4. The fallback works

The browser reads the same public objects over plain HTTPS with `pyodide.http.pyfetch`, including a `Range` request (HTTP 206). That is enough for the tutorials: download small files whole, and use range reads for PMTiles or Parquet. Pyodide also ships `fsspec`. Two things to set up on the R2 side: a public URL (r2.dev or a custom domain), and a CORS policy that allows `GET` and `HEAD` and exposes `Content-Range`/`Content-Length`/`ETag` to the origin that serves the notebooks. I did not test against R2 itself.

## Not tested

- Firefox and Safari. Only Chromium.
- R2 itself, with its CORS rules. source.coop stood in.
- `fsspec` `HTTPFileSystem` in Pyodide as an obstore-like API on top of `fetch`.
- A MemoryStore-only obstore build without object_store's cloud features. Even if it compiled, it would not answer the R2 question.

## Verdict

obstore does not run in WASM marimo notebooks, and it will not without an upstream port. For the tutorials, use one small data-access helper. Natively it uses obstore against R2. In Pyodide (`sys.platform == "emscripten"`) it uses `pyfetch` against R2's public URL. Both paths point at the same objects, so the data lives in one place.

## Part 2: other ways to read web data in WASM

`web_data_probe_mo.py` tries every common way to read a URL, natively and in the same Chromium setup (marimo 0.25.0, Pyodide 314.0.0). All URLs are cross-origin. The CSV (`WH_collar_all.csv`, 5056 bytes) and GeoPackage (`wekahills_gi.gpkg`, 1.7 MB) are bedrock-ge tutorial data on raw.githubusercontent.com, which sends `Access-Control-Allow-Origin: *` and supports Range. The Parquet file is `WH_cpt_Alluvial.csv` written as 952,310 bytes in 10 row groups, served by `run_wasm_probe.py` from a second local port with CORS and Range. That server logs every request, so the runner shows how many bytes each reader pulled.

Natively, every check passes. In Chromium:

| Way in | WASM | Notes |
|---|---|---|
| `pyodide.http.pyfetch` (async) | ok | Browser `fetch`. The base for everything else |
| `pyodide.http.open_url` (sync) | ok | Sync XHR, text only |
| `urllib.request.urlopen` | ok | marimo calls `pyodide_http.patch_all()` at startup, so this is sync XHR |
| `requests.get`, also with `Range` | ok | Same patch. Range gave HTTP 206 |
| `aiohttp.ClientSession` | **fail** | `Cannot connect to host ... [Name does not resolve]`: needs sockets |
| `pandas.read_csv(url)`, `read_parquet(url)` | ok | Downloads the whole file (952,310 bytes, no Range) |
| `polars.read_csv(url)`, `read_parquet(url)` | ok | Whole file, no Range |
| DuckDB `read_csv(url)`, `read_parquet(url)` | ok | Whole file, no Range. Even `select max(Depth)` pulls everything |
| fsspec `https`, default filesystem | **breaks the kernel** | See finding 6 |
| fsspec `http_sync` + `open` | ok, with a trap | Range reads work. Gzipped responses come back truncated, see finding 5 |
| fsspec `http_sync` + pyarrow `ParquetFile.read_row_group(0, columns=["Depth"])` | ok | 3 requests (HEAD + 2 ranges), **137,292 of 952,310 bytes** |
| `geopandas.read_file(url)` | fail | fiona's `/vsicurl/` has no network |
| `geopandas.read_file(local .gpkg)` | **crashes Pyodide** | See finding 7 |
| `read_gpkg_layer` (sqlite3 + shapely) | ok | The notebook's workaround, 0.5 s |

### 5. fsspec `http_sync` truncates gzipped responses

`import fsspec.implementations.http_sync` re-registers `http` and `https` with a synchronous filesystem built for Pyodide (sync XHR). Range reads work, and pyarrow reads one row group of one column with 137 KB of the 952 KB file.

But `fsspec.open(CSV_URL).read()` returned 2016 bytes of a 5056-byte CSV, without an error. raw.githubusercontent.com sends `Content-Encoding: gzip` with `Content-Length: 2016`, the compressed size. fsspec takes `Content-Length` as the file size, the browser hands it the decompressed body, and fsspec stops reading at 2016 bytes. Browser code cannot set `Accept-Encoding`, so this cannot be turned off from Python. Binary formats (Parquet, GeoPackage, PMTiles) are usually served uncompressed and are not affected. Text files (CSV, GeoJSON, JSON) on a CDN that compresses are. Cloudflare compresses text types on proxied domains, so this is a risk for CSV on R2 behind a custom domain. Not tested on R2.

### 6. fsspec's default `https` filesystem breaks marimo's WASM kernel

fsspec's default HTTP filesystem is async and runs on aiohttp. `fsspec.filesystem("https")` alone, without reading anything, left marimo's event loop broken. The cell itself finished, but then the console showed `RuntimeError: loop <pyodide.webloop.WebLoop ...> is not the running loop` and `Cannot enter into task ... AsyncioThread._run_in_context()` (marimo's WASM threading shim in `marimo/_runtime/_wasm/_concurrency/_threading.py`), and no later cell finished. With the read attempt included, the read itself failed with `NotImplementedError: Calling sync() from within a running loop`, and in one run the next cell (`pandas.read_csv`) hung. The probe skips these checks unless `TRY_AIOHTTP_FSSPEC = True`. Without them, the full result rendered and no loop errors were logged.

So in a WASM notebook, import `fsspec.implementations.http_sync` before anything creates an `https` filesystem, and be careful with libraries that create one internally.

### 7. fiona crashes Pyodide on any GeoPackage

Pyodide's geopandas uses fiona (1.9.5 with GDAL 3.8.3 in Pyodide 314.0.0, 1.10.1 in 314.0.7), not pyogrio. GeoJSON reads fine. Any GeoPackage access, reading (`fiona.listlayers`, `gpd.read_file`) or writing (`to_file(driver="GPKG")`), ends the whole runtime:

```
Pyodide has suffered a fatal error. Please report this to the Pyodide maintainers.
RuntimeError: null function or function signature mismatch
```

Reproduced in Node with Pyodide 314.0.0 and 314.0.7, and in Chromium. It is a WASM-level trap, so `try/except` cannot catch it, and the marimo kernel dies with it.

The workaround is in the notebook as the reusable function `read_gpkg_layer(path, layer)`. A GeoPackage is a SQLite file, so it reads the table with the stdlib `sqlite3`, strips the GeoPackage geometry header, decodes the WKB with `shapely.from_wkb`, and takes the CRS definition from `gpkg_spatial_ref_sys`. On the Weka Hills file it reads `Location` as 99 3D LineStrings in `NZGD2000 / New Zealand Transverse Mercator 2000 + NZVD2016 height`. It ignores extended geometry types and does not use the R-tree index, which is fine for tutorial-sized layers.

### Part 2 verdict

For tutorial data on R2:

- **Small files (CSV, GeoJSON, a GeoPackage of a few MB):** download whole. `pandas.read_csv(url)`, `polars.read_csv(url)`, `requests.get(url)` and `pyfetch` all work, thanks to marimo's `pyodide_http` patch. These are the same calls that work natively, so most notebook code needs no WASM branch at all.
- **GeoPackages:** download, then `read_gpkg_layer` instead of `gpd.read_file`, until Pyodide's fiona is fixed.
- **Large Parquet where you want a subset:** fsspec `http_sync` + pyarrow is the only tested path that reads byte ranges in the browser. pandas, polars and DuckDB download the whole file.
- **Avoid:** aiohttp, fsspec's default `https` filesystem, and anything built on them (s3fs, gcsfs, adlfs), plus `gpd.read_file` on a GeoPackage.

Not tested in part 2: R2 itself, Cloudflare's compression on R2 custom domains, `httpx`, zarr/xarray over HTTP, DuckDB's `httpfs` extension (DuckDB read the URLs without loading it), and browsers other than Chromium.
