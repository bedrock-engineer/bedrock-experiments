import marimo

__generated_with = "0.17.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import json

    import marimo as mo
    import geopandas as gpd
    import polars as pl

    cwd = mo.notebook_location()
    feature_04_dir = cwd.parent / "data" / "04_feature"
    return feature_04_dir, gpd


@app.cell
def _():
    soil_colors = {
        'Unknown': '#FFFFFF',  # White
        'Gravelly sand to dense sand': '#FF8C00',  # Dark orange
        'Sands: clean sand to silty sand': '#FFD700',  # Gold
        'Sand mixtures: silty sand to sandy silt': '#F4E4A6',  # Pale yellow
        'Silt mixtures: clayey silt to silty clay': '#90EE90',  # Light green
        'Clays: silty clay to clay': '#8B4513',  # Saddle brown
        'Organic soils / Very soft clay': '#2F4F2F',  # Dark olive green
    }
    return (soil_colors,)


@app.cell
def _(feature_04_dir, gpd, soil_colors):
    gdf = gpd.read_file(feature_04_dir / "cpt_interpreted_rdnap_epsg7415.geojson")
    gdf["color"] = gdf["soil_type"].map(soil_colors).fillna("#FFFFFF")
    gdf.to_file(feature_04_dir / "cpt_interpreted_rdnap_epsg7415.geojson")
    return


if __name__ == "__main__":
    app.run()
