import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium")


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

    print(
        f"Authenticated on {client.server.get().canonical_url} as {client.account.userInfo.name}"
    )

    projects = client.active_user.get_projects()
    return client, projects


@app.cell
def _():
    return


@app.cell
def _(projects):
    projects_dict = {proj.name: proj for proj in projects.items}
    project_names = list(projects_dict.keys())
    project_names = [
      "NL Amsterdam Noord",
      "GroundIQ",
      "Plaxis3D Output",
      "NZ Weka Hills",
      "Fluvial Channels",
      "HK Kai Tak",
    ]
    return project_names, projects_dict


@app.cell
def _(mo, project_names, projects_dict):
    projects_mselect = mo.ui.multiselect(
        projects_dict,
        value=project_names,
        full_width=True,
    )
    delete_old_vers = mo.ui.switch(value=True)
    mo.vstack(
        [
            "Deselect the projects you don't want to republish:",
            projects_mselect,
            "Delete old versions?",
            delete_old_vers,
        ]
    )
    return delete_old_vers, projects_mselect


@app.cell
def _(mo):
    republish_button = mo.ui.run_button(label="Press to load and republish Speckle models for the selected projects")
    republish_button
    return (republish_button,)


@app.cell
def _(
    CreateVersionInput,
    DeleteVersionsInput,
    ServerTransport,
    SpeckleException,
    client,
    delete_old_vers,
    operations,
    projects_mselect,
    republish_button,
):
    if republish_button.value:
        for proj in projects_mselect.value:
            server_transport = ServerTransport(stream_id=proj.id, client=client)
            models = client.model.get_models(proj.id)
            for model in models.items:
                latest_version = client.version.get_versions(
                    project_id=proj.id,
                    model_id=model.id,
                    limit=1,  # only get the latest version
                )
                source_app = latest_version.items[0].source_application
                print(
                    f"Trying to load data for model `{model.name}` of project `{proj.name}`"
                )
                try:
                    received_data = operations.receive(
                        obj_id=latest_version.items[0].referenced_object,
                        remote_transport=server_transport,
                    )
                except SpeckleException as se:
                    print(
                        f"⚠️ This model probably expired. Republish it manually first from the original source application: {source_app}."
                    )
                    print(se, end="\n\n")
                    continue

                print(
                    f"Trying to republish data for model `{model.name}` of project `{proj.name}`"
                )
                try:
                    object_id = operations.send(
                        base=received_data, transports=[server_transport]
                    )
                except SpeckleException as se:
                    if "Object too large" in str(se):
                        print(
                            f"⚠️ Model `{model.name}` of project `{proj.name}` is larger than 100 MB, and can therefore not be republished from Python."
                        )
                        print(
                            f"Instead republish manually from the original source application: {source_app}.\n"
                        )
                    else:
                        print(se, end="\n\n")
                    continue

                version = client.version.create(
                    CreateVersionInput(
                        project_id=proj.id,
                        model_id=model.id,
                        object_id=object_id,
                    )
                )
                print(
                    f"✓ Created version: `{version.id}` of model `{model.name}` on project `{proj.name}`"
                )
                if delete_old_vers.value:
                    all_versions = client.version.get_versions(
                        project_id=proj.id,
                        model_id=model.id,
                    )
                    old_versions = [v.id for v in all_versions.items[1:]]
                    print(f"Deleting old versions: {old_versions}")
                    client.version.delete(
                        DeleteVersionsInput(
                            project_id=proj.id, version_ids=old_versions
                        )
                    )

                print("")
    return


@app.cell
def _():
    import marimo as mo

    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_local_accounts, get_default_account
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput, DeleteVersionsInput
    from specklepy.logging.exceptions import SpeckleException
    from specklepy.transports.server import ServerTransport
    return (
        CreateVersionInput,
        DeleteVersionsInput,
        ServerTransport,
        SpeckleClient,
        SpeckleException,
        get_default_account,
        get_local_accounts,
        mo,
        operations,
    )


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
