import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell
def _():
    import json

    import marimo as mo
    import pdfplumber
    import polars as pl

    cwd = mo.notebook_location()
    cwd
    return cwd, json, mo, pdfplumber, pl


@app.cell
def _(mo):
    mo.md(r"""
    # Extract AGS 3 and AGS 4 Data Dictionaries from the corresponding AGS .pdf documents
    """)
    return


@app.cell
def _():
    def extract_ags3_groups_table(table):
        groups = []
        for row in table[1:]:
            groups.append(
                {
                    "group_name": row[0].strip(),
                    "group_description": row[3].strip().replace("\n", " "),
                    "parent_group": row[6].strip(),
                }
            )
        return groups

    def extract_ags3_headings_table(table):
        headings = []
        for row in table[2:]:  # Skip first 2 rows: 1st = title, 2nd = headings
            headings.append(
                {
                    "status": None if row[0] == "" else row[0].strip(),
                    "heading": row[1].strip(),
                    "unit": None if row[2] == "" else row[2].strip().replace("\n", " "),
                    "description": row[3].strip().replace("\n", " "),
                    "example": None
                    if row[4] == ""
                    else row[4].strip().replace("\n", " "),
                }
            )
        return headings

    def extract_ags4_groups_table(table):
        groups = []
        for row in table[2:]:
            groups.append(
                {
                    "group_name": row[0].strip(),
                    "group_description": row[2].strip().replace("\n", " "),
                    "group_notes": None
                    if row[3] == "" or row[3] == None
                    else row[3].strip().replace("\n", " "),
                    "parent_group": row[-2].strip(),
                }
            )
        return groups

    def extract_ags4_headings_table(table):
        # Skip rows that don't contain data
        for i, row in enumerate(table):
            if "Suggested\nUnit / Type" in row or "Unit / Type" in row:
                first_data_row = i + 1
                break

        headings = []
        for row in table[first_data_row:]:
            row = [x for x in row if x is not None]
            headings.append(
                {
                    "status": None if row[0] == "" else row[0].strip(),
                    "heading": row[1].strip(),
                    "unit": None if row[2] == "" else row[2].strip().replace("\n", ""),
                    "type": row[3].strip(),
                    "description": row[4].strip().replace("\n", " "),
                    "example": None
                    if row[5] == ""
                    else row[5].strip().replace("\n", " "),
                }
            )
        return headings

    return (
        extract_ags3_groups_table,
        extract_ags3_headings_table,
        extract_ags4_groups_table,
        extract_ags4_headings_table,
    )


@app.cell
def _(
    cwd,
    extract_ags3_groups_table,
    extract_ags3_headings_table,
    extract_ags4_groups_table,
    extract_ags4_headings_table,
    pdfplumber,
    pl,
):
    # Adjust the page range based on where the tables are located in the pdfs
    data_dictionaries = {
        "ags3": {
            "pdf": {
                "file_path": cwd / "ags3" / "AGS3_v3-1-2005.pdf",
                "groups": {"from_page": 19, "to_page": 21},
                "headings": {"from_page": 22, "to_page": 69},
            }
        },
        "ags4": {
            "pdf": {
                "file_path": cwd / "ags4" / "AGS4-v4-1-1-2022.pdf",
                "groups": {"from_page": 13, "to_page": 18},
                "headings": {"from_page": 18, "to_page": 160},
            }
        },
    }

    for ags_version, pdf_extraction_info in data_dictionaries.items():
        extracted_groups = []
        extracted_headings = []
        with pdfplumber.open(pdf_extraction_info["pdf"]["file_path"]) as pdf:
            # Extract groups
            from_page = pdf_extraction_info["pdf"]["groups"]["from_page"]
            to_page = pdf_extraction_info["pdf"]["groups"]["to_page"]
            for page_number in range(from_page, to_page):
                # pdfplumber is 0-based, so subtract 1
                page = pdf.pages[page_number - 1]
                tables_on_current_page = page.extract_tables()
                for table in tables_on_current_page:
                    if ags_version == "ags3":
                        groups = extract_ags3_groups_table(table)
                    elif ags_version == "ags4":
                        # The first page with an AGS 4 group table contains
                        # another table we're not interested in.
                        if table[0][1] == "Type":
                            continue
                        groups = extract_ags4_groups_table(table)

                    extracted_groups.extend(groups)

            # Extract headings
            previous_group_name = ""
            from_page = pdf_extraction_info["pdf"]["headings"]["from_page"]
            to_page = pdf_extraction_info["pdf"]["headings"]["to_page"]
            for page_number in range(from_page, to_page):
                # pdfplumber is 0-based, so subtract 1
                page = pdf.pages[page_number - 1]
                tables_on_current_page = page.extract_tables()

                # Iterate through all tables found on the page
                for table in tables_on_current_page:
                    if ags_version == "ags3":
                        table_title = table[0][0].strip()
                    elif ags_version == "ags4":
                        table_title = table[0][1].strip()
                    print(table_title)

                    parts = table_title.split(
                        ": ", 1
                    )  # Split on the first occurrence of ': '
                    if "Group Name" in parts[0]:
                        group_name = parts[1].split(" - ")[0]
                        group_description = " - ".join(parts[1].split(" - ")[1:])
                        group_description = group_description.replace("\n", " ")
                        if ags_version == "ags3":
                            headings = extract_ags3_headings_table(table)
                        elif ags_version == "ags4":
                            headings = extract_ags4_headings_table(table)

                        if group_name == previous_group_name:
                            extracted_headings[-1]["headings"].extend(headings)
                        else:
                            extracted_headings.append(
                                {
                                    "group_name": group_name,
                                    "group_description": group_description,
                                    "headings": headings,
                                }
                            )
                        previous_group_name = group_name

        data_dictionaries[ags_version]["groups"] = pl.DataFrame(extracted_groups)
        data_dictionaries[ags_version]["headings"] = pl.DataFrame(extracted_headings)
    return (data_dictionaries,)


@app.cell
def _(data_dictionaries):
    data_dictionaries["ags3"]["headings"]
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Compare AGS Groups Extracted from the Groups and Headings Tables
    """)
    return


@app.cell
def _(data_dictionaries):
    data_dictionaries
    return


@app.cell
def _(cwd, data_dictionaries, json):
    for ags_v, data_dict in data_dictionaries.items():
        data_dict = data_dict["headings"]

        # Compare the extracted group names with group names that were extracted manually from the PDFs
        with open(cwd / ags_v / f"manually_extracted_groups_{ags_v}.json", "r") as f:
            manual_groups = json.load(f)

        # groups_from_headings = [d["group_name"] for d in data_dict]

        # print(
        #     f"{ags_v} groups in manually extracted groups, not in extracted groups: {set(manual_groups) - set(groups_from_headings)}"
        # )
        # print(
        #     f"{ags_v} groups in extracted groups, not in manually extracted groups: {set(groups_from_headings) - set(manual_groups)}"
        # )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Construct Data Dictionaries and Export to JSON
    """)
    return


@app.cell
def _(cwd, data_dictionaries, json):
    # Save the extracted data dictionaries to a JSON files
    for ags_ver, headings_df in data_dictionaries.items():
        headings_df = headings_df["headings"]
        with open(cwd / ags_ver / f"pdf_data_dict_{ags_ver}.json", "w") as json_file:
            json.dump(drop_nulls(headings_df.to_dicts()), json_file, indent=2)
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
