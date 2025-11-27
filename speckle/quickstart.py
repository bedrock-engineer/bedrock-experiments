import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from specklepy.api import operations
    from specklepy.api.client import SpeckleClient
    from specklepy.api.credentials import get_default_account
    from specklepy.objects.geometry import Point, Line, Polyline
    from specklepy.objects import Base
    from specklepy.transports.server import ServerTransport
    from specklepy.core.api.inputs.project_inputs import ProjectCreateInput
    from specklepy.core.api.inputs.model_inputs import CreateModelInput
    from specklepy.core.api.inputs.version_inputs import CreateVersionInput
    return (
        Base,
        CreateVersionInput,
        Line,
        Point,
        Polyline,
        ServerTransport,
        SpeckleClient,
        get_default_account,
        mo,
        operations,
    )


@app.cell
def _(mo):
    mo.md(r"""
    ### 1. Authenticate
    """)
    return


@app.cell
def _(SpeckleClient, get_default_account):
    # 1. Authenticate
    client = SpeckleClient(host="app.speckle.systems")

    # Authenticate wtih account stored by desktop connector
    account = get_default_account()
    client.authenticate_with_account(account)
    # Authenticate with token
    # token = "your_token_here"  # Replace with your token
    # client.authenticate_with_token(token)

    print(f"✓ Authenticated as {client.account.userInfo.name}")
    return (client,)


@app.cell
def _(mo):
    mo.md(r"""
    ### 2. Create project

    /// danger | `visibility` required
    ProjectCreateInput visibility Field required
    visibility Input should be 'PRIVATE', 'PUBLIC', 'UNLISTED' or 'WORKSPACE'
    ///

    /// danger | Workspaces
    Projects can't be created outside of workspaces
    ///

    Maybe it'd work better to let people input an ID of a existing project, such that they don't run into issues with workspaces or the 1 project per workspace limit on free tier?

    In case you were OK with pushing people towards using marimo notebooks, you could also let people select one of their Speckle projects from a dropdown using:

    ```python
    projects = client.active_user.get_projects()
    projects_dd = mo.ui.dropdown({proj.name: proj for proj in projects.items})
    projects_dd
    ```
    """)
    return


@app.cell
def _(client):
    # 2. Create project
    # project = client.project.create(ProjectCreateInput(
    #     name="My First Python Speckle Project",
    #     description="Learning specklepy",
    #     visibility="PUBLIC"
    # ))
    # print(f"✓ Created project: {project.id}")

    # 2. Get project
    project =  client.project.get("461cc2a20f")
    project.name
    return (project,)


@app.cell
def _(mo):
    mo.md(r"""
    ### 3. Create geometry
    """)
    return


@app.cell
def _(Base, Line, Point, Polyline):
    # 3. Create geometry
    p1 = Point(x=0, y=0, z=0, units="m")
    p2 = Point(x=10, y=0, z=0, units="m")
    p3 = Point(x=10, y=10, z=0, units="m")
    p4 = Point(x=0, y=10, z=0, units="m")

    line = Line(start=p1, end=p2, units="m")

    # Polyline uses a flat list of coordinates
    coords = [
        p1.x, p1.y, p1.z,
        p2.x, p2.y, p2.z,
        p3.x, p3.y, p3.z,
        p4.x, p4.y, p4.z,
        p1.x, p1.y, p1.z,
    ]
    polyline = Polyline(value=coords, units="m")

    data = Base()
    data.line = line
    data.rectangle = polyline
    data.points = [p1, p2, p3, p4]
    print("✓ Created geometry")
    return (data,)


@app.cell
def _(mo):
    mo.md(r"""
    ### 4. Send data
    """)
    return


@app.cell
def _(ServerTransport, client, data, operations, project):
    # 4. Send data
    # Send to server
    transport = ServerTransport(stream_id=project.id, client=client)
    object_id = operations.send(base=data, transports=[transport])
    print(f"✓ Sent data: {object_id}")
    return object_id, transport


@app.cell
def _(mo):
    mo.md(r"""
    #### 5. Create version

    /// danger | `client.model.list` doesn't exist
    'ModelResource' object has no attribute 'list'
    This should instead be `client.model.get_models`
    ///

    /// danger | `models[0]` doesn't work
    'ResourceCollection[Model]' object is not subscriptable
    This should instead use `.items[index]`
    Also there are some other errors in the code =>
    `model = models.items[0]`
    ///
    """)
    return


@app.cell
def _(CreateVersionInput, client, object_id, project):
    # 5. Create version
    # models = client.model.list(project.id)
    models = client.model.get_models(project.id)
    # model_id = models[0].id
    model = models.items[0]

    version_input = CreateVersionInput(
        project_id=project.id,
        model_id=model.id,
        object_id=object_id,
        message="My first version!"
    )
    version = client.version.create(version_input)
    print(f"✓ Created version: {version.id}")
    print(f"View: https://app.speckle.systems/projects/{project.id}/models/{model.id}")
    return


@app.cell
def _(object_id, operations, transport):
    # 6. Receive data
    received_data = operations.receive(obj_id=object_id, remote_transport=transport)
    print(f"✓ Received data: {len(received_data.points)} points")
    return


if __name__ == "__main__":
    app.run()
