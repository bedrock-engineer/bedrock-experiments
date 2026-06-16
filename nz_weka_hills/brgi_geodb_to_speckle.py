# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "folium>=0.12",
#     "geopandas==1.1.3",
#     "mapclassify==2.10.0",
#     "marimo>=0.23.9",
#     "matplotlib==3.11.0",
#     "polars==1.41.2",
#     "pyarrow==24.0.0",
#     "pyvista==0.48.4",
# ]
# ///
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
    gpkg_path = cwd / "wekahills_gi.gpkg"
    raw_githubusercontent_url = "https://raw.githubusercontent.com/bedrock-engineer/bedrock-ge/main/examples/nz_weka_hills_leapfrog/wekahills_gi.gpkg"
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

    geology = gpd.read_file(gpkg_path, layer="Geology")
    geology = geology.dropna(subset="Simple_Lith")

    spt = gpd.read_file(gpkg_path, layer="SPT")
    spt = spt.dropna(subset="SPT")
    # spt = spt[1000:1250]

    # Output
    mo.ui.tabs({"Map": lonlatheight.explore(), "Geology": geology, "SPT": spt})
    return (geology,)


@app.cell
def _(geology, mo, pd, pl, uuid):
    geology_spkl_props = (
        pl.from_pandas(
            pd.DataFrame(geology).assign(
                coords=[list(g.coords) for g in geology.geometry],
                geometry=geology.geometry.astype(str),
            )
        )
        .rename({"geometry": "wkt_geometry"})
        .with_columns(
            pl.col("Simple_Lith")
            .alias("material_name"),
            pl.col("Simple_Lith")
            .replace(
                {
                    "Limestone": "#5FBEF7",
                    "Siltstone": "#4C9973",
                    "Basement": "#852FC7",
                    "Alluvium": "#FFD505",
                    "Granodiorite": "#4DF756",
                    "Vein 1": "#FFC0CB",
                    "Vein 2": "#FF69B4",
                }
            )
            .alias("color_hex"),
        ).with_columns(
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
        )
    )

    mo.ui.table(geology_spkl_props, style_cell=lambda _r, _c, hex: {"backgroundColor": hex})
    return (geology_spkl_props,)


@app.cell
def _(mcolors, plt):
    def spt_n_to_hex(v: int) -> str:
        norm = mcolors.Normalize(vmin=0, vmax=100, clip=True)
        cmap = plt.get_cmap("plasma")
        return mcolors.to_hex(cmap(norm(v)))
    return


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
    return


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
    radius = 2
    def coords_to_pyvista_mesh(coords: list[list[float]]) -> pv.PolyData:
        if len(coords) == 1:
            return pv.Sphere(
                center=np.array(coords[0]),
                radius=radius + 0.1,
                theta_resolution=10,
                phi_resolution=10,
            )
        elif len(coords) == 2:
            return pv.Tube(
                pointa=coords[0],
                pointb=coords[1],
                radius=radius,
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
        props_df: pl.DataFrame, collection_name: str
    ) -> sco.Collection:
        spkl_data_objs = []
        for row in props_df.iter_rows(named=True):
            application_id = row.pop("application_id")
            coords = row.pop("coords")
            obj_name = row.pop("material_name")
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

        return sco.Collection(name=collection_name, elements=spkl_data_objs)
    return (props_df_to_speckle_collection,)


@app.cell
def _(geology_spkl_props, pl):
    color_proxies_df = geology_spkl_props.select(
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
def _(geology_spkl_props, props_df_to_speckle_collection):
    geology_collection = props_df_to_speckle_collection(geology_spkl_props, collection_name="geology")
    return (geology_collection,)


@app.cell
def _(geology_collection):
    geology_collection.elements[10].__dict__
    return


@app.cell
def _(geology_collection, sco, spkl_color_proxies, spkl_material_proxies):
    spkl_gi = sco.Collection(name="gi")
    spkl_gi.elements = [geology_collection]
    spkl_gi.renderMaterialProxies = spkl_material_proxies
    spkl_gi.colorProxies = spkl_color_proxies
    return (spkl_gi,)


@app.cell
def _(SpeckleClient, get_default_account, get_local_accounts, mo):
    # Get all locally stored accounts
    accounts = get_local_accounts()

    for account in accounts:
        print(f"Server: {account.serverInfo.url} , User: {account.userInfo.name}")

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
    spkl_gi,
):
    output = None

    if send_to_speckle.value:
        transport = ServerTransport(stream_id=project.id, client=client)
        object_id = operations.send(base=spkl_gi, transports=[transport])
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
def _():
    return


@app.cell
def _(mo):
    mo.md(r"""
    # Plot the display values (PyVista spheres & pipes)
    """)
    return


@app.cell
def _(coords_to_pyvista_mesh, geology_spkl_props, pl):
    pv_mesh_df = geology_spkl_props.with_columns(
        pl.col("coords").map_elements(coords_to_pyvista_mesh, return_dtype=pl.Object).alias("pyvista_mesh")
    )
    pv_mesh_df
    return (pv_mesh_df,)


@app.cell
def _(mo):
    plot_button = mo.ui.run_button(label="Press to plot")
    plot_button
    return (plot_button,)


@app.cell
def _(plot_button, pv, pv_mesh_df):
    if plot_button.value:
        plotter = pv.Plotter()
        for pv_row in pv_mesh_df.iter_rows(named=True):
            plotter.add_mesh(pv_row["pyvista_mesh"], color=pv_row["color"])

        plotter.show()
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
    tube = line.tube(radius=0.1)  # returns PolyData (a tube mesh)

    # Visualize
    # tube.plot(smooth_shading=True)

    type(tube)
    return


if __name__ == "__main__":
    app.run()
