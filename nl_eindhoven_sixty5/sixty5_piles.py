# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "altair",
#     "ifcopenshell>=0.8",
#     "marimo",
#     "numpy",
#     "polars",
#     "pyproj>=3.7",
# ]
# ///

import marimo

__generated_with = "0.19.7"
app = marimo.App(width="medium")


@app.cell
def _():
    import math
    import urllib.request
    from pathlib import Path

    import altair as alt
    import ifcopenshell
    import ifcopenshell.util.placement
    import ifcopenshell.util.unit
    import marimo as mo
    import numpy as np
    import polars as pl
    import pyproj
    return Path, alt, ifcopenshell, math, mo, np, pl, pyproj, urllib


@app.cell
def _(mo):
    mo.md(r"""
    # Sixty5 piles in an Engineering CRS

    Test dataset for the research question *how do we define an Engineering CRS in a geospatial database (PostGIS, DuckDB spatial, GeoPackage)?*

    The structural IFC model of Sixty5 (Blok S1, Strijp-S, Eindhoven) contains 146 foundation piles. This notebook

    1. extracts the pile head and tip positions with ifcopenshell, in the model's own coordinates (millimetres): these are the `geom` values
    2. defines the model's Engineering CRS as a derived compound CRS on EPSG:7415 (RD New + NAP height), keeping the axes in millimetres
    3. converts the pile positions to RD New + NAP and transforms them to ETRS89 lon, lat, ellipsoidal height: these are the `geog` values
    """)
    return


@app.cell
def _(Path, urllib):
    IFC_URL = "https://r2.eu.bedrock.engineer/ifc-georeferencer-workshop/O-S1-CON-Structural%20engineering%20-%20Constructie.ifc"
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    ifc_path = data_dir / "O-S1-CON-Structural engineering - Constructie.ifc"
    if not ifc_path.exists():
        urllib.request.urlretrieve(IFC_URL, ifc_path)
    return (ifc_path,)


@app.cell
def _(ifc_path, ifcopenshell):
    model = ifcopenshell.open(ifc_path)
    unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
    site = model.by_type("IfcSite")[0]
    {
        "schema": model.schema,
        "length unit [m]": unit_scale,
        "IfcSite.RefLatitude": site.RefLatitude,
        "IfcSite.RefLongitude": site.RefLongitude,
        "IfcPile count": len(model.by_type("IfcPile")),
    }
    return model, unit_scale


@app.cell
def _(mo):
    mo.md(r"""
    The file is IFC2X3 in millimetres and is **not georeferenced**: there is no IfcMapConversion, and `RefLatitude`/`RefLongitude` (42°23′ N, 71°14′ W) is a Revit template default near Boston.

    ## Pile head and tip

    Every pile is an `IfcExtrudedAreaSolid` of a circular profile. The extrusion starts at the pile tip and runs `Depth` along `ExtrudedDirection`, so

    - tip = object placement × solid position × (0, 0, 0)
    - head = tip + `Depth` × extrusion direction
    """)
    return


@app.cell
def _(ifcopenshell, model, np, pl):
    def pile_record(pile):
        solid = pile.Representation.Representations[0].Items[0]
        assert solid.is_a("IfcExtrudedAreaSolid") and solid.SweptArea.is_a("IfcCircleProfileDef")
        placement = ifcopenshell.util.placement.get_local_placement(pile.ObjectPlacement)
        position = ifcopenshell.util.placement.get_axis2placement(solid.Position)
        matrix = placement @ position
        tip = matrix @ np.array([0.0, 0.0, 0.0, 1.0])
        direction = matrix[:3, :3] @ np.array(solid.ExtrudedDirection.DirectionRatios)
        head = tip[:3] + solid.Depth * direction
        return {
            "global_id": pile.GlobalId,
            "name": pile.Name,
            "pile_type": solid.SweptArea.ProfileName,
            "diameter_mm": 2 * solid.SweptArea.Radius,
            "length_mm": solid.Depth,
            "head_x_mm": head[0],
            "head_y_mm": head[1],
            "head_z_mm": head[2],
            "tip_x_mm": tip[0],
            "tip_y_mm": tip[1],
            "tip_z_mm": tip[2],
        }

    piles = pl.DataFrame([pile_record(p) for p in model.by_type("IfcPile")])
    piles
    return (piles,)


@app.cell
def _(mo):
    mo.md(r"""
    ## The Engineering CRS

    The georeferencing comes from the IFC-GeoReferencer export of the *architectural* model of the same project (`O-S1-BWK-BIM architectural - BIM bouwkundig.ifcgref.json` in the ifc-georeferencer-workshop repo). This assumes that the structural model shares the architectural model's project origin.

    The Engineering CRS is a compound of two derived CRSs:

    - horizontal: a `DerivedProjectedCRS` on RD New (EPSG:28992) with an *Affine parametric transformation* (EPSG:9624)
    - vertical: a `DerivedVerticalCRS` on NAP height (EPSG:5709) with a *Vertical Offset* (EPSG:9616)

    The axes stay in millimetres. PROJ applies a deriving conversion from the base CRS to the derived CRS, and EPSG:9624 maps base CRS values (RD, metres) straight onto derived CRS values (site, millimetres). So the factor 1000 lives in the affine coefficients, and A0 and B0 are in millimetres.

    The export has `orthogonalHeight = 0`, so site z = 0 is taken as NAP 0 m. That still needs checking against the project's datum level (*peil*).
    """)
    return


@app.cell
def _():
    # IFC-GeoReferencer export of the architectural model, EPSG:7415
    EASTINGS = 160071.5
    NORTHINGS = 384156.5
    ORTHOGONAL_HEIGHT = 0.0
    X_AXIS_ABSCISSA = 0.6379617540893054
    X_AXIS_ORDINATE = -0.7700680491484481
    return EASTINGS, NORTHINGS, ORTHOGONAL_HEIGHT, X_AXIS_ABSCISSA, X_AXIS_ORDINATE


@app.cell
def _(
    EASTINGS,
    NORTHINGS,
    ORTHOGONAL_HEIGHT,
    X_AXIS_ABSCISSA,
    X_AXIS_ORDINATE,
    math,
    pyproj,
    unit_scale,
):
    theta = math.atan2(X_AXIS_ORDINATE, X_AXIS_ABSCISSA)
    k = 1 / unit_scale  # RD metres -> site millimetres
    a1, a2 = k * math.cos(theta), k * math.sin(theta)
    b1, b2 = -k * math.sin(theta), k * math.cos(theta)
    a0 = -(a1 * EASTINGS + a2 * NORTHINGS)
    b0 = -(b1 * EASTINGS + b2 * NORTHINGS)

    millimetre = {"type": "LinearUnit", "name": "millimetre", "conversion_factor": unit_scale}

    def affine_parameter(name, value, unit):
        return {"name": name, "value": value, "unit": unit}

    site_grid = {
        "type": "DerivedProjectedCRS",
        "name": "Sixty5 site grid",
        "base_crs": pyproj.CRS.from_epsg(28992).to_json_dict(),
        "conversion": {
            "name": "Sixty5 map conversion",
            "method": {"name": "Affine parametric transformation", "id": {"authority": "EPSG", "code": 9624}},
            "parameters": [
                affine_parameter("A0", a0, millimetre),
                affine_parameter("A1", a1, "unity"),
                affine_parameter("A2", a2, "unity"),
                affine_parameter("B0", b0, millimetre),
                affine_parameter("B1", b1, "unity"),
                affine_parameter("B2", b2, "unity"),
            ],
        },
        "coordinate_system": {
            "subtype": "Cartesian",
            "axis": [
                {"name": "Site x", "abbreviation": "x", "direction": "unspecified", "unit": millimetre},
                {"name": "Site y", "abbreviation": "y", "direction": "unspecified", "unit": millimetre},
            ],
        },
    }
    site_z = {
        "type": "DerivedVerticalCRS",
        "name": "Sixty5 site z",
        "base_crs": pyproj.CRS.from_epsg(5709).to_json_dict(),
        "conversion": {
            "name": "Sixty5 orthogonal height",
            "method": {"name": "Vertical Offset", "id": {"authority": "EPSG", "code": 9616}},
            "parameters": [
                {"name": "Vertical Offset", "value": -ORTHOGONAL_HEIGHT, "unit": "metre", "id": {"authority": "EPSG", "code": 8603}}
            ],
        },
        "coordinate_system": {
            "subtype": "vertical",
            "axis": [{"name": "Site z", "abbreviation": "z", "direction": "up", "unit": millimetre}],
        },
    }
    engineering_crs = pyproj.CRS.from_json_dict(
        {"type": "CompoundCRS", "name": "Sixty5 Engineering CRS", "components": [site_grid, site_z]}
    )
    {"rotation from grid east [deg]": math.degrees(theta), "CRS type": engineering_crs.type_name}
    return (engineering_crs,)


@app.cell
def _(engineering_crs, mo):
    mo.accordion(
        {
            "WKT2": mo.md(f"```\n{engineering_crs.to_wkt(pretty=True)}\n```"),
            "PROJJSON": mo.md(f"```json\n{engineering_crs.to_json(pretty=True)}\n```"),
        }
    )
    return


@app.cell
def _(EASTINGS, NORTHINGS, ORTHOGONAL_HEIGHT, engineering_crs, pyproj):
    to_rd_nap = pyproj.Transformer.from_crs(engineering_crs, 7415, always_xy=True)
    # Sanity checks: the site origin lands on the map conversion origin, and 10 m along site x lands 10 m along the rotated axis
    origin = to_rd_nap.transform(0, 0, 0)
    assert abs(origin[0] - EASTINGS) < 1e-6 and abs(origin[1] - NORTHINGS) < 1e-6 and abs(origin[2] - ORTHOGONAL_HEIGHT) < 1e-9
    to_rd_nap.definition
    return (to_rd_nap,)


@app.cell
def _(mo):
    mo.md(r"""
    ## `geom` → RD New + NAP → `geog`

    RD New + NAP → ETRS89 should follow RDNAPTRANS™2018. PROJ does that only when the NSGI grids `nl_nsgi_rdtrans2018.tif` and `nl_nsgi_nlgeo2018.tif` are available, locally or through the PROJ network. Without them it silently falls back to a Helmert transformation that is good to about a metre. The cell below enables the PROJ network and reports which operation it picked.
    """)
    return


@app.cell
def _(engineering_crs, math, piles, pl, pyproj, to_rd_nap):
    pyproj.network.set_network_enabled(True)
    to_etrs89 = pyproj.Transformer.from_crs(engineering_crs, 4937, always_xy=True, allow_ballpark=False)

    head_e, head_n, head_h = to_rd_nap.transform(piles["head_x_mm"], piles["head_y_mm"], piles["head_z_mm"])
    head_lon, head_lat, head_ellh = to_etrs89.transform(piles["head_x_mm"], piles["head_y_mm"], piles["head_z_mm"])
    assert all(map(math.isfinite, head_lon)), "RDNAPTRANS grids unavailable: install them or allow PROJ network access"

    piles_georef = piles.with_columns(
        pl.Series("head_rd_x_m", head_e),
        pl.Series("head_rd_y_m", head_n),
        pl.Series("head_nap_m", head_h),
        pl.Series("head_lon", head_lon),
        pl.Series("head_lat", head_lat),
        pl.Series("head_ellh_m", head_ellh),
    )
    print(to_etrs89.description)
    piles_georef
    return (piles_georef,)


@app.cell
def _(alt, mo, piles_georef):
    mo.ui.altair_chart(
        alt.Chart(piles_georef)
        .mark_circle()
        .encode(
            x=alt.X("head_rd_x_m", scale=alt.Scale(zero=False)),
            y=alt.Y("head_rd_y_m", scale=alt.Scale(zero=False)),
            color="pile_type",
            tooltip=["name", "pile_type", "head_nap_m"],
        )
        .properties(title="Pile heads in RD New", width=500, height=500)
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Next

    Write `piles` to PostGIS, DuckDB spatial and GeoPackage with `geom` in the Engineering CRS (mm) and `geog` in ETRS89, register the Engineering CRS in each store, and check the round trip `geom` → `geog` → `geom` to within a millimetre.
    """)
    return


if __name__ == "__main__":
    app.run()
