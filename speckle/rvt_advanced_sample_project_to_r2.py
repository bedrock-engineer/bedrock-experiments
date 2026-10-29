# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "folium==0.20.0",
#     "geopandas==1.2.0",
#     "geospeckle",
#     "mapclassify==2.11.0",
#     "marimo",
#     "marimo-lens==0.2.4",
#     "matplotlib==3.11.2",
#     "obstore>=0.11.1",
#     "polars==2.1.0",
#     "pyproj==3.8.0",
#     "shapely==2.2.0",
#     "specklepy[bundle]==2026.9.1",
#     "tzdata==2026.5",
#     "wigglystuff==0.5.36",
# ]
#
# [tool.uv.sources]
# geospeckle = { path = "geospeckle", editable = true }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import hashlib
    import io
    import json
    import os
    import warnings
    from collections.abc import Callable, Iterator
    from pathlib import Path
    from urllib.parse import urlsplit

    import geopandas as gpd
    import marimo as mo
    import obstore
    import polars as pl
    import shapely
    from geospeckle import GeoSpeckleViewer, models_gz
    from marimo_lens import Lens
    from obstore.store import S3Store
    from pyproj import CRS, Transformer
    from specklepy import bundle
    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import Account, get_local_accounts
    from specklepy.api.inputs.user_inputs import UserProjectsFilter
    from specklepy.objects.models.collections.collection import Collection
    from specklepy.objects.models.units import get_scale_factor_from_string
    from specklepy.transports.memory import MemoryTransport
    from specklepy.transports.server import ServerTransport
    from wigglystuff import EnvConfig

    return (
        Account,
        CRS,
        Callable,
        Collection,
        EnvConfig,
        GeoSpeckleViewer,
        Iterator,
        Lens,
        MemoryTransport,
        Path,
        S3Store,
        ServerTransport,
        SpeckleClient,
        Transformer,
        UserProjectsFilter,
        bundle,
        get_local_accounts,
        get_scale_factor_from_string,
        gpd,
        hashlib,
        io,
        json,
        mo,
        models_gz,
        obstore,
        operations,
        os,
        pl,
        shapely,
        urlsplit,
        warnings,
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
    Cloudflare R2, and reads them back from R2 into the GeoSpeckle Viewer.

    1. **Speckle bundle (2026.9 data model):** the version's Parquet files (`eav.*`, `envelope.*`,
       `geometries`), as `bundle.receive` downloads them.
    2. **Speckle v3 objects (pre-2026.9 object graph):** every object's JSON. Versions that only
       exist as a bundle have no JSON on the server; their objects are projected from the
       bundle with `Model.to_base()`.

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
    return local_accounts, server_picker


@app.cell
def _(
    EnvConfig,
    local_accounts,
    local_speckle_client,
    mo,
    server_picker,
    token_speckle_client,
):
    # A local account for the server if there is one that works, else a personal access token
    local_client = local_speckle_client(local_accounts, server_picker.value)
    speckle_token = mo.ui.anywidget(
        EnvConfig({"SPECKLE_TOKEN": lambda _token: token_speckle_client(server_picker.value, _token)})
    )
    None if local_client else mo.vstack(
        [mo.md(f"No working local account for `{server_picker.value}`: paste a personal access token."), speckle_token]
    )
    return local_client, speckle_token


@app.cell
def _(local_client, mo, server_picker, speckle_token, token_speckle_client):
    mo.stop(local_client is None and not speckle_token.all_valid)
    speckle_client = local_client or token_speckle_client(server_picker.value, speckle_token["SPECKLE_TOKEN"])
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
    _rvt_advanced_sample = {"ef7cb591fc", "363cae173a", "35e9a2fa3b"}
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
def _(
    latest_versions,
    mo,
    pl,
    receive_button,
    receive_version,
    speckle_client,
):
    mo.stop(not receive_button.value, mo.md("Press **Receive these versions**."))
    received = [
        receive_version(speckle_client, _version)
        for _version in mo.status.progress_bar(
            latest_versions.to_dicts(), title="Receiving", show_eta=True
        )
    ]
    pl.DataFrame(
        [
            {
                "model_name": _version["model_name"],
                "version_id": _version["version_id"],
                "v3_route": _version["v3_route"],
                "speckle_bundle_files": len(_version["speckle_bundle"]),
                "speckle_bundle_mb": sum(map(len, _version["speckle_bundle"].values())) / 1e6,
                "speckle_v3_objects": len(_version["speckle_v3_objects"]),
                "speckle_v3_mb": sum(map(len, _version["speckle_v3_objects"])) / 1e6,
            }
            for _version in received
        ]
    )
    return (received,)


@app.cell
def _(received, speckle_v3_objects_frame):
    # One row per v3 object of every received version, each version's root first
    speckle_v3_objects = speckle_v3_objects_frame(received)
    speckle_v3_objects.drop("content")
    return (speckle_v3_objects,)


@app.cell
def _(GeoSpeckleViewer, models_gz, speckle_v3_objects, version_objects_json):
    # The received versions, straight from Speckle, before they go to R2
    received_viewer = GeoSpeckleViewer(
        objects_gz=models_gz(
            *(
                version_objects_json(speckle_v3_objects, _version_id, _model_name)
                for _version_id, _model_name in speckle_v3_objects.select("version_id", "model_name")
                .unique(maintain_order=True)
                .iter_rows()
            )
        )
    )
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


@app.cell
def _(gpd, ground_slab_footprint, mo, received):
    # The ground floor slab of each model, at the geolocation of its survey point
    slab_footprints = gpd.GeoDataFrame([ground_slab_footprint(_version) for _version in received], crs="EPSG:4326")
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
    ## Cloudflare R2

    The Speckle bundles go to `<prefix>/speckle-bundle/<model_id>/<version_id>/<file>`, and the
    Speckle v3 objects of all versions to `<prefix>/speckle-v3-objects.parquet`. The R2
    credentials come from the environment or the widget below, and are never written to disk.
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
def _(io, mo, pl, r2_prefix, received, speckle_v3_objects):
    # What goes to R2: every Speckle bundle file, and the Speckle v3 objects as one Parquet file
    _prefix = r2_prefix.value.strip("/")
    _parquet = io.BytesIO()
    speckle_v3_objects.write_parquet(_parquet, compression="zstd")
    r2_uploads = {
        f"{_prefix}/speckle-bundle/{_version['model_id']}/{_version['version_id']}/{_name}": _data
        for _version in received
        for _name, _data in _version["speckle_bundle"].items()
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
def _(
    GeoSpeckleViewer,
    models_gz,
    r2_speckle_v3_objects,
    version_objects_json,
):
    r2_viewer = GeoSpeckleViewer(
        objects_gz=models_gz(
            *(
                version_objects_json(r2_speckle_v3_objects, _version_id, _model_name)
                for _version_id, _model_name in r2_speckle_v3_objects.select("version_id", "model_name")
                .unique(maintain_order=True)
                .iter_rows()
            )
        )
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
def _(Account, Callable, Iterator, SpeckleClient):
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


    def local_speckle_client(accounts: list[Account], server_url: str) -> SpeckleClient | None:
        """A client signed in with the local account for a server, or None if it has none
        or its token no longer works."""
        account = next(
            (account for account in accounts if account.serverInfo.url.rstrip("/") == server_url), None
        )
        if account is None:
            return None
        client = SpeckleClient(host=server_url)
        client.authenticate_with_account(account)
        try:
            client.active_user.get()
        except Exception:
            return None
        return client


    def token_speckle_client(server_url: str, token: str) -> SpeckleClient:
        """A client signed in with a personal access token; raises if the token doesn't work."""
        client = SpeckleClient(host=server_url)
        client.authenticate_with_token(token)
        user = client.active_user.get()
        if user is None:
            raise ValueError(f"The token is not valid on {server_url}")
        return client

    return all_items, local_speckle_client, token_speckle_client


@app.cell
def _(
    CRS,
    Collection,
    MemoryTransport,
    Path,
    ServerTransport,
    Transformer,
    bundle,
    get_scale_factor_from_string,
    hashlib,
    io,
    json,
    operations,
    pl,
    shapely,
    warnings,
):
    def _memory_objects(memory: MemoryTransport, root_id: str) -> list[str]:
        """The JSON of every object in a MemoryTransport, root first."""
        return [memory.objects[root_id], *(text for key, text in memory.objects.items() if key != root_id)]


    def _bundle_table(files: dict[str, bytes], table: str) -> pl.DataFrame:
        """One table of a bundle, such as eav.objects or envelope.nodes."""
        (name,) = [name for name in files if name.endswith(f".{table}.parquet")]
        return pl.read_parquet(io.BytesIO(files[name]))


    def _with_all_materials(objects: list[str], files: dict[str, bytes]) -> list[str]:
        """Adds the materials specklepy's bundle projection leaves out.

        `to_base` gives materials only to geometry that belongs to an element, so the geometry
        of family instances, which lives in instance definitions, renders in the viewer's
        default gray. This rebuilds the root's renderMaterialProxies from the bundle's
        envelope: DISPLAY relations (1) map an object to its geometry, HAS_MATERIAL (5) a
        geometry to its material node.
        """
        root = json.loads(objects[0])
        nodes = _bundle_table(files, "envelope.nodes")
        relations = _bundle_table(files, "envelope.relations")
        app_ids = dict(_bundle_table(files, "eav.objects").iter_rows())
        owner = dict(relations.filter(pl.col("rel") == 1).select("dst", "src").iter_rows())
        materials = {}
        for geometry, material in relations.filter(pl.col("rel") == 5).select("src", "dst").iter_rows():
            target = app_ids[owner[geometry]] if geometry in owner else f"def-geo-{geometry}"
            materials.setdefault(material, set()).add(target)
        proxies = []
        for row in nodes.filter(pl.col("kind") == 3, pl.col("id").is_in(list(materials))).iter_rows(named=True):
            value = {
                "speckle_type": "Objects.Other.RenderMaterial",
                "applicationId": f"mat-{row['id']}",
                "name": row["name"] or "material",
                "diffuse": row["argb"] if row["argb"] is not None else -1,
                "opacity": row["opacity"] if row["opacity"] is not None else 1.0,
                "metalness": row["metalness"] or 0.0,
                "roughness": row["roughness"] if row["roughness"] is not None else 1.0,
                "emissive": row["emissive"] or 0,
            }
            value["id"] = hashlib.md5(json.dumps(value, sort_keys=True).encode()).hexdigest()
            proxies.append(
                {
                    "id": hashlib.md5(value["id"].encode()).hexdigest(),
                    "speckle_type": "Objects.Other.RenderMaterialProxy",
                    "applicationId": value["applicationId"],
                    "objects": sorted(materials[row["id"]]),
                    "value": value,
                }
            )
        root["renderMaterialProxies"] = proxies
        return [json.dumps(root), *objects[1:]]


    def _to_base_with_element_geometry(model) -> Collection:
        """specklepy's bundle projection, keeping the geometry of placed elements.

        `to_base` turns an element with instance placements (DISPLAY_INSTANCE, relation 8)
        into InstanceProxy objects only, and drops the element's own DISPLAY geometry. Revit
        structural framing, columns and foundations keep their geometry on the element, in
        model coordinates, and get an empty instance definition, so they vanish. This adds that
        geometry as a DataObject under the element's applicationId, right before its first
        placement, which becomes `<applicationId>-instance-0`.

        Uses specklepy's private `_geometry_object`, so it is tied to the pinned specklepy.
        """
        root = model.to_base()
        elements = {}
        for object_k in {edge.src for edge in model.bundle.relations.display_instance_edges}:
            app_id = model.bundle.object_app_ids.get(object_k)
            element = app_id and bundle.base_projection._geometry_object(model, object_k, app_id)
            if element is not None:
                elements[app_id] = element

        def with_element_geometry(collection: Collection) -> None:
            children = []
            for child in collection.elements:
                if isinstance(child, Collection):
                    with_element_geometry(child)
                elif child.applicationId in elements:
                    children.append(elements[child.applicationId])
                    child.applicationId = child.id = f"{child.applicationId}-instance-0"
                children.append(child)
            collection.elements = children

        with_element_geometry(root)
        return root


    def receive_version(client, version: dict) -> dict:
        """Receives one version as a bundle and as v3 objects.

        Args:
            client: An authenticated SpeckleClient for the version's server.
            version: A row of latest_versions.

        Returns:
            The version row plus speckle_bundle (file name to bytes; empty on a server without
            bundles), speckle_v3_objects (JSON texts, root first) and v3_route: "server" when the
            server has the v3 objects, "projected" when they come from the bundle.
        """
        memory = MemoryTransport()
        speckle_bundle = {}
        # The v3 JSON pipeline (ServerTransport, MemoryTransport, operations.send) is
        # deprecated since 2026.9, and it is exactly the route we want a copy of.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            if version["has_bundle"]:
                with bundle.receive(
                    client.account,
                    version["project_id"],
                    version["model_id"],
                    version["version_id"],
                    mark_received=False,
                ) as model:
                    speckle_bundle = {path.name: path.read_bytes() for path in map(Path, model.files)}
                    if version["bundle_only"]:
                        root_id = operations.send(_to_base_with_element_geometry(model), transports=[memory], use_default_cache=False)
            if not version["bundle_only"]:
                root_id = version["referenced_object"]
                ServerTransport(stream_id=version["project_id"], client=client).copy_object_and_children(
                    root_id, memory
                )
        objects = _memory_objects(memory, root_id)
        if version["bundle_only"]:
            objects = _with_all_materials(objects, speckle_bundle)
        return {
            **version,
            "speckle_bundle": speckle_bundle,
            "speckle_v3_objects": objects,
            "v3_route": "projected" if version["bundle_only"] else "server",
        }


    def speckle_v3_objects_frame(received: list[dict]) -> pl.DataFrame:
        """The v3 objects of received versions as one table, each version's root first."""
        return pl.DataFrame(
            [
                {
                    "server": version["server"],
                    "project_id": version["project_id"],
                    "model_id": version["model_id"],
                    "model_name": version["model_name"],
                    "version_id": version["version_id"],
                    "v3_route": version["v3_route"],
                    "object_id": json.loads(text)["id"],
                    "is_root": index == 0,
                    "content": text,
                }
                for version in received
                for index, text in enumerate(version["speckle_v3_objects"])
            ]
        )


    def version_objects_json(speckle_v3_objects: pl.DataFrame, version_id: str, namespace: str) -> str:
        """One version's v3 objects as JSON array text, root first, for models_gz.

        Args:
            speckle_v3_objects: A table as speckle_v3_objects_frame makes it.
            version_id: Speckle version id.
            namespace: Prefix for the instance definition ids (def-...), so that projected
                bundles can share a viewer: rvt-oda-converter numbers them from def-1 in every
                model.
        """
        contents = speckle_v3_objects.filter(pl.col("version_id") == version_id).sort("is_root", descending=True)["content"]
        return ("[" + ",".join(contents) + "]").replace('"def-', f'"{namespace}/def-')


    def ground_slab_footprint(version: dict) -> dict:
        """The footprint of a version's ground floor slab, placed at its geolocation.

        The ground floor slab is the largest floor on the lowest level: a Revit floor, or an
        IfcSlab of type FLOOR or BASESLAB. Its geometry is the floor's own DISPLAY geometry,
        or, for a placed element such as an IfcSlab, its definition's geometry under each
        placement's transform. A Revit bundle's sharedCoordinates transform then puts the
        survey point at 0,0 with the axes to true north; an IFC bundle has none, and its
        geolocation (from IfcSite) refers to the model's origin. A transverse Mercator
        projection centered on the geolocation finally gives longitude and latitude.

        Args:
            version: A received version with its Speckle bundle (from receive_version).

        Returns:
            model_name, slab, level, area_m2, the geolocation's latitude and longitude, and the
            footprint as a shapely Polygon or MultiPolygon in longitude and latitude.
        """
        files = version["speckle_bundle"]
        eav = _bundle_table(files, "eav.eav").join(_bundle_table(files, "eav.paths"), on="path_index")
        placement = {
            path: text if text is not None else number
            for path, text, number in _bundle_table(files, "eav.model").select("path", "value_string", "value_double").iter_rows()
        }
        relations = _bundle_table(files, "envelope.relations")
        nodes = _bundle_table(files, "envelope.nodes")
        geometries = dict(_bundle_table(files, "geometries").select("geometryIndex", "content").iter_rows())

        def attribute(path: str) -> dict:
            return dict(eav.filter(pl.col("path") == path).select("object_index", "value_string").iter_rows())

        names, category, ifc_type = attribute("name"), attribute("category"), attribute("ifcType")
        predefined = attribute("properties.Attributes.PredefinedType")
        levels = dict(nodes.filter(pl.col("kind") == 5).select("id", "name").iter_rows())
        level_of = dict(relations.filter(pl.col("rel") == 7).select("src", "dst").iter_rows())
        instances = {row["id"]: row for row in nodes.filter(pl.col("kind") == 2).iter_rows(named=True)}
        identity = "1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1"
        shared = [float(value) for value in placement.get("modelPlacement.options.sharedCoordinates.transform", identity).split(",")]
        shared_to_m = get_scale_factor_from_string(placement.get("modelPlacement.units", "m"), "m")

        def sources(element: int) -> list[tuple[int, list[float], float]]:
            """Each geometry of an element, with the 4x4 into model coordinates and that 4x4's unit in m."""
            own = [(g, [float(v) for v in identity.split(",")], 1.0) for g in relations.filter(pl.col("rel") == 1, pl.col("src") == element)["dst"]]
            placed = []
            for instance_k in relations.filter(pl.col("rel") == 8, pl.col("src") == element)["dst"]:
                instance = instances[instance_k]
                transform = [float(v) for v in (instance["transform"] or identity).split(",")]
                to_m = get_scale_factor_from_string(instance["units"] or "m", "m")
                for g in relations.filter(pl.col("rel") == 4, pl.col("src") == instance["def_ref"])["dst"]:
                    placed.append((g, transform, to_m))
            return own + placed

        floors = []
        for element in set(category) | set(ifc_type):
            is_floor = category.get(element) == "Floors" or (
                ifc_type.get(element) == "IfcSlab" and predefined.get(element) in ("FLOOR", "BASESLAB")
            )
            if not is_floor:
                continue
            faces, bottom = [], float("inf")
            for geometry, transform, transform_to_m in sources(element):
                mesh = bundle.sgeo.decode(geometries[geometry])
                mesh_to_m = get_scale_factor_from_string(mesh.units, "m")
                xy = []
                for i in range(0, len(mesh.vertices), 3):
                    x, y, z = (value * mesh_to_m for value in mesh.vertices[i : i + 3])
                    # Into model coordinates, then shared coordinates; both 4x4s are row-major
                    mx, my, mz = (
                        transform[r] * x + transform[r + 1] * y + transform[r + 2] * z + transform[r + 3] * transform_to_m
                        for r in (0, 4, 8)
                    )
                    bottom = min(bottom, mz)
                    xy.append(
                        tuple(shared[r] * mx + shared[r + 1] * my + shared[r + 2] * mz + shared[r + 3] * shared_to_m for r in (0, 4))
                    )
                i = 0
                while i < len(mesh.faces):
                    n = mesh.faces[i]
                    face = shapely.Polygon([xy[j] for j in mesh.faces[i + 1 : i + 1 + n]])
                    if face.area > 1e-6:
                        faces.append(face)
                    i += n + 1
            if faces:
                outline = shapely.union_all(faces)
                floors.append((level_of.get(element), bottom, outline.area, element, outline))
        lowest = min(floors, key=lambda floor: floor[1])[0]
        level, _bottom, area, floor, outline = max((f for f in floors if f[0] == lowest), key=lambda floor: floor[2])

        latitude = placement["geolocation.anchor.latitude"]
        longitude = placement["geolocation.anchor.longitude"]
        to_lonlat = Transformer.from_crs(
            CRS.from_proj4(f"+proj=tmerc +lat_0={latitude} +lon_0={longitude} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m"),
            "EPSG:4326",
            always_xy=True,
        )
        return {
            "model_name": version["model_name"],
            "slab": names.get(floor),
            "level": levels.get(level),
            "area_m2": round(area),
            "latitude": latitude,
            "longitude": longitude,
            "geometry": shapely.transform(outline, to_lonlat.transform, interleaved=False),
        }


    return (
        ground_slab_footprint,
        receive_version,
        speckle_v3_objects_frame,
        version_objects_json,
    )


if __name__ == "__main__":
    app.run()
