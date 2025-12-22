import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import io

    import geopandas as gpd
    import marimo as mo
    import requests

    cwd = mo.notebook_location()
    gpkg_path = cwd / "kaitak_gi.gpkg"
    return gpd, gpkg_path, mo, requests


@app.cell
def _(gpkg_path, requests):
    raw_githubusercontent_url = "https://raw.githubusercontent.com/bedrock-engineer/bedrock-ge/main/examples/hk_kaitak_ags3/kaitak_gi.gpkg"
    response = requests.get(raw_githubusercontent_url)
    response.raise_for_status()  # Check for request errors

    with open(gpkg_path, "wb") as gpkg:
        gpkg.write(response.content)
    return


@app.cell
def _(gpd, gpkg_path):
    gpkg_layers = gpd.list_layers(gpkg_path)
    gpkg_layers
    return


@app.cell
def _(gpd, gpkg_path, mo):
    lonlatheight = gpd.read_file(gpkg_path, layer="LonLatHeight")
    spt = gpd.read_file(gpkg_path, layer="ISPT")
    weathering = gpd.read_file(gpkg_path, layer="WETH")
    mo.ui.tabs({"Map": lonlatheight.explore(), "SPT": spt, "Weathering": weathering})
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
