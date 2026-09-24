#!/usr/bin/env bash
# Q4/Q5: put create_pipeline() in the notebook as a reusable function and let
# find_pipelines() discover it. Runs on a scratch copy; the project is untouched.
# Usage: bash probes/create_pipeline_in_notebook.sh
set -uo pipefail
src="$(cd "$(dirname "$0")/.." && pwd)"
work="$(mktemp -d)/proj"
rsync -a --exclude .venv --exclude __marimo__ --exclude 'data/0[2-8]*/*.*' "$src/" "$work/"
cd "$work"
export COLUMNS=160 KEDRO_DISABLE_TELEMETRY=1

# 1. create_pipeline with a lazy Kedro import inside the function body.
python3 - <<'EOF'
from pathlib import Path
p = Path("cpt_clean_mo.py")
s = p.read_text()
s = s.replace('''@app.function
def do_work(params)''', '''@app.function
def create_pipeline(**kwargs):
    """Return the Kedro pipeline for this notebook."""
    from kedro.pipeline import Pipeline, node

    return Pipeline(
        [
            node(
                clean_cpts,
                inputs=["raw_cpts", "params:clean.area_ratio"],
                outputs="cpts_clean",
                name="clean_cpts",
            )
        ]
    )


@app.function
def do_work(params)''')
p.write_text(s)
EOF
mkdir -p cpt_pipeline/pipelines/clean
printf 'from cpt_clean_mo import create_pipeline\n\n__all__ = ["create_pipeline"]\n' \
  > cpt_pipeline/pipelines/clean/__init__.py
touch cpt_pipeline/pipelines/__init__.py
cat > cpt_pipeline/pipeline_registry.py <<'EOF'
from kedro.framework.project import find_pipelines


def register_pipelines():
    pipelines = find_pipelines(raise_errors=True)
    pipelines["__default__"] = sum(pipelines.values())
    return pipelines
EOF

echo "== marimo check (lazy import)"
uv run -q marimo check cpt_clean_mo.py && echo "ok"
echo "== saved as"
grep -B1 "^def create_pipeline" cpt_clean_mo.py
echo "== kedro registry list"
uv run -q kedro registry list 2>&1 | grep -v "^\s*$" | tail -4
echo "== kedro run --pipeline clean"
uv run -q kedro run --pipeline clean 2>&1 | grep -E "Running node|successfully|Error"
echo "== uv run cpt_clean_mo.py (PEP 723 env, no kedro)"
uv run -q cpt_clean_mo.py --input data/01_raw/cpts.csv --output /tmp/km_probe_clean.csv
echo "== from cpt_clean_mo import create_pipeline; create_pipeline() without kedro"
uv run -q --isolated --no-project --with marimo --with pandas --with pyarrow python -c \
  "from cpt_clean_mo import create_pipeline; create_pipeline()" 2>&1 | tail -1

# 2. Same, but the Kedro import in the setup cell (the marimo-recommended place).
python3 - <<'EOF'
from pathlib import Path
p = Path("cpt_clean_mo.py")
s = p.read_text()
s = s.replace("    import pandas as pd\n", "    import pandas as pd\n    from kedro.pipeline import Pipeline, node\n", 1)
s = s.replace("    from kedro.pipeline import Pipeline, node\n\n    return Pipeline(", "    return Pipeline(")
p.write_text(s)
EOF
echo "== setup-cell import: marimo check"
uv run -q marimo check cpt_clean_mo.py && echo "ok"
echo "== setup-cell import: uv run cpt_clean_mo.py (PEP 723 env, no kedro)"
uv run -q cpt_clean_mo.py --input data/01_raw/cpts.csv --output /tmp/km_probe_clean.csv 2>&1 | tail -1
rm -rf "$(dirname "$work")"
