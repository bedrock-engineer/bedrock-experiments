# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "bimpolars[speckle]",
#     "folium==0.20.0",
#     "geopandas==1.2.0",
#     "mapclassify==2.11.0",
#     "marimo",
#     "marimo-lens==0.2.4",
#     "matplotlib==3.11.2",
#     "obstore>=0.11.1",
#     "polars==2.1.0",
#     "pyproj==3.8.0",
#     "shapely==2.2.0",
#     "specklepy[bundle]==2026.9.1",
#     "specklewidgets",
#     "tzdata==2026.5",
#     "wigglystuff==0.5.36",
# ]
#
# [tool.uv.sources]
# bimpolars = { git = "https://github.com/bedrock-engineer/bimpolars" }
# specklewidgets = { git = "https://github.com/bedrock-engineer/specklestuff" }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import io
    import json
    import os
    from collections.abc import Callable, Iterator
    from urllib.parse import urlsplit

    import bimpolars as bpl
    import geopandas as gpd
    import marimo as mo
    import obstore
    import polars as pl
    import shapely
    import shapely.affinity
    from marimo_lens import Lens
    from obstore.store import S3Store
    import pyproj
    from pyproj import CRS, Transformer
    from specklepy.api.credentials import get_local_accounts
    from specklepy.api.inputs.user_inputs import UserProjectsFilter
    from specklepy.objects.models.units import get_scale_factor_from_string
    from specklewidgets import GeoSpeckleViewer, SpeckleViewer
    from specklewidgets import server as speckle_server
    from specklewidgets.geo import osm_ground_map, pdok_3d_buildings
    from wigglystuff import EnvConfig

    return (
        CRS,
        Callable,
        EnvConfig,
        GeoSpeckleViewer,
        Iterator,
        Lens,
        S3Store,
        SpeckleViewer,
        Transformer,
        UserProjectsFilter,
        bpl,
        get_local_accounts,
        get_scale_factor_from_string,
        gpd,
        io,
        json,
        mo,
        obstore,
        os,
        osm_ground_map,
        pdok_3d_buildings,
        pl,
        pyproj,
        shapely,
        speckle_server,
        urlsplit,
    )


@app.cell
def _(Lens):
    # marimo-lens: select a region of any output and add a note for the notebook agent
    lens = Lens()
    lens
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Revit Advanced Sample Project to R2

    Receives Speckle model versions in both of Speckle's data models, pushes them to
    Cloudflare R2, and reads them back from R2 into Speckle's viewer.

    1. **Speckle bundle (2026.9 data model):** the version's Parquet files (`eav.*`, `envelope.*`,
       `geometries`), as Speckle serves them.
    2. **Speckle v3 objects (pre-2026.9 object graph):** every object's JSON. Versions that only
       exist as a bundle have no JSON on the server; specklewidgets builds their objects
       from the bundle with bimpolars' `bundle_objects`.

    The defaults pick the three models of Autodesk's Revit Advanced Sample Project on
    app.speckle.systems: architecture, structure and MEP.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Speckle
    """)
    return


@app.cell
def _(get_local_accounts, mo):
    # Accounts from Speckle Manager or the connectors, as in download_models.py
    local_accounts = get_local_accounts()
    _servers = sorted(
        {_account.serverInfo.url.rstrip("/") for _account in local_accounts}
        | {"https://app.speckle.systems", "https://speckle.bedrock.engineer"}
    )
    server_picker = mo.ui.dropdown(_servers, value="https://app.speckle.systems", label="Server")
    server_picker
    return (server_picker,)


@app.cell
def _(EnvConfig, mo, server_picker, speckle_server):
    # This machine's Speckle account for the server if one works, else a personal access token
    local_client = speckle_server.local_client(server_picker.value)
    speckle_token = mo.ui.anywidget(
        EnvConfig({"SPECKLE_TOKEN": lambda _token: speckle_server.token_client(_token, server_picker.value)})
    )
    None if local_client else mo.vstack(
        [mo.md(f"No working local account for `{server_picker.value}`: paste a personal access token."), speckle_token]
    )
    return local_client, speckle_token


@app.cell
def _(local_client, mo, server_picker, speckle_server, speckle_token):
    mo.stop(local_client is None and not speckle_token.all_valid)
    speckle_client = local_client or speckle_server.token_client(speckle_token["SPECKLE_TOKEN"], server_picker.value)
    # Self-hosted Speckle 2.x servers have neither bundles nor workspaces
    _server = speckle_client.server.get()
    serves_bundles = not _server.version.startswith("2.")
    has_workspaces = bool(_server.workspaces and _server.workspaces.workspaces_enabled)
    mo.md(
        f"Signed in to `{server_picker.value}` as **{speckle_client.account.userInfo.name}**, "
        f"with {'the local account' if local_client else 'the token above'}.\n\n"
        f"The server runs Speckle {_server.version}. "
        + (
            "Versions come as a Speckle bundle and as Speckle v3 objects. "
            if serves_bundles
            else "That is Speckle 2.x, so versions come as Speckle v3 objects only, without a Speckle bundle. "
        )
        + ("Projects are grouped in workspaces." if has_workspaces else "It has no workspaces.")
    )
    return has_workspaces, serves_bundles, speckle_client


@app.cell
def _(all_items, has_workspaces, mo, speckle_client):
    # Workspaces, when the server has them. "" stands for the projects outside any workspace.
    workspaces = (
        {
            _workspace.name: _workspace.id
            for _workspace in all_items(
                lambda _cursor: speckle_client.active_user.get_workspaces(limit=50, cursor=_cursor)
            )
        }
        if has_workspaces
        else {}
    )
    workspace_picker = mo.ui.dropdown(
        {"Personal projects": "", **workspaces},
        value="Joost's Sandbox" if "Joost's Sandbox" in workspaces else "Personal projects",
        label="Workspace",
    )
    workspace_picker if has_workspaces else None
    return (workspace_picker,)


@app.cell
def _(
    UserProjectsFilter,
    all_items,
    has_workspaces,
    mo,
    speckle_client,
    workspace_picker,
):
    if has_workspaces and workspace_picker.value:
        _projects = all_items(
            lambda _cursor: speckle_client.workspace.get_projects(workspace_picker.value, limit=50, cursor=_cursor)
        )
    else:
        _filter = UserProjectsFilter(personal_only=True) if has_workspaces else None
        _projects = all_items(
            lambda _cursor: speckle_client.active_user.get_projects(limit=50, cursor=_cursor, filter=_filter)
        )
    projects = {f"{_project.name} ({_project.id})": _project.id for _project in _projects}
    _default = next((_label for _label, _id in projects.items() if _id == "461cc2a20f"), None)
    project_picker = mo.ui.dropdown(projects, value=_default, label="Project")
    project_picker
    return (project_picker,)


@app.cell
def _(all_items, mo, project_picker, speckle_client):
    mo.stop(not project_picker.value, mo.md("Pick a project."))
    models = {
        _model.id: f"{_model.name} ({_model.id})"
        for _model in all_items(
            lambda _cursor: speckle_client.project.get_with_models(
                project_picker.value, models_limit=50, models_cursor=_cursor
            ).models
        )
    }
    _rvt_advanced_sample = {"e7f5f7f943", "ef7cb591fc", "363cae173a", "35e9a2fa3b"}
    # One checkbox per model, stacked: the value maps each model id to whether it is picked
    model_picker = mo.ui.dictionary(
        {
            _id: mo.ui.checkbox(value=_id in _rvt_advanced_sample, label=_label)
            for _id, _label in models.items()
        }
    )
    mo.vstack([mo.md("Models"), *(model_picker[_id] for _id in models)], gap=0.25)
    return (model_picker,)


@app.cell
def _(
    mo,
    model_picker,
    pl,
    project_picker,
    server_picker,
    serves_bundles,
    speckle_client,
):
    picked_models = [_id for _id, _picked in model_picker.value.items() if _picked]
    mo.stop(not picked_models, mo.md("Pick one or more models."))
    # The latest version of each model. A referenced_object starting with "bundle." means
    # the version only exists as a bundle, without v3 JSON objects on the server.
    _rows = []
    for _model_id in picked_models:
        _model = speckle_client.model.get(_model_id, project_picker.value)
        _version = speckle_client.version.get_versions(
            project_id=project_picker.value, model_id=_model_id, limit=1
        ).items[0]
        _rows.append(
            {
                "server": server_picker.value,
                "project_id": project_picker.value,
                "model_id": _model_id,
                "model_name": _model.name,
                "version_id": _version.id,
                "created_at": _version.created_at,
                "source_application": _version.source_application,
                "referenced_object": _version.referenced_object,
                "has_bundle": serves_bundles,
            }
        )
    latest_versions = pl.DataFrame(_rows).with_columns(
        bundle_only=pl.col("referenced_object").str.starts_with("bundle.")
    )
    receive_button = mo.ui.run_button(label="Receive these versions")
    mo.vstack([latest_versions, receive_button])
    return latest_versions, receive_button


@app.cell
def _(latest_versions, mo, pl, receive_button, speckle_client, speckle_server):
    mo.stop(not receive_button.value, mo.md("Press **Receive these versions**."))
    # Each version as its bundle, in a temporary folder, and as v3 objects: the server's, or
    # built from the bundle when the version only exists as a bundle
    received = {
        _version["model_name"]: speckle_server.receive(
            speckle_client, _version["project_id"], _version["model_id"], _version["version_id"]
        )
        for _version in mo.status.progress_bar(latest_versions.to_dicts(), title="Receiving", show_eta=True)
    }
    bundle_files = {
        _name: sorted(_path for _path in _version.bundle.iterdir() if _path.is_file()) if _version.bundle else []
        for _name, _version in received.items()
    }
    pl.DataFrame(
        [
            {
                "model_name": _name,
                "version_id": _version.version_id,
                "v3_route": _version.v3_route,
                "speckle_bundle_files": len(bundle_files[_name]),
                "speckle_bundle_mb": sum(_path.stat().st_size for _path in bundle_files[_name]) / 1e6,
                "speckle_v3_objects": len(_version.objects),
            }
            for _name, _version in received.items()
        ]
    )
    return bundle_files, received


@app.cell
def _(json, pl, received):
    # One row per v3 object of every received version, each version's root first
    speckle_v3_objects = pl.DataFrame(
        [
            {
                "server": _version.server,
                "project_id": _version.project_id,
                "model_id": _version.model_id,
                "model_name": _name,
                "version_id": _version.version_id,
                "v3_route": _version.v3_route,
                "object_id": _object["id"],
                "is_root": _index == 0,
                "content": json.dumps(_object, separators=(",", ":")),
            }
            for _name, _version in received.items()
            for _index, _object in enumerate(_version.objects)
        ]
    )
    speckle_v3_objects.drop("content")
    return (speckle_v3_objects,)


@app.cell
def _(SpeckleViewer, received):
    # The received versions, straight from Speckle, before they go to R2
    received_viewer = SpeckleViewer([_version.objects for _version in received.values()])
    received_viewer
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Floor slab footprints

    Where each model says it is. A footprint is the outline of a model's ground floor slab: the largest
    Revit floor, or IfcSlab of type FLOOR or BASESLAB, on the lowest level. A Revit model goes from model
    coordinates to shared coordinates with its sharedCoordinates transform, so its survey point sits at
    the geolocation Revit stores. An IFC model has no such transform: its IfcSite geolocation sits at
    the model's origin. The dots are the geolocations.
    """)
    return


@app.cell(hide_code=True)
def _(gpd, ground_slab_footprint, mo, received, received_bims):
    # The ground floor slab of each model, at the geolocation of its survey point
    slab_footprints = gpd.GeoDataFrame([ground_slab_footprint(_name, _version, received_bims[_name]) for _name, _version in received.items()], crs="EPSG:4326")
    slab_model = mo.ui.radio(
        options=["All models", *slab_footprints["model_name"]],
        value=slab_footprints["model_name"].iloc[0],
        inline=True,
    )
    slab_model
    return slab_footprints, slab_model


@app.cell(hide_code=True)
def _(gpd, slab_footprints, slab_model):
    # The picked model's slab footprint, with a dot at its geolocation
    _slabs = (
        slab_footprints
        if slab_model.value == "All models"
        else slab_footprints[slab_footprints["model_name"] == slab_model.value]
    )
    _geolocations = gpd.GeoDataFrame(
        _slabs[["model_name", "latitude", "longitude"]],
        geometry=gpd.points_from_xy(_slabs["longitude"], _slabs["latitude"]),
        crs="EPSG:4326",
    )
    _map = _slabs.explore(column="model_name", style_kwds={"fillOpacity": 0.6})
    _geolocations.explore(m=_map, color="black", marker_kwds={"radius": 4})
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Aligning the Revit advanced sample models in Amsterdam Noord

    The black dots above are the survey points. The architecture and structure models share theirs,
    at the bottom left of the ground floor slab, and their columns coincide to the millimeter. The MEP
    model's survey point was never set: it still sits on the internal origin, and its geolocation is
    Munich. Fitting MEP's structural columns onto the architecture model's puts the shared survey point
    at (-12.28, -12.31) m in MEP's internal coordinates, give or take 10 cm, as MEP drew its columns
    again by hand.

    With the survey points lined up, all three models go to Amsterdam Noord with the parameters
    `amsterdam_noord_geobim.py` fits from the Rhino placement of the structure model: where the
    architecture model's internal origin lies in RD New + NAP height (EPSG:7415), and how far it is
    rotated from grid north.
    """)
    return


@app.cell
def _():
    # The MEP model's survey point, which Revit left on the internal origin, in internal mm
    SURVEY_POINT_CORRECTIONS = {
        "rvt-advanced-sample-mep": (-12275.0, -12309.0, 0.0)
    }
    # The architecture model's internal origin in RD New + NAP height, from amsterdam_noord_geobim.py
    AMS_NOORD_GEOREF_PARAMS = {
        "compound_crs": "EPSG:7415",
        "easting": 122096,
        "northing": 488756,
        "orthometric_height": 3.3,
        "rotation": -160,
    }
    return AMS_NOORD_GEOREF_PARAMS, SURVEY_POINT_CORRECTIONS


@app.cell
def _(lightbim_dataframe, received):
    # The received versions with footprints and LightBIM features, read once, so that editing the
    # placement does not read them again
    received_bims = {_name: lightbim_dataframe(_version) for _name, _version in received.items()}
    return (received_bims,)


@app.cell
def _(AMS_NOORD_GEOREF_PARAMS, mo):
    # To edit: the map below follows every change, the GeoSpeckleViewer only the Place button
    ams_noord_georef = mo.ui.dictionary(
        {
            "compound_crs": mo.ui.text(
                value=AMS_NOORD_GEOREF_PARAMS["compound_crs"], 
                disabled=True
            ),
            "easting": mo.ui.number(
                value=AMS_NOORD_GEOREF_PARAMS["easting"],
                step=1,
                debounce=True,
            ),
            "northing": mo.ui.number(
                value=AMS_NOORD_GEOREF_PARAMS["northing"],
                step=1,
                debounce=True,
            ),
            "orthometric_height": mo.ui.number(       
                value=AMS_NOORD_GEOREF_PARAMS["orthometric_height"],
                step=0.2,
                debounce=True,
            ),
            "rotation": mo.ui.number(
                value=AMS_NOORD_GEOREF_PARAMS["rotation"],
                step=2,
                debounce=True,
            ),
        },
        label="amsterdam_noord_georef_params",
    )
    # The parameters the models in the GeoSpeckleViewer are placed with: the ones above as they were when
    # Place was last pressed
    get_placed_georef, set_placed_georef = mo.state(AMS_NOORD_GEOREF_PARAMS)
    ams_noord_place = mo.ui.button(
        label="Place the models in the GeoSpeckleViewer",
        on_click=lambda _: set_placed_georef(ams_noord_georef.value),
    )
    return ams_noord_georef, ams_noord_place, get_placed_georef


@app.cell(hide_code=True)
def _(
    CRS,
    Transformer,
    ams_noord_georef,
    ams_noord_place,
    bpl,
    gpd,
    ground_slab,
    mo,
    received,
    received_bims,
    shapely,
    survey_point,
):
    # The structure model's ground floor slab where the parameters below put it
    _georef = ams_noord_georef.value
    _site_crs = bpl.site_crs(
        **_georef, unit="millimetre", name="Amsterdam Noord"
    )
    _to_compound = Transformer.from_crs(
        _site_crs, _georef["compound_crs"], always_xy=True
    )
    _slab = ground_slab(received_bims["rvt-advanced-sample-str"])
    # From the structure model's survey point to the architecture model's, where the site CRS starts
    _shift = [
        _ref - _own
        for _ref, _own in zip(
            survey_point(received["rvt-advanced-sample-arch"]),
            survey_point(received["rvt-advanced-sample-str"]),
        )
    ]
    _outline = shapely.affinity.translate(
        shapely.force_3d(shapely.from_wkb(_slab["footprint"])), *_shift
    )
    _outline = shapely.force_2d(
        shapely.transform(
            _outline, _to_compound.transform, include_z=True, interleaved=False
        )
    )
    _map = gpd.GeoDataFrame(
        [
            {
                "slab": _slab["name"],
                "level": _slab["level"],
                "area_m2": round(_slab["area_m2"]),
            }
        ],
        geometry=[_outline],
        crs=CRS(_georef["compound_crs"]).sub_crs_list[0],
    ).explore(style_kwds={"fillOpacity": 0.5})
    mo.vstack([_map, ams_noord_georef, ams_noord_place])
    return


@app.cell(hide_code=True)
def _(
    GeoSpeckleViewer,
    ams_noord_bim,
    ams_noord_ground_map,
    ams_noord_tilesets,
    mo,
    received,
    survey_point,
):
    # All models in Amsterdam Noord as one BimDataFrame, with axes at the shared survey point
    ams_noord_viewer = mo.ui.anywidget(
        GeoSpeckleViewer(
            ams_noord_bim,
            ground_map=ams_noord_ground_map,
            tilesets=ams_noord_tilesets,
            markers=[
                {
                    "name": "Survey Point",
                    "position": [
                        _value / 1000
                        for _value in survey_point(
                            received["rvt-advanced-sample-arch"]
                        )
                    ],
                }
            ],
            height=550
        )
    )
    ams_noord_viewer
    return (ams_noord_viewer,)


@app.cell(hide_code=True)
def _(ams_noord_bim, ams_noord_viewer, mo, pl):
    selected_elements_bdf = ams_noord_bim.frame.filter(
        pl.col("id").is_in(
            [
                _obj["applicationId"]
                for _obj in ams_noord_viewer.value["selected"]
            ]
        )
    )
    mo.vstack(
        [
            mo.md(f"**Selected elements**: {len(selected_elements_bdf)}"),
            selected_elements_bdf,
        ]
    )
    return


@app.cell(hide_code=True)
def _(
    SURVEY_POINT_CORRECTIONS,
    Transformer,
    bpl,
    get_placed_georef,
    pl,
    pyproj,
    received,
    received_bims,
    survey_point,
):
    # RD New + NAP to WGS 84 follows RDNAPTRANS2018 only with the NSGI grids, which PROJ fetches
    pyproj.network.set_network_enabled(True)

    # Each model in the architecture model's site CRS: its own CRS puts its survey point on the
    # architecture model's, and to_crs moves its geometry from there
    _georef = get_placed_georef()
    ams_noord_site_crs = bpl.site_crs(
        **_georef, unit="millimetre", name="Amsterdam Noord"
    )
    _site_to_compound = Transformer.from_crs(
        ams_noord_site_crs, _georef["compound_crs"], always_xy=True
    )
    _reference = survey_point(received["rvt-advanced-sample-arch"])
    ams_noord_models = {}
    _rows = []
    for _name, _bim in received_bims.items():
        _survey = SURVEY_POINT_CORRECTIONS.get(
            _name, survey_point(received[_name])
        )
        _origin = _site_to_compound.transform(
            *(_ref - _own for _ref, _own in zip(_reference, _survey))
        )
        _crs = bpl.site_crs(
            _georef["compound_crs"],
            *_origin,
            _georef["rotation"],
            unit=_bim,
            name=_name,
        )
        ams_noord_models[_name] = bpl.to_crs(
            bpl.set_crs(_bim, _crs), ams_noord_site_crs
        )
        _rows.append(
            {
                "model_name": _name,
                "survey_point_mm": [round(_value, 1) for _value in _survey],
                "internal_origin_easting": round(_origin[0], 3),
                "internal_origin_northing": round(_origin[1], 3),
                "internal_origin_height": round(_origin[2], 3),
            }
        )

    # All models as one BimDataFrame in the site CRS, with the model each element comes from. Element
    # ids are unique across the models; only the synthetic level ids (level-3) repeat. model_name goes
    # first and the long Revit ids last, so that a table of it reads from the model.
    ams_noord_bim = ams_noord_models["rvt-advanced-sample-arch"].with_frame(
        pl.concat(
            [_bimdf.frame.with_columns(model_name=pl.lit(_name)) for _name, _bimdf in ams_noord_models.items()],
            how="diagonal_relaxed",
        ).select("model_name", pl.exclude("model_name", "id"), "id")
    )
    pl.DataFrame(_rows)
    return ams_noord_bim, ams_noord_models


@app.cell
def _(ams_noord_models, osm_ground_map, pdok_3d_buildings):
    # OpenStreetMap 150 m around the architecture model, and the 3D BAG over the same area
    _arch = ams_noord_models["rvt-advanced-sample-arch"]
    ams_noord_ground_map = osm_ground_map(_arch)
    ams_noord_tilesets = [pdok_3d_buildings(_arch, ams_noord_ground_map["bounds"])]
    return ams_noord_ground_map, ams_noord_tilesets


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Combine arch and str

    - Remove topo and other "crap"
    - All of str + (arch - where arch coincides with str) or arch + str foundation?
      Verditct: All of str + some arch
    """)
    return


@app.cell(hide_code=True)
def _(ams_noord_bim, mo, pl):
    # The structure model's elements selected to start with. A marimo table can't start filtered, so
    # the other models' rows stay in the table, to add to the selection.
    ams_noord_bimtbl = mo.ui.table(
        ams_noord_bim.frame,
        initial_selection=ams_noord_bim.frame.with_row_index()
        .filter(pl.col("model_name") == "rvt-advanced-sample-str")
        .get_column("index")
        .to_list(),
    )
    ams_noord_bimtbl
    return (ams_noord_bimtbl,)


@app.cell(hide_code=True)
def _(
    GeoSpeckleViewer,
    ams_noord_bim,
    ams_noord_bimtbl,
    ams_noord_ground_map,
    ams_noord_tilesets,
    mo,
):
    # The rows selected in the table above, in the CRS all the Amsterdam Noord models share, on their
    # own on the same ground map and 3D BAG
    ams_noord_selected_in_table = ams_noord_bim.with_frame(ams_noord_bimtbl.value)

    ams_noord_single_model_viewer = mo.ui.anywidget(
        GeoSpeckleViewer(
            ams_noord_selected_in_table,
            ground_map=ams_noord_ground_map,
            tilesets=ams_noord_tilesets,
            height=525,
        )
    )
    ams_noord_single_model_viewer
    return (ams_noord_single_model_viewer,)


@app.cell(hide_code=True)
def _(ams_noord_bim, ams_noord_single_model_viewer, mo, pl):
    _sel_elements_bdf = ams_noord_bim.frame.filter(
        pl.col("id").is_in(
            [
                _obj["applicationId"]
                for _obj in ams_noord_single_model_viewer.value["selected"]
            ]
        )
    )
    mo.vstack(
        [
            mo.md(f"**Selected elements**: {len(_sel_elements_bdf)}"),
            _sel_elements_bdf,
        ]
    )
    return


@app.cell
def _(
    GeoSpeckleViewer,
    ams_noord_ground_map,
    ams_noord_models,
    ams_noord_tilesets,
    mo,
    pl,
):
    # The structure model's elements below ground level: those whose bbox tops out at or under the
    # ground map, which lies at the site origin's height (z = 0, the placed orthometric height)
    _str = ams_noord_models["rvt-advanced-sample-str"]
    ams_noord_str_below_ground = _str.with_frame(
        _str.frame.filter(pl.col("bbox").struct.field("zmax") <= 0)
    )
    ams_noord_str_below_ground_viewer = mo.ui.anywidget(
        GeoSpeckleViewer(
            ams_noord_str_below_ground,
            # Translucent, since every element here lies under the map
            ground_map={**ams_noord_ground_map, "opacity": 0.35},
            tilesets=ams_noord_tilesets,
            height=540,
        )
    )
    mo.vstack(
        [
            mo.md(
                f"{len(ams_noord_str_below_ground)} of {len(_str)} elements of the structure model lie below ground level."
            ),
            ams_noord_str_below_ground_viewer,
        ]
    )
    return


@app.cell
def _(ams_noord_models, mo, pl):
    # Arch and str in one BimDataFrame: all of str, plus the arch elements that str doesn't model
    # already. Arch's site and placeholder content goes first, and so does arch's own structure:
    # str is the structural model, and arch's canopy, for one, is a different design (W250 columns
    # and 8K1 joists against str's UC356 columns, UB beams and concrete deck). An arch element counts
    # as modelled by str when at least 80 % of its bbox lies inside the bbox of a str element of the
    # same class, like arch's hollow core planks inside str's 300 mm slabs and its core walls inside
    # str's. Across classes the test is too coarse: mullions fall inside the bbox of a str slab.
    ARCH_SITE_CLASSES = ["Topography", "Planting", "Parking", "Entourage", "Mass", "Rooms", "<Room Separation>", "Levels"]
    ARCH_STRUCTURAL_CLASSES = ["Structural Columns", "Structural Framing", "Structural Beam Systems"]
    # Arch's 75 mm canopy roof lay on arch's canopy joists; on str's concrete deck it would float
    ARCH_CANOPY_ROOF_ID = "5d2f94ca-45eb-4b7a-a78b-f803f510b4c4-0003122e"
    _arch = ams_noord_models["rvt-advanced-sample-arch"]
    _str = ams_noord_models["rvt-advanced-sample-str"]
    _arch_frame = _arch.frame.filter(
        ~pl.col("class").cast(pl.String).is_in(ARCH_SITE_CLASSES + ARCH_STRUCTURAL_CLASSES),
        pl.col("id") != ARCH_CANOPY_ROOF_ID,
    )
    _axes = ("xmin", "ymin", "zmin", "xmax", "ymax", "zmax")


    def _boxes(frame, suffix):
        return frame.filter(pl.col("bbox").is_not_null()).select(
            pl.col("id").alias(f"id{suffix}"), pl.col("class").cast(pl.String), *(pl.col("bbox").struct.field(_axis).alias(f"{_axis}{suffix}") for _axis in _axes)
        )


    def _extent(axis):
        return (
            pl.min_horizontal(f"{axis}max_a", f"{axis}max_s") - pl.max_horizontal(f"{axis}min_a", f"{axis}min_s")
        ).clip(0)


    _arch_in_str = (
        _boxes(_arch_frame, "_a")
        .join(_boxes(_str.frame, "_s"), on="class")
        .with_columns(
            _inside=_extent("x") * _extent("y") * _extent("z")
            / ((pl.col("xmax_a") - pl.col("xmin_a")) * (pl.col("ymax_a") - pl.col("ymin_a")) * (pl.col("zmax_a") - pl.col("zmin_a")))
        )
        .filter(pl.col("_inside") >= 0.8)
        .get_column("id_a")
        .unique()
    )
    ams_noord_arch_str = _str.with_frame(
        pl.concat(
            [
                _str.frame.with_columns(model_name=pl.lit("rvt-advanced-sample-str")),
                _arch_frame.filter(~pl.col("id").is_in(_arch_in_str.implode())).with_columns(
                    model_name=pl.lit("rvt-advanced-sample-arch")
                ),
            ],
            how="diagonal_relaxed",
        )
    )
    mo.md(
        f"""
        {len(_arch.frame) - len(_arch_frame)} site, placeholder and structural elements of arch left out

        {len(_arch_in_str)} arch elements modelled by str
    
        {len(ams_noord_arch_str)} elements combined
        """
    )
    return (ams_noord_arch_str,)


@app.cell
def _(
    GeoSpeckleViewer,
    ams_noord_arch_str,
    ams_noord_ground_map,
    ams_noord_tilesets,
    mo,
):
    # Arch and str combined in Amsterdam Noord, colored by the model each element comes from
    ams_noord_arch_str_viewer = mo.ui.anywidget(
        GeoSpeckleViewer(
            ams_noord_arch_str,
            color="elevation",
            ground_map=ams_noord_ground_map,
            tilesets=ams_noord_tilesets,
            height=550,
        )
    )
    ams_noord_arch_str_viewer
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Pushing BIM-data to Cloudflare R2 object storage

    - BimDataFrame GeoParquets go to `<model_name>-bdf.parquet`
    - Speckle bundles go to `<prefix>/speckle-bundle/<model_id>/<version_id>/<file>`
    - Speckle v3 objects of all versions to `<prefix>/speckle-v3-objects.parquet`

    The R2 credentials come from the environment or the widget below, and are never written to disk.
    `R2_S3_API` is the bucket's S3 API URL as the Cloudflare dashboard shows it under R2, the
    bucket, Settings: `https://<account id>.eu.r2.cloudflarestorage.com/<bucket>`.
    """)
    return


@app.cell
def _(EnvConfig, latest_versions, mo, os, project_picker):
    # The S3 API URL is not secret, so it is a plain text field; the keys stay hidden
    r2_s3_api = mo.ui.text(
        value=os.environ.get("R2_S3_API", ""),
        placeholder="https://<account id>.eu.r2.cloudflarestorage.com/<bucket>",
        label="R2_S3_API",
        full_width=True,
    )
    r2_config = mo.ui.anywidget(EnvConfig(["R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"]))
    # The picked models' common name, such as rvt-advanced-sample, else the project id
    _common = os.path.commonprefix(latest_versions["model_name"].to_list()).rstrip("-_ ")
    r2_prefix = mo.ui.text(
        value=f"bimpolars/{_common or project_picker.value}",
        label="Prefix",
        full_width=True,
    )
    mo.vstack([r2_s3_api, r2_config, r2_prefix])
    return r2_config, r2_prefix, r2_s3_api


@app.cell
def _(S3Store, mo, r2_config, r2_s3_api, urlsplit):
    # The S3 API URL is the account's endpoint followed by the bucket
    _url = urlsplit(r2_s3_api.value.strip())
    _bucket = _url.path.strip("/")
    mo.stop(
        not (_url.scheme and _url.netloc and _bucket and r2_config.all_valid),
        mo.md("Set the R2 fields above."),
    )
    r2_store = S3Store(
        _bucket,
        endpoint=f"{_url.scheme}://{_url.netloc}",
        access_key_id=r2_config["R2_ACCESS_KEY_ID"],
        secret_access_key=r2_config["R2_SECRET_ACCESS_KEY"],
        region="auto",
    )
    return (r2_store,)


@app.cell
def _(bundle_files, io, mo, pl, r2_prefix, received, speckle_v3_objects):
    # What goes to R2: every Speckle bundle file, and the Speckle v3 objects as one Parquet file
    _prefix = r2_prefix.value.strip("/")
    _parquet = io.BytesIO()
    speckle_v3_objects.write_parquet(_parquet, compression="zstd")
    r2_uploads = {
        f"{_prefix}/speckle-bundle/{_version.model_id}/{_version.version_id}/{_path.name}": _path.read_bytes()
        for _name, _version in received.items()
        for _path in bundle_files[_name]
    } | {f"{_prefix}/speckle-v3-objects.parquet": _parquet.getvalue()}
    push_button = mo.ui.run_button(label=f"Push {len(r2_uploads)} files to R2")
    mo.vstack(
        [
            pl.DataFrame(
                {
                    "file": [_url_path.rsplit("/", 1)[-1] for _url_path in r2_uploads],
                    "url_path": list(r2_uploads),
                    "mb": [round(len(_data) / 1e6, 1) for _data in r2_uploads.values()],
                }
            ),
            push_button,
        ]
    )
    return push_button, r2_uploads


@app.cell
def _(mo, obstore, push_button, r2_store, r2_uploads):
    mo.stop(not push_button.value, mo.md("Press **Push** to upload. Existing keys are overwritten."))
    for _key, _data in mo.status.progress_bar(list(r2_uploads.items()), title="Pushing"):
        obstore.put(r2_store, _key, _data)
    pushed = list(r2_uploads)
    return (pushed,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Back from R2

    Everything below reads from R2 only: the listing under the prefix, and the v3 objects
    for the viewer. It reruns after a push.
    """)
    return


@app.cell
def _(io, obstore, pl, pushed, r2_prefix, r2_store):
    pushed
    _prefix = r2_prefix.value.strip("/")
    r2_listing = pl.DataFrame(
        [
            {"key": _meta["path"], "mb": _meta["size"] / 1e6, "last_modified": _meta["last_modified"]}
            for _batch in obstore.list(r2_store, prefix=_prefix)
            for _meta in _batch
        ]
    )
    r2_speckle_v3_objects = pl.read_parquet(
        io.BytesIO(obstore.get(r2_store, f"{_prefix}/speckle-v3-objects.parquet").bytes().to_bytes())
    )
    r2_listing
    return (r2_speckle_v3_objects,)


@app.cell
def _(SpeckleViewer, bpl, r2_speckle_v3_objects):
    r2_viewer = SpeckleViewer(
        [
            bpl.version_objects(r2_speckle_v3_objects, _version_id)
            for _version_id in r2_speckle_v3_objects["version_id"].unique(maintain_order=True)
        ]
    )
    r2_viewer
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Implementation
    """)
    return


@app.cell
def _(Callable, Iterator):
    def all_items(fetch: Callable) -> Iterator:
        """Every item of a paginated Speckle collection.

        Args:
            fetch: Takes a cursor (None for the first page) and returns a ResourceCollection.
        """
        cursor = None
        while True:
            page = fetch(cursor)
            yield from page.items
            cursor = page.cursor
            if not cursor or not page.items:
                return



    return (all_items,)


@app.cell
def _(bpl, pl, shapely):
    def lightbim_dataframe(version):
        """A received version as a BimDataFrame with footprints and LightBIM features.

        Args:
            version: A ReceivedVersion with its bundle, from speckle_server.receive.

        Returns:
            The BimDataFrame of bpl.simple_features(..., lightbim=True), in the model's own CRS.
        """
        bim = version.bimdataframe()
        # Speckle's IFC converter leaves category empty, so take the class from the IFC entity
        ifc_type = pl.col("properties").struct.field("object").struct.field("ifcType")
        if "ifcType" in bim.frame.lazy().select(pl.col("properties").struct.field("object").struct.unnest()).collect_schema():
            bim = bim.with_frame(
                bim.frame.with_columns(pl.coalesce(ifc_type, pl.col("class").cast(pl.String)).cast(pl.Categorical).alias("class"))
            )
        return bpl.simple_features(bim, lightbim=True)


    def ground_slab(bdf) -> dict:
        """A model's ground floor slab: the largest slab on the lowest level, as LightBIM classifies them.

        Args:
            bdf: A BimDataFrame from lightbim_dataframe.

        Returns:
            The slab's row, with its level's name as level and its footprint's area as area_m2.
        """
        to_m = bdf.crs.axis_info[0].unit_conversion_factor
        levels = bdf.frame.filter(pl.col("elevation").is_not_null()).select(
            pl.col("id").alias("footprint_ref"), pl.col("name").alias("level")
        )
        slabs = bdf.frame.filter(pl.col("lightbim_kind").struct.field("role") == "slab").join(
            levels, on="footprint_ref", how="left"
        )
        slabs = slabs.with_columns(
            bottom=pl.col("bbox").struct.field("zmin"),
            area_m2=pl.Series(shapely.area(shapely.from_wkb(slabs["footprint"].to_numpy())) * to_m**2),
        )
        lowest = slabs.sort("bottom").row(0, named=True)["footprint_ref"]
        return slabs.filter(pl.col("footprint_ref") == lowest).sort("area_m2", descending=True).row(0, named=True)

    return ground_slab, lightbim_dataframe


@app.cell
def _(
    CRS,
    Transformer,
    get_scale_factor_from_string,
    ground_slab,
    model_placement,
    shapely,
):
    def ground_slab_footprint(model_name: str, version, bdf) -> dict:
        """The footprint of a version's ground floor slab, placed at its geolocation.

        The ground floor slab comes from ground_slab, with its footprint in model coordinates. A
        Revit bundle's sharedCoordinates transform then puts the survey point at 0,0 with the axes to true
        north; an IFC bundle has none, and its geolocation (from IfcSite) refers to the model's
        origin. A transverse Mercator projection centered on the geolocation finally gives
        longitude and latitude.

        Args:
            model_name: The version's model name.
            version: A ReceivedVersion with its bundle, from speckle_server.receive.
            bdf: The version's BimDataFrame, from lightbim_dataframe.

        Returns:
            model_name, slab, level, area_m2, the geolocation's latitude and longitude, and the
            footprint as a shapely Polygon or MultiPolygon in longitude and latitude.
        """
        to_m = bdf.crs.axis_info[0].unit_conversion_factor
        slab = ground_slab(bdf)

        placement = model_placement(version)
        identity = "1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1"
        m = [float(value) for value in placement.get("modelPlacement.options.sharedCoordinates.transform", identity).split(",")]
        shared_to_m = get_scale_factor_from_string(placement.get("modelPlacement.units", "m"), "m")
        # Model units to shared metres: the row-major 4x4's plan part, its translation in its own units
        outline = shapely.affinity.affine_transform(
            shapely.force_2d(shapely.from_wkb(slab["footprint"])),
            [m[0] * to_m, m[1] * to_m, m[4] * to_m, m[5] * to_m, m[3] * shared_to_m, m[7] * shared_to_m],
        )

        latitude = placement["geolocation.anchor.latitude"]
        longitude = placement["geolocation.anchor.longitude"]
        to_lonlat = Transformer.from_crs(
            CRS.from_proj4(f"+proj=tmerc +lat_0={latitude} +lon_0={longitude} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m"),
            "EPSG:4326",
            always_xy=True,
        )
        return {
            "model_name": model_name,
            "slab": slab["name"],
            "level": slab["level"],
            "area_m2": round(slab["area_m2"]),
            "latitude": latitude,
            "longitude": longitude,
            "geometry": shapely.transform(outline, to_lonlat.transform, interleaved=False),
        }

    return (ground_slab_footprint,)


@app.cell
def _(pl):
    def model_placement(version) -> dict:
        """The model-level placement values of a version's bundle, such as its reference points.

        Args:
            version: A ReceivedVersion with its bundle, from speckle_server.receive.

        Returns:
            Each path of the bundle's model table, such as geolocation.anchor.latitude, with its
            value: the text, or the number when there is no text.
        """
        (model_table,) = version.bundle.glob("*.eav.model.parquet")
        return {
            path: text if text is not None else number
            for path, text, number in pl.read_parquet(model_table).select("path", "value_string", "value_double").iter_rows()
        }


    def survey_point(version) -> tuple[float, float, float]:
        """A Revit version's survey point in internal coordinates, in the bundle's placement unit.

        Args:
            version: A ReceivedVersion with its bundle, from speckle_server.receive.

        Returns:
            x, y and z of the survey point, 0 where the bundle has none.
        """
        placement = model_placement(version)
        return tuple(float(placement.get(f"referencePoints.surveyPoint.position.{axis}", 0.0)) for axis in "xyz")

    return model_placement, survey_point


if __name__ == "__main__":
    app.run()
