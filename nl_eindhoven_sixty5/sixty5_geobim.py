# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anywidget==0.11.0",
#     "folium>=0.12",
#     "geopandas==1.2.0",
#     "ifcopenshell>=0.8",
#     "mapbox-earcut==2.1.0",
#     "mapclassify==2.11.0",
#     "marimo",
#     "marimo-lens==0.2.4",
#     "matplotlib==3.11.2",
#     "numpy",
#     "polars",
#     "pyarrow==26.0.0",
#     "pyproj>=3.7",
#     "shapely==2.2.0",
#     "specklepy==2026.9.1",
#     "specklewidgets",
#     "traitlets==5.16.1",
# ]
#
# [tool.uv.sources]
# specklewidgets = { git = "https://github.com/bedrock-engineer/specklestuff" }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import math
    import multiprocessing
    import struct
    import urllib.parse
    import urllib.request
    import warnings
    from collections.abc import Iterable, Iterator, Sequence
    from pathlib import Path

    import anywidget
    import geopandas as gpd
    import ifcopenshell
    import ifcopenshell.geom
    import ifcopenshell.util.element
    import ifcopenshell.util.placement
    import ifcopenshell.util.unit
    import mapbox_earcut as earcut
    import marimo as mo
    import numpy as np
    import polars as pl
    import pyproj
    import shapely
    import traitlets
    from specklepy.api import operations
    from specklepy.objects import data_objects as sdo
    from specklepy.objects import geometry as sg
    from specklepy.objects.models.collections.collection import Collection
    from specklepy.objects.other import RenderMaterial
    from specklepy.objects.proxies import ColorProxy, RenderMaterialProxy
    from specklepy.transports.memory import MemoryTransport
    from specklewidgets import GeoSpeckleViewer, models_gz

    return (
        Collection,
        ColorProxy,
        GeoSpeckleViewer,
        Iterable,
        Iterator,
        MemoryTransport,
        Path,
        RenderMaterial,
        RenderMaterialProxy,
        Sequence,
        anywidget,
        earcut,
        gpd,
        ifcopenshell,
        json,
        math,
        mo,
        models_gz,
        multiprocessing,
        np,
        operations,
        pl,
        pyproj,
        sdo,
        sg,
        shapely,
        struct,
        traitlets,
        urllib,
        warnings,
    )


@app.cell(hide_code=True)
def _():
    # marimo-lens: select a region of any output and add a note for the notebook agent
    from marimo_lens import Lens

    lens = Lens()
    lens
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Sixty5 GeoBIM

    The structural IFC model of Sixty5 (Blok S1, Strijp-S, Eindhoven) in a geospatial setting. This notebook

    1. defines the model's Engineering CRS: a derived compound CRS on RD New + NAP (EPSG:7415) that keeps the model's millimeters
    2. turns every building element into a 3D simple feature, with `geom` in the Engineering CRS and `geog` in OGC:CRS84h
    3. shows the model in Speckle's viewer on an OpenStreetMap ground map among the 3D BAG buildings, with the selected elements on a map and in tables
    4. places the model on the globe in CesiumJS

    It is the test dataset for the research question *how do we define an Engineering CRS in a geospatial database (PostGIS, DuckDB spatial, GeoPackage)?* The functions and widgets are under Implementation at the bottom.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Inputs

    - **The IFC**: IFC2X3 in millimeters. It is **not georeferenced**: there is no IfcMapConversion, and `RefLatitude`/`RefLongitude` (42°23′ N, 71°14′ W) is a Revit template default near Boston.
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
    ## The Engineering CRS

    The georeferencing comes from the IFC-GeoReferencer export of the *architectural* model of the same project (`O-S1-BWK-BIM architectural - BIM bouwkundig.ifcgref.json` in the ifc-georeferencer-workshop repo). This assumes that the structural model shares the architectural model's project origin.

    The Engineering CRS is a compound of two derived CRSs:

    - horizontal: a `DerivedProjectedCRS` on RD New (EPSG:28992) with an *Affine parametric transformation* (EPSG:9624)
    - vertical: a `DerivedVerticalCRS` on NAP height (EPSG:5709) with a *Vertical Offset* (EPSG:9616)

    The axes stay in millimetres. PROJ applies a deriving conversion from the base CRS to the derived CRS, and EPSG:9624 maps base CRS values (RD, metres) straight onto derived CRS values (site, millimetres). So the factor 1000 lives in the affine coefficients, and A0 and B0 are in millimetres.

    The export has `orthogonalHeight = 0`, which would put site z = 0 at NAP 0 m, about 19 m below the ground at Sixty5. The georeferencer didn't know the height, so site z = 0 is set to the AHN4 ground level at the nulpunt instead: NAP +18.625 m.
    """)
    return


@app.cell
def _():
    # IFC-GeoReferencer export of the architectural model, EPSG:7415
    EASTINGS = 160071.5
    NORTHINGS = 384156.5
    # Not from the export (it has 0): AHN4 DTM 0.5 m at the nulpunt (EASTINGS, NORTHINGS),
    # from PDOK's WMS layer dtm_05m
    ORTHOGONAL_HEIGHT = 18.625
    X_AXIS_ABSCISSA = 0.6379617540893054
    X_AXIS_ORDINATE = -0.7700680491484481
    return (
        EASTINGS,
        NORTHINGS,
        ORTHOGONAL_HEIGHT,
        X_AXIS_ABSCISSA,
        X_AXIS_ORDINATE,
    )


@app.cell
def _(
    EASTINGS,
    NORTHINGS,
    ORTHOGONAL_HEIGHT,
    X_AXIS_ABSCISSA,
    X_AXIS_ORDINATE,
    derived_engineering_crs,
    math,
    unit_scale,
):
    # The rotation from grid north, as IfcMapConversion gives it: the direction of the site x-axis
    # in the grid
    ROTATION = math.degrees(math.atan2(X_AXIS_ORDINATE, X_AXIS_ABSCISSA))
    engineering_crs = derived_engineering_crs(
        "EPSG:7415", EASTINGS, NORTHINGS, ORTHOGONAL_HEIGHT, ROTATION, unit=unit_scale, name="Sixty5"
    )
    {"rotation from grid north [deg]": ROTATION, "CRS type": engineering_crs.type_name}
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
def _(mo):
    mo.md(r"""
    ## `geom` → RD New + NAP → `geog`

    RD New + NAP → ETRS89 should follow RDNAPTRANS™2018. PROJ does that only when the NSGI grids `nl_nsgi_rdtrans2018.tif` and `nl_nsgi_nlgeo2018.tif` are available, locally or through the PROJ network. Without them it silently falls back to a Helmert transformation that is good to about a metre. The cell below enables the PROJ network and reports which operation it picked.
    """)
    return


@app.cell
def _(engineering_crs, linearized_site_to_ecef, math, mo, pyproj, unit_scale):
    pyproj.network.set_network_enabled(True)
    to_etrs89 = pyproj.Transformer.from_crs(engineering_crs, 4937, always_xy=True, allow_ballpark=False)
    assert math.isfinite(to_etrs89.transform(0, 0, 0)[0]), (
        "RDNAPTRANS grids unavailable: install them or allow PROJ network access"
    )
    # ECEF (WGS 84 geocentric, which EPSG takes as equal to ETRS89) for the 3D Tiles and
    # Cesium, and one 4x4 from site meters to ECEF meters, linearized at the nulpunt (site 0, 0, 0)
    to_ecef = pyproj.Transformer.from_crs(engineering_crs, 4978, always_xy=True, allow_ballpark=False)
    site_to_ecef = linearized_site_to_ecef(to_ecef, unit_scale)
    mo.vstack([mo.md(f"`to_etrs89`: {to_etrs89.description}"), site_to_ecef])
    return site_to_ecef, to_etrs89


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## BIM to simple features

    `bim_simple_features` turns each building element of the IFC into one 3D simple feature,
    with the thickness reduced the way a structural analysis model does it:

    | Element | Simple feature |
    |---|---|
    | columns, beams, piles | `LINESTRING Z` through the centroid of the profile, along the extrusion |
    | slabs | horizontal `POLYGON Z`, the profile outline at mid-depth |
    | footings | horizontal `POLYGON Z` at the bottom face, the bearing level |
    | walls | vertical `POLYGON Z` in the midplane: the profile's long midline, swept up |
    | anything else | horizontal `POLYGON Z`, the footprint at the height of the center of gravity |

    The result is a polars DataFrame with one row per element. `profile`, `body` and `bbox`
    are Structs; `geom` (Engineering CRS, mm) and `geog` (OGC:CRS84h) are WKB, so the table
    goes to GeoParquet or DuckDB as it is. `geom_source` says how each feature was derived:
    cuts (clippings, openings) are ignored, and Breps fall back to their principal axes.

    GEOS works in 2D, so it sees a vertical wall or column as a collapsed geometry.
    `plan()` gives the 2D view: a wall's trace and a column's point.
    """)
    return


@app.cell(hide_code=True)
def _(ifcopenshell, mo, model, pl):
    # Which shape representations does the IFC carry per element class? Body is the 3D
    # volume; Axis (centreline), FootPrint (2D outline), Box and Surface are the simple
    # geometries an exporter may add. Mapped items (type geometry) are resolved one level.
    def _item_types(representation: ifcopenshell.entity_instance) -> str:
        types = set()
        for item in representation.Items:
            if item.is_a("IfcMappedItem"):
                types |= {
                    f"mapped {mapped.is_a()}"
                    for mapped in item.MappingSource.MappedRepresentation.Items
                }
            else:
                types.add(item.is_a())
        return ", ".join(sorted(types))


    ifc_representations = (
        pl.DataFrame(
            [
                {
                    "ifc_class": _product.is_a(),
                    "identifier": _representation.RepresentationIdentifier,
                    "representation_type": _representation.RepresentationType,
                    "items": _item_types(_representation),
                }
                for _product in model.by_type("IfcProduct")
                if _product.Representation
                for _representation in _product.Representation.Representations
            ]
        )
        .group_by(pl.all())
        .len("elements")
        .sort("ifc_class", "identifier", "elements", descending=[False, False, True])
    )
    mo.vstack(
        [
            mo.md(
                f"Structural analysis model: **{len(model.by_type('IfcStructuralAnalysisModel'))}** "
                f"`IfcStructuralAnalysisModel`, {len(model.by_type('IfcStructuralCurveMember'))} "
                f"curve members, {len(model.by_type('IfcStructuralSurfaceMember'))} surface members. "
                f"Exported by `{model.by_type('IfcApplication')[0].ApplicationFullName}`."
            ),
            ifc_representations,
        ]
    )
    return


@app.cell(hide_code=True)
def _(bim_simple_features, mo, model, to_etrs89):
    features = bim_simple_features(model, to_etrs89)
    mo.vstack(
        [
            features.group_by("ifc_class", "kind", "geom_source")
            .len("elements")
            .sort("ifc_class", "geom_source"),
            features,
        ]
    )
    return (features,)


@app.cell
def _(engineering_crs, features, gpd, plan, shapely):
    # The simple features in plan, in the 2D site grid: the horizontal part of the Engineering CRS
    features_plan = gpd.GeoDataFrame(
        features.select("global_id", "ifc_class", "name", "kind", "geom_source").to_pandas(),
        geometry=plan(shapely.from_wkb(features["geom"].to_numpy())),
        crs=engineering_crs.sub_crs_list[0],
    )
    features_plan.explore()
    return (features_plan,)


@app.cell(hide_code=True)
def _(ifc_element_meshes, ifc_property_sets, model, pl, unit_scale):
    # The IFC's own geometry, tessellated by ifcopenshell in site mm: one row per element and
    # surface style. And every element's property and quantity sets.
    ifc_meshes = ifc_element_meshes(model, unit_scale)
    property_sets = ifc_property_sets(model)
    ifc_meshes.group_by("ifc_class", "style").agg(pl.len().alias("elements"), pl.first("rgb")).sort(
        "ifc_class", "style"
    )
    return ifc_meshes, property_sets


@app.cell(hide_code=True)
def _(features, pl, property_sets):
    # Per element: its simple feature and its IFC property sets
    element_data = features.join(
        pl.DataFrame(
            [{"global_id": _global_id, "properties": _sets} for _global_id, _sets in property_sets.items()],
            infer_schema_length=None,
        ),
        on="global_id",
        how="left",
    )
    element_data
    return (element_data,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## GeoSpeckle Viewer

    Speckle's viewer shows the model on an OpenStreetMap ground map, among the buildings of PDOK's 3D Basisvoorziening (the 3D BAG). Sixty5 itself is in the 3D BAG too: its BAG pand, found under the model's footprint, is left out to make room for the model.

    The switch shows either the IFC's own geometry, tessellated by ifcopenshell and colored by its surface styles, or the simple features. The simple features reach the viewer as Speckle objects built in memory, one `DataObject` per row. A polygon has to be cut into triangles before WebGL can fill it, so slabs, footings and walls get a display mesh there, triangulated with earcut on the polygon's own vertices. That mesh exists only in the Speckle objects, not in the table.

    Click an element to select it; shift-click adds to the selection. The map and the tables below follow the selection.
    """)
    return


@app.cell
def _():
    # Colors per IFC class, for the simple features in Speckle and the model in Cesium
    IFC_TYPE_COLORS = {
        "IfcPile": (0.36, 0.56, 0.52),
        "IfcFooting": (0.45, 0.45, 0.50),
        "IfcSlab": (0.86, 0.86, 0.89),
        "IfcColumn": (0.55, 0.55, 0.62),
        "IfcBeam": (0.62, 0.40, 0.36),
        "IfcWallStandardCase": (0.50, 0.72, 0.56),
    }
    return (IFC_TYPE_COLORS,)


@app.cell
def _(
    bag_panden_under,
    features,
    features_plan,
    mo,
    np,
    osm_ground_map,
    pdok_3d_buildings,
    shapely,
    site_to_ecef,
    to_etrs89,
):
    # The surroundings in the viewer's world (site meters): an OpenStreetMap snapshot 150 m
    # around the model, and the 3D BAG over the same area without Sixty5's own building. That
    # building is the BAG pand under the slabs and footings; 0.5 m extra catches the vertices
    # on its outline.
    ground_map, _residual_mm = osm_ground_map(features_plan.total_bounds, to_etrs89, margin=150_000)
    _surfaces = features["kind"].is_in(["midplane", "bottom"]).to_numpy()
    _sixty5_panden = bag_panden_under(
        shapely.union_all(features_plan.geometry.to_numpy()[_surfaces]), to_etrs89
    )
    context_tilesets = [
        pdok_3d_buildings(
            ground_map["bounds"],
            np.linalg.inv(site_to_ecef),
            hide_within=[
                shapely.transform(_pand.buffer(500), lambda _xy: _xy / 1000)
                for _pand in _sixty5_panden.values()
            ],
        )
    ]
    mo.md(
        f"Ground map: {ground_map['width']} x {ground_map['height']} px; one affine transform from "
        f"lon/lat to site is off by at most **{_residual_mm:.1f} mm** over the map. "
        f"3D BAG: {len(context_tilesets[0]['tileset']['root']['children'])} tiles, without BAG pand "
        + ", ".join(f"`{_identificatie}`" for _identificatie in _sixty5_panden)
        + "."
    )
    return context_tilesets, ground_map


@app.cell
def _(
    IFC_TYPE_COLORS,
    features,
    ifc_meshes,
    ifc_meshes_to_speckle,
    models_gz,
    property_sets,
    simple_features_to_speckle,
    speckle_base_objects,
):
    # The two geometries the viewer can show, packed for GeoSpeckleViewer.objects_gz
    viewer_objects = {
        "IFC geometry": models_gz(
            speckle_base_objects(ifc_meshes_to_speckle(ifc_meshes, property_sets, "Sixty5 structure", "mm"))
        ),
        "Simple features": models_gz(
            speckle_base_objects(
                simple_features_to_speckle(
                    features, "Sixty5 structure: simple features", "mm", IFC_TYPE_COLORS
                )
            )
        ),
    }
    return (viewer_objects,)


@app.cell
def _(mo, viewer_objects):
    geometry_choice = mo.ui.radio(list(viewer_objects), value="IFC geometry", inline=True)
    geometry_choice
    return (geometry_choice,)


@app.cell(hide_code=True)
def _(GeoSpeckleViewer, context_tilesets, ground_map, mo):
    viewer = mo.ui.anywidget(GeoSpeckleViewer(ground_map=ground_map, tilesets=context_tilesets))
    viewer
    return (viewer,)


@app.cell(hide_code=True)
def _(features_plan, selected_ids):
    # All elements in plan in gray, the selected ones on top in color and in view
    _map = features_plan.explore(
        color="#9a9a9a", tooltip=["ifc_class", "name"], style_kwds={"weight": 1, "fill": False}, name="All elements"
    )
    _selected = features_plan[features_plan["global_id"].isin(selected_ids)]
    if len(_selected):
        _selected.explore(m=_map, column="ifc_class", tooltip=["ifc_class", "name", "global_id"], name="Selected")
        _west, _south, _east, _north = _selected.to_crs(4326).total_bounds
        _map.fit_bounds([[_south, _west], [_north, _east]], max_zoom=21)
    _map
    return


@app.cell(hide_code=True)
def _(element_data, mo, pl, selected_ids):
    mo.vstack(
        [
            mo.md(f"**Selected elements**: {len(selected_ids)}"),
            element_data.filter(pl.col("global_id").is_in(selected_ids)),
        ]
    )
    return


@app.cell(hide_code=True)
def _(element_data, mo):
    mo.vstack([mo.md(f"**All elements**: {element_data.height}"), element_data])
    return


@app.cell
def _(geometry_choice, viewer, viewer_objects):
    # Swap the geometry in the viewer that is already there, so the ground map and the 3D BAG
    # stay loaded
    viewer.widget.objects_gz = viewer_objects[geometry_choice.value]
    return


@app.cell
def _(viewer):
    # The GlobalIds of the elements selected in the viewer: applicationId in both geometries
    selected_ids = [obj["applicationId"] for obj in viewer.value["selected"]]
    return (selected_ids,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## CesiumJS GeoBIM Viewer

    CesiumJS works in ECEF (EPSG:4978). The meshes stay in local site metres, as ifcopenshell
    tessellates them, and a single 4x4 model matrix places them on the globe. That matrix is
    the exact chain (Engineering CRS, RD New + NAP, RDNAPTRANS to ETRS89, ECEF) linearised at
    the `nulpunt`, the site origin (0, 0, 0). Over this model the linearisation is off by at
    most about 0.7 mm. Keeping the vertices small and the offset in the matrix also keeps
    them precise as glTF float32.

    The terrain comes from [Re:Earth Terrain](https://terrain.reearth.land): Mapterhorn's
    DEM plus the EGM2008 geoid, so its heights are ellipsoidal like the model's. The surface
    is slightly transparent and the camera can go underground, to see the piles.

    Site z = 0 sits at the AHN4 ground level at the nulpunt (NAP +18.625 m), so the model
    stands on the terrain. Re:Earth's ground there is NAP +18.67 m: Mapterhorn's DEM and its
    EGM2008 geoid against AHN4 and RDNAPTRANS' NLGEO2018.
    """)
    return


@app.cell
def _(IFC_TYPE_COLORS, element_meshes_glb, ifc_meshes, mo):
    cesium_glb = element_meshes_glb(ifc_meshes, IFC_TYPE_COLORS)
    mo.md(f"`cesium_glb`: {len(cesium_glb) / 1e6:.1f} MB of binary glTF")
    return (cesium_glb,)


@app.cell
def _(CesiumModelViewer, cesium_glb, mo, site_to_ecef):
    cesium_viewer = mo.ui.anywidget(
        CesiumModelViewer(
            glb=cesium_glb,
            model_matrix=site_to_ecef.flatten(order="F").tolist(),  # Cesium is column-major
            height=550,
        )
    )
    cesium_viewer
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Implementation

    The functions and widgets the cells above use, roughly in the order they appear.
    """)
    return


@app.cell
def _(math, np, pyproj):
    # An Engineering CRS from georeferencing parameters, and its linearization to ECEF
    def derived_engineering_crs(
        base_crs: pyproj.CRS | str | int,
        easting: float,
        northing: float,
        orthometric_height: float,
        rotation: float,
        unit: float,
        name: str,
    ) -> pyproj.CRS:
        """Derives an Engineering CRS from a compound CRS by georeferencing parameters.

        The site origin (0, 0, 0) lands on (easting, northing) in the projected CRS and on
        orthometric_height in the vertical CRS. The scale between site and map is not a
        parameter: it follows from unit and the base CRS's own units. The result is a compound
        of a DerivedProjectedCRS with an Affine parametric transformation (EPSG:9624) and a
        DerivedVerticalCRS with a Vertical Offset (EPSG:9616), with the axes in the site's unit.

        Args:
            base_crs: Compound CRS of a projected and a vertical CRS, such as EPSG:7415.
            easting: Easting of the site origin, in the projected CRS's unit.
            northing: Northing of the site origin, in the projected CRS's unit.
            orthometric_height: Height of the site origin, in the vertical CRS's unit.
            rotation: Angle in degrees from grid north to the site's y-axis, counterclockwise
                positive. Grid north, not true north.
            unit: The site's length unit in meters, 0.001 for millimeters.
            name: Name of the site, used in the names of the CRS and its parts.

        Returns:
            The Engineering CRS.
        """
        base_crs = pyproj.CRS.from_user_input(base_crs)
        projected, vertical = base_crs.sub_crs_list
        map_unit = projected.axis_info[0].unit_conversion_factor  # meters per map unit
        height_unit = vertical.axis_info[0]
        theta = math.radians(rotation)
        k = map_unit / unit  # map units -> site units
        a1, a2 = k * math.cos(theta), k * math.sin(theta)
        b1, b2 = -k * math.sin(theta), k * math.cos(theta)
        a0 = -(a1 * easting + a2 * northing)
        b0 = -(b1 * easting + b2 * northing)
        site_unit = {
            "type": "LinearUnit",
            "name": {0.001: "millimetre", 0.01: "centimetre", 1.0: "metre"}.get(unit, "site unit"),
            "conversion_factor": unit,
        }

        def parameter(name: str, value: float, unit: dict | str) -> dict:
            return {"name": name, "value": value, "unit": unit}

        site_grid = {
            "type": "DerivedProjectedCRS",
            "name": f"{name} site grid",
            "base_crs": projected.to_json_dict(),
            "conversion": {
                "name": f"{name} georeferencing",
                "method": {"name": "Affine parametric transformation", "id": {"authority": "EPSG", "code": 9624}},
                "parameters": [
                    parameter("A0", a0, site_unit),
                    parameter("A1", a1, "unity"),
                    parameter("A2", a2, "unity"),
                    parameter("B0", b0, site_unit),
                    parameter("B1", b1, "unity"),
                    parameter("B2", b2, "unity"),
                ],
            },
            "coordinate_system": {
                "subtype": "Cartesian",
                "axis": [
                    {"name": "Site x", "abbreviation": "x", "direction": "unspecified", "unit": site_unit},
                    {"name": "Site y", "abbreviation": "y", "direction": "unspecified", "unit": site_unit},
                ],
            },
        }
        site_z = {
            "type": "DerivedVerticalCRS",
            "name": f"{name} site z",
            "base_crs": vertical.to_json_dict(),
            "conversion": {
                "name": f"{name} orthometric height",
                "method": {"name": "Vertical Offset", "id": {"authority": "EPSG", "code": 9616}},
                "parameters": [
                    {
                        "name": "Vertical Offset",
                        "value": -orthometric_height,
                        "unit": {
                            "type": "LinearUnit",
                            "name": height_unit.unit_name,
                            "conversion_factor": height_unit.unit_conversion_factor,
                        },
                        "id": {"authority": "EPSG", "code": 8603},
                    }
                ],
            },
            "coordinate_system": {
                "subtype": "vertical",
                "axis": [{"name": "Site z", "abbreviation": "z", "direction": "up", "unit": site_unit}],
            },
        }
        return pyproj.CRS.from_json_dict(
            {"type": "CompoundCRS", "name": f"{name} Engineering CRS", "components": [site_grid, site_z]}
        )


    def linearized_site_to_ecef(to_ecef: pyproj.Transformer, unit: float) -> np.ndarray:
        """Linearizes the transformation from site coordinates to ECEF at the site origin.

        Args:
            to_ecef: Transformer from the Engineering CRS to ECEF (EPSG:4978).
            unit: The site's length unit in meters.

        Returns:
            A 4x4 matrix from site meters to ECEF meters.
        """
        origin_and_axes = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]) / unit  # 1 m along each axis
        origin, x, y, z = np.column_stack(to_ecef.transform(*origin_and_axes.T))
        matrix = np.eye(4)
        matrix[:3, :3] = np.column_stack([x - origin, y - origin, z - origin])
        matrix[:3, 3] = origin
        return matrix

    return derived_engineering_crs, linearized_site_to_ecef


@app.cell
def _(Iterator, ifcopenshell, math, np, pl, pyproj, shapely):
    # One 3D simple feature per building element, with the thickness reduced the way a
    # structural analysis model does it: members become a line through the centroid of their
    # profile, slabs and footings a horizontal surface, walls a vertical surface in their
    # midplane. Any other element becomes its footprint at the height of its center of gravity.
    SIMPLE_FEATURE_KINDS = {
        "IfcColumn": "line",
        "IfcBeam": "line",
        "IfcPile": "line",
        "IfcMember": "line",
        "IfcSlab": "midplane",
        "IfcPlate": "midplane",
        "IfcRoof": "midplane",
        "IfcFooting": "bottom",  # the bearing level
        "IfcWall": "wall",
        "IfcWallStandardCase": "wall",
    }


    def ifc_body_items(
        product: ifcopenshell.entity_instance,
    ) -> Iterator[tuple[np.ndarray, ifcopenshell.entity_instance, bool]]:
        """Yields the items of a product's Body representation.

        Mapped items are resolved, and boolean results (clippings, CSG) are reduced to their
        first operand: the solid before anything was cut away.

        Args:
            product: An IfcProduct with a representation.

        Yields:
            The placement matrix, the geometric item, and whether a boolean result was reduced.
        """
        placement = ifcopenshell.util.placement.get_local_placement(product.ObjectPlacement)
        for representation in product.Representation.Representations:
            if representation.RepresentationIdentifier != "Body":
                continue
            for item in representation.Items:
                if item.is_a("IfcMappedItem"):
                    matrix = placement @ ifcopenshell.util.placement.get_mappeditem_transformation(item)
                    mapped = item.MappingSource.MappedRepresentation.Items
                else:
                    matrix, mapped = placement, [item]
                for solid in mapped:
                    clipped = False
                    while solid.is_a("IfcBooleanResult"):
                        solid, clipped = solid.FirstOperand, True
                    yield matrix, solid, clipped


    def _trim_angle(trim: tuple, matrix: np.ndarray, scale: float) -> float:
        """A trimming point's angle on the circle, in radians: its parameter value, else its position."""
        for value in trim:
            if value.is_a("IfcParameterValue"):
                return value.wrappedValue * scale
        x, y = np.linalg.solve(matrix[:2, :2], np.subtract(trim[0].Coordinates[:2], matrix[:2, 3]))
        return math.atan2(y, x)


    def _arc_points(circle: ifcopenshell.entity_instance, start: float, end: float) -> list[list[float]]:
        """2D points on an IfcCircle from angle start to end, one every 11.25 degrees."""
        angles = np.linspace(start, end, max(2, math.ceil(abs(end - start) / math.radians(11.25)) + 1))
        matrix = ifcopenshell.util.placement.get_axis2placement(circle.Position)
        local = circle.Radius * np.c_[np.cos(angles), np.sin(angles)]
        return (local @ matrix[:2, :2].T + matrix[:2, 3]).tolist()


    def ifc_curve_points(curve: ifcopenshell.entity_instance) -> list:
        """Samples a 2D IFC curve.

        Args:
            curve: An IfcPolyline, IfcCircle, IfcTrimmedCurve on a circle, or an
                IfcCompositeCurve of those.

        Returns:
            2D points along the curve; arcs get a point every 11.25 degrees.

        Raises:
            NotImplementedError: For any other kind of curve.
        """
        if curve.is_a("IfcPolyline"):
            return [point.Coordinates[:2] for point in curve.Points]
        if curve.is_a("IfcCompositeCurve"):
            points = []
            for segment in curve.Segments:
                segment_points = ifc_curve_points(segment.ParentCurve)
                for point in segment_points if segment.SameSense else segment_points[::-1]:
                    if not points or np.linalg.norm(np.subtract(point, points[-1])) > 1e-9:
                        points.append(point)
            return points
        if curve.is_a("IfcCircle"):
            return _arc_points(curve, 0, 2 * math.pi)
        if curve.is_a("IfcTrimmedCurve") and curve.BasisCurve.is_a("IfcCircle"):
            matrix = ifcopenshell.util.placement.get_axis2placement(curve.BasisCurve.Position)
            scale = ifcopenshell.util.unit.calculate_unit_scale(curve.file, "PLANEANGLEUNIT")
            start = _trim_angle(curve.Trim1, matrix, scale)
            end = _trim_angle(curve.Trim2, matrix, scale)
            if curve.SenseAgreement and end <= start:
                end += 2 * math.pi
            elif not curve.SenseAgreement and end >= start:
                end -= 2 * math.pi
            return _arc_points(curve.BasisCurve, start, end)
        raise NotImplementedError(curve.is_a())


    def ifc_profile_outline(profile: ifcopenshell.entity_instance) -> shapely.Polygon:
        """Gives the swept area of an extrusion as a polygon in the extrusion's xy plane.

        Args:
            profile: An IfcRectangleProfileDef, IfcIShapeProfileDef (its outer box),
                IfcCircleProfileDef or IfcArbitraryClosedProfileDef (with voids).

        Returns:
            The outline, with the profile's own Position applied.

        Raises:
            NotImplementedError: For any other kind of profile.
        """
        if profile.is_a("IfcRectangleProfileDef"):
            outline = shapely.box(-profile.XDim / 2, -profile.YDim / 2, profile.XDim / 2, profile.YDim / 2)
        elif profile.is_a("IfcIShapeProfileDef"):
            # The outer box: an I-shape is symmetric, so the centroid is the same
            outline = shapely.box(
                -profile.OverallWidth / 2, -profile.OverallDepth / 2,
                profile.OverallWidth / 2, profile.OverallDepth / 2,
            )
        elif profile.is_a("IfcCircleProfileDef"):
            outline = shapely.Point(0, 0).buffer(profile.Radius, quad_segs=8)
        elif profile.is_a("IfcArbitraryClosedProfileDef"):
            outline = shapely.Polygon(
                ifc_curve_points(profile.OuterCurve),
                [ifc_curve_points(curve) for curve in getattr(profile, "InnerCurves", None) or ()],
            )
        else:
            raise NotImplementedError(profile.is_a())
        if getattr(profile, "Position", None) is None:
            return outline
        matrix = ifcopenshell.util.placement.get_axis2placement(profile.Position)
        return shapely.affinity.affine_transform(
            outline, [matrix[0, 0], matrix[0, 1], matrix[1, 0], matrix[1, 1], matrix[0, -1], matrix[1, -1]]
        )


    def ifc_brep_faces(item: ifcopenshell.entity_instance) -> list[list[tuple[float, float, float]]]:
        """Reads the faces of a Brep.

        Args:
            item: An IfcFacetedBrep or IfcFaceBasedSurfaceModel.

        Returns:
            The outer loop of every face, as 3D points.
        """
        shells = [item.Outer] if item.is_a("IfcFacetedBrep") else item.FbsmFaces
        return [
            [point.Coordinates for point in bound.Bound.Polygon]
            for shell in shells
            for face in shell.CfsFaces
            for bound in face.Bounds
            if bound.is_a("IfcFaceOuterBound") or len(face.Bounds) == 1
        ]


    def _site(matrix: np.ndarray, xyz: np.ndarray) -> np.ndarray:
        """Points through a placement matrix, into site coordinates."""
        return np.asarray(xyz, dtype=float) @ matrix[:3, :3].T + matrix[:3, 3]


    def _extrusion_feature(
        kind: str, matrix: np.ndarray, solid: ifcopenshell.entity_instance, outline: shapely.Polygon
    ) -> shapely.Geometry:
        """The simple feature of an extruded solid, for kind line, midplane, bottom or wall."""
        direction = np.array(solid.ExtrudedDirection.DirectionRatios, dtype=float)
        sweep = solid.Depth * direction / np.linalg.norm(direction)

        def lift(xy: np.ndarray, along: float) -> np.ndarray:  # profile coordinates, a fraction along the sweep -> site
            return _site(matrix, np.c_[np.asarray(xy)[:, :2], np.zeros(len(xy))] + along * sweep)

        if kind == "line":
            centroid = np.array(outline.centroid.coords)
            return shapely.LineString(np.r_[lift(centroid, 0), lift(centroid, 1)])
        if kind in ("midplane", "bottom"):
            if kind == "midplane":
                along = 0.5
            else:  # the lower of the two faces
                along = 0.0 if lift(np.zeros((1, 2)), 0)[0, 2] <= lift(np.zeros((1, 2)), 1)[0, 2] else 1.0
            return shapely.Polygon(
                lift(np.array(outline.exterior.coords), along),
                [lift(np.array(ring.coords), along) for ring in outline.interiors],
            )
        # wall: the long midline of the profile, swept into a vertical surface
        corners = np.array(shapely.oriented_envelope(outline).exterior.coords)[:4]
        edges = np.roll(corners, -1, axis=0) - corners
        short = np.argmin(np.linalg.norm(edges, axis=1))
        ends = np.array([corners[short] + edges[short] / 2, corners[(short + 2) % 4] + edges[(short + 2) % 4] / 2])
        bottom, top = lift(ends, 0), lift(ends, 1)
        return shapely.Polygon([bottom[0], bottom[1], top[1], top[0]])


    def _principal_axis(points: np.ndarray) -> np.ndarray:
        """First principal axis of a point cloud. Within 5 degrees of a site axis it snaps to
        that axis: vertices bunched up at notches and chamfers tilt it slightly."""
        axis = np.linalg.svd(points - points.mean(axis=0))[2][0]
        nearest = np.argmax(np.abs(axis))
        if abs(axis[nearest]) > math.cos(math.radians(5)):
            axis = np.eye(len(axis))[nearest]
        return axis


    def _fallback_feature(kind: str, points: np.ndarray, faces: list[np.ndarray]) -> shapely.Geometry:
        """The simple feature of a Brep, from its vertices: principal axes instead of a profile."""
        lower, upper = points.min(axis=0), points.max(axis=0)
        center = (lower + upper) / 2
        if kind == "line":
            axis = _principal_axis(points)
            along = (points - center) @ axis
            return shapely.LineString([center + along.min() * axis, center + along.max() * axis])
        if kind in ("midplane", "bottom"):
            z = center[2] if kind == "midplane" else lower[2]
            # The faces that aren't vertical, merged in plan
            plan = shapely.union_all(
                [polygon for polygon in map(shapely.Polygon, (face[:, :2] for face in faces)) if polygon.area > 1]
            )
            return shapely.force_3d(plan, z)
        if kind == "wall":
            axis = _principal_axis(points[:, :2])
            along = (points[:, :2] - center[:2]) @ axis
            ends = center[:2] + np.outer([along.min(), along.max()], axis)
            return shapely.Polygon(
                [(*ends[0], lower[2]), (*ends[1], lower[2]), (*ends[1], upper[2]), (*ends[0], upper[2])]
            )
        raise ValueError(kind)


    def _extrusion_mass(
        matrix: np.ndarray, solid: ifcopenshell.entity_instance, outline: shapely.Polygon
    ) -> tuple[shapely.Geometry, np.ndarray, float]:
        """Plan footprint, center of gravity (site) and volume of an extruded solid.

        The footprint is the union of both caps and the side faces in plan, so a slanted
        extrusion covers its whole shadow.
        """
        direction = np.array(solid.ExtrudedDirection.DirectionRatios, dtype=float)
        sweep = solid.Depth * direction / np.linalg.norm(direction)

        def lift(xy: np.ndarray, along: float) -> np.ndarray:
            return _site(matrix, np.c_[np.asarray(xy)[:, :2], np.zeros(len(xy))] + along * sweep)

        rings = [np.array(ring.coords) for ring in (outline.exterior, *outline.interiors)]
        caps = [
            shapely.Polygon(lift(rings[0], along)[:, :2], [lift(ring, along)[:, :2] for ring in rings[1:]])
            for along in (0, 1)
        ]
        sides = []
        for ring in rings:
            bottom, top = lift(ring, 0)[:, :2], lift(ring, 1)[:, :2]
            sides += [shapely.Polygon(np.r_[bottom[i : i + 2], top[i : i + 2][::-1]]) for i in range(len(ring) - 1)]
        footprint = shapely.union_all([part for part in caps + sides if part.area > 1e-6])
        center = lift(np.array(outline.centroid.coords), 0.5)[0]
        return footprint, center, outline.area * solid.Depth


    def _brep_mass(faces: list[np.ndarray]) -> tuple[shapely.Geometry, np.ndarray, float]:
        """Plan footprint, center of gravity and volume of a Brep, from its faces in site coordinates.

        The center of gravity comes from the divergence theorem over the faces, fan-triangulated;
        an open shell without volume falls back to the center of its bounding box.
        """
        footprint = shapely.union_all(
            [
                polygon
                for polygon in (shapely.make_valid(shapely.Polygon(face[:, :2])) for face in faces if len(face) >= 3)
                if polygon.area > 1e-6
            ]
        )
        points = np.concatenate(faces)
        origin = points.mean(axis=0)
        volume, moment = 0.0, np.zeros(3)
        for face in faces:
            a = face[0] - origin
            for b, c in zip(face[1:-1] - origin, face[2:] - origin):
                tetrahedron = a @ np.cross(b, c) / 6
                volume += tetrahedron
                moment += tetrahedron * (a + b + c) / 4
        if abs(volume) < 1e-9 * np.prod(np.ptp(points, axis=0) + 1):
            return footprint, (points.min(axis=0) + points.max(axis=0)) / 2, 0.0
        return footprint, origin + moment / volume, abs(volume)


    def bim_simple_features(model: ifcopenshell.file, to_crs84h: pyproj.Transformer) -> pl.DataFrame:
        """Gives every building element of an IFC model its 3D simple feature.

        Args:
            model: The IFC model.
            to_crs84h: Transformer from the model's Engineering CRS to OGC:CRS84h (lon, lat,
                ellipsoidal height).

        Returns:
            One row per building element with a Body representation: global_id, ifc_class,
            name, kind, geom_source, body_items, the Structs profile, body and bbox, and the
            feature as WKB in geom (Engineering CRS, model units) and geog (OGC:CRS84h).
        """
        rows, geoms = [], []
        for element in model.by_type("IfcBuildingElement"):
            if not element.Representation:
                continue
            kind = SIMPLE_FEATURE_KINDS.get(element.is_a(), "footprint")
            candidates, points = [], []
            for matrix, item, clipped in ifc_body_items(element):
                if item.is_a("IfcExtrudedAreaSolid"):
                    matrix = matrix @ ifcopenshell.util.placement.get_axis2placement(item.Position)
                    outline = ifc_profile_outline(item.SweptArea)
                    direction = np.array(item.ExtrudedDirection.DirectionRatios, dtype=float)
                    ring = np.c_[np.array(outline.exterior.coords), np.zeros(len(outline.exterior.coords))]
                    points += [_site(matrix, ring), _site(matrix, ring + item.Depth * direction / np.linalg.norm(direction))]
                    candidates.append(
                        {
                            "volume": outline.area * item.Depth,
                            "feature": lambda m=matrix, s=item, o=outline: _extrusion_feature(kind, m, s, o),
                            "mass": lambda m=matrix, s=item, o=outline: _extrusion_mass(m, s, o),
                            "geom_source": "extrusion, cuts ignored" if clipped else "extrusion",
                            "profile": {"type": item.SweptArea.is_a(), "name": item.SweptArea.ProfileName, "area": outline.area},
                            "body": {"item": item.is_a(), "depth": item.Depth, "direction": direction.tolist()},
                        }
                    )
                elif item.is_a("IfcFacetedBrep") or item.is_a("IfcFaceBasedSurfaceModel"):
                    faces = [_site(matrix, face) for face in ifc_brep_faces(item)]
                    face_points = np.concatenate(faces)
                    points.append(face_points)
                    candidates.append(
                        {
                            "volume": float(np.prod(np.ptp(face_points, axis=0) + 1)),
                            "feature": lambda p=face_points, f=faces: _fallback_feature(kind, p, f),
                            "mass": lambda f=faces: _brep_mass(f),
                            "geom_source": "principal axes of the brep",
                            "profile": None,
                            "body": {"item": item.is_a(), "depth": None, "direction": None},
                        }
                    )
            if not points:
                continue
            points = np.concatenate(points)
            # Elements with several items (mapped type geometry) take the largest one
            primary = max(candidates, key=lambda candidate: candidate["volume"])
            if kind == "footprint":
                # All body items together, at their volume-weighted center of gravity
                footprints, centers, volumes = zip(*(candidate["mass"]() for candidate in candidates))
                volumes = np.array(volumes)
                z = np.average(np.array(centers)[:, 2], weights=volumes if volumes.sum() > 0 else None)
                geom = shapely.force_3d(shapely.union_all(footprints), z)
                geom_source = "footprint at the center of gravity"
            else:
                geom, geom_source = primary["feature"](), primary["geom_source"]
            geoms.append(geom)
            rows.append(
                {
                    "global_id": element.GlobalId,
                    "ifc_class": element.is_a(),
                    "name": element.Name,
                    "kind": kind,
                    "geom_source": geom_source,
                    "body_items": len(candidates),
                    "profile": primary["profile"],
                    "body": primary["body"],
                    "bbox": dict(zip(("xmin", "ymin", "zmin", "xmax", "ymax", "zmax"), [*points.min(axis=0), *points.max(axis=0)])),
                }
            )
        geoms = np.array(geoms, dtype=object)
        geogs = shapely.transform(
            geoms, lambda xyz: np.column_stack(to_crs84h.transform(*xyz.T)), include_z=True
        )
        return pl.DataFrame(rows, infer_schema_length=None).with_columns(
            pl.Series("geom", shapely.to_wkb(geoms, output_dimension=3), dtype=pl.Binary),
            pl.Series("geog", shapely.to_wkb(geogs, output_dimension=3), dtype=pl.Binary),
        )

    return (bim_simple_features,)


@app.cell
def _(ifcopenshell, multiprocessing, np, pl):
    # The IFC's own geometry and properties: ifcopenshell tessellates every element in the
    # model's coordinates, which are the Engineering CRS's, and reads its property sets
    def _style_name(model: ifcopenshell.file, material_name: str) -> str:
        """The IfcSurfaceStyle name behind an ifcopenshell material, named like
        IfcSurfaceStyleRendering-868, or the material name itself."""
        _, _, step_id = material_name.rpartition("-")
        if step_id.isdigit():
            for style in model.get_inverse(model.by_id(int(step_id))):
                if style.is_a("IfcSurfaceStyle") and style.Name:
                    return style.Name
        return material_name


    def ifc_element_meshes(model: ifcopenshell.file, unit: float) -> pl.DataFrame:
        """Tessellates the elements of an IFC with ifcopenshell, in the model's coordinates.

        Args:
            model: The IFC.
            unit: The model's length unit in meters; ifcopenshell tessellates in meters.

        Returns:
            One row per element and surface style: global_id, ifc_class, name, style, rgb (0..1),
            opacity, vertices (flat x, y, z in the model's unit) and triangles (flat indices into
            vertices). Openings are left out.
        """
        settings = ifcopenshell.geom.settings()
        settings.set("use-world-coords", True)
        iterator = ifcopenshell.geom.iterator(
            settings, model, multiprocessing.cpu_count(), exclude=("IfcOpeningElement",)
        )
        rows = []
        if iterator.initialize():
            while True:
                shape = iterator.get()
                element = model.by_guid(shape.guid)
                geometry = shape.geometry
                vertices = np.reshape(geometry.verts, (-1, 3)) / unit
                triangles = np.reshape(geometry.faces, (-1, 3))
                material_ids = np.asarray(geometry.material_ids)
                for material_id in np.unique(material_ids):
                    # -1: faces without a style
                    material = geometry.materials[material_id] if material_id >= 0 else None
                    used, remapped = np.unique(triangles[material_ids == material_id], return_inverse=True)
                    rows.append(
                        {
                            "global_id": shape.guid,
                            "ifc_class": element.is_a(),
                            "name": element.Name,
                            "style": _style_name(model, material.name) if material else None,
                            "rgb": list(material.diffuse.components) if material else [0.7, 0.7, 0.7],
                            "opacity": 1 - float(np.nan_to_num(material.transparency)) if material else 1.0,
                            "vertices": vertices[used].ravel().tolist(),
                            "triangles": remapped.ravel().tolist(),
                        }
                    )
                if not iterator.next():
                    break
        return pl.DataFrame(rows)


    def ifc_property_sets(model: ifcopenshell.file) -> dict[str, dict[str, dict]]:
        """Reads the property and quantity sets of every element, its type's included.

        Args:
            model: The IFC.

        Returns:
            Per element GlobalId, its sets by name, each a dict of values by property name.
        """
        return {
            element.GlobalId: {
                name: {key: value for key, value in values.items() if key != "id"}
                for name, values in ifcopenshell.util.element.get_psets(element).items()
            }
            for element in model.by_type("IfcElement")
            if not element.is_a("IfcOpeningElement")
        }

    return ifc_element_meshes, ifc_property_sets


@app.cell
def _(np, shapely):
    def plan(geoms: np.ndarray) -> np.ndarray:
        """Gives the 2D view of 3D simple features.

        A vertical surface becomes its trace, a vertical line a point. The tolerances are in the
        units of the CRS: mm here.

        Args:
            geoms: Array of 3D shapely geometries.

        Returns:
            Array of 2D shapely geometries.
        """
        flat = shapely.force_2d(geoms)
        dimension = shapely.get_dimensions(flat)
        out = flat.copy()
        walls = (dimension == 2) & (shapely.area(flat) < 1)
        out[walls] = [shapely.line_merge(shapely.unary_union(shapely.boundary(g))) for g in flat[walls]]
        posts = (dimension == 1) & (shapely.length(flat) < 1)
        out[posts] = shapely.get_point(flat[posts], 0)
        return out

    return (plan,)


@app.cell
def _(
    Collection,
    ColorProxy,
    MemoryTransport,
    RenderMaterial,
    RenderMaterialProxy,
    earcut,
    np,
    operations,
    pl,
    sdo,
    sg,
    shapely,
    warnings,
):
    # Simple features as Speckle v3 objects, for the viewer: one DataObject per row, with
    # applicationId = GlobalId and the other columns as properties. Points, lines and polylines
    # go into displayValue as they are. Speckle has no polygon type the viewer fills, so a
    # POLYGON Z gets a display mesh, triangulated in its own plane. That mesh exists only here,
    # not in the features table.
    def _speckle_color(rgb: tuple[float, float, float]) -> int:
        """RGB in 0..1 to Speckle's signed 32-bit ARGB int."""
        red, green, blue = (round(255 * channel) for channel in rgb)
        return ((0xFF << 24) | (red << 16) | (green << 8) | blue) - (1 << 32)


    def _polygon_mesh(polygon: shapely.Polygon, units: str) -> sg.Mesh:
        """A POLYGON Z as a Speckle Mesh on the polygon's own vertices, triangulated with earcut
        in the polygon's plane (walls are vertical)."""
        rings = [np.array(ring.coords)[:-1, :3] for ring in (polygon.exterior, *polygon.interiors)]
        vertices = np.concatenate(rings)
        origin = rings[0].mean(axis=0)
        # Newell's method: the normal of a planar polygon, whatever its orientation
        normal = np.cross(rings[0], np.roll(rings[0], -1, axis=0)).sum(axis=0)
        normal /= np.linalg.norm(normal)
        u = rings[0][np.argmax(np.linalg.norm(rings[0] - origin, axis=1))] - origin
        u -= (u @ normal) * normal
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        triangles = earcut.triangulate_float64(
            (vertices - origin) @ np.c_[u, v], np.cumsum([len(ring) for ring in rings]).astype(np.uint32)
        )
        faces = np.c_[np.full(len(triangles) // 3, 3), triangles.reshape(-1, 3)]
        return sg.Mesh(vertices=vertices.ravel().tolist(), faces=faces.ravel().tolist(), units=units)


    def speckle_display_value(geom: shapely.Geometry, units: str) -> list:
        """Converts a 3D simple feature to the Speckle geometry the viewer draws.

        Args:
            geom: A 3D shapely geometry; multi-part geometries are split into their parts.
            units: Speckle units of the coordinates, such as "mm".

        Returns:
            Speckle Points, Lines, Polylines and Meshes.

        Raises:
            NotImplementedError: For a geometry type without a Speckle equivalent.
        """
        if geom.geom_type.startswith("Multi") or geom.geom_type == "GeometryCollection":
            return [part for sub in shapely.get_parts(geom) for part in speckle_display_value(sub, units)]
        if geom.geom_type == "Point":
            return [sg.Point(x=geom.x, y=geom.y, z=geom.z, units=units)]
        if geom.geom_type == "LineString":
            coords = np.array(geom.coords)
            if len(coords) == 2:
                start, end = (sg.Point(x=x, y=y, z=z, units=units) for x, y, z in coords)
                return [sg.Line(start=start, end=end, units=units)]
            return [sg.Polyline(value=coords.ravel().tolist(), units=units)]
        if geom.geom_type == "Polygon":
            return [_polygon_mesh(geom, units)]
        raise NotImplementedError(geom.geom_type)


    def simple_features_to_speckle(
        features: pl.DataFrame,
        name: str,
        units: str,
        colors: dict[str, tuple[float, float, float]],
        default_color: tuple[float, float, float] = (0.6, 0.6, 0.6),
    ) -> Collection:
        """Converts simple features to a Speckle Collection, one sub-collection per IFC class.

        Colors per class go into color proxies (points, lines) and render material proxies
        (meshes), keyed on the DataObjects' applicationIds.

        Args:
            features: Simple features as bim_simple_features makes them.
            name: Name of the root collection.
            units: Speckle units of the geom column, such as "mm".
            colors: RGB in 0..1 per IFC class.
            default_color: RGB for the classes not in colors.

        Returns:
            The root collection.
        """
        collections = {}
        for row, geom in zip(
            features.drop("geom", "geog").iter_rows(named=True),
            shapely.from_wkb(features["geom"].to_numpy()),
        ):
            collections.setdefault(row["ifc_class"], []).append(
                sdo.DataObject(
                    applicationId=row["global_id"],
                    name=row["name"] or row["global_id"],
                    properties=row,
                    displayValue=speckle_display_value(geom, units),
                )
            )
        root = Collection(
            name=name,
            elements=[Collection(name=ifc_class, elements=objects) for ifc_class, objects in sorted(collections.items())],
        )
        root.colorProxies, root.renderMaterialProxies = [], []
        for ifc_class, objects in sorted(collections.items()):
            color = _speckle_color(colors.get(ifc_class, default_color))
            ids = [obj.applicationId for obj in objects]
            root.colorProxies.append(ColorProxy(name=ifc_class, value=color, objects=ids))
            root.renderMaterialProxies.append(
                RenderMaterialProxy(value=RenderMaterial(name=ifc_class, diffuse=color), objects=ids)
            )
        return root


    def speckle_base_objects(base: Collection) -> str:
        """Serializes a Speckle Base to v3 objects, without a server.

        Args:
            base: The root object.

        Returns:
            The v3 objects (with ids and __closure) as JSON array text, root first: the same
            format GeoSpeckleViewer loads, see models_gz.
        """
        with warnings.catch_warnings():  # the v3 send pipeline is deprecated since 2026.9
            warnings.simplefilter("ignore", DeprecationWarning)
            transport = MemoryTransport()
            root_id = operations.send(base, transports=[transport], use_default_cache=False)
        children = [content for object_id, content in transport.objects.items() if object_id != root_id]
        return "[" + ",".join([transport.objects[root_id], *children]) + "]"

    def ifc_meshes_to_speckle(
        meshes: pl.DataFrame, property_sets: dict[str, dict[str, dict]], name: str, units: str
    ) -> Collection:
        """Converts tessellated IFC elements to a Speckle Collection, one sub-collection per IFC class.

        Every element becomes a DataObject with applicationId = GlobalId, its property sets as
        properties and one Mesh per surface style, colored by a render material proxy per style.

        Args:
            meshes: Element meshes as ifc_element_meshes makes them.
            property_sets: Property sets per GlobalId, as ifc_property_sets reads them.
            name: Name of the root collection.
            units: Speckle units of the vertices, such as "mm".

        Returns:
            The root collection.
        """
        collections, styles = {}, {}
        for (global_id,), group in meshes.group_by("global_id", maintain_order=True):
            display_value = []
            for index, row in enumerate(group.iter_rows(named=True)):
                faces = np.c_[np.full(len(row["triangles"]) // 3, 3), np.reshape(row["triangles"], (-1, 3))]
                mesh = sg.Mesh(vertices=row["vertices"], faces=faces.ravel().tolist(), units=units)
                mesh.applicationId = f"{global_id}/{index}"
                display_value.append(mesh)
                material, mesh_ids = styles.setdefault(
                    (row["style"], tuple(row["rgb"]), row["opacity"]),
                    (
                        RenderMaterial(
                            name=row["style"] or "unstyled", diffuse=_speckle_color(row["rgb"]), opacity=row["opacity"]
                        ),
                        [],
                    ),
                )
                mesh_ids.append(mesh.applicationId)
            first = group.row(0, named=True)
            collections.setdefault(first["ifc_class"], []).append(
                sdo.DataObject(
                    applicationId=global_id,
                    name=first["name"] or global_id,
                    properties=property_sets.get(global_id, {}),
                    displayValue=display_value,
                )
            )
        root = Collection(
            name=name,
            elements=[Collection(name=ifc_class, elements=objects) for ifc_class, objects in sorted(collections.items())],
        )
        root.renderMaterialProxies = [
            RenderMaterialProxy(value=material, objects=mesh_ids) for material, mesh_ids in styles.values()
        ]
        return root

    return (
        ifc_meshes_to_speckle,
        simple_features_to_speckle,
        speckle_base_objects,
    )


@app.cell
def _(Iterable, Sequence, json, math, np, pyproj, shapely, urllib):
    # The model's surroundings for GeoSpeckleViewer: an OpenStreetMap ground map, PDOK's 3D BAG
    # buildings, and the BAG panden the model replaces
    PDOK_3D_BUILDINGS = (
        "https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/gebouwen/3dtiles?f=json"
    )


    def osm_ground_map(
        site_bounds: Sequence[float],
        to_crs84h: pyproj.Transformer,
        margin: float,
        width: int = 2048,
        z: float = 0.0,
        opacity: float = 0.85,
    ) -> tuple[dict, float]:
        """Places an OpenStreetMap snapshot under the model, for GeoSpeckleViewer.ground_map.

        The map's corners go to the viewer's world (site meters) through one affine transform
        from lon/lat, fitted on a 21 x 21 grid against the exact transformation. Over a few
        hundred meters one affine is enough.

        Args:
            site_bounds: [xmin, ymin, xmax, ymax] in site coordinates (mm).
            to_crs84h: Transformer from the Engineering CRS to OGC:CRS84h.
            margin: Extra map around site_bounds, in mm.
            width: Width of the map image in pixels; the height follows from the bounds.
            z: Height of the map plane in the viewer's world (m).
            opacity: Opacity of the map plane.

        Returns:
            The ground map and the largest residual of the affine fit, in mm.
        """
        xmin, ymin, xmax, ymax = site_bounds
        x = [xmin - margin, xmax + margin]
        y = [ymin - margin, ymax + margin]
        lon, lat, _ = to_crs84h.transform([x[0], x[1], x[1], x[0]], [y[0], y[0], y[1], y[1]], [0, 0, 0, 0])
        west, east, south, north = float(min(lon)), float(max(lon)), float(min(lat)), float(max(lat))

        lon_grid, lat_grid = (
            grid.ravel() for grid in np.meshgrid(np.linspace(west, east, 21), np.linspace(south, north, 21))
        )
        _, _, ground_h = to_crs84h.transform(0, 0, 0)
        site_x, site_y, _ = to_crs84h.transform(
            lon_grid, lat_grid, np.full(lon_grid.size, ground_h), direction="INVERSE"
        )
        design = np.c_[lon_grid, lat_grid, np.ones(lon_grid.size)]
        world = np.c_[site_x, site_y] / 1000
        affine = np.linalg.lstsq(design, world, rcond=None)[0]  # columns: x, y
        residual_mm = 1000 * np.linalg.norm(design @ affine - world, axis=1).max()

        # Pixels in proportion to the bounds in Web Mercator, so MapLibre fills them exactly
        mercator_y = [math.log(math.tan(math.pi / 4 + math.radians(phi) / 2)) for phi in (south, north)]
        ground_map = {
            "bounds": [west, south, east, north],
            "width": width,
            "height": round(width * (mercator_y[1] - mercator_y[0]) / math.radians(east - west)),
            "lnglat_to_world": affine.T.ravel().tolist(),
            "z": z,
            "opacity": opacity,
        }
        return ground_map, float(residual_mm)


    def pdok_3d_buildings(
        bounds: Sequence[float], ecef_to_world: np.ndarray, hide_within: Iterable[shapely.Polygon] = ()
    ) -> dict:
        """Selects PDOK's 3D Basisvoorziening buildings (LoD 2.2), for GeoSpeckleViewer.tilesets.

        Args:
            bounds: [west, south, east, north] in degrees.
            ecef_to_world: 4x4 from ECEF, where the tiles are, to the viewer's world.
            hide_within: Polygons in the viewer's world; buildings mostly inside one are left out.

        Returns:
            The tileset entry: tileset, ecef_to_world, attribution and hide_within.
        """
        return {
            "tileset": site_3d_tiles(PDOK_3D_BUILDINGS, bounds),
            "ecef_to_world": np.asarray(ecef_to_world).flatten(order="F").tolist(),
            "attribution": "3D Basisvoorziening © Kadaster (CC BY 4.0)",
            "hide_within": [
                [np.asarray(ring.coords)[:, :2].tolist() for ring in (polygon.exterior, *polygon.interiors)]
                for polygon in hide_within
            ],
        }


    def site_3d_tiles(tileset_url: str, bounds: Sequence[float]) -> dict:
        """Builds a small tileset with only the finest tiles of tileset_url that overlap bounds.

        The tree is walked only along tiles whose region overlaps the bounds, fetching just the
        external tilesets on that path. 3d-tiles-renderer 0.3.46 marks every child of a tile
        without content as used, in view or not, so on the full PDOK tree it would fetch the
        external tilesets of half the country.

        Args:
            tileset_url: URL of a 3D Tiles tileset with region bounding volumes.
            bounds: [west, south, east, north] in degrees.

        Returns:
            A one-level tileset: an empty root over the content tiles, each with its accumulated
            transform and an absolute content URL.
        """
        west, south, east, north = (math.radians(value) for value in bounds)

        def overlaps(region: list[float]) -> bool:
            return region[0] <= east and region[2] >= west and region[1] <= north and region[3] >= south

        def fetch(url: str) -> dict:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.load(response)

        leaves = []

        def walk(tile: dict, base_url: str, transform: np.ndarray) -> None:
            if not overlaps(tile["boundingVolume"]["region"]):
                return
            if "transform" in tile:
                transform = transform @ np.array(tile["transform"]).reshape(4, 4, order="F")
            uri = tile.get("content", {}).get("uri")
            if uri and uri.split("?")[0].endswith(".json"):
                external_url = urllib.parse.urljoin(base_url, uri)
                walk(fetch(external_url)["root"], external_url, transform)
                return
            children = [child for child in tile.get("children", []) if overlaps(child["boundingVolume"]["region"])]
            if uri and (not children or tile["geometricError"] == 0):
                leaves.append(
                    {
                        "boundingVolume": tile["boundingVolume"],
                        "geometricError": 0,
                        "transform": transform.flatten(order="F").tolist(),
                        "content": {"uri": urllib.parse.urljoin(base_url, uri)},
                    }
                )
                return
            for child in children:
                walk(child, base_url, transform)

        root = fetch(tileset_url)
        walk(root["root"], tileset_url, np.eye(4))
        regions = np.array([leaf["boundingVolume"]["region"] for leaf in leaves])
        return {
            "asset": {"version": "1.1"},
            "geometricError": 1000,
            "root": {
                "boundingVolume": {"region": [*regions[:, :2].min(axis=0), *regions[:, 2:4].max(axis=0), regions[:, 4].min(), regions[:, 5].max()]},
                "geometricError": 1000,
                "refine": "ADD",
                "children": leaves,
            },
        }


    def bag_panden_under(footprint: shapely.Geometry, to_crs84h: pyproj.Transformer) -> dict[str, shapely.Polygon]:
        """Finds the BAG panden with more than half of their area inside a footprint.

        Args:
            footprint: 2D (multi)polygon in site coordinates.
            to_crs84h: Transformer from the Engineering CRS to OGC:CRS84h.

        Returns:
            The panden from PDOK's BAG OGC API, by identificatie, as polygons in site
            coordinates.
        """
        _, _, ground_h = to_crs84h.transform(0, 0, 0)

        def to_site(lonlat: np.ndarray) -> np.ndarray:
            x, y, _ = to_crs84h.transform(
                lonlat[:, 0], lonlat[:, 1], np.full(len(lonlat), ground_h), direction="INVERSE"
            )
            return np.c_[x, y]

        x0, y0, x1, y1 = footprint.bounds
        lon, lat, _ = to_crs84h.transform([x0, x1, x1, x0], [y0, y0, y1, y1], [0, 0, 0, 0])
        url = "https://api.pdok.nl/kadaster/bag/ogc/v2/collections/pand/items?" + urllib.parse.urlencode(
            {"bbox": f"{min(lon)},{min(lat)},{max(lon)},{max(lat)}", "f": "json", "limit": 1000}
        )
        with urllib.request.urlopen(url, timeout=30) as response:
            panden = json.load(response)["features"]
        under = {}
        for pand in panden:
            polygon = shapely.transform(shapely.geometry.shape(pand["geometry"]), to_site)
            if polygon.intersection(footprint).area > polygon.area / 2:
                under[pand["properties"]["identificatie"]] = polygon
        return under

    return bag_panden_under, osm_ground_map, pdok_3d_buildings


@app.cell
def _(json, np, pl, struct):
    def triangles_glb(groups: dict[str, tuple[np.ndarray, tuple[float, float, float]]]) -> bytes:
        """Writes triangles as binary glTF (z up, meters), one flat-shaded primitive per group.

        Args:
            groups: Per name, the triangles as an (n, 3, 3) array of corner coordinates and an
                RGB color in 0..1.

        Returns:
            The glb file content.
        """
        buffer, buffer_views, accessors, primitives, materials = bytearray(), [], [], [], []

        def add_vec3(array: np.ndarray) -> int:
            data = np.ascontiguousarray(array, dtype=np.float32)
            buffer_views.append(
                {"buffer": 0, "byteOffset": len(buffer), "byteLength": data.nbytes, "target": 34962}
            )
            buffer.extend(data.tobytes())
            accessors.append(
                {
                    "bufferView": len(buffer_views) - 1,
                    "componentType": 5126,  # float32
                    "count": len(data),
                    "type": "VEC3",
                    "min": data.min(axis=0).tolist(),
                    "max": data.max(axis=0).tolist(),
                }
            )
            return len(accessors) - 1

        for name, (triangles, rgb) in groups.items():
            normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
            lengths = np.linalg.norm(normals, axis=1, keepdims=True)
            normals = np.where(lengths > 0, normals / np.where(lengths > 0, lengths, 1), [0, 0, 1])
            materials.append(
                {
                    "name": name,
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [*rgb, 1.0],
                        "metallicFactor": 0.0,
                        "roughnessFactor": 0.9,
                    },
                    "doubleSided": True,
                }
            )
            primitives.append(
                {
                    "attributes": {
                        "POSITION": add_vec3(triangles.reshape(-1, 3)),
                        "NORMAL": add_vec3(np.repeat(normals, 3, axis=0)),
                    },
                    "material": len(materials) - 1,
                }
            )

        buffer.extend(b"\0" * (-len(buffer) % 4))
        gltf = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": primitives}],
            "materials": materials,
            "buffers": [{"byteLength": len(buffer)}],
            "bufferViews": buffer_views,
            "accessors": accessors,
        }
        json_chunk = json.dumps(gltf).encode()
        json_chunk += b" " * (-len(json_chunk) % 4)
        return b"".join(
            [
                struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(json_chunk) + 8 + len(buffer)),
                struct.pack("<I4s", len(json_chunk), b"JSON"),
                json_chunk,
                struct.pack("<I4s", len(buffer), b"BIN\0"),
                bytes(buffer),
            ]
        )


    def element_meshes_glb(
        meshes: pl.DataFrame,
        colors: dict[str, tuple[float, float, float]],
        default_color: tuple[float, float, float] = (0.7, 0.7, 0.7),
    ) -> bytes:
        """Writes element meshes as binary glTF in meters, one primitive per IFC class.

        Args:
            meshes: Element meshes in mm, as ifc_element_meshes makes them.
            colors: RGB in 0..1 per IFC class.
            default_color: RGB for the classes not in colors.

        Returns:
            The glb file content.
        """
        groups = {}
        for (ifc_class,), group in meshes.group_by("ifc_class"):
            corners = np.concatenate(
                [
                    np.reshape(vertices, (-1, 3))[np.reshape(triangles, (-1, 3))]
                    for vertices, triangles in zip(group["vertices"].to_list(), group["triangles"].to_list())
                ]
            )
            groups[ifc_class] = (corners / 1000, colors.get(ifc_class, default_color))
        return triangles_glb(groups)

    return (element_meshes_glb,)


@app.cell
def _(anywidget, np, traitlets):
    CESIUM_VIEWER_ESM = """
    const CESIUM = "https://cdn.jsdelivr.net/npm/cesium@1.146.0/Build/Cesium/";

    async function render({ model, el }) {
      // Cesium loads its web workers and assets relative to CESIUM_BASE_URL
      window.CESIUM_BASE_URL = CESIUM;
      const Cesium = await import(`${CESIUM}index.js`);
      const css = document.createElement("link");
      css.rel = "stylesheet";
      css.href = `${CESIUM}Widgets/widgets.css`;
      el.appendChild(css);
      const container = document.createElement("div");
      container.style.cssText = `width: 100%; height: ${model.get("height")}px;`;
      el.appendChild(container);

      // OpenStreetMap on a quantized-mesh terrain with ellipsoidal heights: nothing that
      // needs a Cesium ion token
      Cesium.Ion.defaultAccessToken = null;
      const terrainUrl = model.get("terrain_url");
      const viewer = new Cesium.Viewer(container, {
        baseLayer: new Cesium.ImageryLayer(
          new Cesium.OpenStreetMapImageryProvider({ url: "https://tile.openstreetmap.org/" })
        ),
        terrain: terrainUrl
          ? new Cesium.Terrain(
              Cesium.CesiumTerrainProvider.fromUrl(terrainUrl, { requestVertexNormals: true })
            )
          : undefined,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        fullscreenButton: false,
        animation: false,
        timeline: false,
        infoBox: false,
        selectionIndicator: false,
      });

      // See-through surface and a camera that can go underground
      // https://cesium.com/blog/2020/06/16/visualizing-underground/
      const { globe } = viewer.scene;
      globe.depthTestAgainstTerrain = true;
      globe.translucency.enabled = true;
      globe.translucency.frontFaceAlpha = model.get("globe_alpha");
      globe.translucency.backFaceAlpha = 1.0; // don't look through to the far side of the Earth
      globe.undergroundColor = Cesium.Color.fromCssColorString("#e8e4e0");
      viewer.scene.screenSpaceCameraController.enableCollisionDetection = false;

      // Light along the view direction, so the model is lit whatever the time of day
      viewer.scene.light = new Cesium.DirectionalLight({ direction: viewer.scene.camera.directionWC });
      viewer.scene.preRender.addEventListener((scene) => {
        scene.light.direction = Cesium.Cartesian3.clone(scene.camera.directionWC, scene.light.direction);
      });

      let current;
      async function load() {
        if (current) viewer.scene.primitives.remove(current);
        current = undefined;
        const bytes = model.get("glb");
        if (!bytes || bytes.byteLength === 0) return;
        const url = URL.createObjectURL(new Blob([bytes], { type: "model/gltf-binary" }));
        current = await Cesium.Model.fromGltfAsync({
          url,
          modelMatrix: Cesium.Matrix4.fromArray(model.get("model_matrix")),
          upAxis: Cesium.Axis.Z,
          forwardAxis: Cesium.Axis.X,
        });
        viewer.scene.primitives.add(current);
        current.readyEvent.addEventListener(() => {
          const sphere = current.boundingSphere;
          viewer.camera.flyToBoundingSphere(sphere, {
            duration: 0,
            offset: new Cesium.HeadingPitchRange(0, -0.35, sphere.radius * 3),
          });
        });
      }
      model.on("change:glb", load);
      model.on("change:model_matrix", load);
      await load();
      return () => viewer.destroy();
    }

    export default { render };
    """


    class CesiumModelViewer(anywidget.AnyWidget):
        """A CesiumJS globe with one glTF model, placed by a 4x4 model-to-ECEF matrix."""

        _esm = CESIUM_VIEWER_ESM
        glb = traitlets.Bytes(b"").tag(sync=True)
        model_matrix = traitlets.List(np.eye(4).flatten().tolist()).tag(sync=True)  # column-major
        height = traitlets.Int(600).tag(sync=True)
        # Quantized-mesh terrain with heights above the WGS84 ellipsoid; "" for none
        terrain_url = traitlets.Unicode(
            "https://terrain.reearth.land/cesium-mesh/ellipsoid"
        ).tag(sync=True)
        globe_alpha = traitlets.Float(0.7).tag(sync=True)  # opacity of the terrain surface

    return (CesiumModelViewer,)


if __name__ == "__main__":
    app.run()
