# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "duckdb==1.5.5",
#     "marimo>=0.24.0",
#     "polars==1.44.0",
#     "sqlmodel==0.0.39",
# ]
# ///

import marimo

__generated_with = "0.24.0"
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
    speckle_datadb_path
    return speckle_datadb_path, speckle_objectsdb_path


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
    return (spkl_objectsdb_sqlite_engine,)


@app.cell
def _(mo, spkl_objectsdb_sqlite_engine):
    objs_df = mo.sql(
        f"""
        SELECT
            *
        FROM "objects"
        LIMIT	20;
        """,
        engine=spkl_objectsdb_sqlite_engine
    )
    return (objs_df,)


@app.cell
def _(json, objs_df, pl):
    spkl_objs_df = pl.DataFrame({
        "hash": objs_df.select("hash"),
        "content": [json.loads(c) for c in objs_df["content"]]
    })
    spkl_objs_df
    return


if __name__ == "__main__":
    app.run()
