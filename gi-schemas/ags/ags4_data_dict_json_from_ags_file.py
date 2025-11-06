import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import polars as pl

    cwd = mo.notebook_location()
    cwd
    return cwd, mo, pl


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

    v4_0_4_groups, _ = AGS4.AGS4_to_dataframe(cwd / 'Standard_dictionary_v4_0_4.ags')
    v4_0_4_tables = {}
    for group, df in v4_0_4_groups.items():
        v4_0_4_tables[group] = pl.from_pandas(AGS4.convert_to_numeric(df))
    

    v4_1_groups, _ = AGS4.AGS4_to_dataframe(cwd / 'Standard_dictionary_v4_1.ags')
    v4_1_tables = {}
    for group, df in v4_1_groups.items():
        v4_1_tables[group] = pl.from_pandas(AGS4.convert_to_numeric(df))

    mo.vstack([v4_0_4_tables["ABBR"], v4_1_tables["ABBR"]])
    return v4_0_4_tables, v4_1_tables


@app.cell
def _(mo, pl, v4_0_4_tables, v4_1_tables):
    left = v4_0_4_tables["DICT"].drop([
        "HEADING", 
        # "DICT_DESC", 
        # "DICT_EXMP", 
        # "DICT_UNIT",
        "DICT_REM"
    ])
    right = v4_1_tables["DICT"].drop([
        "HEADING", 
        # "DICT_DESC", 
        # "DICT_EXMP", 
        # "DICT_UNIT",
        "DICT_REM", 
        "FILE_FSET"
    ])
    in_v4_0_4_only = left.join(right, on=left.columns, how='anti')
    in_v4_1_only = right.join(left, on=right.columns, how='anti')

    # Find desprecated and new tables by applying a GROUP filter on the DICT_TYPE column
    deprecated_tables = ["ERES", "IPRG", "IPRT"]
    new_tables =["CTRC", "CTRD", "CTRG", "CTRP", "CTRS", "DLOG", "ECTN", "ELRG", "FGHG", "FGHI", "FGHS", "FGHT", "LFCN", "LTCH", "LUCT", "RCAG", "RCAT", "RESC", "RESD", "RESG", "RESP", "RESS", "WGPG", "WGPT"]
    # Remove deprecated and new tables from the comparison
    in_v4_0_4_only = in_v4_0_4_only.filter(~pl.col("DICT_GRP").is_in(deprecated_tables))
    in_v4_1_only = in_v4_1_only.filter(~pl.col("DICT_GRP").is_in(deprecated_tables + new_tables))

    # Find deprecated headings by filtering the DICT_STAT column of the v4_1 df on DEPRECATED
    deprecated_headings = ["PMTD_ARM1", "PMTD_ARM2", "PMTD_ARM3", "RUCS_E", "RUCS_MU", "RUCS_ESTR", "RUCS_ETYP"]
    # Find new headings by comparing the DICT_HDNG column
    v4_0_4_headings = set(in_v4_0_4_only.select(pl.col("DICT_HDNG")).unique().to_series().to_list())
    v4_1_headings = set(in_v4_1_only.select(pl.col("DICT_HDNG")).unique().to_series().to_list())
    new_headings = sorted(v4_1_headings - v4_0_4_headings)
    # No headings were deprecated. Remove deprecated and new headings from the comparison
    in_v4_0_4_only = in_v4_0_4_only.filter(~pl.col("DICT_HDNG").is_in(deprecated_headings))
    in_v4_1_only = in_v4_1_only.filter(~pl.col("DICT_HDNG").is_in(deprecated_headings + new_headings))

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


@app.cell
def _(pl, v4_1_tables):
    v4_1_tables["DICT"].drop(["HEADING", "DICT_REM", "FILE_FSET"]).filter(pl.col("DICT_TYPE") == "GROUP")
    # "group_name": "PROJ",
    # "group_description": "Project Information",
    return


if __name__ == "__main__":
    app.run()
