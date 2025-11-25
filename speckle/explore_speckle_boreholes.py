import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from specklepy.api import operations
    from specklepy.api.credentials import get_local_accounts, get_default_account
    from specklepy.api.client import SpeckleClient
    from specklepy.transports.server import ServerTransport
    from specklepy.objects.geometry import Point, Line, Polyline
    from specklepy.objects import Base
    return (
        Base,
        Line,
        Point,
        Polyline,
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

    transport = ServerTransport(stream_id=projects_dd.value.id, client=client)

    models = client.model.get_models(project_id)
    models_dd = mo.ui.dropdown({mdl.name: mdl for mdl in models.items})
    models_dd
    return (transport,)


@app.cell
def _(Base, Line, Point, Polyline):
    # Create some points
    p1 = Point(x=0, y=0, z=0, units="m")
    p2 = Point(x=10, y=0, z=0, units="m")
    p3 = Point(x=10, y=10, z=0, units="m")
    p4 = Point(x=0, y=10, z=0, units="m")

    # Create a line
    line = Line(start=p1, end=p2)

    # Create a polyline (closed rectangle)
    # Polyline uses a flat list of coordinates: [x1, y1, z1, x2, y2, z2, ...]
    coords = [
        p1.x, p1.y, p1.z,
        p2.x, p2.y, p2.z,
        p3.x, p3.y, p3.z,
        p4.x, p4.y, p4.z,
        p1.x, p1.y, p1.z,  # Close the shape
    ]
    polyline = Polyline(value=coords)
    polyline.units = "m"

    # ✅ IMPORTANT: Wrap geometry in Base object for viewer visibility
    object = Base()
    object.line = line
    object.rectangle = polyline
    object.points = [p1, p2, p3, p4]
    return


@app.cell
def _(ams_noord, ams_noord_models, client, operations, transport):
    ams_noord_gi_latest = client.version.get_versions(
        project_id=ams_noord.id, 
        model_id=ams_noord_models["epsg:7415/geo/gi"].id,
        limit=1 # only get the latest version
    )
    ams_noord_gi = operations.receive(
        obj_id=ams_noord_gi_latest.items[0].id,
        remote_transport=transport
    )
    return


if __name__ == "__main__":
    app.run()
