# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.25.0",
#     "numpy>=2.0",
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

    import numpy as np
    import pandas as pd

    PA = 0.1  # atmospheric pressure [MPa]
    # Robertson (2010) SBT zones by upper bound of the SBT index Isbt.
    SBT_ZONES = [
        (1.31, 7, "gravelly sand to dense sand"),
        (2.05, 6, "sands: clean sand to silty sand"),
        (2.60, 5, "sand mixtures: silty sand to sandy silt"),
        (2.95, 4, "silt mixtures: clayey silt to silty clay"),
        (3.60, 3, "clays: silty clay to clay"),
        (np.inf, 2, "organic soils: clay and peat"),
    ]


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Classify CPTs by soil behaviour type

    Robertson (2010) non-normalized SBT index

    $$I_{SBT} = \sqrt{(3.47 - \log_{10}(q_t / p_a))^2 + (\log_{10} R_f + 1.22)^2}$$

    mapped to SBT zones 2 to 7, then merged into layers per CPT. The logic
    lives in the reusable functions `classify_cpts` and `summarize_layers`,
    which Kedro imports as nodes.
    """)
    return


@app.function
def sbt_index(qt: pd.Series, rf: pd.Series) -> pd.Series:
    """Return the Robertson (2010) non-normalized SBT index `Isbt`.

    Args:
        qt: Corrected cone resistance [MPa].
        rf: Friction ratio [%].
    """
    return np.sqrt((3.47 - np.log10(qt / PA)) ** 2 + (np.log10(rf) + 1.22) ** 2)


@app.function
def classify_cpts(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Add `Isbt`, `sbt_zone` and `sbt_name` to a cleaned CPT table.

    Args:
        cleaned: Output of `clean_cpts`, with at least `qt` [MPa] and `Rf` [%].

    Returns:
        A copy of `cleaned` with the three extra columns. Readings with
        `Rf <= 0` get `Isbt` NaN and are dropped.
    """
    df = cleaned[cleaned["Rf"] > 0].copy()
    df["Isbt"] = sbt_index(df["qt"], df["Rf"])
    bounds = [b for b, _, _ in SBT_ZONES]
    idx = np.searchsorted(bounds, df["Isbt"].to_numpy(), side="right")
    df["sbt_zone"] = np.array([z for _, z, _ in SBT_ZONES])[idx]
    df["sbt_name"] = np.array([n for _, _, n in SBT_ZONES])[idx]
    return df.reset_index(drop=True)


@app.function
def summarize_layers(
    classified: pd.DataFrame, min_layer_thickness: float = 0.0
) -> pd.DataFrame:
    """Merge consecutive readings of one SBT zone into layers, per CPT.

    Layers thinner than `min_layer_thickness` are absorbed into the layer
    above them (or below, for the first layer), and neighbours that end up in
    the same zone are merged.

    Args:
        classified: Output of `classify_cpts`.
        min_layer_thickness: Thinnest layer to keep [m].

    Returns:
        One row per layer: `cpt_id`, `layer`, `top`, `bottom`, `thickness`,
        `sbt_zone`, `sbt_name`, `qc_mean`, `Rf_mean` and `n_readings`.
    """
    names = {z: n for _, z, n in SBT_ZONES}
    rows = []
    for cpt_id, cpt in classified.sort_values(["cpt_id", "depth"]).groupby("cpt_id"):
        depth = cpt["depth"].to_numpy()
        step = np.median(np.diff(depth)) if len(depth) > 1 else 0.0
        zones = cpt["sbt_zone"].to_numpy().copy()

        def runs(z):
            starts = np.flatnonzero(np.r_[True, z[1:] != z[:-1]])
            ends = np.r_[starts[1:], len(z)]
            return list(zip(starts, ends))

        # Absorb the thinnest too-thin run into its neighbour until none is left.
        while True:
            thin = [
                (depth[e - 1] - depth[s] + step, s, e)
                for s, e in runs(zones)
                if depth[e - 1] - depth[s] + step < min_layer_thickness
            ]
            if not thin or len(runs(zones)) == 1:
                break
            _, s, e = min(thin)
            zones[s:e] = zones[s - 1] if s > 0 else zones[e]

        for i, (s, e) in enumerate(runs(zones), start=1):
            part = cpt.iloc[s:e]
            rows.append(
                {
                    "cpt_id": cpt_id,
                    "layer": i,
                    "top": depth[s],
                    "bottom": round(depth[e - 1] + step, 3),
                    "sbt_zone": int(zones[s]),
                    "sbt_name": names[int(zones[s])],
                    "qc_mean": round(part["qc"].mean(), 3),
                    "Rf_mean": round(part["Rf"].mean(), 2),
                    "n_readings": e - s,
                }
            )
    layers = pd.DataFrame(rows)
    layers.insert(4, "thickness", (layers["bottom"] - layers["top"]).round(3))
    return layers


@app.function
def do_work(params) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Classify `params.input` and write readings and layers if asked."""
    cleaned = pd.read_parquet(params.input)
    classified = classify_cpts(cleaned)
    layers = summarize_layers(classified, params.min_layer_thickness)
    for df, out in [(classified, params.output_readings), (layers, params.output_layers)]:
        if out is None:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix == ".csv":
            df.to_csv(out, index=False)
        else:
            df.to_parquet(out, index=False)
        print(f"{len(df)} rows -> {out}")
    return classified, layers


@app.cell
def _():
    from pydantic import Field, FilePath, ValidationError
    from pydantic_settings import BaseSettings, CliApp

    return BaseSettings, CliApp, Field, FilePath, ValidationError


@app.cell
def _(BaseSettings, Field, FilePath):
    class Args(BaseSettings):
        """Classify cleaned CPTs by Robertson (2010) SBT and summarize layers."""

        input: FilePath = Field(description="Cleaned CPT Parquet from cpt_clean_mo.py")
        output_readings: Path | None = Field(
            None, description="Parquet or CSV for classified readings"
        )
        output_layers: Path | None = Field(
            None, description="Parquet or CSV for the layer summary"
        )
        min_layer_thickness: float = Field(
            0.3, description="Absorb layers thinner than this [m]"
        )

    return (Args,)


@app.cell
def _(mo):
    ui_args = (
        mo.md(
            """
            **Cleaned CPT Parquet** {input}

            **Readings output** (empty: none) {output_readings}

            **Layers output** (empty: none) {output_layers}

            **Min layer thickness [m]** {min_layer_thickness}
            """
        )
        .batch(
            input=mo.ui.text(
                value="data/02_intermediate/cpts_clean.parquet", full_width=True
            ),
            output_readings=mo.ui.text(value="", full_width=True),
            output_layers=mo.ui.text(value="", full_width=True),
            min_layer_thickness=mo.ui.number(start=0, stop=2, step=0.1, value=0.3),
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
    classified, layers = do_work(params)
    return classified, layers


@app.cell
def _(classified, layers, mo):
    mo.vstack(
        [
            mo.md(f"**{len(layers)} layers in {layers['cpt_id'].nunique()} CPTs**"),
            mo.ui.table(layers, page_size=20),
            mo.ui.table(classified, page_size=10),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
