# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.20",
#     "specklepy>=3.0",
# ]
# ///

import marimo

__generated_with = "0.20.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(
    SpeckleClient,
    contextlib,
    get_default_account,
    get_local_accounts,
    io,
    mo,
):
    # Get all locally stored accounts
    accounts = get_local_accounts()

    auth_stdout = io.StringIO()
    with contextlib.redirect_stdout(auth_stdout):
        print("**Accounts:**")
        for i, account in enumerate(accounts):
            print(f"{i+1}. Server: {account.serverInfo.url}, User: {account.userInfo.name}\n")

        # Get the default account
        account = get_default_account()
        if account:
            client = SpeckleClient(host=account.serverInfo.url)
            client.authenticate_with_account(account)

        print("**Authenticated with the default account:**")
        print(f"- Server: {client.server.get().canonical_url}")
        print(f"- User: {client.account.userInfo.name}")

    projects = client.active_user.get_projects()

    mo.md(auth_stdout.getvalue())
    return client, projects


@app.cell(hide_code=True)
def _(mo, projects):
    projects_dict = {proj.name: proj for proj in projects.items}
    project_names = list(projects_dict.keys())
    project_names_tbl = mo.ui.table(data={"Projects": project_names})
    delete_old_vers = mo.ui.switch(value=True)
    mo.vstack(
        [
            "Select the projects you want to republish:",
            project_names_tbl,
            "Delete old versions?",
            delete_old_vers,
        ]
    )
    return delete_old_vers, project_names_tbl, projects_dict


@app.cell(hide_code=True)
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
    fmt,
    io,
    logging,
    mo,
    operations,
    project_names_tbl,
    projects_dict,
    republish_button,
    stdout_handler,
):
    # Instantiate the logger and add the stdout and buffer handlers
    repub_logger = logging.getLogger(__name__ + ".republish")
    repub_logger.setLevel(logging.DEBUG)
    # Create a file buffer for the logger to write the logs to
    repub_buffer = io.StringIO()
    buffer_handler = logging.StreamHandler(repub_buffer)
    buffer_handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    # Add stdout and buffer handlers to the logger if the logger has no handlers yet
    repub_logger.handlers.clear()
    repub_logger.addHandler(buffer_handler)
    repub_logger.addHandler(stdout_handler)

    if republish_button.value:
        repub_projects = [
            projects_dict[pn] for pn in project_names_tbl.value["Projects"]
        ]
        for proj in repub_projects:
            server_transport = ServerTransport(stream_id=proj.id, client=client)
            models = client.model.get_models(proj.id)
            for model in models.items:
                latest_version = client.version.get_versions(
                    project_id=proj.id,
                    model_id=model.id,
                    limit=1,  # only get the latest version
                )
                source_app = latest_version.items[0].source_application
                repub_logger.info(
                    f"↓ Trying to load data for model `{model.name}` of project `{proj.name}`"
                )
                try:
                    received_data = operations.receive(
                        obj_id=latest_version.items[0].referenced_object,
                        remote_transport=server_transport,
                    )
                except SpeckleException as se:
                    repub_logger.warning(
                        f"⚠️ This model probably expired. Republish it manually first from the original source application: {source_app}."
                    )
                    repub_logger.warning(se)
                    continue

                repub_logger.info(
                    f"↑ Trying to republish data for model `{model.name}` of project `{proj.name}`"
                )
                try:
                    object_id = operations.send(
                        base=received_data, transports=[server_transport]
                    )
                except SpeckleException as se:
                    if "Object too large" in str(se):
                        repub_logger.warning(
                            f"⚠️ Model `{model.name}` of project `{proj.name}` is larger than 100 MB, and can therefore not be republished from Python."
                        )
                        repub_logger.warning(
                            f"Instead republish manually from the original source application: {source_app}."
                        )
                    else:
                        repub_logger.warning(se)
                    continue

                version = client.version.create(
                    CreateVersionInput(
                        project_id=proj.id,
                        model_id=model.id,
                        object_id=object_id,
                    )
                )
                repub_logger.info(
                    f"✓ Created version: `{version.id}` of model `{model.name}` on project `{proj.name}`"
                )
                if delete_old_vers.value:
                    all_versions = client.version.get_versions(
                        project_id=proj.id,
                        model_id=model.id,
                    )
                    old_versions = [v.id for v in all_versions.items[1:]]
                    repub_logger.info(f"Deleting old versions: {old_versions}")
                    client.version.delete(
                        DeleteVersionsInput(
                            project_id=proj.id, version_ids=old_versions
                        )
                    )

                print("")

    mo.md(f"""
    ```txt
    {repub_buffer.getvalue()}
    ```
    """)
    return


@app.cell
def _(logging, sys):
    # fmt = "%(levelname)s %(asctime)s %(filename)s %(funcName)s %(lineno)d %(message)s"
    fmt = "%(levelname)s %(asctime)s %(message)s"
    formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")

    # stdout log handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    return fmt, stdout_handler


@app.cell
def _():
    import contextlib
    import io
    import logging
    import sys

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
        contextlib,
        get_default_account,
        get_local_accounts,
        io,
        logging,
        mo,
        operations,
        sys,
    )


if __name__ == "__main__":
    app.run()
