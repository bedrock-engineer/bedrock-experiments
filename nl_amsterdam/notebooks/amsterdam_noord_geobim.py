# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "bimpolars[speckle]",
#     "marimo",
#     "marimo-lens==0.2.4",
#     "polars==2.1.0",
#     "pyproj==3.8.0",
#     "specklewidgets",
# ]
#
# [tool.uv.sources]
# bimpolars = { git = "https://github.com/bedrock-engineer/bimpolars" }
# specklewidgets = { git = "https://github.com/bedrock-engineer/specklestuff" }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import io
    import urllib.request

    import bimpolars as bpl
    import marimo as mo
    import pyproj
    from marimo_lens import Lens
    from specklewidgets import GeoSpeckleViewer
    from specklewidgets.geo import osm_ground_map, pdok_3d_buildings

    return (
        GeoSpeckleViewer,
        Lens,
        bpl,
        io,
        mo,
        osm_ground_map,
        pdok_3d_buildings,
        pyproj,
        urllib,
    )


@app.cell
def _(Lens):
    # marimo-lens: select a region of any output and add a note for the notebook agent
    lens = Lens()
    lens
    return


@app.cell
def _(mo):
    mo.md(r"""
    # Amsterdam Noord GeoBIM

    Revit's advanced sample project placed on a plot at Overhoeks, Amsterdam Noord: the
    architecture and structure models combined into one BimDataFrame, as
    `speckle/rvt_advanced_sample_project_to_r2.py` pushed it to R2, among OpenStreetMap and the
    3D BAG.
    """)
    return


@app.cell
def _(bpl, io, pyproj, urllib):
    # RD New + NAP to WGS 84 follows RDNAPTRANS2018 only with the NSGI grids, which PROJ fetches
    pyproj.network.set_network_enabled(True)

    # Arch and str combined, in the Amsterdam Noord georeferenced BIM CRS
    COMBINED_ARCH_STR_URL = "https://r2.eu.bedrock.engineer/bimpolars/rvt-advanced-sample/rvt-advanced-sample-combined-arch-str-bdf.parquet"
    with urllib.request.urlopen(COMBINED_ARCH_STR_URL) as _response:
        combined_arch_str = bpl.read_parquet(io.BytesIO(_response.read()))
    return (combined_arch_str,)


@app.cell
def _(
    GeoSpeckleViewer,
    combined_arch_str,
    mo,
    osm_ground_map,
    pdok_3d_buildings,
):
    # OpenStreetMap 150 m around the model, and the 3D BAG over the same area
    _ground_map = osm_ground_map(combined_arch_str)
    combined_arch_str_viewer = mo.ui.anywidget(
        GeoSpeckleViewer(
            combined_arch_str,
            color="class",
            ground_map=_ground_map,
            tilesets=[pdok_3d_buildings(combined_arch_str, _ground_map["bounds"])],
            height=550,
        )
    )
    combined_arch_str_viewer
    return


if __name__ == "__main__":
    app.run()
