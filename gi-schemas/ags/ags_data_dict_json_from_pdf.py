import marimo

__generated_with = "0.17.7"
app = marimo.App()


@app.cell
def _():
    import json

    import marimo as mo
    import pdfplumber

    cwd = mo.notebook_location()
    cwd
    return cwd, json, mo, pdfplumber


@app.cell
def _(mo):
    mo.md(r"""
    ## Extract AGS 3 and AGS 4 Data Dictionaries from the corresponding AGS .pdf documents
    """)
    return


@app.cell
def _():
    def extract_ags3_data_dict_table(table):
        headings = []
        for row in table[2:]:  # Skip first 2 rows: 1st = title, 2nd = headings
            headings.append(
                {
                    "status": None if row[0] == "" else row[0].strip(),
                    "heading": row[1].strip(),
                    "unit": None if row[2] == "" else row[2].strip().replace("\n", " "),
                    "description": row[3].strip().replace("\n", " "),
                    "example": None if row[4] == "" else row[4].strip().replace("\n", " "),
                }
            )
        return headings


    def extract_ags4_data_dict_table(table):
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
                    "example": None if row[5] == "" else row[5].strip().replace("\n", " "),
                }
            )
        return headings
    return extract_ags3_data_dict_table, extract_ags4_data_dict_table


@app.cell
def _(
    cwd,
    extract_ags3_data_dict_table,
    extract_ags4_data_dict_table,
    pdfplumber,
):
    data_dictionaries = {
        "ags3": {"pdf_file": cwd / "AGS3_v3-1-2005.pdf", "from_page": 22, "to_page": 69},
        "ags4": {"pdf_file": cwd / "AGS4-v4-1-1-2022.pdf", "from_page": 18, "to_page": 160},
    }

    for ags_version, pdf_extraction_info in data_dictionaries.items():
        pdf_file, from_page, to_page = pdf_extraction_info.values()

        # List to store extracted data for each group
        extracted_data = []
        previous_group_name = ""
        with pdfplumber.open(pdf_file) as pdf:
            # Adjust the page range based on where the tables are located
            for page_number in range(from_page, to_page):
                page = pdf.pages[page_number - 1]  # pdfplumber is 0-based, so subtract 1
                tables_on_current_page = page.extract_tables()  # Extract tables from the page

                # Iterate through all tables found on the page
                for table in tables_on_current_page:
                    if ags_version == "ags3":
                        table_title = table[0][0].strip()  # Get table title from AGS3
                    elif ags_version == "ags4":
                        table_title = table[0][1].strip()  # Get table title from AGS4
                    print(table_title)

                    parts = table_title.split(": ", 1)  # Split on the first occurrence of ': '
                    if "Group Name" in parts[0]:
                        group_name = parts[1].split(" - ")[0]
                        group_description = " - ".join(parts[1].split(" - ")[1:])
                        group_description = group_description.replace("\n", " ")
                        if ags_version == "ags3":
                            headings = extract_ags3_data_dict_table(table)
                        elif ags_version == "ags4":
                            headings = extract_ags4_data_dict_table(table)

                        if group_name == previous_group_name:
                            extracted_data[-1]["headings"].extend(headings)
                        else:
                            extracted_data.append(
                                {
                                    "group_name": group_name,
                                    "group_description": group_description,
                                    "headings": headings,
                                }
                            )
                        previous_group_name = group_name

        data_dictionaries[ags_version]["data_dictionary"] = extracted_data
    return (data_dictionaries,)


@app.cell
def _(data_dictionaries):
    data_dictionaries
    return


@app.cell
def _(cwd, data_dictionaries, json):
    for ags_v, data_dict in data_dictionaries.items():
        data_dict = data_dict["data_dictionary"]

        # Compare the extracted group names with group names that were extracted manually from the PDFs
        with open(cwd / f"{ags_v}_manually_extracted_groups.json", "r") as f:
            manual_groups = json.load(f)

        extracted_groups = [d["group_name"] for d in data_dict]

        print(f"{ags_v} groups in manually extracted groups, not in extracted groups: {set(manual_groups) - set(extracted_groups)}")
        print(f"{ags_v} groups in extracted groups, not in manually extracted groups: {set(extracted_groups) - set(manual_groups)}")

        # Save the extracted data dictionaries to a JSON files
        with open(cwd / f"{ags_v}_data_dict.json", "w") as json_file:
            json.dump(data_dict, json_file, indent=2)
    return


if __name__ == "__main__":
    app.run()
