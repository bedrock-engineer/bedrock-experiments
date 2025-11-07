import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell
def _():
    import json

    import marimo as mo
    import polars as pl

    cwd = mo.notebook_location()
    cwd
    return cwd, json, mo, pl


@app.cell
def _(mo):
    mo.md(r"""
    # AGS 4 data dictionaries from AGS files

    AGS 4 has seen 4 revisions since its initial release (v4.0.3) in 2011:
    - v4.0 (2010)
    - v4.0.3 (2011)
    - v4.0.4 (2017)
    - v4.1 (2020)
    - v4.1.1 (2022)

    The AGS data management working group published .pdf documents for each of these revisions, on the [AGS 4 Data Format page](https://www.ags.org.uk/data-format/ags4-data-format/). Additionally, AGS 4 data dictionaries are also available in .ags file format in the GitLab repository of the [`ags-python-library`](https://gitlab.com/ags-data-format-wg/ags-python-library/-/tree/main/python_ags4).

    When comparing these data dictionaries with each other, it becomes clear that 4.0.3 → 4.0.4 only had minor changes in the data dictionary .ags files, mostly related to water / moisture content, minor changes in some data types and some formatting.

    From the AGS data format blog [v4.1.1 release post](https://www.ags.org.uk/data-format-blog/ags-format-4-1-1-released/):

    > AGS 4.1 represents a substantial update of the Data Dictionary, introducing 19 new Groups, some of which replace Groups such as ERES, IPRG and IPRT.

    In order to compare the data dictionaries of AGS 4.0.4, AGS 4.1 and AGS 4.1.1, I downloaded the data dictionary .ags files from the `ags-python-library` repository and then compared the data dictionary tables after converting them to dataframes using the `python_ags4` library:
    """)
    return


@app.cell
def _(cwd):
    import urllib.request

    ags4_versions = ["v4_0_3", "v4_0_4", "v4_1", "v4_1_1"]
    ags4_dd_files = [f"Standard_dictionary_{ver}.ags" for ver in ags4_versions]
    base_url = "https://gitlab.com/ags-data-format-wg/ags-python-library/-/raw/main/python_ags4/"

    for ags4_dd_file in ags4_dd_files:
        with urllib.request.urlopen(base_url + ags4_dd_file) as resp:
            content = resp.read()
        out = cwd / ags4_dd_file
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content)
    return


@app.cell
def _(cwd, mo, pl):
    from python_ags4 import AGS4

    v4_0_4_groups, _ = AGS4.AGS4_to_dataframe(cwd / "Standard_dictionary_v4_0_4.ags")
    v4_0_4_tables = {}
    for group, df in v4_0_4_groups.items():
        v4_0_4_tables[group] = pl.from_pandas(AGS4.convert_to_numeric(df))

    v4_1_groups, _ = AGS4.AGS4_to_dataframe(cwd / "Standard_dictionary_v4_1.ags")
    v4_1_tables = {}
    for group, df in v4_1_groups.items():
        v4_1_tables[group] = pl.from_pandas(AGS4.convert_to_numeric(df))

    v4_1_1_groups, _ = AGS4.AGS4_to_dataframe(cwd / "Standard_dictionary_v4_1.ags")
    v4_1_1_tables = {}
    for group, df in v4_1_1_groups.items():
        v4_1_1_tables[group] = pl.from_pandas(AGS4.convert_to_numeric(df))

    mo.vstack([v4_0_4_tables["ABBR"], v4_1_1_tables["ABBR"]])
    return v4_0_4_tables, v4_1_1_tables, v4_1_tables


@app.cell
def _(mo, pl, v4_0_4_tables, v4_1_tables):
    left = v4_0_4_tables["DICT"].drop(
        [
            "HEADING",
            # "DICT_DESC",
            # "DICT_EXMP",
            # "DICT_UNIT",
            "DICT_REM",
        ]
    )
    right = v4_1_tables["DICT"].drop(
        [
            "HEADING",
            # "DICT_DESC",
            # "DICT_EXMP",
            # "DICT_UNIT",
            "DICT_REM",
            "FILE_FSET",
        ]
    )
    in_v4_0_4_only = left.join(right, on=left.columns, how="anti")
    in_v4_1_only = right.join(left, on=right.columns, how="anti")

    # Find desprecated and new tables by applying a GROUP filter on the DICT_TYPE column
    deprecated_tables = ["ERES", "IPRG", "IPRT"]
    new_tables = [
        "CTRC",
        "CTRD",
        "CTRG",
        "CTRP",
        "CTRS",
        "DLOG",
        "ECTN",
        "ELRG",
        "FGHG",
        "FGHI",
        "FGHS",
        "FGHT",
        "LFCN",
        "LTCH",
        "LUCT",
        "RCAG",
        "RCAT",
        "RESC",
        "RESD",
        "RESG",
        "RESP",
        "RESS",
        "WGPG",
        "WGPT",
    ]
    # Remove deprecated and new tables from the comparison
    in_v4_0_4_only = in_v4_0_4_only.filter(~pl.col("DICT_GRP").is_in(deprecated_tables))
    in_v4_1_only = in_v4_1_only.filter(
        ~pl.col("DICT_GRP").is_in(deprecated_tables + new_tables)
    )

    # Find deprecated headings by filtering the DICT_STAT column of the v4_1 df on DEPRECATED
    deprecated_headings = [
        "PMTD_ARM1",
        "PMTD_ARM2",
        "PMTD_ARM3",
        "RUCS_E",
        "RUCS_MU",
        "RUCS_ESTR",
        "RUCS_ETYP",
    ]
    # Find new headings by comparing the DICT_HDNG column
    v4_0_4_headings = set(
        in_v4_0_4_only.select(pl.col("DICT_HDNG")).unique().to_series().to_list()
    )
    v4_1_headings = set(
        in_v4_1_only.select(pl.col("DICT_HDNG")).unique().to_series().to_list()
    )
    new_headings = sorted(v4_1_headings - v4_0_4_headings)
    # No headings were deprecated. Remove deprecated and new headings from the comparison
    in_v4_0_4_only = in_v4_0_4_only.filter(
        ~pl.col("DICT_HDNG").is_in(deprecated_headings)
    )
    in_v4_1_only = in_v4_1_only.filter(
        ~pl.col("DICT_HDNG").is_in(deprecated_headings + new_headings)
    )

    mo.vstack([in_v4_0_4_only, in_v4_1_only])
    return


@app.cell
def _(mo):
    mo.md(r"""
    Conclusions from 4.0.4 → 4.1 comparison:

    - The DICT table has a FILE_FSET column (heading) that is new in 4.1.
    - Deprecated tables in 4.1:
      `[ERES, IPRG, IPRT]`
    - New tables in 4.1:
      `[CTRC, CTRD, CTRG, CTRP, CTRS, DLOG, ECTN, ELRG, FGHG, FGHI, FGHS, FGHT, LFCN, LTCH, LUCT, RCAG, RCAT, RESC, RESD, RESG, RESP, RESS, WGPG, WGPT]`
    - Deprecated headings in 4.1:
      `[PMTD_ARM1, PMTD_ARM2, PMTD_ARM3, RUCS_E, RUCS_MU, RUCS_ESTR, RUCS_ETYP]`
    - Many new headings in 4.1, see `headings_only_in_v4_1`. Especially HEADING_DEV is new, which is described as: "Deviation from the specified procedure".
    - Some types were changed.
    - New descriptions and examples.
    - Formatting of e.g. units "Bar" → "bar"

    From the AGS data format blog [v4.1.1 release post](https://www.ags.org.uk/data-format-blog/ags-format-4-1-1-released/):

    > This Edition 4.1.1 is a very minor update to AGS Format 4.1. It removes a few incorrect headings and amends incorrect examples.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Creating the JSON Data Dictionary

    Now that we know that we can simply use the latest v4.1.1 data dictionary, because deprecated groups and headings are still present in that data dictionary, neatly indicated as DEPRECATED.

    First we create a dataframe with all the AGS groups, which we'll call tables from now on. Additionally, this dataframe will also contain parent tables and add a column that indicates whether a group is deprecated:
    """)
    return


@app.cell
def _(pl, v4_1_1_tables):
    tables_df = (
        v4_1_1_tables["DICT"]
        .filter(pl.col("DICT_TYPE") == "GROUP")
        .select(
            pl.col("DICT_GRP").alias("table_name"),
            pl.col("DICT_DESC").alias("description"),
            pl.col("DICT_PGRP").alias("parent"),
            pl.when(pl.col("DICT_STAT") == "DEPRECATED")
              .then(True)
              .otherwise(None)
              .alias("deprecated")
        )
    )
    tables_df
    return (tables_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Then we need to also create a dataframe with all the AGS headings, these represent the columns of each table (AGS group). In order to do this properly, we don't only need the columns of each AGS table, but also the units used in AGS, and we need to map the types used in AGS to more commonly used data types, such as the types with constraints as used in JSON schema. So, we start by mapping the AGS data types to JSON schema compatible data types and constraints (`format`, `enum`):

    | AGS Type | Meaning | JSON Schema Type |
    | ----- | ----- | ----- |
    | `0DP` | Value with 0 decimal places, so an integer | `integer` |
    | `0DP`, `1DP`, `2DP`, `3DP`, `4DP` | Value with fixed decimal places | `number` |
    | `0SCI`, `1SCI`, `2SCI`, `3SCI`, `4SCI` | Scientific notation number | `number` |
    | `1SF`, `2SF`, `3SF`, `4SF` | Significant figures  | `number` |
    | `DMS`| Degrees:Minutes:Seconds (formatted string) | `string` |
    | `DT` | Date/time in ISO format   | `string` (`format: date-time`)  |
    | `ID` | Unique identifier | `string` |
    | `MC` | Moisture content (percentage value) | `number` |
    | `PA` | As listed in ABBR Group  | `string`, `integer` or `enum` depending on the categories |
    | `PT` | Text listed in TYPE Group  | `string` `enum` |
    | `PU` | Text listed in UNIT Group  | `string` `enum` |
    | `RL` | Record link (likely an ID)| `string` |
    | `T`  | Elapsed time (e.g., seconds, minutes) | `string` (`format: duration`) |
    | `U`  | Variable format numeric/text   | `string` |
    | `X`  | Text| `string` |
    | `XN` | Text or numeric | `string` |
    | `YN` | Yes/No   | `boolean`   |
    """)
    return


@app.cell
def _(cwd, json, pl, v4_1_1_tables):
    ags_units_df = v4_1_1_tables["UNIT"].select(
            pl.col("UNIT_UNIT").alias("ags_unit"),
            pl.col("UNIT_DESC").alias("ags_unit_description"),
    )
    ags_units_df.write_csv(cwd / "ags4_units.csv")

    ags_types_df = v4_1_1_tables["TYPE"].select(
            pl.col("TYPE_TYPE").alias("ags_type"),
            pl.col("TYPE_DESC").alias("ags_type_description"),
    )

    ags_type_mapping = pl.DataFrame([
        {"ags_type": "0DP", "type": "integer"},
        {"ags_type": "0SCI", "type": "number"},
        {"ags_type": "1DP", "type": "number"},
        {"ags_type": "1SCI", "type": "number"},
        {"ags_type": "1SF", "type": "number"},
        {"ags_type": "2DP", "type": "number"},
        {"ags_type": "2SCI", "type": "number"},
        {"ags_type": "2SF", "type": "number"},
        {"ags_type": "3DP", "type": "number"},
        {"ags_type": "3SCI", "type": "number"},
        {"ags_type": "3SF", "type": "number"},
        {"ags_type": "4DP", "type": "number"},
        {"ags_type": "4SCI", "type": "number"},
        {"ags_type": "4SF", "type": "number"},
        {"ags_type": "DMS", "type": "string"},
        {"ags_type": "DT", "type": "string", "format": "date-time"},
        {"ags_type": "ID", "type": "string"},
        {"ags_type": "MC", "type": "number"},
        {"ags_type": "PA", "type": "string"},
        {
            "ags_type": "PT",
            "type": "string",
            "enum": ags_types_df["ags_type"].to_list(),
        },
        {
            "ags_type": "PU",
            "type": "string",
            "enum": ags_units_df["ags_unit"].to_list(),
        },
        {"ags_type": "RL", "type": "string"},
        {"ags_type": "T", "type": "string", "format": "duration"},
        {"ags_type": "U", "type": "string"},
        {"ags_type": "X", "type": "string"},
        {"ags_type": "XN", "type": "string"},
        {"ags_type": "YN", "type": "boolean"},
    ]).join(ags_types_df, on="ags_type")

    with open(cwd / "ags4_types.json", "w") as f:
        json.dump(drop_nulls(ags_type_mapping.to_dicts()), f, indent=2)

    ags_type_mapping
    return (ags_type_mapping,)


@app.cell
def _(ags_type_mapping, pl, v4_1_1_tables):
    columns_df = (
        v4_1_1_tables["DICT"]
        .filter(pl.col("DICT_TYPE") == "HEADING")
        .select(
            pl.col("DICT_GRP").alias("table_name"),
            pl.col("DICT_HDNG").alias("name"),
            pl.when(pl.col("DICT_UNIT") == "")
            .then(None)
            .otherwise(pl.col("DICT_UNIT"))
            .alias("unit"),
            pl.col("DICT_DESC").alias("description"),
            pl.when(pl.col("DICT_EXMP") == "")
            .then(None)
            .otherwise(pl.col("DICT_EXMP"))
            .alias("example"),
            pl.col("DICT_DTYP").alias("ags_type"),
            pl.col("DICT_STAT").alias("ags_status"),
            pl.when(pl.col("DICT_STAT") == "DEPRECATED")
            .then(True)
            .otherwise(None)
            .alias("deprecated"),
        )
        .join(ags_type_mapping.drop("ags_type_description"), on="ags_type")
    )
    columns_df
    return (columns_df,)


@app.cell
def _(mo):
    mo.md(r"""
    It's also possible to create enums from the
    """)
    return


@app.cell
def _(pl, v4_1_1_tables):
    ags_abbr_categories_df = (
        v4_1_1_tables["ABBR"]
        .select(
            pl.col("ABBR_HDNG").alias("column_name"),
            pl.col("ABBR_CODE").alias("value"),
            pl.col("ABBR_DESC").alias("label"),
        )
        .group_by("column_name")
        # .agg(pl.struct())
    )
    # BKFL_LEG and GEOL_LEG have integer values, the rest are string values
    ags_abbr_categories_df
    return


@app.cell
def _(columns_df, pl, tables_df):
    tables_with_cols = (
        tables_df.join(columns_df, on="table_name", maintain_order="left")
        .group_by(["table_name", "description", "parent", "deprecated"])
        .agg(pl.struct(pl.exclude(["table_name", "description", "parent", "group_name"])).alias("columns"))
    )
    tables_with_cols
    return


@app.cell
def _(columns_df, pl):
    columns_df.group_by("table_name").agg(pl.struct(pl.exclude("table_name")))
    return


@app.cell
def _(columns_df, tables_df):
    tables_df.join(columns_df, on="table_name", maintain_order="left")
    return


@app.function
def drop_nulls(obj):
    if isinstance(obj, dict):
        return {k: drop_nulls(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [drop_nulls(v) for v in obj]
    return obj


if __name__ == "__main__":
    app.run()
