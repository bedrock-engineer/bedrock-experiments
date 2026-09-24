"""Measure what `import cpt_clean_mo` does besides defining functions.

Run from the project root: `uv run python probes/import_probe.py`
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
before = set(sys.modules)

t0 = time.perf_counter()
import cpt_clean_mo  # noqa: E402

elapsed = time.perf_counter() - t0
new = set(sys.modules) - before

print(f"import took {elapsed:.2f} s, {len(new)} new modules")
print("marimo modules loaded:", sum(m.split(".")[0] == "marimo" for m in new))
print("pandas loaded:", "pandas" in new, "| kedro loaded:", "kedro" in new)
print("pydantic_settings loaded:", "pydantic_settings" in new)
print("clean_cpts is a", type(cpt_clean_mo.clean_cpts))
print("module-level names:", sorted(n for n in vars(cpt_clean_mo) if not n.startswith("__")))
print("cells registered on app:", len(list(cpt_clean_mo.app._cell_manager.cell_ids())))
print("output file written by import:", Path("/tmp/km/import_probe.parquet").exists())
