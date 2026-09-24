"""Kedro node that runs a whole marimo notebook with `app.run(defs=...)`.

Built for comparison with the function nodes in `pipeline_registry.py`.
"""

from pathlib import Path
from types import SimpleNamespace

import pandas as pd


def run_clean_notebook(raw_path: str, area_ratio: float) -> pd.DataFrame:
    """Run every cell of `cpt_clean_mo.py` and return its `cleaned` definition.

    `params` must be overridden: without it the resolve cell sees mode
    "script" and calls `CliApp.run(Args)` on Kedro's own `sys.argv`. The
    override replaces only that cell; the notebook still reads its input from
    `raw_path` itself, so the Kedro catalog never sees the raw data.
    """
    from cpt_clean_mo import app

    params = SimpleNamespace(input=Path(raw_path), output=None, area_ratio=area_ratio)
    _outputs, defs = app.run(defs={"params": params})
    return defs["cleaned"]
