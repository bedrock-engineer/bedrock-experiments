# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "marimo",
#     "specklepy[bundle]==2026.9.1",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    from importlib.metadata import version as _version

    mo.md(f"**specklepy** `{_version('specklepy')}`")
    return


@app.cell
def _():
    import shutil
    import warnings
    import weakref

    import marimo as mo

    from specklepy import bundle
    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_local_accounts, get_default_account
    from specklepy.transports.server import ServerTransport

    return (
        ServerTransport,
        SpeckleClient,
        bundle,
        get_default_account,
        get_local_accounts,
        mo,
        operations,
        shutil,
        warnings,
        weakref,
    )


@app.cell
def _(get_default_account, get_local_accounts, mo):
    # The accounts stored locally by Speckle Manager or a connector, one per server login
    accounts = get_local_accounts()


    def _label(acc):
        return f"{acc.serverInfo.name} ({acc.serverInfo.url})"


    server_dd = mo.ui.dropdown(
        {_label(acc): acc for acc in accounts},
        value=_label(get_default_account()),
        label="Speckle server",
    )
    return (server_dd,)


@app.cell
def _(SpeckleClient, mo, server_dd):
    account = server_dd.value
    client = SpeckleClient(host=account.serverInfo.url)
    client.authenticate_with_account(account)

    print(
        f"Authenticated on {client.server.get().canonical_url} as {client.account.userInfo.name}"
    )

    projects = client.active_user.get_projects()
    projects_dd = mo.ui.dropdown({proj.name: proj for proj in projects.items})
    return account, client, projects_dd


@app.cell
def _(client, mo, projects_dd):
    project = projects_dd.value
    models_dd = "Select a Speckle project first"
    if project:
        models = client.model.get_models(project.id)
        models_dd = mo.ui.dropdown({mdl.name: mdl for mdl in models.items})
    return models, models_dd, project


@app.cell
def _(models):
    {mdl.name: mdl for mdl in models.items}
    return


@app.cell
def _(mo):
    receive_route = mo.ui.radio(
        options={
            "Bundle (2026.9 data model)": "bundle",
            "v3 JSON objects (pre-2026.9)": "v3",
        },
        value="Bundle (2026.9 data model)",
        label="Receive as",
    )
    return (receive_route,)


@app.cell
def _(mo, models_dd, projects_dd, receive_route, server_dd):
    mo.vstack([server_dd, projects_dd, models_dd, receive_route])
    return


@app.cell
def _(
    ServerTransport,
    account,
    bundle,
    client,
    mo,
    models_dd,
    operations,
    project,
    receive_route,
    shutil,
    warnings,
    weakref,
):
    mo.stop(
        not isinstance(models_dd, mo.ui.dropdown) or models_dd.value is None,
        mo.md("Select a project and a model first."),
    )
    model = models_dd.value
    latest_version = client.version.get_versions(
        project_id=project.id,
        model_id=model.id,
        limit=1,  # only get the latest version
    ).items[0]

    # The v3 JSON pipeline is deprecated since 2026.9. On a bundle-only version,
    # operations.receive projects the bundle onto a v3 tree (Model.to_base()).
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        if receive_route.value == "bundle":
            received_data = bundle.receive(
                account, project.id, model.id, latest_version.id, mark_received=False
            )
            # Delete the download folder once a rerun has replaced this model and
            # it is garbage-collected (the parsed tables don't need the files)
            weakref.finalize(received_data, shutil.rmtree, received_data.directory, True)
        else:
            received_data = operations.receive(
                obj_id=latest_version.referenced_object,
                remote_transport=ServerTransport(stream_id=project.id, client=client),
            )

    mo.vstack(
        [
            mo.md(
                f"Received **{model.name}** @ `{latest_version.id}` "
                f"(`{latest_version.source_application}`) as **{receive_route.value}**"
            ),
            received_data.files if receive_route.value == "bundle" else received_data,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
