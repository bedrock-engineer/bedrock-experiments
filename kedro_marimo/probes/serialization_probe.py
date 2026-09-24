"""Show which cells marimo saves as `@app.function` and why others are demoted.

Feeds cell sources to the same codegen the editor calls on save
(`marimo._ast.codegen.generate_filecontents`, private API, marimo 0.25.0) and
prints the hint marimo attaches to every cell (the text the editor shows in
the cell's bottom-right marker).

Run: `uv run python probes/serialization_probe.py`
"""

from marimo._ast.cell import CellConfig
from marimo._ast.codegen import generate_filecontents
from marimo._ast.toplevel import TopLevelExtraction

CELLS = {
    "setup": "import pandas as pd\nPA = 0.1",
    "threshold_cell": "threshold = 0.5",
    "uses_setup_only": (
        "def uses_setup_only(df: pd.DataFrame) -> pd.DataFrame:\n"
        "    return df[df['qt'] > PA]"
    ),
    "uses_cell_variable": (
        "def uses_cell_variable(df):\n    return df[df['qc'] > threshold]"
    ),
    "calls_demoted": "def calls_demoted(df):\n    return uses_cell_variable(df)",
    "calls_valid": "def calls_valid(df):\n    return uses_setup_only(df)",
    "private": "def _private(df):\n    return df",
    "two_defs": "def two_a(): ...\ndef two_b(): ...",
    "def_plus_statement": "def with_extra(): ...\nx = with_extra()",
    "lazy_kedro_import": (
        "def create_pipeline():\n"
        "    from kedro.pipeline import Pipeline, node\n"
        "    return Pipeline([node(uses_setup_only, 'a', 'b')])"
    ),
    "trailing_comment": "def commented(df):\n    return df\n# trailing",
}

codes = list(CELLS.values())
names = list(CELLS.keys())
configs = [CellConfig() for _ in codes]

setup_defs = {"pd", "PA"}
extraction = TopLevelExtraction(codes[1:], names[1:], configs[1:], setup_defs)
for status in extraction:
    hint = (status.hint or "").replace("\n", " ")
    print(f"{status.name:>20}: {hint}")

print("\n--- saved file (decorator lines only) ---")
src = generate_filecontents(list(codes), list(names), list(configs))
for line in src.splitlines():
    if line.startswith(("@app.", "with app.setup", "def ", "class ")):
        print(line)
