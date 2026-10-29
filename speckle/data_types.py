import marimo

__generated_with = "0.18.0"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    from specklepy.objects import Base
    from specklepy.objects.geometry import Point
    return Base, Point, mo


@app.cell
def _(mo):
    mo.md(r"""
    ## The Three Types

    ### Type 1: Custom Data

    **What it is:** Data you create from scratch with your own structure.

    **Characteristics:**
    - Simple Base objects with custom properties
    - No connector-specific structure
    - Direct property access
    - Full control over schema

    **Example:**

    /// danger | `untis="???"` required
    `Point(x=0, y=0, z=10.5, units="m")`
    ///
    """)
    return


@app.cell
def _(Base, Point):
    # You create this structure
    survey = Base()
    survey.name = "Site Survey 2024"
    survey.date = "2024-01-15"
    survey.points = [
        Point(x=0, y=0, z=10.5, units="m"),
        Point(x=100, y=50, z=12.3, units="m"),
    ]
    survey.notes = "Initial survey"
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### Type 2: Simple Model Data

    **What it is:** Geometry with attached properties, typically from simple exports or scripts.

    **Characteristics:**
    - Geometry objects (Point, Line, Mesh)
    - Properties as dictionaries or direct attributes
    - Optional `displayValue` for visualization
    - Material and layer information
    - Moderate nesting (1-2 levels)

    **Example:**

    ```json
    {
        "speckle_type": "Objects.Geometry.Mesh",
        "vertices": [...],
        "faces": [...],
        "properties": {
            "Material": "Concrete",
            "Thickness": 200,
            "LoadBearing": true
        },
        "layer": "Walls",
        "color": "0xFF808080"
    }
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ### The Speckle objects we need for 3D geospatial GI features

    #### POINT Z

    ```json
    {
        "speckle_type": "Objects.Geometry.Point",
        "vertices": [...],
        "faces": [...],
        "properties": {
            "Material": "Concrete",
            "Thickness": 200,
            "LoadBearing": true
        },
        "layer": "Walls",
        "color": "0xFF808080"
    }
    ```
    """)
    return


if __name__ == "__main__":
    app.run()
