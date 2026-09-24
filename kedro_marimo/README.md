# Kedro nodes from marimo reusable functions

Experiment: can a Kedro pipeline use functions defined inside marimo notebooks as its nodes?

The design under test: each marimo notebook defines one process. Its pure logic lives in marimo reusable functions (`@app.function`, imports in `with app.setup:`), so `from cpt_clean_mo import clean_cpts` works from plain Python. The rest of the notebook (form, tables, CLI args, file I/O) makes it a CLI script, an app and an editable notebook. Kedro imports the functions, wraps them in `node(...)` and wires the notebooks together through its Data Catalog. The notebooks never import Kedro.

Short answer: it works, with three traps. Kedro's default `src/` layout cannot see notebooks at the project root. A function that marimo refuses to make reusable still imports, and it fails silently. Each notebook now has two dependency declarations, one used by `uv run` and one used by Kedro.

## Layout

```
kedro_marimo/
├── cpt_clean_mo.py          # notebook: clean_cpts(raw) -> cleaned
├── cpt_classify_mo.py       # notebook: classify_cpts(cleaned), summarize_layers(classified)
├── cpt_pipeline/            # Kedro package (settings, registry, whole-notebook node)
├── conf/base/               # catalog.yml, parameters.yml
├── data/01_raw/cpts.csv     # synthetic input, 3 CPTs, 362 rows
├── make_raw_cpts.py         # regenerates the input CSV (fixed seed)
├── probes/                  # scripts behind the findings below
├── tests/                   # pytest, imports the notebook functions directly
└── pyproject.toml, uv.lock  # the Kedro project environment
```

Data flow (`kedro run`):

```
raw_cpts (CSV) -> clean_cpts -> cpts_clean (Parquet) -> classify_cpts -> cpts_classified (Parquet)
    -> summarize_layers -> cpt_layers (CSV)
```

## How to run

From `kedro_marimo/`:

```bash
uv sync                                   # project env: Kedro, marimo, pandas, pytest
uv run kedro run                          # whole pipeline
uv run kedro run --to-nodes=clean_cpts    # only the clean step
uv run kedro run --from-nodes=classify_cpts
uv run kedro run --pipeline app_run       # the whole-notebook node, for comparison
uv run pytest

# Each notebook on its own (own PEP 723 environment, no Kedro):
uv run cpt_clean_mo.py --input data/01_raw/cpts.csv --output data/02_intermediate/cpts_clean.parquet
uv run cpt_classify_mo.py --input data/02_intermediate/cpts_clean.parquet --output_layers layers.csv
uv run cpt_clean_mo.py --help

# As notebook or app (project env):
uv run marimo edit cpt_clean_mo.py
uv run marimo run cpt_classify_mo.py

# Graph view without adding kedro-viz to the project:
uv run --with kedro-viz kedro viz build   # static site in build/
uv run --with kedro-viz kedro viz run     # local server
```

## Decisions

- **Notebook conventions.** The notebooks follow the vault's `Scripts/_Scripts.md`: `<name>_mo.py`, PEP 723 header, an `Args(BaseSettings)` cell, a `ui_args` form, a resolve cell with `CliApp.run(Args)` in script mode, and `do_work(params)`. Docstrings follow marimo's style. The vault-only parts are left out: the commit guard, the Obsidian reload and `--apply`. This is repo code, not vault code, and output files are the effect, so a dry-run flag adds nothing. Without `--output` a notebook only previews.
- **Reusable functions take DataFrames, not paths.** `clean_cpts`, `classify_cpts` and `summarize_layers` do no I/O, so Kedro's catalog can own the I/O. `do_work(params)` does the file I/O for CLI and UI mode and is not used by Kedro.
- **`source_dir = "."`** in `[tool.kedro]`, with the `cpt_pipeline/` package next to the notebooks. See finding 4.
- **Hand-written Kedro project**, not `kedro new`: `pyproject.toml` `[tool.kedro]`, `cpt_pipeline/{__init__,settings,pipeline_registry}.py`, `conf/base/`. The mandatory keys (`package_name`, `project_name`, `kedro_init_version`) and the `source_dir` default (`"src"`) come from `kedro/framework/startup.py` in Kedro 1.6.0. The docs page on minimal projects returned 404 when I checked.
- **Manual pipeline registry**, not `find_pipelines()`. See finding 4.
- **Telemetry off.** Kedro 1.6.0 installs `kedro-telemetry` 0.9.0, which treats a missing answer as consent. `.telemetry` contains `consent: false`, the opt-out that the plugin's own message describes.
- **Synthetic data.** `make_raw_cpts.py` writes 3 CPTs through sand, clay, peat and dense sand, and adds 3 negative `qc`, 2 missing `fs`, 1 missing `u2` and 2 duplicate rows. It is a plain PEP 723 script, not a marimo notebook, because it is test-fixture generation, not a process step.
- **Classification.** Robertson (2010) non-normalized SBT index `Isbt = sqrt((3.47 - log10(qt/pa))^2 + (log10(Rf) + 1.22)^2)` with the Ic zone bounds 1.31/2.05/2.60/2.95/3.60 (zones 7 to 2). `summarize_layers` absorbs layers thinner than `min_layer_thickness` (0.3 m, a Kedro parameter) into their neighbor.

## Versions

Python 3.13.15, uv 0.12.18, marimo 0.25.0, Kedro 1.6.0, kedro-datasets 9.6.0, kedro-telemetry 0.9.0, kedro-viz 12.4.0 (via `--with`, not locked), pandas 3.0.6, pyarrow 25.0.1, pydantic 2.13.5, pydantic-settings 2.15.0, pytest 9.1.1. Linux, 2026-09-24.

Sources checked: [marimo reusable functions](https://docs.marimo.io/guides/reusing_functions/), [marimo App API](https://docs.marimo.io/api/app/), [Kedro pipeline registry](https://docs.kedro.org/en/stable/build/pipeline_registry/), [uv scripts guide](https://docs.astral.sh/uv/guides/scripts/), plus the installed source files named below. Where the docs are silent (import side effects, what happens on failure), the findings come from the source and the probes.

## FINDINGS

### 1. Does marimo serialize the functions as importable top-level functions?

**Yes, if the function only refers to setup-cell names and other reusable functions. Otherwise marimo silently saves it as a regular cell, and the import still succeeds but gives you the wrong object.**

`cpt_clean_mo.py` and `cpt_classify_mo.py` contain `@app.function def clean_cpts(...)` and so on, and `uv run marimo check --fix` leaves both files byte-identical, so marimo agrees with that serialization. The import works and gives a plain function:

```
$ uv run python probes/import_probe.py
clean_cpts is a <class 'function'>
```

Source: `marimo/_ast/cell_manager.py`, `cell_decorator`: "Top level functions are exposed as the function itself." `@app.function` returns the original function object and adds no wrapper.

What makes marimo refuse, from `probes/serialization_probe.py`. It feeds cells to the codegen that the editor calls on save (`marimo._ast.codegen.generate_filecontents`, a private API) and prints the hint the editor shows in the cell's corner marker:

```
      threshold_cell: Cell must contain exactly one function definition
     uses_setup_only: Valid
  uses_cell_variable: This function depends on variables defined by other cells:  {'threshold'}  To make this function importable from other Python modules, move these variables to the setup cell.
       calls_demoted: Function contains references to variables {'uses_cell_variable'} which were unable to become reusable.
         calls_valid: Valid
             private: Definitions starting with `_` are local to a cell.
            two_defs: Cell must contain exactly one function definition
  def_plus_statement: Cell must contain exactly one function definition
     create_pipeline: Valid
    trailing_comment: Cell cannot contain non-indented trailing comments.
```

Demotion spreads: a function that calls a demoted function is demoted too (`calls_demoted`).

**The fallback is silent and dangerous.** A refused function is saved as `@app.cell def uses_cell_variable(threshold): ...`. The module attribute of that name is then a `marimo._ast.cell.Cell`, not your function:

```
uses_setup_only -> builtins.function
uses_cell_variable -> marimo._ast.cell.Cell
```

Calling that `Cell` with a DataFrame raises nothing. The DataFrame binds to the cell's first ref (`threshold`), the cell runs, and the call returns `None`. Kedro accepts the `Cell` as a node function too, and fails only when it saves the output:

```
node.run -> {'b': None}
DatasetError: b: Saving 'None' to a 'Dataset' is not allowed
```

If the demoted cell is anonymous (`def _(...)`, what `marimo check --fix` writes), the name is gone from the module and the import fails with `AttributeError: module 'bad_mo' has no attribute 'do_work'`. I reproduced this by hand-writing `@app.function` on a function that uses `mo` from a regular cell. `marimo check` exited 0 on that file, and `marimo check --fix` rewrote it into `@app.cell def _(mo):` without a warning.

`marimo convert` of a py:percent script (with `--with jupytext`) creates no setup cell. Its imports land in a regular cell, so every converted function that uses `pd` came out as `@app.cell`. Reusable functions need a hand-made setup cell.

Guard: `tests/test_notebook_functions.py::test_node_functions_are_plain_functions` asserts `inspect.isfunction(...)` for every node function.

### 2. Does importing the notebook have side effects?

**It runs the `with app.setup:` block and registers the cells, but runs no cell. marimo must be installed. It adds about 0.35 s over importing pandas.**

```
$ uv run python probes/import_probe.py
import took 0.60 s, 1254 new modules
marimo modules loaded: 496
pandas loaded: True | kedro loaded: False
pydantic_settings loaded: False
module-level names: ['Path', 'RAW_COLUMNS', '_', 'app', 'clean_cpts', 'do_work', 'marimo', 'pd']
cells registered on app: 11
output file written by import: False
```

For comparison, `import pandas` alone takes 0.26 s and `import marimo` alone 0.33 s. `pydantic_settings` is imported in a regular cell, so it does not load at import time, and the file-writing `do_work` cell does not run. Setup-block names (`pd`, `Path`, `RAW_COLUMNS`) become module attributes. Without marimo installed:

```
$ uv run --isolated --no-project --with pandas --with pyarrow python -c "from cpt_clean_mo import clean_cpts"
ModuleNotFoundError: No module named 'marimo'
```

One more import-time detail from `cell_manager.py`: when `PYTEST_VERSION` is set, marimo registers cells in pytest-rewrite mode. It made no difference to these tests, because `@app.function` still returns the raw function.

### 3. `kedro run`, partial runs, kedro-viz

**All work.**

```
$ uv run kedro run
INFO Running node: clean_cpts: clean_cpts([raw_cpts;params:clean.area_ratio]) -> [cpts_clean]
INFO Running node: classify_cpts: classify_cpts([cpts_clean]) -> [cpts_classified]
INFO Running node: summarize_layers: summarize_layers([cpts_classified;params:classify.min_layer_thickness]) -> [cpt_layers]
INFO Pipeline execution completed successfully in 0.1 sec.
```

That is 1.26 s wall for the whole command. `data/08_reporting/cpt_layers.csv` is identical (`diff`) to the output of running the two notebooks as CLI scripts: 4 layers per CPT, sand / clay / peat / sand.

```
$ uv run kedro run --to-nodes=clean_cpts
INFO Running node: clean_cpts: ...   Completed 1 out of 1 tasks
$ uv run kedro run --from-nodes=classify_cpts
INFO Running node: classify_cpts: ...   INFO Running node: summarize_layers: ...   Completed 2 out of 2 tasks
```

With `data/02_intermediate/cpts_clean.parquet` deleted, `--from-nodes=classify_cpts` fails with `DatasetError ... FileNotFoundError: [Errno 2] No such file or directory: '.../cpts_clean.parquet'`. Kedro does not rebuild missing upstream data or track staleness. You choose the slice yourself.

`uv run --with kedro-viz kedro viz build` installed cleanly (81 packages, kedro-viz 12.4.0) and wrote a static site to `build/` (git-ignored, deleted afterwards, no server left running). `build/api/main` holds 3 task nodes, 4 datasets, 2 parameters, 8 edges and pipelines `__default__` and `cpt`. The node source links point into the notebooks (`kedro_marimo/cpt_clean_mo.py`, code starting `@app.function`), so viz shows the notebook code. It warned `Run events file .viz/kedro_pipeline_events.json not found` and printed a FastAPI deprecation warning. Neither mattered.

### 4. Where Kedro and the notebook conventions clash

**src/ layout.** With Kedro's default `source_dir = "src"` and the notebooks at the project root, `kedro run` fails:

```
❱  3 from cpt_classify_mo import classify_cpts, summarize_layers
ModuleNotFoundError: No module named 'cpt_classify_mo'
```

`bootstrap_project()` puts only `source_dir` on `sys.path` (`kedro/framework/startup.py`, `_add_src_to_path`), and the `kedro` entry point does not add the working directory. The fix is `source_dir = "."`, which Kedro accepts: it only checks that the path exists and is inside the project. With it, the Kedro package sits next to the notebooks and `conf/`. The other options are worse. Moving the notebooks into `src/` hides them from people who want to `uv run` them. Packaging the notebooks as installed modules adds a build step to single-file scripts. pytest needs the same fix: `pythonpath = ["."]` in `[tool.pytest.ini_options]`.

**`find_pipelines()` vs manual registry.** `find_pipelines()` only imports `<package>.pipeline` and `<package>.pipelines.<dir>` subpackages that expose `create_pipeline()` (`kedro/framework/project/__init__.py`; the [docs](https://docs.kedro.org/en/stable/build/pipeline_registry/) say the same). Single-file notebooks at the root are never found. It does work with a one-line shim package per notebook, `cpt_pipeline/pipelines/clean/__init__.py` = `from cpt_clean_mo import create_pipeline`, if the notebook defines `create_pipeline` (see 5):

```
$ bash probes/create_pipeline_in_notebook.sh
== kedro registry list
- __default__
- clean
== kedro run --pipeline clean
INFO Running node: clean_cpts: clean_cpts([raw_cpts;params:clean.area_ratio]) -> [cpts_clean]
INFO Pipeline execution completed successfully in 0.0 sec.
```

I kept the manual registry. It is one file, it keeps Kedro out of the notebooks, and wiring across notebooks (dataset names) lives in one place.

**PEP 723 vs pyproject.toml.** Neither one wins. Each command uses a different one:

| Command | Environment used |
|---|---|
| `uv run cpt_clean_mo.py ...` | PEP 723 header, own cached env (`~/.cache/uv/environments-v2/cpt-clean-mo-.../bin/python`, 36 packages, no Kedro) |
| `uv run kedro run`, `uv run pytest` | `pyproject.toml` / `uv.lock` (`.venv`) |
| `uv run marimo edit` / `marimo run` | `pyproject.toml` (`.venv`) |
| `marimo edit --sandbox` | PEP 723 (not tested here) |

The uv docs say it directly: "When using inline script metadata, even if `uv run` is used in a project, the project's dependencies will be ignored." So `uv run nb_mo.py` still works inside the Kedro project, but the same function runs against two dependency sets: PEP 723 lower bounds resolved fresh, and `uv.lock` pinned. They can drift, and a dependency added only to a notebook's PEP 723 header gives `ModuleNotFoundError` under `kedro run`. Every notebook dependency must also be in `pyproject.toml`. Nothing checks this for you.

`marimo edit` served the notebook (`GET /` 200, `/health` `{"status":"healthy"}`) and `marimo run cpt_classify_mo.py` served (200). I did not drive the form in a browser. `marimo export html cpt_clean_mo.py` ran every cell in non-script mode without errors and stopped at "Submit the form to run.", which is the intended UI branch.

### 5. Can `create_pipeline()` live in the notebook as a reusable function? Is that a good idea?

**It can. I would not do it.**

With the Kedro import inside the function body, marimo keeps it reusable (`@app.function def create_pipeline(**kwargs):`), `marimo check` passes, `find_pipelines()` finds it through the shim, `kedro run --pipeline clean` works, and `uv run cpt_clean_mo.py` still runs without Kedro. Calling `create_pipeline()` without Kedro installed raises `ModuleNotFoundError: No module named 'kedro'`, as you would expect.

With the Kedro import in the setup cell (where marimo wants imports), the notebook's standalone CLI breaks, because the PEP 723 env has no Kedro:

```
== setup-cell import: uv run cpt_clean_mo.py (PEP 723 env, no kedro)
ModuleNotFoundError: No module named 'kedro'
```

Why not: it breaks the premise that the notebook does not know about Kedro. Dataset names (`raw_cpts`, `cpts_clean`) are catalog vocabulary of one project, so the notebook stops being reusable across projects. It forces either a lazy import, which marimo's editor will not help you keep, or Kedro in every notebook's PEP 723 header. It also still needs a shim package per notebook for autodiscovery. A registry in the Kedro package does the same job without those costs.

### 6. Whole notebook as a node via `app.run(defs=...)`

Built as `cpt_pipeline/notebook_nodes.py::run_clean_notebook`, registered as pipeline `app_run`. The output is identical to the function node (`pd.testing.assert_frame_equal`, 355 x 7):

```
$ uv run kedro run --pipeline app_run
INFO Running node: run_clean_notebook: run_clean_notebook([params:raw_cpts_path;params:clean.area_ratio]) -> [cpts_clean_app_run]
INFO Pipeline execution completed successfully in 0.1 sec.
```

Problems hit on the way, in order:

1. **`mo.app_meta().mode` is `"script"` under `app.run()`** (`probes/mode_probe_mo.py`). This answers an open question in the research note: a commit guard gated on script mode would fire when a notebook is run from another process.
2. **So the resolve cell calls `CliApp.run(Args)` on Kedro's `sys.argv`** unless `params` is overridden. Simulated with `sys.argv = ["kedro", "run"]`: `kedro: error: unrecognized arguments: run`, then exit status 2, which kills the host process.
3. **Overriding one cell means supplying every global it defines.** The first run failed with `IncompleteRefsError: When providing refs that override cell definitions, you must provide all definitions from those cells. Missing: ['e']`. The error-printing loop variable `e` in the resolve cell was a cell global. I fixed it by renaming it to `_e` (cell-local). Any refactor of that cell can break the node again, and only at run time.

Differences from function nodes:

| | Function nodes | `app.run` node |
|---|---|---|
| I/O | Kedro catalog | The notebook reads its own file. The raw path is passed as a parameter, so `raw_cpts` in the catalog is bypassed and lineage is lost |
| Granularity in viz and `--from-nodes` | One node per function | One opaque node per notebook |
| What runs | Only the function | Every cell, including the form and table cells |
| Cost per call | 4.4 ms (`read_csv` + `clean_cpts`) | 29 ms |
| Coupling | Function signature | Cell global names (`params`, `cleaned`) as strings, plus the resolve cell's exact defs |
| Testability | Import and call | Needs a file on disk |

The `app.run` node is useful as a smoke test that the notebook as authored still produces the same result (`test_app_run_node_matches_function_node`). As the production wiring it is worse on every row.

### 7. Unit tests

`tests/test_notebook_functions.py` imports from `cpt_clean_mo` and `cpt_classify_mo` directly. It checks that the node functions are plain functions (the guard from finding 1), cleaning rules, `qt`/`Rf`, SBT zones for textbook values, `Isbt` against the formula, thin-layer absorption, the full chain on the synthetic data (zones `[6, 3, 2, 6]` per CPT), that the registry's nodes are the notebook functions, and that the `app.run` node equals the function path.

```
$ uv run pytest -v
...
tests/test_notebook_functions.py::test_app_run_node_matches_function_node PASSED [100%]
============================== 15 passed in 0.88s ==============================
```

The first run had 1 failure: my own test case `(qt=20, Rf=0.4) -> zone 7` was wrong (Isbt is 1.43, zone 6). I replaced it with `(40, 0.3)`, Isbt 1.12.

## What did not work or was not tested

- Kedro's default `src/` layout with root notebooks: `ModuleNotFoundError` (finding 4).
- `marimo convert` of a py:percent script without `jupytext`: "Converting py:percent format requires jupytext". With it, no setup cell is made, so no functions become reusable.
- `marimo check` does not flag a hand-written `@app.function` that marimo would demote, and `--fix` demotes it silently.
- Not tested: `marimo edit --sandbox`, form submission in a real browser, Kedro's `ParallelRunner` (which re-imports the package in worker processes), Windows.

## Verdict

Kedro can use marimo reusable functions as nodes, and the notebook stays Kedro-free, runnable and editable. The costs are `source_dir = "."`, a manual registry, dependencies declared twice, and a silent-demotion failure mode that you have to guard with a test. What Kedro adds over the research note's "runner notebook plus subprocesses" is catalog-managed I/O, `--from-nodes`/`--to-nodes` and a graph view. It does not add staleness tracking or scheduling. For two notebooks that is not worth a Kedro project. The pattern itself (pure `@app.function` logic, I/O at the edges, tests importing the notebook) is worth keeping with or without Kedro.
