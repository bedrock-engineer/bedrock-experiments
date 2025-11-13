import marimo

__generated_with = "0.17.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import os
    from pathlib import Path

    import duckdb
    import marimo as mo
    import polars as pl
    import sqlmodel
    return Path, duckdb, json, mo, os, pl, sqlmodel


@app.cell
def _(Path, os):
    speckle_datadb_path = Path(os.environ["APPDATA"]) / "Speckle" / "Data.db"
    speckle_objectsdb_path = Path(os.environ["APPDATA"]) / "Speckle" / "Objects.db"

    hk_kaitak_brgi_gpkg_path = Path(
        r"C:\Users\joost\ReposWindows\bedrock-ge\examples\hk_kaitak_ags3\kaitak_gi.gpkg"
    )
    return (
        hk_kaitak_brgi_gpkg_path,
        speckle_datadb_path,
        speckle_objectsdb_path,
    )


@app.cell
def _(duckdb, speckle_datadb_path, speckle_objectsdb_path, sqlmodel):
    spkl_datadb_sqlite_engine = sqlmodel.create_engine(
        f"sqlite:///{speckle_datadb_path}"
    )
    spkl_objectsdb_sqlite_engine = sqlmodel.create_engine(
        f"sqlite:///{speckle_objectsdb_path}"
    )
    spkl_objectsdb_duckdb_engine = duckdb.connect(
        speckle_objectsdb_path, read_only=False
    )
    return (spkl_objectsdb_duckdb_engine,)


@app.cell
def _(hk_kaitak_brgi_gpkg_path, sqlmodel):
    hk_kaitak_sqlite_engine = sqlmodel.create_engine(
        f"sqlite:///{hk_kaitak_brgi_gpkg_path}"
    )
    return


@app.cell
def _(mo, objects, spkl_objectsdb_duckdb_engine):
    duckdb_df = mo.sql(
        f"""
        SELECT
            *
        FROM "objects"
        LIMIT 100;
        """,
        engine=spkl_objectsdb_duckdb_engine
    )
    return (duckdb_df,)


@app.cell
def _(duckdb_df, json, pl):
    spkl_objs_df = pl.DataFrame({
        "hash": duckdb_df.select("hash"),
        "content": [json.loads(c) for c in duckdb_df["content"]]
    })
    spkl_objs_df
    return


if __name__ == "__main__":
    app.run()
