import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo
    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_local_accounts, get_default_account
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput
    from specklepy.objects import Base
    from specklepy.objects.geometry import Point, Line, Polyline
    from specklepy.transports.server import ServerTransport

    appdata = Path(os.environ["APPDATA"])
    speckle_local_path = appdata / "Speckle"
    speckle_local_path
    return (
        ServerTransport,
        SpeckleClient,
        get_default_account,
        get_local_accounts,
        mo,
        operations,
    )


@app.cell
def _(SpeckleClient, get_default_account, get_local_accounts):
    # Get all locally stored accounts
    accounts = get_local_accounts()

    for account in accounts:
        print(f"Server: {account.serverInfo.url}, User: {account.userInfo.name}")

    # Get the default account
    account = get_default_account()
    if account:
        client = SpeckleClient(host=account.serverInfo.url)
        client.authenticate_with_account(account)

    server_info = client.server.get()
    print(
        f"Authenticated on {server_info.canonical_url} as {client.account.userInfo.name}"
    )
    return (client,)


@app.cell
def _(client, mo):
    # has_workspaces = (
    #     server_info.workspaces and server_info.workspaces.workspaces_enabled
    # )
    # if has_workspaces:
    #     workspaces = client.active_user.get_workspaces()
    #     workspaces_dd = mo.ui.dropdown({ws.name: ws for ws in workspaces.items})

    projects = client.active_user.get_projects()
    projects_dd = mo.ui.dropdown({proj.name: proj for proj in projects.items})
    projects_dd
    return (projects_dd,)


@app.cell
def _(ServerTransport, client, mo, projects_dd):
    project_id = projects_dd.value.id

    server_transport = ServerTransport(stream_id=projects_dd.value.id, client=client)

    models = client.model.get_models(project_id)
    models_dd = mo.ui.dropdown({mdl.name: mdl for mdl in models.items})
    models_dd
    return models_dd, project_id, server_transport


@app.cell
def _(client, models_dd, operations, project_id, server_transport):
    model_id = models_dd.value.id

    latest_version = client.version.get_versions(
        project_id=project_id, 
        model_id=model_id,
        limit=1 # only get the latest version
    )

    received_data = operations.receive(
        obj_id=latest_version.items[0].referenced_object,
        remote_transport=server_transport
    )

    received_data.__dict__
    return (received_data,)


@app.cell
def _(received_data):
    received_data.colorProxies[5].__dict__
    return


@app.cell
def _(received_data):
    received_data.elements[0].elements[0].elements[0].displayValue[0].__dict__
    return


if __name__ == "__main__":
    app.run()
