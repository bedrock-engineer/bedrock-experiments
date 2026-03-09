import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_local_accounts, get_default_account
    from specklepy.transports.server import ServerTransport
    return (
        ServerTransport,
        SpeckleClient,
        get_default_account,
        get_local_accounts,
        mo,
        operations,
    )


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
def _(client, mo, projects_dd):
    project = projects_dd.value
    models_dd = "Select a Speckle project first"
    if project:
        models = client.model.get_models(project.id)
        models_dd = mo.ui.dropdown({mdl.name: mdl for mdl in models.items})
    return models_dd, project


@app.cell
def _(mo, models_dd, projects_dd):
    mo.vstack([projects_dd, models_dd])
    return


@app.cell
def _(ServerTransport, client, models_dd, operations, project):
    # Get the model that was selected in the dropdown UI element
    model = models_dd.value

    # Optionally manually specify the project ID
    project_id = project.id
    project_id = "8be1007be1"  # Speckle Demo Models ProjectID

    # Optionally manually specify the model ID
    model_id = model.id
    model_id = {
        "interiors": "87f3ba9541",
        "furniture": "1c72499f69",
        "roof": "cc878fae03",
        "structure": "de46f47fc2",
        "facade": "478d7a4664",
    }
    model_id = model_id["interiors"]

    latest_version = client.version.get_versions(
        project_id=project_id,
        model_id=model_id,
        limit=1,  # only get the latest version
    )

    server_transport = ServerTransport(stream_id=project_id, client=client)
    received_data = operations.receive(
        obj_id=latest_version.items[0].referenced_object,
        remote_transport=server_transport,
    )

    received_data.__dict__
    return


if __name__ == "__main__":
    app.run()
