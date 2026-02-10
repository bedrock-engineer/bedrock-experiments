import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import uuid

    import geopandas as gpd
    import marimo as mo
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import numpy as np
    import pandas as pd
    import polars as pl
    import pyvista as pv
    import requests

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

    cwd = mo.notebook_location()
    return (
        ColorProxy,
        CreateVersionInput,
        RenderMaterial,
        RenderMaterialProxy,
        ServerTransport,
        SpeckleClient,
        cwd,
        get_default_account,
        get_local_accounts,
        gpd,
        mcolors,
        mo,
        np,
        operations,
        pd,
        pl,
        plt,
        pv,
        requests,
        sco,
        sdo,
        sg,
        specklepy,
        uuid,
    )


@app.cell
def _(cwd, requests):
    gpkg_path = cwd / "kaitak_gi.gpkg"
    raw_githubusercontent_url = "https://raw.githubusercontent.com/bedrock-engineer/bedrock-ge/main/examples/hk_kaitak_ags3/kaitak_gi.gpkg"
    response = requests.get(raw_githubusercontent_url)
    response.raise_for_status()  # Check for request errors

    with open(gpkg_path, "wb") as gpkg:
        gpkg.write(response.content)
    return (gpkg_path,)


@app.cell
def _(gpd, gpkg_path):
    gpkg_layers = gpd.list_layers(gpkg_path)
    gpkg_layers
    return


@app.cell
def _(gpd, gpkg_path, mo):
    lonlatheight = gpd.read_file(gpkg_path, layer="LonLatHeight")

    spt = gpd.read_file(gpkg_path, layer="ISPT")
    spt = spt.dropna(subset="ISPT_NVAL")
    # spt = spt[1000:1250]

    weth = gpd.read_file(gpkg_path, layer="WETH").dropna(subset=["WETH_BASE"])
    weth = weth[weth["WETH_GRAD"] != "V/III"]
    mapping = {
        "I/II": "II/I",
        "II/III": "III/II",
        "III/IV": "IV/III",
        "IV/V": "V/IV",
    }
    weth["WETH_GRAD"] = weth["WETH_GRAD"].replace(mapping)
    # weth = weth[1000:1250]

    # Output
    mo.ui.tabs({"Map": lonlatheight.explore(), "SPT": spt, "Weathering": weth})
    return spt, weth


@app.cell
def _(mcolors, plt):
    def spt_n_to_hex(v: int) -> str:
        norm = mcolors.Normalize(vmin=0, vmax=100, clip=True)
        cmap = plt.get_cmap("plasma")
        return mcolors.to_hex(cmap(norm(v)))
    return (spt_n_to_hex,)


@app.cell
def _(mcolors, plt):
    def weathering_grade_to_hex(weth_grad: str) -> str:
        weathering_grade_vals = {
            "I": 1,
            "II/I": 1.5,
            "II": 2,
            "III/II": 2.5,
            "III": 3,
            "IV/III": 3.5,
            "IV": 4,
            "V/IV": 4.5,
            "V": 5,
            "VI/V": 5.5,
            "VI": 6
        }
        v = weathering_grade_vals[weth_grad]
        norm = mcolors.Normalize(vmin=1,vmax=6)
        cmap = plt.get_cmap("YlGnBu")
        return mcolors.to_hex(cmap(norm(v)))
    return (weathering_grade_to_hex,)


@app.cell
def _(np, sg):
    def coords_to_speckle_geom(
        coords: list[list[float]],
    ) -> sg.Point | sg.Line | sg.Polyline:
        if len(coords) == 1:
            return sg.Point(
                x=coords[0][0],
                y=coords[0][1],
                z=coords[0][2],
                units="m",
            )
        elif len(coords) == 2:
            return sg.Line(
                start=sg.Point(
                    x=coords[0][0],
                    y=coords[0][1],
                    z=coords[0][2],
                    units="m",
                ),
                end=sg.Point(
                    x=coords[1][0],
                    y=coords[1][1],
                    z=coords[1][2],
                    units="m",
                ),
                units="m",
            )
        else:
            return sg.Polyline(
                value=np.array(coords).flatten().tolist(), units="m"
            )
    return (coords_to_speckle_geom,)


@app.cell
def _(np, pv):
    def coords_to_pyvista_mesh(coords: list[list[float]]) -> pv.PolyData:
        if len(coords) == 1:
            return pv.Sphere(
                center=np.array(coords[0]),
                radius=0.7,
                theta_resolution=10,
                phi_resolution=10,
            )
        elif len(coords) == 2:
            return pv.Tube(
                pointa=coords[0],
                pointb=coords[1],
                radius=0.6,
                n_sides=10,
                capping=True
            ).triangulate()
    return (coords_to_pyvista_mesh,)


@app.cell
def _(pv, sg):
    def pyvista_mesh_to_display_value(pv_mesh: pv.PolyData) -> sg.Mesh:
        return sg.Mesh(
            vertices=pv_mesh.points.flatten().tolist(),
            faces=pv_mesh.faces.tolist(),
            units="m"
        )
    return (pyvista_mesh_to_display_value,)


@app.cell
def _(
    coords_to_pyvista_mesh,
    coords_to_speckle_geom,
    pl,
    pyvista_mesh_to_display_value,
    sco,
    sdo,
):
    def props_df_to_speckle_collection(
        props_df: pl.DataFrame, obj_name: str
    ) -> sco.Collection:
        spkl_data_objs = []
        for row in props_df.iter_rows(named=True):
            application_id = row.pop("application_id")
            coords = row.pop("coords")
            pv_mesh = coords_to_pyvista_mesh(coords)
            # Create Speckle Data Object
            spkl_obj = sdo.DataObject(
                name=obj_name,
                applicationId=application_id,
                properties=row,
                displayValue=[pyvista_mesh_to_display_value(pv_mesh)],
            )
            # Attach Speckle geometry
            spkl_obj.geometry = coords_to_speckle_geom(coords)

            spkl_data_objs.append(spkl_obj)

        return sco.Collection(name=obj_name, elements=spkl_data_objs)
    return (props_df_to_speckle_collection,)


@app.cell
def _(pd, pl, spt, spt_n_to_hex, uuid):
    spt_spkl_props = (
        pl.from_pandas(
            pd.DataFrame(spt).assign(
                coords=[list(g.coords) for g in spt.geometry],
                geometry=spt.geometry.astype(str),
            )
        )
        .rename({"geometry": "wkt_geometry"})
        .with_columns(
            pl.col("ISPT_NVAL")
            .map_elements(spt_n_to_hex, return_dtype=str)
            .alias("color"),
            pl.arange(0, pl.len())
            .map_elements(lambda _: str(uuid.uuid4()))
            .alias("application_id"),
        )
    )
    spt_spkl_props
    return (spt_spkl_props,)


@app.cell
def _(pd, pl, uuid, weathering_grade_to_hex, weth):
    weth_spkl_props = (
        pl.from_pandas(
            pd.DataFrame(weth).assign(
                coords=[list(g.coords) for g in weth.geometry],
                geometry=weth.geometry.astype(str),
            )
        )
        .rename({"geometry": "wkt_geometry"})
        .with_columns(
            pl.col("WETH_GRAD")
            .map_elements(weathering_grade_to_hex, return_dtype=str)
            .alias("color"),
            pl.arange(0, pl.len())
            .map_elements(lambda _: str(uuid.uuid4()))
            .alias("application_id"),
        )
    )
    weth_spkl_props
    return (weth_spkl_props,)


@app.cell
def _(pl, spt_spkl_props, weth_spkl_props):
    color_proxies_df = pl.concat(
        [
            spt_spkl_props.select(
                (
                    pl.lit("SPT N-value: ")
                    + pl.col("ISPT_NVAL").clip(0, 100).cast(int).cast(str)
                ).alias("material_name"),
                pl.col("color"),
                pl.col("application_id"),
            ),
            weth_spkl_props.select(
                (pl.lit("Weathering grade: ") + pl.col("WETH_GRAD")).alias(
                    "material_name"
                ),
                pl.col("color"),
                pl.col("application_id"),
            ),
        ],
        how="vertical",
    )

    color_proxies_df = color_proxies_df.group_by("material_name").agg(
        pl.concat_str(
                [
                    pl.lit("FF"),
                    pl.first("color").str.strip_prefix("#"),
                ]
            )
            .str.to_integer(base=16)
            .alias("rgba_int"),
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
def _(props_df_to_speckle_collection, spt_spkl_props, weth_spkl_props):
    spt_collection = props_df_to_speckle_collection(spt_spkl_props, obj_name="spt")
    weathering_collection = props_df_to_speckle_collection(
        weth_spkl_props, obj_name="weathering"
    )
    return spt_collection, weathering_collection


@app.cell
def _(weathering_collection):
    # spt_collection.elements[10].displayValue[0].__dict__
    weathering_collection.elements[10].displayValue[0].__dict__
    return


@app.cell
def _(
    sco,
    spkl_color_proxies,
    spkl_material_proxies,
    spt_collection,
    weathering_collection,
):
    speckle_data = sco.Collection(name="gi")
    speckle_data.elements = [spt_collection, weathering_collection]
    speckle_data.renderMaterialProxies = spkl_material_proxies
    speckle_data.colorProxies = spkl_color_proxies
    return (speckle_data,)


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


@app.cell
def _(mo):
    mo.md(r"""
    # Plot the display values (PyVista spheres & pipes)
    """)
    return


@app.cell
def _(coords_to_pyvista_mesh, pl, weth_spkl_props):
    pv_mesh_df = weth_spkl_props[1000:1250].with_columns(
        pl.col("coords").map_elements(coords_to_pyvista_mesh, return_dtype=pl.Object).alias("pyvista_mesh")
    )
    pv_mesh_df
    return (pv_mesh_df,)


@app.cell
def _(pv, pv_mesh_df):
    plotter = pv.Plotter()
    for pv_row in pv_mesh_df.iter_rows(named=True):
        # print(pv_row["pyvista_mesh"])
        plotter.add_mesh(pv_row["pyvista_mesh"], color=pv_row["color"])

    plotter.show()
    return


@app.cell
def _(np, pl, pv, spt_spkl_props):
    pdata = pv.PolyData(
        np.squeeze(spt_spkl_props["coords"].cast(pl.Array(pl.Array(float, 3), 1)))
    )
    pdata["spt_n"] = spt_spkl_props["ISPT_NVAL"]

    sphere = pv.Sphere(radius=0.7, theta_resolution=10, phi_resolution=10)
    spheres = pdata.glyph(orient=False, scale=False, geom=sphere)
    vertices = spheres.points.flatten()
    faces = spheres.faces

    pltr = pv.Plotter()
    pltr.add_mesh(spheres, scalars="spt_n", cmap="plasma", clim=(0, 100))
    pltr.show()
    return (spheres,)


@app.cell
def _(spheres):
    spheres
    return


@app.cell
def _(np, pv):
    # Example: N points defining your 3D polyline
    # shape: (N, 3) with columns [x, y, z]
    points = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.5, 0.0],
        [2.0, 1.0, 0.5],
        [3.0, 1.0, 1.0],
    ])

    # Helper to build a single polyline cell from points
    def polyline_from_points(points: np.ndarray) -> pv.PolyData:
        poly = pv.PolyData()
        poly.points = points
        # one line cell using all points in order
        the_cell = np.arange(0, len(points), dtype=np.int_)
        the_cell = np.insert(the_cell, 0, len(points))  # prepend length
        poly.lines = the_cell
        return poly

    line = polyline_from_points(points)

    # Make a tube (pipe) around the line
    radius = 0.1  # pipe radius
    tube = line.tube(radius=radius)  # returns PolyData (a tube mesh)

    # Visualize
    # tube.plot(smooth_shading=True)

    type(tube)
    return


@app.cell
def _(mo):
    mo.md(r"""
    1. Create Speckle Geometry
    2. Create `displayValue` using PyVista

    For GI data there are two types of geospatial geometry:
    1. POINT Z
    2. LINESTRING Z

    In Speckle and PyVista these become three types of geometry:
    1. POINT Z -> sg.Point + pv.Sphere
    2. LINESTRING Z with 2 points -> sg.Line + pv.Tube
    3. LINESTRING Z with more than 2 points -> sg.PolyLine +
    """)
    return


if __name__ == "__main__":
    app.run()
