import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import uuid

    import bromodels
    import marimo as mo
    import numpy as np
    import polars as pl
    import pyproj
    import trimesh

    import specklepy
    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_local_accounts, get_default_account
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput
    from specklepy.objects import data_objects as sdo
    from specklepy.objects import geometry as sg
    from specklepy.objects.models.collections import collection as sco
    from specklepy.objects.other import RenderMaterial
    from specklepy.objects.proxies import RenderMaterialProxy, ColorProxy
    from specklepy.transports.server import ServerTransport
    return (
        ColorProxy,
        CreateVersionInput,
        RenderMaterial,
        RenderMaterialProxy,
        ServerTransport,
        SpeckleClient,
        bromodels,
        get_default_account,
        get_local_accounts,
        mo,
        operations,
        pl,
        pyproj,
        sco,
        sdo,
        sg,
        specklepy,
        uuid,
    )


@app.cell
def _(pyproj):
    lon = 4.903216131629909
    lat = 52.38561797347398

    easting = 122050
    northing = 488750
    height_wrt_nap = 3

    transformer = pyproj.Transformer.from_crs(28992, 4326, always_xy=True)
    lon, lat = transformer.transform(easting, northing)

    {
        "Easting [m]": easting,
        "Northing [m]": northing,
        "Height wrt NAP [m]": height_wrt_nap,
    }
    return easting, northing


@app.cell
def _(bromodels, mo, pl):
    lithok_map = (
        pl.from_pandas(bromodels.GeoTop.geotop_lithology_class())
        .filter(pl.col("VOXEL_NR").is_not_null())
        .with_columns(
            pl.col("VOXEL_NR").cast(pl.Int64),
            pl.struct(["RED_DEC", "GREEN_DEC", "BLUE_DEC"])
            .map_elements(
                lambda c: (
                    f"#{c['RED_DEC']:02x}{c['GREEN_DEC']:02x}{c['BLUE_DEC']:02x}"
                ),
                return_dtype=pl.String,
            )
            .alias("color_hex"),
        )
        # Put the color_hex column first
        .select(["color_hex", pl.all().exclude("color_hex")])
    )
    mo.ui.table(
        lithok_map, style_cell=lambda _r, _c, hex: {"backgroundColor": hex}
    )
    return (lithok_map,)


@app.cell
def _(bromodels, mo, pl):
    strat_map = (
        pl.from_pandas(bromodels.GeoTop.geotop_stratigraphic_unit())
        .with_columns(
            pl.struct(["RED_DEC", "GREEN_DEC", "BLUE_DEC"])
            .map_elements(
                lambda c: (
                    f"#{c['RED_DEC']:02x}{c['GREEN_DEC']:02x}{c['BLUE_DEC']:02x}"
                ),
                return_dtype=pl.String,
            )
            .alias("color_hex")
        )
        # Put the color_hex column first
        .select(["color_hex", pl.all().exclude("color_hex")])
    )
    mo.ui.table(strat_map, style_cell=lambda _r, _c, hex: {"backgroundColor": hex})
    return (strat_map,)


@app.cell
def _(bromodels, easting, northing):
    geotop_xr = bromodels.GTM.GeoTop.GeoTopDomain(
        west=easting - 200,
        south=northing - 200,
        east=easting + 200,
        north=northing + 200,
        bottom=-50
    )
    geotop_xr
    return (geotop_xr,)


@app.cell
def _(geotop_xr, lithok_map, mo, pl, strat_map):
    # .reset_index() is necessary, because x, y, z are the indices, and polars doesn't work with indices.
    geotop_df = (
        pl.from_pandas(geotop_xr.to_dataframe().reset_index())
        .select(["x", "y", "z", "lithok", "strat", "onz_lk", "onz_ls"])
        .filter(pl.col("lithok").is_not_null())
        .with_columns(
            pl.col("x").cast(pl.Float32),
            pl.col("y").cast(pl.Float32),
            pl.col("lithok").cast(pl.Int32),
            pl.col("strat").cast(pl.Int32),
        )
        .join(
            strat_map.select(
                ["VOXEL_NR", "color_hex", "STR_UNIT_CD", "DESCRIPTION"]
            ),
            left_on="strat",
            right_on="VOXEL_NR",
            how="left",
        )
        .rename(
            {
                "color_hex": "strat_hex",
                "STR_UNIT_CD": "prop.stratigraphic_unit",
                "DESCRIPTION": "prop.geologische_eenheid",
            }
        )
        .join(
            lithok_map.select(
                ["VOXEL_NR", "color_hex", "LITHO_CLASS_CD", "DESCRIPTION"]
            ),
            left_on="lithok",
            right_on="VOXEL_NR",
            how="left",
        )
        .rename(
            {
                "LITHO_CLASS_CD": "prop.lithostratigraphic_class",
                "DESCRIPTION": "prop.grondsoort",
            }
        )
        .select(["color_hex", pl.all().exclude("color_hex")])
    )

    mo.ui.table(geotop_df, style_cell=lambda _r, _c, hex: {"backgroundColor": hex})
    return (geotop_df,)


@app.cell
def _(mo):
    mo.md(r"""
    ### Prepare data for sending to Speckle

    #### Create a mesh for each voxel
    """)
    return


@app.cell
def _(geotop_df, mo, pl, uuid):
    geotop_speckle_df = geotop_df.with_columns(
        pl.col("onz_lk").alias("prop.onzekerheid_grondsoort"),
        pl.col("onz_ls").alias("prop.onzekerheid_geologische_eenheid"),
        pl.col("prop.grondsoort").alias("material_name"),
        pl.concat_str(
            [
                pl.lit("FF"),
                pl.col("color_hex").str.strip_prefix("#"),
            ]
        )
        .str.to_integer(base=16)
        .alias("rgba_int"),
        pl.arange(0, pl.len())
        .map_elements(lambda _: str(uuid.uuid4()))
        .alias("application_id"),
        pl.concat_list([
                pl.col("x") - 50, pl.col("y") - 50, pl.col("z") - 0.25,
                pl.col("x") + 50, pl.col("y") - 50, pl.col("z") - 0.25,
                pl.col("x") + 50, pl.col("y") + 50, pl.col("z") - 0.25,
                pl.col("x") - 50, pl.col("y") + 50, pl.col("z") - 0.25,
                pl.col("x") - 50, pl.col("y") - 50, pl.col("z") + 0.25,
                pl.col("x") + 50, pl.col("y") - 50, pl.col("z") + 0.25,
                pl.col("x") + 50, pl.col("y") + 50, pl.col("z") + 0.25,
                pl.col("x") - 50, pl.col("y") + 50, pl.col("z") + 0.25,
            ]).alias("display_value.vertices"),
        pl.lit([4, 0, 1, 2, 3, 4, 4, 5, 6, 7, 4, 0, 1, 5, 4, 4, 2, 3, 7, 6, 4, 0, 4, 5, 1, 4, 2, 6, 5, 1])
        # Faces list, in case triangular faces are necessary (incorrect tho)
        # pl.lit([
        #     3, 1, 3, 0,
        #     3, 4, 1, 0,
        #     3, 0, 3, 2,
        #     3, 2, 4, 0,
        #     3, 1, 7, 3,
        #     3, 5, 1, 4,
        #     3, 5, 7, 1,
        #     3, 3, 7, 2,
        #     3, 6, 4, 2,
        #     3, 2, 7, 6,
        #     3, 6, 5, 4,
        #     3, 7, 5, 6
        # ])
        .alias("display_value.faces"),
    )
    mo.ui.table(
        geotop_speckle_df, style_cell=lambda _r, _c, hex: {"backgroundColor": hex}
    )
    return (geotop_speckle_df,)


@app.cell
def _(mo):
    mo.md(r"""
    #### Create Speckle color proxies and elements
    """)
    return


@app.cell
def _(geotop_speckle_df, pl):
    color_proxies_df = geotop_speckle_df.select(
                pl.col("material_name"),
                pl.col("rgba_int"),
                pl.col("application_id"),
            )

    color_proxies_df = color_proxies_df.group_by("material_name").agg(
        pl.first("rgba_int"),
        pl.col("application_id"),
    ).sort("material_name")
    color_proxies_df
    return (color_proxies_df,)


@app.cell
def _(ColorProxy, RenderMaterial, RenderMaterialProxy, color_proxies_df):
    spkl_material_proxies = []
    spkl_color_proxies = []
    for color_row in color_proxies_df.iter_rows(named=True):
        material_proxy = RenderMaterialProxy(
            value=RenderMaterial(
                name=color_row["material_name"], diffuse=color_row["rgba_int"]
            ),
            objects=color_row["application_id"],
        )
        spkl_material_proxies.append(material_proxy)

        color_proxy = ColorProxy(
            name=color_row["material_name"],
            value=color_row["rgba_int"],
            objects=color_row["application_id"],
        )
        spkl_color_proxies.append(color_proxy)
    return spkl_color_proxies, spkl_material_proxies


@app.cell
def _(pl, sco, sdo, sg):
    def df_to_speckle_collection(
        speckle_df: pl.DataFrame, collection_name: str
    ) -> sco.Collection:
        spkl_data_objs = []
        for row in speckle_df.iter_rows(named=True):
            spkl_obj = sdo.DataObject(
                applicationId=row["application_id"],
                name=row["material_name"],
                properties={
                    k.removeprefix("prop."): v
                    for k, v in row.items()
                    if k.startswith("prop.")
                },
                displayValue=[
                    sg.Mesh(
                        vertices=row["display_value.vertices"],
                        faces=row["display_value.faces"],
                        # colors=row.get("display_value.colors"),
                        units="m",
                    )
                ],
            )

            spkl_data_objs.append(spkl_obj)

        return sco.Collection(name=collection_name, elements=spkl_data_objs)
    return (df_to_speckle_collection,)


@app.cell
def _(df_to_speckle_collection, geotop_speckle_df):
    geotop_collection = df_to_speckle_collection(geotop_speckle_df, collection_name="geotop")
    return


@app.cell
def _(
    df_to_speckle_collection,
    geotop_speckle_df,
    sco,
    spkl_color_proxies,
    spkl_material_proxies,
):
    speckle_data = sco.Collection(name="bro-data")
    speckle_data.elements = [df_to_speckle_collection(geotop_speckle_df, collection_name="geotop")]
    speckle_data.renderMaterialProxies = spkl_material_proxies
    speckle_data.colorProxies = spkl_color_proxies
    return (speckle_data,)


@app.cell
def _(mo):
    mo.md(r"""
    ### Publish to Speckle
    """)
    return


@app.cell
def _(SpeckleClient, get_default_account, get_local_accounts, mo):
    # Get all locally stored accounts
    accounts = get_local_accounts()

    for account in accounts:
        print(f"Server: {account.serverInfo.url}, User: {account.userInfo.name}")

    # Get the default account
    account = get_default_account()
    if account:
        client = SpeckleClient(host=account.serverInfo.url)
        client.authenticate_with_account(account)

    print(
        f"Authenticated on {client.server.get().canonical_url} as {client.account.userInfo.name}"
    )

    projects = client.active_user.get_projects()
    projects_dd = mo.ui.dropdown({proj.name: proj for proj in projects.items})
    return client, projects_dd


@app.cell
def _(client, mo, projects_dd, specklepy):
    project = projects_dd.value
    if isinstance(project, specklepy.core.api.models.current.Project):
        models = client.model.get_models(project.id)
        models_dd = mo.ui.dropdown({mdl.name: mdl for mdl in models.items})
    else:
        models_dd = "Select a Speckle project first ↑"
    return models_dd, project


@app.cell
def _(mo, models_dd, specklepy):
    model = None
    if isinstance(models_dd, mo.ui.dropdown):
        model = models_dd.value

    if isinstance(model, specklepy.core.api.models.current.Model):
        send_to_speckle = mo.ui.run_button(label="Press to send GI to Speckle")
    else:
        send_to_speckle = "Select a Speckle model first ↑"
    return model, send_to_speckle


@app.cell
def _(mo, models_dd, projects_dd, send_to_speckle):
    mo.vstack([projects_dd, models_dd, send_to_speckle])
    return


@app.cell
def _(
    CreateVersionInput,
    ServerTransport,
    client,
    mo,
    model,
    operations,
    project,
    send_to_speckle,
    speckle_data,
):
    output = None

    if send_to_speckle.value:
        transport = ServerTransport(stream_id=project.id, client=client)
        object_id = operations.send(base=speckle_data, transports=[transport])
        version_input = CreateVersionInput(
            project_id=project.id,
            model_id=model.id,
            object_id=object_id,
        )
        version = client.version.create(version_input)

        output = mo.vstack(
            [
                mo.md(rf"""
        ✓ Created version: `{version.id}` of model `{model.name}` on project `{project.name}`
        """),
                mo.Html(
                    rf'<iframe title="Speckle" src="https://app.speckle.systems/projects/{project.id}/models/{model.id}" width="800" height="500" frameborder="0"></iframe>'
                ),
            ]
        )

    output
    return


if __name__ == "__main__":
    app.run()
