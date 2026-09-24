"""Build Kedro pipelines from the reusable functions in the marimo notebooks."""

from cpt_classify_mo import classify_cpts, summarize_layers
from cpt_clean_mo import clean_cpts
from kedro.pipeline import Pipeline, node

from cpt_pipeline.notebook_nodes import run_clean_notebook


def register_pipelines() -> dict[str, Pipeline]:
    cpt = Pipeline(
        [
            node(
                clean_cpts,
                inputs=["raw_cpts", "params:clean.area_ratio"],
                outputs="cpts_clean",
                name="clean_cpts",
            ),
            node(classify_cpts, inputs="cpts_clean", outputs="cpts_classified", name="classify_cpts"),
            node(
                summarize_layers,
                inputs=["cpts_classified", "params:classify.min_layer_thickness"],
                outputs="cpt_layers",
                name="summarize_layers",
            ),
        ]
    )
    # For comparison: the whole clean notebook as one node, via app.run().
    app_run = Pipeline(
        [
            node(
                run_clean_notebook,
                inputs=["params:raw_cpts_path", "params:clean.area_ratio"],
                outputs="cpts_clean_app_run",
                name="run_clean_notebook",
            )
        ]
    )
    return {"__default__": cpt, "cpt": cpt, "app_run": app_run}
