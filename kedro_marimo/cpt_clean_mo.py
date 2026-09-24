# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.0",
#     "pandas>=3.0",
#     "pyarrow>=25.0",
#     "pydantic>=2.13",
#     "pydantic-settings>=2.15",
# ]
# ///

import marimo

__generated_with = "0.25.0"
app = marimo.App(width="medium")

with app.setup:
    from pathlib import Path

    import pandas as pd

    RAW_COLUMNS = ["cpt_id", "depth", "qc", "fs", "u2"]


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Clean raw CPTs

    Drop invalid readings from a raw CPT table and add the corrected cone
    resistance `qt` and the friction ratio `Rf`. The logic lives in the
    reusable function `clean_cpts`, which Kedro imports as a node.
    """)
    return


@app.function
def clean_cpts(raw: pd.DataFrame, area_ratio: float = 0.8) -> pd.DataFrame:
    """Clean a raw CPT table and add `qt` and `Rf`.

    Rows with a missing or negative `depth`, `qc` or `fs` are dropped, and so
    are repeated depths within one CPT. `u2` may be missing; it is then taken
    as zero for `qt`.

    Args:
        raw: One row per reading, with columns `cpt_id`, `depth` [m],
            `qc` [MPa], `fs` [MPa] and `u2` [MPa].
        area_ratio: Net area ratio `a` of the cone, used in
            `qt = qc + u2 * (1 - a)`.

    Returns:
        The cleaned table sorted by `cpt_id` and `depth`, with extra columns
        `qt` [MPa] and `Rf` [%].

    Examples:
        ```python
        from cpt_clean_mo import clean_cpts

        cleaned = clean_cpts(pd.read_csv("data/01_raw/cpts.csv"))
        ```
    """
    missing = set(RAW_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"raw CPT table misses columns {sorted(missing)}")

    df = raw[RAW_COLUMNS].dropna(subset=["depth", "qc", "fs"])
    df = df[(df["depth"] >= 0) & (df["qc"] > 0) & (df["fs"] >= 0)]
    df = df.sort_values(["cpt_id", "depth"]).drop_duplicates(["cpt_id", "depth"])
    df = df.assign(
        u2=df["u2"].fillna(0.0),
        qt=df["qc"] + df["u2"].fillna(0.0) * (1 - area_ratio),
    )
    df = df.assign(Rf=df["fs"] / df["qt"] * 100)
    return df.reset_index(drop=True)


@app.function
def do_work(params) -> pd.DataFrame:
    """Read `params.input`, clean it with `clean_cpts`, write `params.output`.

    The output format follows the suffix of `params.output`: `.parquet` or
    `.csv`.
    """
    raw = pd.read_csv(params.input)
    cleaned = clean_cpts(raw, area_ratio=params.area_ratio)
    if params.output is not None:
        params.output.parent.mkdir(parents=True, exist_ok=True)
        if params.output.suffix == ".csv":
            cleaned.to_csv(params.output, index=False)
        else:
            cleaned.to_parquet(params.output, index=False)
        print(f"{len(raw)} raw rows -> {len(cleaned)} clean rows -> {params.output}")
    return cleaned


@app.cell
def _():
    from pydantic import Field, FilePath, ValidationError
    from pydantic_settings import BaseSettings, CliApp

    return BaseSettings, CliApp, Field, FilePath, ValidationError


@app.cell
def _(BaseSettings, Field, FilePath):
    class Args(BaseSettings):
        """Clean raw CPTs and add `qt` and `Rf`."""

        input: FilePath = Field(description="Raw CPT CSV (cpt_id, depth, qc, fs, u2)")
        output: Path | None = Field(
            None, description="Parquet or CSV to write; omit to only preview"
        )
        area_ratio: float = Field(0.8, description="Net area ratio a of the cone")

    return (Args,)


@app.cell
def _(mo):
    ui_args = (
        mo.md(
            """
            **Input CSV** {input}

            **Output file** (empty: preview only) {output}

            **Net area ratio** {area_ratio}
            """
        )
        .batch(
            input=mo.ui.text(value="data/01_raw/cpts.csv", full_width=True),
            output=mo.ui.text(value="", full_width=True),
            area_ratio=mo.ui.number(start=0.5, stop=1.0, step=0.01, value=0.8),
        )
        .form(submit_button_label="Run")
    )
    ui_args
    return (ui_args,)


@app.cell
def _(Args, CliApp, ValidationError, mo, ui_args):
    if mo.app_meta().mode == "script":
        try:
            params = CliApp.run(Args)
        except ValidationError as err:
            for e in err.errors():
                print(f"--{'.'.join(map(str, e['loc']))}: {e['msg']}")
            raise SystemExit(2)
    else:
        mo.stop(ui_args.value is None, mo.md("Submit the form to run."))
        params = Args(**{k: v for k, v in ui_args.value.items() if v != ""})
    return (params,)


@app.cell
def _(params):
    cleaned = do_work(params)
    return (cleaned,)


@app.cell
def _(cleaned, mo):
    mo.vstack(
        [
            mo.md(f"**{len(cleaned)} clean readings in {cleaned['cpt_id'].nunique()} CPTs**"),
            mo.ui.table(cleaned, page_size=10),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
