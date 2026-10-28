# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo",
#     "polars==2.1.0",
#     "specklepy[bundle]==2026.9.1",
#     "tzdata==2026.5",
#     "wigglystuff==0.5.36",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import shutil
    import sqlite3
    import warnings
    from datetime import datetime, timezone
    from pathlib import Path

    import marimo as mo
    import polars as pl
    from wigglystuff import EnvConfig

    from specklepy import bundle
    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_local_accounts
    from specklepy.core.helpers.speckle_path_provider import user_speckle_folder_path
    from specklepy.transports.server import ServerTransport
    from specklepy.transports.sqlite import SQLiteTransport

    return (
        EnvConfig,
        Path,
        SQLiteTransport,
        ServerTransport,
        SpeckleClient,
        bundle,
        datetime,
        get_local_accounts,
        json,
        mo,
        operations,
        pl,
        shutil,
        sqlite3,
        timezone,
        user_speckle_folder_path,
        warnings,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Download Speckle models to SQLite and Parquet

    Receives the latest version of each model in `speckle_targets` from
    app.speckle.systems in two ways and stores both on disk, so other notebooks
    (`analyze_models.py`) can work with the data without receiving it again:

    1. **Bundle (2026.9 data model):** `bundle.receive` downloads the version's Parquet
       bundle (`eav.*`, `envelope.*`, `geometries`). The files are copied to
       `bundles/<project_id>/<model_id>/<version_id>/`.
    2. **v3 JSON objects (pre-2026.9 object graph):** stored in `v3_objects.db`, a SQLite
       file with Speckle's `objects(hash, content)` schema.
        - Versions published before 2026.9 still have their JSON objects on the
          server; `operations.receive` caches them into the SQLite file (`v3_route = "server"`).
        - Versions that only exist as a bundle (server-side converters, 2026.9
          connectors) have no JSON on the server. Their v3 tree is projected from the
          bundle with `Model.to_base()` and serialized into SQLite (`v3_route = "projected"`).

    `v3_objects.db` also holds a `versions` table: one row per downloaded version, with
    names, ids, source application, the v3 root object id, the route and the bundle folder.

    **Data folder:** the `SPECKLE_DATA_DIR` environment variable (or the widget below),
    else Speckle's own user folder (`%APPDATA%\Speckle` on Windows). The file names don't
    clash with Speckle's own `Objects.db`.
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
def _(Path, env_config, mo, user_speckle_folder_path):
    # SPECKLE_DATA_DIR if set, else Speckle's user folder (%APPDATA%\Speckle on Windows)
    data_dir = Path(
        env_config.get("SPECKLE_DATA_DIR") or user_speckle_folder_path()
    ).expanduser()
    bundles_dir = data_dir / "bundles"
    v3_db_path = data_dir / "v3_objects.db"
    mo.md(f"Data folder: `{data_dir}`")
    return bundles_dir, data_dir, v3_db_path


@app.cell
def _():
    SPECKLE_SERVER = "https://app.speckle.systems"

    speckle_targets = {
        # (a) Speckle Demo Models, as listed in the vault note Clippings/Speckle's Demo Models.md
        "8be1007be1": [
            "06612622aa",  # revit/snowdon towers/structure
            "13a2953168",  # revit/snowdon towers/architecture
            "57b96dc670",  # revit/sample house/architecture
            "974c745988",  # revit/speckle tower/rooms
            "ca3fb98f70",  # revit/speckle tower/structure
            "425506f1c6",  # revit/speckle tower/architecture
            "65a12a0665",  # rhino/clubhouse/site
            "87f3ba9541",  # rhino/clubhouse/interiors
            "1c72499f69",  # rhino/clubhouse/furniture
            "cc878fae03",  # rhino/clubhouse/roof elements
            "de46f47fc2",  # rhino/clubhouse/structure
            "478d7a4664",  # rhino/clubhouse/facade
            "5d98221bf2",  # sketchup/modern family house
        ],
        # (b) rvt-advanced-sample
        "461cc2a20f": [
            "ef7cb591fc",  # rvt-advanced-sample-mep
            "363cae173a",  # rvt-advanced-sample-arch
            "35e9a2fa3b",  # rvt-advanced-sample-str
        ],
        # (c) Sixty5
        "790844ad61": [
            "7c0a2f7581",  # architecture
            "a499835adf",  # facade
            "4522b8f2c0",  # structure
            "e780545d18",  # bouwplaats
        ],
    }
    return SPECKLE_SERVER, speckle_targets


@app.cell
def _(SPECKLE_SERVER, SpeckleClient, get_local_accounts, mo):
    account = next(
        _account
        for _account in get_local_accounts()
        if _account.serverInfo.url.rstrip("/") == SPECKLE_SERVER
    )
    client = SpeckleClient(host=SPECKLE_SERVER)
    client.authenticate_with_account(account)
    mo.md(f"Authenticated on `{SPECKLE_SERVER}` as **{account.userInfo.name}**")
    return account, client


@app.cell
def _(client, mo, pl, speckle_targets):
    # Latest version of every target model. A referenced_object starting with "bundle."
    # means the version only exists as a bundle (no v3 JSON objects on the server).
    _rows = []
    for _project_id, _model_ids in speckle_targets.items():
        _project = client.project.get(_project_id)
        for _model_id in _model_ids:
            _model = client.model.get(_model_id, _project_id)
            _version = client.version.get_versions(
                project_id=_project_id, model_id=_model_id, limit=1
            ).items[0]
            _rows.append(
                {
                    "project_id": _project_id,
                    "project_name": _project.name,
                    "model_id": _model_id,
                    "model_name": _model.name,
                    "version_id": _version.id,
                    "created_at": _version.created_at,
                    "source_application": _version.source_application,
                    "referenced_object": _version.referenced_object,
                }
            )
    latest_versions = pl.DataFrame(_rows).with_columns(
        bundle_only=pl.col("referenced_object").str.starts_with("bundle.")
    )
    versions_table = mo.ui.table(
        latest_versions,
        selection="multi",
        initial_selection=list(range(latest_versions.height)),
        page_size=25,
        label="Versions to download (all selected by default)",
    )
    return (versions_table,)


@app.cell
def _(mo, versions_table):
    download_button = mo.ui.run_button(label="Download selected versions")
    mo.vstack([versions_table, download_button])
    return (download_button,)


@app.cell
def _(
    Path,
    ServerTransport,
    account,
    bundle,
    bundles_dir,
    client,
    data_dir,
    datetime,
    operations,
    pl,
    shutil,
    sqlite3,
    timezone,
    warnings,
):
    MANIFEST_COLUMNS = [
        "project_id",
        "project_name",
        "model_id",
        "model_name",
        "version_id",
        "created_at",
        "source_application",
        "referenced_object",
        "v3_root_id",
        "v3_route",
        "bundle_dir",
        "bundle_schema_version",
        "received_at",
    ]


    def read_manifest(db_path):
        """The versions table of v3_objects.db, or an empty frame if nothing was downloaded yet."""
        if not db_path.exists():
            return pl.DataFrame(schema={column: pl.String for column in MANIFEST_COLUMNS})
        with sqlite3.connect(db_path) as connection:
            has_table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'versions'"
            ).fetchone()
            if not has_table:
                return pl.DataFrame(schema={column: pl.String for column in MANIFEST_COLUMNS})
            return pl.read_database("SELECT * FROM versions", connection)


    def write_manifest_row(db_path, row):
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                f"CREATE TABLE IF NOT EXISTS versions ({', '.join(MANIFEST_COLUMNS)}, "
                "PRIMARY KEY (version_id))"
            )
            connection.execute(
                f"INSERT OR REPLACE INTO versions VALUES ({', '.join('?' * len(MANIFEST_COLUMNS))})",
                [row[column] for column in MANIFEST_COLUMNS],
            )


    def download_version(version, sqlite_transport):
        """Store one version as a Parquet bundle and as v3 JSON objects in SQLite.

        Returns the manifest row; the caller writes it once both routes succeeded.
        """
        project_id, model_id, version_id = (
            version["project_id"],
            version["model_id"],
            version["version_id"],
        )
        bundle_dir = bundles_dir / project_id / model_id / version_id
        # The v3 JSON pipeline (ServerTransport, operations.send/receive) is deprecated
        # since 2026.9, which is exactly the route we want to keep a copy of.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with bundle.receive(
                account, project_id, model_id, version_id, mark_received=False
            ) as model:
                bundle_dir.mkdir(parents=True, exist_ok=True)
                for path in map(Path, model.files):
                    shutil.copy2(path, bundle_dir / path.name)
                schema_version = pl.read_parquet(
                    next(bundle_dir.glob("*.envelope.meta.parquet"))
                )["schema_version"][0]

                if version["referenced_object"].startswith("bundle."):
                    v3_root_id = operations.send(
                        model.to_base(),
                        transports=[sqlite_transport],
                        use_default_cache=False,
                    )
                    v3_route = "projected"
                else:
                    operations.receive(
                        obj_id=version["referenced_object"],
                        remote_transport=ServerTransport(stream_id=project_id, client=client),
                        local_transport=sqlite_transport,
                    )
                    v3_root_id = version["referenced_object"]
                    v3_route = "server"

        return {
            **version,
            "created_at": version["created_at"].isoformat(),
            "v3_root_id": v3_root_id,
            "v3_route": v3_route,
            "bundle_dir": bundle_dir.relative_to(data_dir).as_posix(),
            "bundle_schema_version": schema_version,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

    return download_version, read_manifest, write_manifest_row


@app.cell
def _(json):
    def write_bundle_index(manifest, bundles_dir, server):
        """Write bundles/index.json and bundles/index.md: what each id folder is.

        The folder layout is bundles/<project_id>/<model_id>/<version_id>/. Returns the
        Markdown.
        """
        rows = manifest.sort("project_name", "model_name").to_dicts()
        index = {}
        for row in rows:
            project_url = f"{server}/projects/{row['project_id']}"
            model_url = f"{project_url}/models/{row['model_id']}"
            project = index.setdefault(
                row["project_id"],
                {"name": row["project_name"], "url": project_url, "models": {}},
            )
            model = project["models"].setdefault(
                row["model_id"],
                {"name": row["model_name"], "url": model_url, "versions": {}},
            )
            model["versions"][row["version_id"]] = {
                "url": f"{model_url}@{row['version_id']}",
                "created_at": row["created_at"],
                "source_application": row["source_application"],
                "bundle_schema_version": row["bundle_schema_version"],
                "v3_route": row["v3_route"],
                "received_at": row["received_at"],
            }
        (bundles_dir / "index.json").write_text(
            json.dumps(index, indent=2) + "\n", encoding="utf-8"
        )

        lines = [
            "# Speckle bundles",
            "",
            "Folders are `<project_id>/<model_id>/<version_id>/`. Generated by "
            "`download_models.py` from the `versions` table in `../v3_objects.db`, "
            "so don't edit this file by hand.",
            "",
            "| Project | Model | Version | Created | Source application | Schema | v3 route | Folder |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for row in rows:
            project_url = f"{server}/projects/{row['project_id']}"
            model_url = f"{project_url}/models/{row['model_id']}"
            folder = f"{row['project_id']}/{row['model_id']}/{row['version_id']}"
            lines.append(
                f"| [{row['project_name']}]({project_url}) "
                f"| [{row['model_name']}]({model_url}) "
                f"| [`{row['version_id']}`]({model_url}@{row['version_id']}) "
                f"| {row['created_at'][:10]} "
                f"| {row['source_application']} "
                f"| {row['bundle_schema_version']} "
                f"| {row['v3_route']} "
                f"| [`{folder}`]({folder}/) |"
            )
        markdown = "\n".join(lines) + "\n"
        (bundles_dir / "index.md").write_text(markdown, encoding="utf-8")
        return markdown

    return (write_bundle_index,)


@app.cell
def _(
    SQLiteTransport,
    data_dir,
    download_button,
    download_version,
    mo,
    pl,
    read_manifest,
    sqlite3,
    v3_db_path,
    versions_table,
    warnings,
    write_manifest_row,
):
    mo.stop(
        not download_button.value,
        mo.md("Select versions above and press **Download selected versions**."),
    )


    def _label(version):
        return f"{version['project_name']} / {version['model_name']} @ {version['version_id']}"


    _done = set(read_manifest(v3_db_path)["version_id"])
    _selected = versions_table.value.to_dicts()
    _todo = [_version for _version in _selected if _version["version_id"] not in _done]
    _log = [
        {"version": _label(_version), "status": "already downloaded", "error": None}
        for _version in _selected
        if _version["version_id"] in _done
    ]
    # Only open v3_objects.db when there is something to add: SQLiteTransport switches the
    # file to WAL mode, which a synced copy (Nextcloud) shouldn't be left in
    if _todo:
        data_dir.mkdir(parents=True, exist_ok=True)
        with warnings.catch_warnings():  # deprecated since 2026.9, still what we want here
            warnings.simplefilter("ignore", DeprecationWarning)
            _sqlite = SQLiteTransport(base_path=str(data_dir), scope="v3_objects")
        for _version in mo.status.progress_bar(_todo, title="Downloading", show_eta=True):
            try:
                write_manifest_row(v3_db_path, download_version(_version, _sqlite))
                _log.append({"version": _label(_version), "status": "downloaded", "error": None})
            except Exception as _error:
                _log.append(
                    {"version": _label(_version), "status": "failed", "error": repr(_error)}
                )
        # Fold the WAL into v3_objects.db and leave WAL mode, so the file alone is complete
        # when it is copied or synced
        with sqlite3.connect(v3_db_path) as _connection:
            _connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            _connection.execute("PRAGMA journal_mode=DELETE")
    download_log = pl.DataFrame(_log)
    download_log
    return (download_log,)


@app.cell
def _(
    SPECKLE_SERVER,
    bundles_dir,
    download_log,
    mo,
    read_manifest,
    v3_db_path,
    write_bundle_index,
):
    # Rerun after a download: what is on disk now, plus bundles/index.json and index.md
    download_log
    manifest = read_manifest(v3_db_path)
    mo.vstack([manifest, mo.md(write_bundle_index(manifest, bundles_dir, SPECKLE_SERVER))])
    return


if __name__ == "__main__":
    app.run()
