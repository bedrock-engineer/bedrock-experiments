"""Build Kedro pipelines from the reusable functions in the marimo notebooks."""

from cpt_classify_mo import classify_cpts, summarize_layers
from cpt_clean_mo import clean_cpts
from kedro.pipeline import Pipeline, node


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
    return {"__default__": cpt, "cpt": cpt}
