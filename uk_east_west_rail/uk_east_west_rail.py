import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell
def _():
    import geopandas as gpd
    import marimo as mo
    import matplotlib.pyplot as plt
    from python_ags4 import AGS4

    return AGS4, gpd, mo, plt


@app.cell
def _(mo):
    mo.md(r"""
    # AGS Example Notebook: Plot locations on a map and create a simple strip log from an AGS4 file

    ## 1. Import AGS4 data

    We will use part of a publicly avaiable dataset provided by the British Geological Survey for this example. The name of the file is ***East West Rail BGS Pre October 2018 upload (partial).ags*** and a copy is included in this repo. The full file can be found at https://github.com/BritishGeologicalSurvey/pyagsapi/tree/main/test/files/real.
    """)
    return


@app.cell
def _(AGS4, mo):
    cwd = mo.notebook_location()
    groups, headings = AGS4.AGS4_to_dataframe(
        cwd / "East West Rail BGS Pre October 2018 upload (partial).ags"
    )
    return (groups,)


@app.cell
def _(groups, mo):
    mo.vstack([list(groups.keys()), groups["LOCA"]])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Plot locations

    All imported data is of the data type `str` so relevant numeric columns have to converted to `float` before they can be plotted. The following code converts all AGS4 groups to numeric data.
    """)
    return


@app.cell
def _(AGS4, groups):
    # Data types in imported LOCA table (first six columns only)
    tables = {}
    for group, df in groups.items():
        tables[group] = AGS4.convert_to_numeric(df)

    tables["LOCA"]
    return (tables,)


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Convert to geospatial data

    The LOCA data which is currently in a Pandas DataFrame can be converted to a GeoDataFrame that provides additional functionality to perform geospatial operations. This requires the installation of the `geopandas` package with its many dependencies. The `geopandas` documentation strongly recommends installing the package using the `conda` package manager since it can be tricky to correctly install all the dependencies, especially in a Windows environment (https://geopandas.org/en/stable/getting_started/install.html).
    """)
    return


@app.cell
def _(gpd, tables):
    loca_df = tables["LOCA"].dropna(axis=0)
    loca_gdf = gpd.GeoDataFrame(
        loca_df,
        geometry=gpd.points_from_xy(loca_df["LOCA_NATE"], loca_df["LOCA_NATN"]),
        crs="EPSG:27700",
    )

    loca_gdf
    return (loca_gdf,)


@app.cell
def _(loca_gdf):
    loca_gdf.explore()
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Produce Strip Logs

    It's possible to extract lithology intervals from the GEOL table and plot a basic strip log using https://github.com/agile-geoscience/striplog.

    The stiplog library has not been updated in several years however, and the plotting functionality doesn't work very well.
    """)
    return


@app.cell
def _(plt, tables):
    from striplog import Interval, Legend, Lexicon, Striplog

    # Pick the borehole ID for which you want to make a striplog
    borehole_id = "CP2A15CE"

    # Create custom legend
    legend_csv = """colour, component lithology, hatch
    orange, GRAVEL, o
    yellow, SAND, .
    greenyellow, SILT, |
    green, CLAY, /
    """
    legend = Legend.from_csv(text=legend_csv)

    # Initiate list to store intervals/layers
    intervals = []

    # You will want a lexicon of some kind to interpret entries in GEOL_DESC
    lexicon = Lexicon.default()

    # Extract lithology information from the GEOL table
    geol_df = tables["GEOL"]
    for row in geol_df.loc[geol_df["LOCA_ID"].eq(borehole_id), :].to_dict(
        orient="records"
    ):
        interval = Interval(
            top=row["GEOL_TOP"],
            base=row["GEOL_BASE"],
            description=row["GEOL_DESC"],
            lexicon=lexicon,
        )
        intervals.append(interval)

    # Then make a striplog from the list:
    slog = Striplog(list_of_Intervals=intervals)

    # Plot Lithology
    fig, ax = plt.subplots(1, 2)
    slog.plot(
        ax=ax[0],
        ladder=True,
        aspect=5,
        ticks=1,
        legend=legend,
        match_only=["lithology"],
    )
    legend.plot(ax=ax[1])

    fig
    return


if __name__ == "__main__":
    app.run()
