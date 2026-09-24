"""Unit tests that import the reusable functions straight from the notebooks."""

import inspect

import numpy as np
import pandas as pd
import pytest

import cpt_classify_mo
import cpt_clean_mo
from cpt_classify_mo import classify_cpts, sbt_index, summarize_layers
from cpt_clean_mo import clean_cpts
from make_raw_cpts import make_raw_cpts


@pytest.mark.parametrize(
    "func",
    [
        cpt_clean_mo.clean_cpts,
        cpt_classify_mo.sbt_index,
        cpt_classify_mo.classify_cpts,
        cpt_classify_mo.summarize_layers,
    ],
)
def test_node_functions_are_plain_functions(func):
    # If marimo demotes a function to @app.cell, the import still succeeds but
    # yields a marimo Cell that returns None when called.
    assert inspect.isfunction(func)


def test_clean_drops_bad_rows_and_adds_qt_rf():
    raw = pd.DataFrame(
        {
            "cpt_id": ["A"] * 5,
            "depth": [0.0, 0.1, 0.1, 0.2, 0.3],
            "qc": [1.0, 2.0, 2.0, -0.1, 4.0],
            "fs": [0.01, 0.02, 0.02, 0.01, np.nan],
            "u2": [0.0, 0.5, 0.5, 0.0, 0.0],
        }
    )
    cleaned = clean_cpts(raw, area_ratio=0.8)
    assert cleaned["depth"].tolist() == [0.0, 0.1]
    assert cleaned["qt"].tolist() == pytest.approx([1.0, 2.1])
    assert cleaned["Rf"].tolist() == pytest.approx([1.0, 0.02 / 2.1 * 100])


def test_clean_rejects_missing_columns():
    with pytest.raises(ValueError, match="u2"):
        clean_cpts(pd.DataFrame(columns=["cpt_id", "depth", "qc", "fs"]))


@pytest.mark.parametrize(
    ("qt", "rf", "zone"),
    [(40.0, 0.3, 7), (8.0, 0.6, 6), (0.8, 3.5, 3), (0.2, 8.0, 2)],
)
def test_classify_zones(qt, rf, zone):
    df = pd.DataFrame({"qt": [qt], "Rf": [rf]})
    assert classify_cpts(df)["sbt_zone"].item() == zone


def test_sbt_index_matches_formula():
    isbt = sbt_index(pd.Series([1.0]), pd.Series([1.0]))
    assert isbt.item() == pytest.approx(np.hypot(3.47 - 1.0, 1.22))


def test_summarize_layers_absorbs_thin_layer():
    classified = pd.DataFrame(
        {
            "cpt_id": "A",
            "depth": np.round(np.arange(0, 1.0, 0.1), 1),
            "sbt_zone": [6, 6, 6, 6, 3, 6, 6, 6, 6, 6],
            "qc": 1.0,
            "Rf": 1.0,
        }
    )
    assert len(summarize_layers(classified, 0.0)) == 3
    layers = summarize_layers(classified, 0.3)
    assert layers[["top", "bottom", "sbt_zone"]].values.tolist() == [[0.0, 1.0, 6]]


def test_chain_finds_four_layers_per_cpt():
    layers = summarize_layers(classify_cpts(clean_cpts(make_raw_cpts())), 0.3)
    assert layers.groupby("cpt_id")["sbt_zone"].apply(list).tolist() == [[6, 3, 2, 6]] * 3


def test_registry_nodes_are_the_notebook_functions():
    from cpt_pipeline.pipeline_registry import register_pipelines

    funcs = {n.name: n.func for n in register_pipelines()["cpt"].nodes}
    assert funcs == {
        "clean_cpts": clean_cpts,
        "classify_cpts": classify_cpts,
        "summarize_layers": summarize_layers,
    }


def test_app_run_node_matches_function_node(tmp_path):
    from cpt_pipeline.notebook_nodes import run_clean_notebook

    raw = make_raw_cpts()
    path = tmp_path / "raw.csv"
    raw.to_csv(path, index=False)
    via_app_run = run_clean_notebook(str(path), 0.8)
    via_function = clean_cpts(pd.read_csv(path), 0.8)
    pd.testing.assert_frame_equal(via_app_run, via_function)
