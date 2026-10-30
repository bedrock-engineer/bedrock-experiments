# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "folium>=0.12",
#     "geopandas==1.2.0",
#     "mapclassify==2.11.0",
#     "marimo",
#     "marimo-lens==0.2.4",
#     "matplotlib==3.11.2",
#     "numpy",
#     "polars",
#     "pyarrow==26.0.0",
#     "pyproj>=3.7",
#     "shapely==2.2.0",
#     "specklepy[bundle]==2026.9.1",
#     "specklewidgets",
#     "wigglystuff==0.5.36",
# ]
#
# [tool.uv.sources]
# specklewidgets = { git = "https://github.com/bedrock-engineer/specklestuff" }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import hashlib
    import json
    import math
    import sqlite3
    import urllib.parse
    import urllib.request
    import warnings
    from collections.abc import Callable, Iterable, Iterator, Sequence
    from contextlib import closing
    from pathlib import Path

    import geopandas as gpd
    import marimo as mo
    import numpy as np
    import polars as pl
    import pyproj
    import shapely
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_local_accounts
    from specklepy.transports.memory import MemoryTransport
    from specklepy.transports.server import ServerTransport
    from specklewidgets import GeoSpeckleViewer, models_gz
    from wigglystuff import EnvConfig

    return (
        Callable,
        EnvConfig,
        GeoSpeckleViewer,
        Iterable,
        MemoryTransport,
        Path,
        ServerTransport,
        SpeckleClient,
        closing,
        get_local_accounts,
        hashlib,
        json,
        math,
        mo,
        models_gz,
        np,
        pl,
        pyproj,
        shapely,
        sqlite3,
        warnings,
    )


@app.cell(hide_code=True)
def _():
    # marimo-lens: select a region of any output and add a note for the notebook agent
    from marimo_lens import Lens

    lens = Lens()
    lens
    return


@app.cell
def _(mo):
    mo.md(r"""
    # Amsterdam Noord GeoBIM

    Revit's advanced sample project placed on a plot at Overhoeks, Amsterdam Noord, among the site model, the 3D BGT, GeoTOP and the BRO CPTs.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Inputs

    `speckle/download_models.py` stored these Speckle models in `v3_objects.db`, and the original bundles next to it:

    - Revit's advanced sample project, `rvt-advanced-sample-arch` and `rvt-advanced-sample-str` on app.speckle.systems, converted from `.rvt` by rvt-oda-converter
    - the NL Amsterdam Noord project on speckle.bedrock.engineer: `site`, the plot; `bgt-3d`, the 3D BGT around it; and `str`, the same structural model, placed on the plot by hand in Rhino (`grasshopper/bgt_bag_site_bim.3dm`). All three are in RD New and NAP, in meters. The notebook receives them straight from the server, with this machine's Speckle account.
    """)
    return


@app.cell
def _(EnvConfig, Path, mo):
    def _absolute_path(value: str) -> None:
        if not Path(value).expanduser().is_absolute():
            raise ValueError("SPECKLE_DATA_DIR must be an absolute path")


    speckle_env = mo.ui.anywidget(EnvConfig({"SPECKLE_DATA_DIR": _absolute_path}))
    speckle_env
    return (speckle_env,)


@app.cell
def _(Path, mo, speckle_env):
    mo.stop(
        not speckle_env.get("SPECKLE_DATA_DIR"),
        mo.md("Set `SPECKLE_DATA_DIR` to the folder `speckle/download_models.py` wrote to."),
    )
    speckle_dir = Path(speckle_env.get("SPECKLE_DATA_DIR")).expanduser()
    speckle_db = speckle_dir / "v3_objects.db"
    # Revit's advanced sample project on app.speckle.systems
    REVIT_VERSIONS = {"arch": "d5e5bacdde", "str": "b66058b4d1"}
    # Left out of the viewers: the landscape, and Revit's volumes that are no building parts
    HIDDEN_CATEGORIES = ("Planting", "Entourage", "Topography", "Parking", "Mass", "Rooms", "<Room Separation>")
    return HIDDEN_CATEGORIES, REVIT_VERSIONS, speckle_db, speckle_dir


@app.cell
def _(speckle_receive):
    # NL Amsterdam Noord on speckle.bedrock.engineer
    SITE_SERVER = "https://speckle.bedrock.engineer"
    SITE_PROJECT = "03f6fd3bc9"
    SITE_VERSIONS = {"site": "8a9b7b4322", "bgt-3d": "acb62e2061", "str": "18d09a8868"}
    site_models = {
        _model: speckle_receive(SITE_SERVER, SITE_PROJECT, _version_id) for _model, _version_id in SITE_VERSIONS.items()
    }
    return (site_models,)


@app.cell
def _(
    REVIT_VERSIONS,
    mo,
    pl,
    revit_elements,
    site_models,
    speckle_db,
    speckle_dir,
    speckle_object_properties,
):
    # Every element of the models in the two viewers, for the tables of selected elements
    revit_elements_table = pl.concat(
        [
            revit_elements(speckle_dir, speckle_db, _version_id).with_columns(model=pl.lit(_model))
            for _model, _version_id in REVIT_VERSIONS.items()
        ],
        how="diagonal_relaxed",
    )
    site_elements_table = pl.concat(
        [
            revit_elements_table.filter(pl.col("model") == "arch"),
            *(speckle_object_properties(site_models[_model]).with_columns(model=pl.lit(_model)) for _model in ("str", "site", "bgt-3d")),
        ],
        how="diagonal_relaxed",
    )
    mo.md(f"{len(revit_elements_table)} Revit elements; {len(site_elements_table)} elements on the site")
    return revit_elements_table, site_elements_table


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Where is the BIM origin?

    Revit has three reference points: the *Internal Origin*, fixed in the file; the *Project Base Point*, the origin of the project coordinates; and the *Survey Point*, the origin of the shared coordinates that link a model to the world. The bundles keep all three, together with which one the geometry is relative to (`modelPlacement.source`).
    """)
    return


@app.cell
def _(REVIT_VERSIONS, pl, revit_model_placement, speckle_db, speckle_dir):
    # The reference points of both models, side by side
    revit_placement = (
        pl.concat(
            [
                revit_model_placement(speckle_dir, speckle_db, _version_id).with_columns(model=pl.lit(_model))
                for _model, _version_id in REVIT_VERSIONS.items()
            ]
        )
        .filter(pl.col("path").str.contains(r"^(modelPlacement|referencePoints|projectLocation|geolocation)\."))
        .pivot("model", index=["path", "unit"], values="value")
    )
    revit_placement
    return (revit_placement,)


@app.cell
def _(
    GeoSpeckleViewer,
    HIDDEN_CATEGORIES,
    REVIT_VERSIONS,
    mo,
    models_gz,
    pl,
    revit_placement,
    revit_version_objects,
    speckle_db,
    speckle_dir,
):
    # Both models in one viewer, with axes at the Project Base Point and the Survey Point
    _survey_mm = [
        float(revit_placement.filter(pl.col("path") == f"referencePoints.surveyPoint.position.{_axis}")["arch"][0])
        for _axis in "xyz"
    ]
    revit_viewer = mo.ui.anywidget(
        GeoSpeckleViewer(
            objects_gz=models_gz(
                *(
                    revit_version_objects(speckle_dir, speckle_db, _version_id, _model, HIDDEN_CATEGORIES)
                    for _model, _version_id in REVIT_VERSIONS.items()
                )
            ),
            markers=[
                {"name": "Project Base Point = Internal Origin", "position": [0, 0, 0]},
                {"name": "Survey Point", "position": [_value / 1000 for _value in _survey_mm]},
            ],
        )
    )
    revit_viewer
    return (revit_viewer,)


@app.cell
def _(mo, revit_elements_table, revit_viewer, viewer_selection):
    _selected = viewer_selection(revit_viewer.value["selected"], revit_elements_table)
    mo.vstack([mo.md(f"**Selected in the viewer above**: {len(_selected)} (shift-click to add)"), _selected])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Where did the model go on the plot?

    The `str` model on speckle.bedrock.engineer is Revit's structural model as Rhino placed it. Its blocks keep Revit's element id (`properties.elementId`), and so do the instances in the bundle, as the last eight hex digits of the Revit UniqueId. For an element that occurs once in both, the block's transform times the inverse of the instance's transform is the transformation from Revit's internal coordinates to RD New and NAP. The notebook takes the median over all such elements, and checks how far a single element strays from it.
    """)
    return


@app.cell
def _(
    REVIT_VERSIONS,
    math,
    mo,
    np,
    pl,
    revit_instance_placement,
    revit_placement,
    site_models,
    speckle_db,
    speckle_version_objects,
):
    revit_to_rd, _deviation = revit_instance_placement(
        site_models["str"], speckle_version_objects(speckle_db, REVIT_VERSIONS["str"])
    )
    EASTING, NORTHING, ORTHOMETRIC_HEIGHT = revit_to_rd[:3, 3]
    # From grid east to Revit's x-axis, which is also from grid north to its y-axis
    ROTATION = math.degrees(math.atan2(revit_to_rd[1, 0], revit_to_rd[0, 0]))
    _survey = revit_to_rd @ [
        *(
            float(revit_placement.filter(pl.col("path") == f"referencePoints.surveyPoint.position.{_axis}")["str"][0]) / 1000
            for _axis in "xyz"
        ),
        1,
    ]
    mo.md(f"""
    | Revit's internal origin | |
    |---|---|
    | Easting | {EASTING:.3f} m |
    | Northing | {NORTHING:.3f} m |
    | Orthometric height | NAP {ORTHOMETRIC_HEIGHT:+.3f} m |
    | Rotation, grid north to Revit's y-axis, counterclockwise | {ROTATION:.4f}° |
    | Scale | {np.linalg.det(revit_to_rd[:3, :3]):.9f} |
    | Largest deviation of one element | {_deviation * 1000:.4f} mm |

    Revit's Survey Point lands at {_survey[0]:.3f} E, {_survey[1]:.3f} N: the placement in Rhino ignored the shared coordinates.
    """)
    return EASTING, NORTHING, ORTHOMETRIC_HEIGHT, ROTATION, revit_to_rd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Engineering CRS

    From these parameters `derived_engineering_crs` builds the Engineering CRS of the site: Revit's internal coordinates in millimeters, derived from RD New + NAP height (EPSG:7415).
    """)
    return


@app.cell
def _(
    EASTING,
    NORTHING,
    ORTHOMETRIC_HEIGHT,
    ROTATION,
    derived_engineering_crs,
    mo,
    np,
    pyproj,
    revit_to_rd,
):
    engineering_crs = derived_engineering_crs(
        "EPSG:7415", EASTING, NORTHING, ORTHOMETRIC_HEIGHT, ROTATION, unit=0.001, name="Amsterdam Noord"
    )
    # The CRS has to put points where the Rhino placement does
    _to_rd = pyproj.Transformer.from_crs(engineering_crs, "EPSG:7415", always_xy=True)
    _site_mm = np.array([[0, 0, 0], [10_000, 0, 0], [0, 20_000, 0], [-9_202, -22_635, 4_100]])
    _error = np.column_stack(_to_rd.transform(*_site_mm.T)) - (revit_to_rd @ np.c_[_site_mm / 1000, np.ones(4)].T).T[:, :3]
    assert np.abs(_error).max() < 1e-6, _error
    mo.accordion({"Engineering CRS as WKT": mo.plain_text(engineering_crs.to_wkt(pretty=True))})
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The model in its surroundings

    The architectural model from the bundle as Revit placed it, and the models from speckle.bedrock.engineer moved from RD New and NAP into the Engineering CRS. Where the Rhino `str` model and the `arch` model meet, the placement checks itself.
    """)
    return


@app.cell
def _(
    GeoSpeckleViewer,
    HIDDEN_CATEGORIES,
    REVIT_VERSIONS,
    mo,
    models_gz,
    np,
    revit_to_rd,
    revit_version_objects,
    site_models,
    speckle_db,
    speckle_dir,
    speckle_transform,
):
    _rd_to_site = np.linalg.inv(revit_to_rd)
    site_viewer = mo.ui.anywidget(
        GeoSpeckleViewer(
            objects_gz=models_gz(
                revit_version_objects(
                    speckle_dir,
                    speckle_db,
                    REVIT_VERSIONS["arch"],
                    "arch",
                    HIDDEN_CATEGORIES,
                ),
                *(
                    speckle_transform(site_models[_model], _rd_to_site)
                    for _model in ("str", "site", "bgt-3d")
                ),
            ),
        )
    )
    site_viewer
    return (site_viewer,)


@app.cell
def _(mo, site_elements_table, site_viewer, viewer_selection):
    _selected = viewer_selection(site_viewer.value["selected"], site_elements_table)
    mo.vstack([mo.md(f"**Selected in the viewer above**: {len(_selected)} (shift-click to add)"), _selected])
    return


@app.cell
def _(site_viewer):
    site_viewer.value["selected"]
    return


@app.cell
def _(site_elements_table):
    site_elements_table
    return


app._unparsable_cell(
    r"""
    mo.vstack(
        [
            selected_ids = [obj["applicationId"] for obj in site_viewer.value["selected"]]
            mo.md(f"**Selected elements**: {len(selected_ids)}"),
            element_data.filter(pl.col("global_id").is_in(selected_ids)),
        ]
    )
    """,
    name="_"
)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Implementation

    The functions the cells above use. The viewer, `GeoSpeckleViewer`, comes from [specklewidgets](https://github.com/bedrock-engineer/specklestuff).
    """)
    return


@app.cell
def _(Iterable, Path, closing, hashlib, json, np, pl, shapely, sqlite3):
    # Reading v3_objects.db, as speckle/download_models.py writes it: versions maps a version id
    # to its v3 root object, objects holds every object's JSON by hash.
    def _connect(db_path: Path | str) -> closing:
        return closing(sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True))


    def _root_id(connection: sqlite3.Connection, version_id: str) -> str:
        (root_id,) = connection.execute(
            "SELECT v3_root_id FROM versions WHERE version_id = ?", (version_id,)
        ).fetchone()
        return root_id


    def _read_objects(connection: sqlite3.Connection, object_ids: Iterable[str]) -> dict[str, dict]:
        """Parsed v3 objects by id, for the given ids."""
        return {
            object_id: json.loads(content)
            for object_id, content in connection.execute(
                "SELECT hash, content FROM objects WHERE hash IN (SELECT value FROM json_each(?))",
                (json.dumps(list(object_ids)),),
            )
        }


    def speckle_version_objects(db_path: Path | str, version_id: str, namespace: str | None = None) -> str:
        """Reads one version's v3 objects.

        Args:
            db_path: Path to v3_objects.db.
            version_id: Speckle version id.
            namespace: Prefix for the instance definition ids (def-...), so that projected
                bundles can share a viewer: rvt-oda-converter numbers them from def-1 in every
                model.

        Returns:
            The objects as JSON array text, root first.
        """
        with _connect(db_path) as connection:
            root_id = _root_id(connection, version_id)
            (root,) = connection.execute(
                "SELECT content FROM objects WHERE hash = ?", (root_id,)
            ).fetchone()
            children = [
                content
                for (content,) in connection.execute(
                    "SELECT content FROM objects WHERE hash IN (SELECT value FROM json_each(?))",
                    (json.dumps(list(json.loads(root)["__closure"])),),
                )
            ]
        text = "[" + ",".join([root, *children]) + "]"
        return text.replace('"def-', f'"{namespace}/def-') if namespace else text


    def _bundle_file(data_dir: Path | str, db_path: Path | str, version_id: str, table: str) -> Path:
        """The path of one table of a version's bundle, such as eav.model or envelope.nodes."""
        with _connect(db_path) as connection:
            (bundle_dir,) = connection.execute(
                "SELECT bundle_dir FROM versions WHERE version_id = ?", (version_id,)
            ).fetchone()
        (path,) = (Path(data_dir) / bundle_dir).glob(f"*.{table}.parquet")
        return path


    def revit_model_placement(data_dir: Path | str, db_path: Path | str, version_id: str) -> pl.DataFrame:
        """Reads the model-level values of a Revit bundle (eav.model.parquet).

        Args:
            data_dir: The folder download_models.py wrote to; bundle_dir is relative to it.
            db_path: Path to v3_objects.db.
            version_id: Speckle version id of a Revit bundle.

        Returns:
            One row per value (reference points, placement, geolocation, project info): path,
            value as text, and unit.
        """
        return pl.read_parquet(_bundle_file(data_dir, db_path, version_id, "eav.model")).select(
            "path",
            pl.coalesce(
                "value_string", pl.col("value_double").cast(pl.String), pl.col("value_boolean").cast(pl.String)
            ).alias("value"),
            "unit",
        )


    def revit_version_objects(
        data_dir: Path | str,
        db_path: Path | str,
        version_id: str,
        namespace: str,
        hidden_categories: Iterable[str] = (),
    ) -> str:
        """Reads one Revit version's v3 objects, with every material and without some categories.

        specklepy's projection of a bundle (`to_base`) gives materials only to geometry that
        belongs to an element, so the geometry of family instances, which lives in instance
        definitions, renders in the viewer's default gray. This reads the material of each
        geometry from the bundle's envelope instead.

        Args:
            data_dir: The folder download_models.py wrote to; bundle_dir is relative to it.
            db_path: Path to v3_objects.db.
            version_id: Speckle version id of a Revit bundle.
            namespace: Prefix for the instance definition ids, as in speckle_version_objects.
            hidden_categories: Revit categories to leave out, such as "Planting".

        Returns:
            The objects as JSON array text, root first.
        """
        objects = json.loads(speckle_version_objects(db_path, version_id, namespace))
        root = objects[0]
        nodes = pl.read_parquet(_bundle_file(data_dir, db_path, version_id, "envelope.nodes"))
        relations = pl.read_parquet(_bundle_file(data_dir, db_path, version_id, "envelope.relations"))
        app_ids = dict(pl.read_parquet(_bundle_file(data_dir, db_path, version_id, "eav.objects")).iter_rows())
        # DISPLAY: object -> geometry; DEFINES: definition -> geometry; HAS_MATERIAL: geometry -> material
        owner = dict(relations.filter(pl.col("rel") == 1).select("dst", "src").iter_rows())
        materials = {}
        for geometry, material in relations.filter(pl.col("rel") == 5).select("src", "dst").iter_rows():
            target = app_ids[owner[geometry]] if geometry in owner else f"{namespace}/def-geo-{geometry}"
            materials.setdefault(material, set()).add(target)
        proxies = []
        for row in nodes.filter(pl.col("kind") == 3, pl.col("id").is_in(list(materials))).iter_rows(named=True):
            value = {
                "speckle_type": "Objects.Other.RenderMaterial",
                "applicationId": f"{namespace}/mat-{row['id']}",
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

        categories = (
            pl.read_parquet(_bundle_file(data_dir, db_path, version_id, "eav.eav"))
            .join(pl.read_parquet(_bundle_file(data_dir, db_path, version_id, "eav.paths")), on="path_index")
            .filter(pl.col("path") == "category", pl.col("value_string").is_in(list(hidden_categories)))
        )
        hidden_app_ids = {app_ids[object_index] for object_index in categories["object_index"]}
        # An element with more than one placement gets <applicationId>-instance-<i> after the first
        hidden = {
            obj["id"]
            for obj in objects
            if (obj.get("applicationId") or "").split("-instance-")[0] in hidden_app_ids
        }
        kept = []
        for obj in objects:
            if obj["id"] in hidden:
                continue
            if "elements" in obj:
                obj["elements"] = [ref for ref in obj["elements"] if ref.get("referencedId") not in hidden]
            kept.append(obj)
        root["__closure"] = {key: depth for key, depth in root["__closure"].items() if key not in hidden}
        return json.dumps(kept)

    def revit_elements(data_dir: Path | str, db_path: Path | str, version_id: str) -> pl.DataFrame:
        """Reads the elements of a Revit bundle with their instance and type parameters.

        Args:
            data_dir: The folder download_models.py wrote to; bundle_dir is relative to it.
            db_path: Path to v3_objects.db.
            version_id: Speckle version id of a Revit bundle.

        Returns:
            One row per element: applicationId (the Revit UniqueId), then a column per property
            path, such as category, family, type and properties.Parameters..., as text.
        """
        def read(table: str) -> pl.DataFrame:
            return pl.read_parquet(_bundle_file(data_dir, db_path, version_id, table))

        def values(eav: pl.DataFrame, index: str) -> pl.DataFrame:
            return (
                eav.join(read("eav.paths"), on="path_index")
                .select(
                    index,
                    "path",
                    pl.coalesce(
                        "value_string", pl.col("value_double").cast(pl.String), pl.col("value_boolean").cast(pl.String)
                    ).alias("value"),
                )
                .pivot("path", index=index, values="value", aggregate_function="first")
            )

        instances = values(read("eav.eav"), "object_index")
        types = values(read("eav.type_eav"), "type_index")
        # Instance values win over type values of the same path
        types = types.select("type_index", *(column for column in types.columns[1:] if column not in instances.columns))
        return (
            read("eav.objects")
            .join(instances, on="object_index", how="left")
            .join(read("eav.object_type"), on="object_index", how="left")
            .join(types, on="type_index", how="left")
            .drop("object_index", "type_index")
            .rename({"application_id": "applicationId"})
        )

    def speckle_elements(db_path: Path | str, version_id: str) -> pl.DataFrame:
        """Reads the DataObjects of a version: the elements the viewer selects.

        Args:
            db_path: Path to v3_objects.db.
            version_id: Speckle version id.

        Returns:
            One row per DataObject. The object's own fields become columns and `properties`
            stays a nested Struct. `displayValue` holds the references to the element's
            meshes; `__closure` is left out.
        """
        with _connect(db_path) as connection:
            root_id = _root_id(connection, version_id)
            root = _read_objects(connection, [root_id])[root_id]
            objects = _read_objects(connection, root["__closure"])
        rows = [
            {key: value for key, value in obj.items() if key != "__closure"}
            for obj in objects.values()
            if obj["speckle_type"] == "Objects.Data.DataObject"
        ]
        # infer_schema_length=None: merge every element's property tree into one Struct schema
        return pl.DataFrame(rows, infer_schema_length=None)


    def speckle_display_geometries(db_path: Path | str, display_values: list[list[dict]]) -> list[shapely.MultiPolygon | None]:
        """Reads the display meshes of elements as polygons in mm, the Engineering CRS's unit.

        Args:
            db_path: Path to v3_objects.db.
            display_values: Per element, its displayValue: references to its meshes.

        Returns:
            Per element, a MULTIPOLYGON Z with one polygon per mesh face, or None for an empty
            displayValue.
        """
        with _connect(db_path) as connection:
            meshes = _read_objects(
                connection, {ref["referencedId"] for refs in display_values for ref in refs}
            )
            # Long arrays are detached into DataChunks
            chunks = _read_objects(
                connection,
                {
                    item["referencedId"]
                    for mesh in meshes.values()
                    for key in ("vertices", "faces")
                    for item in mesh[key]
                    if isinstance(item, dict)
                },
            )

        def resolve(items: list) -> list:
            values = []
            for item in items:
                if isinstance(item, dict):
                    values += chunks[item["referencedId"]]["data"]
                else:
                    values.append(item)
            return values

        def face_polygons_mm(mesh: dict) -> list[shapely.Polygon]:
            assert mesh["units"] == "m"
            xyz = 1000 * np.array(resolve(mesh["vertices"])).reshape(-1, 3)
            faces = resolve(mesh["faces"])
            polygons, i = [], 0
            while i < len(faces):
                n = faces[i] + 3 if faces[i] < 3 else faces[i]  # 0 and 1: legacy triangle, quad
                polygons.append(shapely.Polygon(xyz[faces[i + 1 : i + 1 + n]]))
                i += n + 1
            return polygons

        geometries = []
        for refs in display_values:
            polygons = [
                polygon for ref in refs for polygon in face_polygons_mm(meshes[ref["referencedId"]])
            ]
            geometries.append(shapely.MultiPolygon(polygons) if polygons else None)
        return geometries

    return (
        revit_elements,
        revit_model_placement,
        revit_version_objects,
        speckle_version_objects,
    )


@app.cell
def _(math, pyproj):
    # An Engineering CRS from georeferencing parameters
    def derived_engineering_crs(
        base_crs: pyproj.CRS | str | int,
        easting: float,
        northing: float,
        orthometric_height: float,
        rotation: float,
        unit: float,
        name: str,
    ) -> pyproj.CRS:
        """Derives an Engineering CRS from a compound CRS by georeferencing parameters.

        The site origin (0, 0, 0) lands on (easting, northing) in the projected CRS and on
        orthometric_height in the vertical CRS. The scale between site and map is not a
        parameter: it follows from unit and the base CRS's own units. The result is a compound
        of a DerivedProjectedCRS with an Affine parametric transformation (EPSG:9624) and a
        DerivedVerticalCRS with a Vertical Offset (EPSG:9616), with the axes in the site's unit.

        Args:
            base_crs: Compound CRS of a projected and a vertical CRS, such as EPSG:7415.
            easting: Easting of the site origin, in the projected CRS's unit.
            northing: Northing of the site origin, in the projected CRS's unit.
            orthometric_height: Height of the site origin, in the vertical CRS's unit.
            rotation: Angle in degrees from grid north to the site's y-axis, counterclockwise
                positive. Grid north, not true north.
            unit: The site's length unit in meters, 0.001 for millimeters.
            name: Name of the site, used in the names of the CRS and its parts.

        Returns:
            The Engineering CRS.
        """
        base_crs = pyproj.CRS.from_user_input(base_crs)
        projected, vertical = base_crs.sub_crs_list
        map_unit = projected.axis_info[0].unit_conversion_factor  # meters per map unit
        height_unit = vertical.axis_info[0]
        theta = math.radians(rotation)
        k = map_unit / unit  # map units -> site units
        a1, a2 = k * math.cos(theta), k * math.sin(theta)
        b1, b2 = -k * math.sin(theta), k * math.cos(theta)
        a0 = -(a1 * easting + a2 * northing)
        b0 = -(b1 * easting + b2 * northing)
        site_unit = {
            "type": "LinearUnit",
            "name": {0.001: "millimetre", 0.01: "centimetre", 1.0: "metre"}.get(unit, "site unit"),
            "conversion_factor": unit,
        }

        def parameter(name: str, value: float, unit: dict | str) -> dict:
            return {"name": name, "value": value, "unit": unit}

        site_grid = {
            "type": "DerivedProjectedCRS",
            "name": f"{name} site grid",
            "base_crs": projected.to_json_dict(),
            "conversion": {
                "name": f"{name} georeferencing",
                "method": {"name": "Affine parametric transformation", "id": {"authority": "EPSG", "code": 9624}},
                "parameters": [
                    parameter("A0", a0, site_unit),
                    parameter("A1", a1, "unity"),
                    parameter("A2", a2, "unity"),
                    parameter("B0", b0, site_unit),
                    parameter("B1", b1, "unity"),
                    parameter("B2", b2, "unity"),
                ],
            },
            "coordinate_system": {
                "subtype": "Cartesian",
                "axis": [
                    {"name": "Site x", "abbreviation": "x", "direction": "unspecified", "unit": site_unit},
                    {"name": "Site y", "abbreviation": "y", "direction": "unspecified", "unit": site_unit},
                ],
            },
        }
        site_z = {
            "type": "DerivedVerticalCRS",
            "name": f"{name} site z",
            "base_crs": vertical.to_json_dict(),
            "conversion": {
                "name": f"{name} orthometric height",
                "method": {"name": "Vertical Offset", "id": {"authority": "EPSG", "code": 9616}},
                "parameters": [
                    {
                        "name": "Vertical Offset",
                        "value": -orthometric_height,
                        "unit": {
                            "type": "LinearUnit",
                            "name": height_unit.unit_name,
                            "conversion_factor": height_unit.unit_conversion_factor,
                        },
                        "id": {"authority": "EPSG", "code": 8603},
                    }
                ],
            },
            "coordinate_system": {
                "subtype": "vertical",
                "axis": [{"name": "Site z", "abbreviation": "z", "direction": "up", "unit": site_unit}],
            },
        }
        return pyproj.CRS.from_json_dict(
            {"type": "CompoundCRS", "name": f"{name} Engineering CRS", "components": [site_grid, site_z]}
        )

    return (derived_engineering_crs,)


@app.cell
def _(
    Callable,
    MemoryTransport,
    ServerTransport,
    SpeckleClient,
    get_local_accounts,
    json,
    np,
    pl,
    warnings,
):
    # Receiving from a Speckle server, and finding and moving models
    SPECKLE_UNITS = {"mm": 0.001, "cm": 0.01, "m": 1.0}


    def speckle_receive(server_url: str, project_id: str, version_id: str) -> str:
        """Receives one version from a Speckle server, with this machine's account for it.

        Args:
            server_url: The server, such as https://speckle.bedrock.engineer.
            project_id: Speckle project id.
            version_id: Speckle version id.

        Returns:
            The version's objects as JSON array text, root first, like speckle_version_objects.
        """
        account = next(
            (account for account in get_local_accounts() if account.serverInfo.url.rstrip("/") == server_url.rstrip("/")),
            None,
        )
        if account is None:
            raise LookupError(f"No Speckle account for {server_url} on this machine")
        client = SpeckleClient(host=server_url)
        client.authenticate_with_account(account)
        object_id = client.version.get(version_id, project_id).referenced_object
        with warnings.catch_warnings():
            # specklepy deprecates the JSON transports in favor of bundles, which a 2.x server lacks
            warnings.simplefilter("ignore", DeprecationWarning)
            memory = MemoryTransport()
            ServerTransport(stream_id=project_id, client=client).copy_object_and_children(object_id, memory)
        objects = memory.objects
        return "[" + ",".join([objects[object_id], *(text for key, text in objects.items() if key != object_id)]) + "]"


    def _instance_transforms(model: str, element_id: Callable[[dict], int | None]) -> dict[int, np.ndarray]:
        """The transforms in meters of the InstanceProxies of elements with exactly one instance."""
        found = {}
        for obj in json.loads(model):
            if obj.get("speckle_type") != "Speckle.Core.Models.Instances.InstanceProxy":
                continue
            key = element_id(obj)
            if key is None:
                continue
            transform = np.reshape(obj["transform"], (4, 4)).astype(float)
            transform[:3, 3] *= SPECKLE_UNITS[obj["units"]]
            found.setdefault(key, []).append(transform)
        return {key: transforms[0] for key, transforms in found.items() if len(transforms) == 1}


    def revit_instance_placement(placed: str, revit: str) -> tuple[np.ndarray, float]:
        """Finds where a copy of a Revit model was placed, from the instances both share.

        Args:
            placed: The placed copy as JSON array text, with the Revit element id in the
                InstanceProxies' properties.elementId, as the Speckle Rhino connector keeps it.
            revit: The model in Revit's internal coordinates as JSON array text, with the Revit
                UniqueId as the InstanceProxies' applicationId, as rvt-oda-converter writes it. A
                UniqueId ends in the element id, in eight hex digits.

        Returns:
            The 4x4 transformation in meters from Revit's internal coordinates to the placed
            copy's: the median over the elements with one instance in both. And the largest
            distance in meters between where one such element's own transformation and the
            median put its instance origin or a point 1 m along one of its axes.
        """
        placed_transforms = _instance_transforms(
            placed, lambda obj: int(obj["properties"]["elementId"]) if "elementId" in (obj.get("properties") or {}) else None
        )
        revit_transforms = _instance_transforms(
            revit, lambda obj: int(obj["applicationId"][-8:], 16) if obj.get("applicationId") else None
        )
        shared = sorted(placed_transforms.keys() & revit_transforms.keys())
        transform = np.median([placed_transforms[key] @ np.linalg.inv(revit_transforms[key]) for key in shared], axis=0)
        probe = np.array([[0, 0, 0, 1], [1, 0, 0, 1], [0, 1, 0, 1], [0, 0, 1, 1]]).T
        deviation = max(
            np.linalg.norm((placed_transforms[key] @ probe - transform @ revit_transforms[key] @ probe)[:3], axis=0).max()
            for key in shared
        )
        return transform, float(deviation)


    def speckle_transform(model: str, matrix: np.ndarray) -> str:
        """Moves a model by an affine transformation, in its own coordinates.

        Points, vectors, mesh vertices and instance transforms move. Geometry inside instance
        definitions is in the definition's own coordinates and stays. Bounding boxes are
        dropped rather than moved.

        Args:
            model: Objects as JSON array text, root first, as speckle_receive returns them, with
                all geometry in meters.
            matrix: 4x4 transformation in meters.

        Returns:
            The moved objects as JSON array text, root first.
        """
        objects = json.loads(model)
        by_id = {obj["id"]: obj for obj in objects}
        members = {item for definition in objects[0].get("instanceDefinitionProxies") or [] for item in definition["objects"]}
        in_definitions = set()
        for obj in objects:
            if obj.get("applicationId") in members:
                in_definitions |= {obj["id"], *(obj.get("__closure") or {})}
        linear, translation = matrix[:3, :3], matrix[:3, 3]

        def resolve(items: list) -> list:
            # Long arrays are detached into DataChunks
            values = []
            for item in items:
                if isinstance(item, dict):
                    values += by_id[item["referencedId"]]["data"]
                else:
                    values.append(item)
            return values

        def move(value):
            if isinstance(value, list):
                return [move(item) for item in value]
            if not isinstance(value, dict) or "referencedId" in value:
                return value
            speckle_type = value.get("speckle_type", "")
            if speckle_type in ("Objects.Geometry.Polyline", "Objects.Geometry.Curve", "Objects.Geometry.Brep"):
                raise NotImplementedError(f"Moving {speckle_type}")
            if "units" in value and speckle_type.startswith(("Objects.Geometry", "Speckle.Core.Models.Instances")):
                assert value["units"] == "m", value["units"]
            if speckle_type in ("Objects.Geometry.Point", "Objects.Geometry.Vector"):
                xyz = linear @ [value["x"], value["y"], value["z"]]
                if speckle_type == "Objects.Geometry.Point":
                    xyz = xyz + translation
                return {**value, "x": xyz[0], "y": xyz[1], "z": xyz[2]}
            moved = {key: None if key == "bbox" else move(item) for key, item in value.items()}
            if speckle_type == "Objects.Geometry.Mesh":
                vertices = np.reshape(resolve(value["vertices"]), (-1, 3)) @ linear.T + translation
                moved["vertices"] = vertices.ravel().tolist()
            elif speckle_type == "Speckle.Core.Models.Instances.InstanceProxy":
                moved["transform"] = (matrix @ np.reshape(value["transform"], (4, 4))).ravel().tolist()
            return moved

        return json.dumps([obj if obj["id"] in in_definitions else move(obj) for obj in objects])

    def speckle_object_properties(model: str) -> pl.DataFrame:
        """Reads the objects of a model that carry properties, as Speckle's connectors send them.

        Args:
            model: Objects as JSON array text, root first, as speckle_receive returns them.

        Returns:
            One row per object with an applicationId and properties: applicationId, name,
            speckle_type, then a column per property, nested keys joined by dots, as text.
        """
        def flatten(properties: dict, prefix: str = "") -> dict[str, str]:
            flat = {}
            for key, value in properties.items():
                if isinstance(value, dict):
                    flat |= flatten(value, f"{prefix}{key}.")
                elif value is not None:
                    flat[f"{prefix}{key}"] = value if isinstance(value, str) else json.dumps(value)
            return flat

        rows = [
            {
                "applicationId": obj["applicationId"],
                "name": obj.get("name"),
                "speckle_type": obj["speckle_type"],
                **flatten(obj["properties"]),
            }
            for obj in json.loads(model)
            if obj.get("applicationId") and isinstance(obj.get("properties"), dict) and obj["properties"]
        ]
        return pl.DataFrame(rows, infer_schema_length=None)


    def viewer_selection(selected: list[dict], elements: pl.DataFrame) -> pl.DataFrame:
        """The rows of the elements selected in a GeoSpeckleViewer.

        Args:
            selected: GeoSpeckleViewer.selected, the raw selected objects.
            elements: Elements with an applicationId column.

        Returns:
            The selected rows, in the order of the selection, without the columns that are
            empty for all of them.
        """
        # An element with more than one placement gets <applicationId>-instance-<i> after the first
        ids = [(obj.get("applicationId") or "").split("-instance-")[0] for obj in selected]
        rows = (
            pl.DataFrame({"applicationId": ids}, schema={"applicationId": pl.String})
            .unique(maintain_order=True)
            .join(elements, on="applicationId", how="inner", maintain_order="left")
        )
        return rows.select(column for column in rows.columns if rows[column].null_count() < len(rows))

    return (
        revit_instance_placement,
        speckle_object_properties,
        speckle_receive,
        speckle_transform,
        viewer_selection,
    )


if __name__ == "__main__":
    app.run()
