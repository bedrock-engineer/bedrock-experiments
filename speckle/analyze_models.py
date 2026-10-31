# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "duckdb==2.0.0",
#     "marimo",
#     "polars==2.1.0",
#     "specklepy[bundle]==2026.9.1",
#     "sqlalchemy==2.1.6",
#     "sqlglot==30.25.0",
#     "tzdata==2026.5",
#     "wigglystuff==0.5.36",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import base64
    import io
    import re
    import shutil
    import sqlite3
    import warnings
    from collections import Counter
    from pathlib import Path

    import marimo as mo
    import polars as pl
    import sqlalchemy
    from wigglystuff import EnvConfig

    from specklepy import bundle
    from specklepy.api import operations
    from specklepy.core.helpers.speckle_path_provider import user_speckle_folder_path
    from specklepy.serialization.base_object_serializer import BaseObjectSerializer
    from specklepy.transports.memory import MemoryTransport
    from specklepy.transports.sqlite import SQLiteTransport

    user_speckle_folder_path()
    return (
        BaseObjectSerializer,
        Counter,
        EnvConfig,
        MemoryTransport,
        Path,
        SQLiteTransport,
        base64,
        bundle,
        mo,
        operations,
        pl,
        re,
        shutil,
        sqlalchemy,
        user_speckle_folder_path,
        warnings,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Analyze downloaded Speckle models

    Works on the data that `download_models.py` stored, without a Speckle account or
    network access:

    - `bundles/<project_id>/<model_id>/<version_id>/*.parquet`: the 2026.9 bundle
    - `v3_objects.db`: the pre-2026.9 JSON objects (`objects` table) and the `versions`
      manifest

    **Data folder:** `SPECKLE_DATA_DIR` (environment variable or the widget below), else
    Speckle's own user folder (`%APPDATA%\Speckle` on Windows).
    """)
    return


@app.cell
def _(EnvConfig, Path, mo):
    def _absolute_path(value):
        if not Path(value).expanduser().is_absolute():
            raise ValueError("SPECKLE_DATA_DIR must be an absolute path")


    env_config = mo.ui.anywidget(EnvConfig({"SPECKLE_DATA_DIR": _absolute_path}))
    env_config
    return (env_config,)


@app.cell
def _(Path, env_config, sqlalchemy, user_speckle_folder_path):
    # SPECKLE_DATA_DIR if set, else Speckle's user folder (%APPDATA%\Speckle on Windows)
    data_dir = Path(
        env_config.get("SPECKLE_DATA_DIR") or user_speckle_folder_path()
    ).expanduser()
    v3_db_path = data_dir / "v3_objects.db"

    # SQLAlchemy engine for marimo SQL cells. Read-only (mode=ro), so analysis never
    # writes to the shared copy; as_posix() keeps Windows backslashes out of the URL.
    v3_db_con = sqlalchemy.create_engine(
        f"sqlite:///file:{v3_db_path.as_posix()}?mode=ro&uri=true"
    )
    return data_dir, v3_db_con


@app.cell
def _(mo, v3_db_con):
    manifest = mo.sql(
        f"""
        SELECT * FROM versions
        """,
        engine=v3_db_con
    )
    return (manifest,)


@app.cell(hide_code=True)
def _(mo, v3_db_con):
    _df = mo.sql(
        f"""
        SELECT * FROM objects
        """,
        engine=v3_db_con
    )
    return


@app.cell
def _(manifest, mo):
    version_picker = mo.ui.dropdown(
        {
            f"{_row['project_name']} / {_row['model_name']}": _row["version_id"]
            for _row in manifest.sort("project_name", "model_name").iter_rows(named=True)
        },
        value="Speckle Demo Models / rhino/clubhouse/interiors",
        searchable=True,
        label="Model",
    )
    version_picker
    return (version_picker,)


@app.cell
def _(manifest, mo, pl, version_picker):
    selected_version = manifest.filter(
        pl.col("version_id") == version_picker.value
    ).row(0, named=True)
    mo.md(
        f"**{selected_version['project_name']} / {selected_version['model_name']}** "
        f"@ `{selected_version['version_id']}` from `{selected_version['source_application']}`, "
        f"bundle schema {selected_version['bundle_schema_version']}, "
        f"v3 objects via **{selected_version['v3_route']}**"
    )
    return (selected_version,)


@app.cell
def _(Path, pl, re):
    _TABLE_NAME = re.compile(r"\.((?:eav|envelope)\.\w+|geometries)\.parquet$")


    def read_bundle_tables(paths):
        """One DataFrame per bundle table, keyed like "envelope.relations" or "geometries".

        Bundle files are prefixed with the version id or the source filename
        (e.g. "Clubhouse.3dm."), so the table name is matched from the end.
        """
        return {
            _TABLE_NAME.search(path.name).group(1): pl.read_parquet(path)
            for path in map(Path, paths)
            if _TABLE_NAME.search(path.name)
        }

    return (read_bundle_tables,)


@app.cell
def _(data_dir, mo, read_bundle_tables, selected_version):
    mo.stop(
        selected_version["bundle_dir"] is None,
        mo.md(
            "This version comes from a Speckle 2.x server, which serves no bundle. "
            "Only its v3 objects are in `v3_objects.db`."
        ),
    )
    bundle_tables = read_bundle_tables(
        (data_dir / selected_version["bundle_dir"]).glob("*.parquet")
    )
    mo.ui.tabs(bundle_tables)
    return (bundle_tables,)


@app.cell
def _(bundle, bundle_tables, mo, pl, selected_version):
    # Bundles can be newer than the spec vendored in specklepy (e.g. schema 1.5.0 vs 1.2.0).
    # Relation types the SDK doesn't know are kept in the tables but ignored by bundle.Model.
    _known = {_row.id for _row in bundle.spec.REL_TYPES}
    unknown_rel_types = bundle_tables["envelope.rel_types"].filter(
        ~pl.col("rel").is_in(_known)
    )
    mo.md(
        f"Bundle schema **{selected_version['bundle_schema_version']}**, specklepy spec "
        f"**{bundle.SCHEMA_VERSION}**. Relation types unknown to specklepy: "
        f"{unknown_rel_types.height}"
    )
    return


@app.cell
def _(bundle_tables, pl):
    # Wide objects table: one row per object, one column per property path.
    # Numbers and booleans also come as text in value_string, so a path gets the
    # typed column whenever that column covers every value. Type-level paths (Revit
    # type parameters) only occur in type_eav and are left out here.
    _eav = bundle_tables["eav.eav"].join(bundle_tables["eav.paths"], on="path_index")
    _paths = _eav.select("path_index", "path").unique().sort("path_index")["path"].to_list()
    _strings, _doubles, _booleans = (
        _eav.pivot(on="path", index="object_index", values=_values).sort("object_index")
        for _values in ("value_string", "value_double", "value_boolean")
    )


    def _typed(path):
        for _column in (_doubles[path], _booleans[path]):
            if _column.count() >= _strings[path].count():
                return _column
        return _strings[path]


    bundle_objects = bundle_tables["eav.objects"].join(
        pl.DataFrame([_strings["object_index"], *(_typed(_path) for _path in _paths)]),
        on="object_index",
        how="left",
    )
    bundle_objects
    return


@app.cell
def _(SQLiteTransport, data_dir, operations, selected_version, warnings):
    # The v3 object tree from v3_objects.db, no network: all objects are in the local SQLite
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        received_data = operations.receive(
            obj_id=selected_version["v3_root_id"],
            local_transport=SQLiteTransport(base_path=str(data_dir), scope="v3_objects"),
        )
    received_data
    return (received_data,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## v3 objects as columns

    `v3_objects.db` stores each object as JSON text in `objects.content`. The objects of
    all versions share this table (content-addressed by hash), and the 13 speckle_types
    have different keys, so a single nested schema can't be inferred for all of them.

    Instead the objects are unnested one level: SQLite's `json_each` splits every object
    into its top-level `key ? value` pairs, and Polars pivots the keys into columns.
    Scalars get a typed column; nested objects and arrays (`properties`, `displayValue`,
    `vertices`, `data`, ...) stay JSON text, to decode per column later. `__closure`
    (child hash ? depth) is left out.
    """)
    return


@app.cell
def _(mo, v3_db_con):
    v3_object_fields = mo.sql(
        f"""
        -- Every top-level key of every object, one row each (~1.9 M rows, ~20 s)
        SELECT o.hash, j.key, j.type AS json_type, CAST(j.value AS TEXT) AS value
        FROM objects AS o, json_each(o.content) AS j
        WHERE j.key <> '__closure'
        """,
        engine=v3_db_con,
    )
    return (v3_object_fields,)


@app.cell
def _(pl, v3_object_fields):
    # The JSON types a key holds across all objects decide its column type
    _key_types = dict(
        v3_object_fields.filter(pl.col("json_type") != "null")
        .group_by("key")
        .agg(pl.col("json_type").unique())
        .iter_rows()
    )


    def _typed(key, json_types):
        json_types = set(json_types)
        if json_types <= {"integer"}:
            return pl.col(key).cast(pl.Int64)
        if json_types <= {"integer", "real"}:
            return pl.col(key).cast(pl.Float64)
        if json_types <= {"true", "false"}:
            return pl.col(key).cast(pl.Int8).cast(pl.Boolean)
        return pl.col(key)  # text, or a nested object/array as JSON text


    expanded_objects = (
        v3_object_fields.pivot(on="key", index="hash", values="value")
        .with_columns(_typed(_key, _json_types) for _key, _json_types in _key_types.items())
        .select("hash", "speckle_type", pl.exclude("hash", "speckle_type"))
    )
    expanded_objects
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Migrate the v3 object tree to a bundle, locally

    The open-source Speckle server (2.31.x) only serves the old object graph. specklepy
    has no migrator for it (Speckle's `BundleMigrator` runs server-side, in .NET), but it
    does ship the bundle *writer*: `bundle.BundleBuilder`. `build()` writes the Parquet
    files to a local folder without touching a server, so we can convert a v3 tree
    ourselves:

    | v3 object graph | bundle |
    |---|---|
    | nested `Collection.elements` | `CONTAINER` nodes + `IN_COLLECTION` edges |
    | object `properties` + root scalars | `eav` rows |
    | `displayValue` meshes and curves | SGEO geometry + `DISPLAY` edges |
    | `encodedValue` (native .3dm) | raw geometry + `SOLID` edges |
    | `renderMaterialProxies` / `colorProxies` | `MATERIAL` / `COLOR` nodes |

    `base_to_bundle` converts `received_data` (the v3 tree from `v3_objects.db`), and the
    result is compared with the server's bundle of the same version (`bundle_tables`).
    For a `bundle` version the v3 tree was itself built from that bundle, so the
    comparison is a round trip. Instance proxies, duplicate applicationIds and geometry
    SGEO can't encode are skipped and counted.
    """)
    return


@app.cell
def _(Counter, base64, bundle, shutil):
    def base_to_bundle(root, producer):
        """Write a v3 Collection tree as bundle Parquet files.

        Returns the built files and a count of what was skipped.
        """
        builder = bundle.BundleBuilder(producer, units=root.units or "m")
        objects, geometries = {}, {}
        skipped = Counter()

        def walk(collection, path):
            for element in getattr(collection, "elements", None) or []:
                if "Collection" in element.speckle_type:
                    walk(element, [*path, element.name or element.id])
                    continue
                application_id = element.applicationId or element.id
                if application_id in objects:
                    skipped["duplicate applicationId"] += 1
                    continue
                obj = builder.get_or_add_object(application_id)
                obj.set_properties(
                    getattr(element, "properties", None) or {},
                    name=getattr(element, "name", None),
                    speckle_type=element.speckle_type,
                    units=getattr(element, "units", None),
                    root_scalars=[
                        (member, getattr(element, member))
                        for member in ("area", "volume", "length")
                        if isinstance(getattr(element, member, None), (int, float))
                    ],
                )
                obj.collection = builder.get_or_add_container_path(path)
                for geometry in getattr(element, "displayValue", None) or []:
                    if bundle.sgeo.try_get_primitive_type(geometry) is None:
                        skipped[geometry.speckle_type] += 1
                        continue
                    geometry_id = geometry.applicationId or geometry.id
                    geometries[geometry_id] = obj.add_geometry(geometry, geometry_id)
                encoded = getattr(element, "encodedValue", None)
                if encoded is not None:
                    obj.add_raw_geometry(base64.b64decode(encoded.contents), encoded.format)
                objects[application_id] = obj

        def assign(proxy, attribute, node):
            # A proxy lists the applicationIds it applies to: geometries or whole objects.
            # An edge can't be set twice, so the first proxy that names a target wins.
            for target in proxy.objects:
                owner = geometries.get(target) or objects.get(target)
                if owner is None:
                    continue
                if getattr(owner, attribute) is not None:
                    skipped[f"second {attribute} for one target"] += 1
                    continue
                setattr(owner, attribute, node)

        try:
            with builder:  # on an error, __exit__ closes the Parquet writers
                walk(root, [root.name or root.id])
                for proxy in getattr(root, "renderMaterialProxies", None) or []:
                    material = proxy.value
                    assign(
                        proxy,
                        "material",
                        builder.get_or_add_material(
                            proxy.applicationId or material.id,
                            bundle.Material(
                                argb=material.diffuse,
                                opacity=material.opacity,
                                metalness=material.metalness,
                                roughness=material.roughness,
                                name=material.name,
                                emissive=getattr(material, "emissive", None),
                                ior=getattr(material, "ior", None),
                            ),
                        ),
                    )
                for proxy in getattr(root, "colorProxies", None) or []:
                    assign(proxy, "color", builder.get_or_add_color(proxy.value))
                files = builder.build()
        except BaseException:
            shutil.rmtree(builder.directory, ignore_errors=True)
            raise
        return files, dict(skipped)

    return (base_to_bundle,)


@app.cell
def _(base_to_bundle, bundle, mo, read_bundle_tables, received_data, shutil):
    # Convert the v3 tree, read the Parquet into Polars, delete the temp folder
    _files, migration_skipped = base_to_bundle(
        received_data, bundle.Producer(slug="bedrock-migrate", version="0.0.1")
    )
    try:
        migrated_tables = read_bundle_tables(_files.files)
    finally:
        shutil.rmtree(_files.directory, ignore_errors=True)
    mo.vstack([mo.md(f"Skipped: `{migration_skipped}`"), mo.ui.tabs(migrated_tables)])
    return (migrated_tables,)


@app.cell
def _(bundle_tables, migrated_tables):
    def _relation_counts(tables):
        return (
            tables["envelope.relations"]
            .join(tables["envelope.rel_types"], on="rel")
            .group_by("name")
            .len()
        )


    # Same version, two migrations: ours (local) vs the server's bundle
    rel_comparison = (
        _relation_counts(migrated_tables)
        .rename({"len": "local"})
        .join(
            _relation_counts(bundle_tables).rename({"len": "server"}),
            on="name",
            how="full",
            coalesce=True,
        )
        .sort("name")
    )
    rel_comparison
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Geometry storage: v3 JSON objects vs bundle rows

    **v3 (pre-2026.9):** a `Mesh` is a JSON object inside the object tree. Its big arrays
    (`vertices`, `faces`, `colors`, ...) are *detachable* and *chunkable*: they are written
    as separate `DataChunk` objects (max 31 250 / 62 500 values each) and the mesh only
    keeps `{"referencedId": "<hash>"}` references plus a `__closure` list. Numbers are
    decimal text. A native solid (`encodedValue`) is a base64 string inside the object JSON.

    **Bundle (2026.9):** one row per geometry in `geometries.parquet`: `geometryIndex`
    (int32), `id` (content hash), `type` (`mesh`, `3dm`, ...) and `content` (binary). A mesh
    is one SGEO blob with f64 vertices and int32 faces; a native solid is stored as raw
    bytes. Objects point at geometry through `DISPLAY` / `SOLID` edges in
    `envelope.relations`, not by nesting.

    The cell below serializes every mesh (and native solid, where there is one) of
    `received_data` both ways and compares the byte counts. Uncompressed: Parquet and
    Speckle's transfer both compress on top of this.
    """)
    return


@app.cell
def _(
    BaseObjectSerializer,
    MemoryTransport,
    base64,
    bundle,
    mo,
    pl,
    received_data,
    warnings,
):
    def _leaves(collection):
        for element in getattr(collection, "elements", None) or []:
            if "Collection" in element.speckle_type:
                yield from _leaves(element)
            else:
                yield element


    def _v3_json_bytes(base):
        """Bytes of every JSON object the v3 serializer writes for `base`, chunks included."""
        transport = MemoryTransport()
        BaseObjectSerializer(write_transports=[transport]).traverse_base(base)
        return sum(len(json_text) for json_text in transport.objects.values())


    _rows = []
    # The v3 JSON serializer is deprecated since 2026.9; we only use it to measure
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        for _element in _leaves(received_data):
            _meshes = [
                _geometry
                for _geometry in getattr(_element, "displayValue", None) or []
                if _geometry.speckle_type.endswith("Mesh")
            ]
            _encoded = getattr(_element, "encodedValue", None)
            for _ord, _mesh in enumerate(_meshes):
                # The native solid belongs to the element; count it once, on its first mesh
                _solid = _encoded if _ord == 0 else None
                _rows.append(
                    {
                        "application_id": _element.applicationId,
                        "vertices": len(_mesh.vertices) // 3,
                        "mesh_v3_json": _v3_json_bytes(_mesh),
                        "mesh_sgeo": len(bundle.sgeo.encode(_mesh)),
                        "solid_v3_base64": len(_solid.contents) if _solid else None,
                        "solid_raw": len(base64.b64decode(_solid.contents)) if _solid else None,
                    }
                )
    geometry_storage = pl.DataFrame(_rows)

    mo.vstack(
        [
            geometry_storage.select(
                pl.len().alias("meshes"),
                pl.sum("vertices"),
                pl.sum("mesh_v3_json", "mesh_sgeo", "solid_v3_base64", "solid_raw"),
                (pl.sum("mesh_sgeo") / pl.sum("mesh_v3_json")).alias("mesh_ratio"),
                (pl.sum("solid_raw") / pl.sum("solid_v3_base64")).alias("solid_ratio"),
            ),
            geometry_storage,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
