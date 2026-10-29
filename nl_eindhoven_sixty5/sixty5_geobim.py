# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "altair",
#     "anywidget==0.11.0",
#     "folium>=0.12",
#     "geopandas==1.2.0",
#     "ifcopenshell>=0.8",
#     "mapbox-earcut==2.1.0",
#     "mapclassify==2.11.0",
#     "marimo",
#     "matplotlib==3.11.2",
#     "numpy",
#     "polars",
#     "pyarrow==26.0.0",
#     "pyproj>=3.7",
#     "shapely==2.2.0",
#     "specklepy==2026.9.1",
#     "traitlets==5.16.1",
#     "wigglystuff==0.5.36",
# ]
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import gzip
    import json
    import math
    import sqlite3
    import struct
    import urllib.parse
    import urllib.request
    import warnings
    from contextlib import closing
    from pathlib import Path

    import altair as alt
    import anywidget
    import geopandas as gpd
    import ifcopenshell
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
    from wigglystuff import EnvConfig

    return (
        Collection,
        ColorProxy,
        EnvConfig,
        MemoryTransport,
        Path,
        RenderMaterial,
        RenderMaterialProxy,
        alt,
        anywidget,
        closing,
        earcut,
        gpd,
        gzip,
        ifcopenshell,
        json,
        math,
        mo,
        np,
        operations,
        pl,
        pyproj,
        sdo,
        sg,
        shapely,
        sqlite3,
        struct,
        traitlets,
        urllib,
        warnings,
    )


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
def _(mo, model, pl):
    # Which shape representations does the IFC carry per element class? Body is the 3D
    # volume; Axis (centreline), FootPrint (2D outline), Box and Surface are the simple
    # geometries an exporter may add. Mapped items (type geometry) are resolved one level.
    def _item_types(representation):
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
    return engineering_crs, theta


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
def _(np, pyproj, to_etrs89):
    # Site metres -> ECEF metres, linearised at the nulpunt (site 0, 0, 0)
    _etrs89_to_ecef = pyproj.Transformer.from_crs(4937, 4978, always_xy=True)


    def site_mm_to_ecef(xyz_mm):
        lon, lat, h = to_etrs89.transform(*np.asarray(xyz_mm, dtype=float).T)
        return np.column_stack(_etrs89_to_ecef.transform(lon, lat, h))


    _origin, _x, _y, _z = site_mm_to_ecef(
        [[0, 0, 0], [1000, 0, 0], [0, 1000, 0], [0, 0, 1000]]
    )
    site_to_ecef = np.eye(4)
    site_to_ecef[:3, :3] = np.column_stack([_x - _origin, _y - _origin, _z - _origin])
    site_to_ecef[:3, 3] = _origin
    site_to_ecef
    return site_mm_to_ecef, site_to_ecef


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
    return piles_georef, to_etrs89


@app.cell(expand_output=True)
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
def _(engineering_crs, gpd, piles_georef):
    # Pile heads with one geometry column per CRS; geom (the authored position) is active.
    # geog reuses the RDNAPTRANS result in ETRS89: EPSG's "ETRS89 to WGS 84 (1)" is a null
    # transformation, accurate to 1 m by definition. OGC:CRS84h is the 3D CRS84 (lon, lat,
    # ellipsoidal height); 2D OGC:CRS84 would pass the site z through as if it were a height.
    piles_gdf = gpd.GeoDataFrame(
        piles_georef.select(
            "global_id", "name", "pile_type", "diameter_mm", "length_mm"
        ).to_pandas(),
        geometry=gpd.points_from_xy(
            piles_georef["head_x_mm"].to_numpy(),
            piles_georef["head_y_mm"].to_numpy(),
            piles_georef["head_z_mm"].to_numpy(),
            crs=engineering_crs,
        ),
    ).rename_geometry("geom")
    piles_gdf["geom_rd_nap"] = gpd.points_from_xy(
        piles_georef["head_rd_x_m"].to_numpy(),
        piles_georef["head_rd_y_m"].to_numpy(),
        piles_georef["head_nap_m"].to_numpy(),
        crs=7415,
    )
    piles_gdf["geog"] = gpd.points_from_xy(
        piles_georef["head_lon"].to_numpy(),
        piles_georef["head_lat"].to_numpy(),
        piles_georef["head_ellh_m"].to_numpy(),
        crs="OGC:CRS84h",
    )
    piles_gdf
    return (piles_gdf,)


@app.cell
def _(piles_gdf):
    piles_gdf.set_geometry("geom").explore()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Pile positions in Speckle

    `speckle/download_models.py` stored two Speckle copies of this IFC in `v3_objects.db`:

    - **speckle.bedrock.engineer**, project *NL Eindhoven Sixty5*, model `str`: imported
      server-side with ifcopenshell by a Speckle 2.x server. Each pile is a `DataObject`
      (`applicationId` = IFC `GlobalId`, IFC properties) with a display mesh in meters.
    - **app.speckle.systems**, project *Sixty5*, model `structure`: a 2026.9 bundle, projected
      to v3 objects with `Model.to_base()`. Each pile is a bare `InstanceProxy`
      (`applicationId` = `GlobalId`, no properties left) that places a shared definition's
      mesh with a 4x4 transform.

    The head and tip below are the centers of the top and bottom of each pile's bounding
    box, compared with the positions extracted from the IFC above.
    """)
    return


@app.cell
def _(EnvConfig, Path, mo):
    def _absolute_path(value):
        if not Path(value).expanduser().is_absolute():
            raise ValueError("SPECKLE_DATA_DIR must be an absolute path")


    speckle_env = mo.ui.anywidget(EnvConfig({"SPECKLE_DATA_DIR": _absolute_path}))
    speckle_env
    return (speckle_env,)


@app.cell
def _(Path, closing, json, mo, np, piles, pl, speckle_env, sqlite3):
    mo.stop(
        not speckle_env.get("SPECKLE_DATA_DIR"),
        mo.md("Set `SPECKLE_DATA_DIR` to the folder `download_models.py` wrote to."),
    )
    SPECKLE_VERSIONS = {
        "speckle.bedrock.engineer": "b61e178775",  # NL Eindhoven Sixty5 / str
        "app.speckle.systems": "9273b71eed",  # Sixty5 / structure
    }
    speckle_db = Path(speckle_env.get("SPECKLE_DATA_DIR")).expanduser() / "v3_objects.db"


    def _content(connection, object_id):
        (text,) = connection.execute(
            "SELECT content FROM objects WHERE hash = ?", (object_id,)
        ).fetchone()
        return json.loads(text)


    def _objects(connection, closure, where, *params):
        """The objects of one version (its root's closure) that match a SQL condition."""
        return [
            json.loads(text)
            for (text,) in connection.execute(
                "SELECT content FROM objects WHERE hash IN (SELECT value FROM json_each(?)) "
                f"AND {where}",
                (closure, *params),
            )
        ]


    def _vertices_mm(connection, mesh):
        assert mesh["units"] == "m"
        # Long arrays are detached into DataChunks; follow the references
        values = []
        for item in mesh["vertices"]:
            if isinstance(item, dict):
                values += _content(connection, item["referencedId"])["data"]
            else:
                values.append(item)
        return 1000 * np.array(values).reshape(-1, 3)


    def _display_vertices_mm(connection, obj):
        return np.vstack(
            [
                _vertices_mm(connection, _content(connection, ref["referencedId"]))
                for ref in obj["displayValue"]
            ]
        )


    def _pile_vertices_mm(connection, root_id):
        """GlobalId -> the pile's mesh vertices in mm, in the IFC's own coordinates."""
        root = _content(connection, root_id)
        closure = json.dumps(list(root["__closure"]))
        piles_by_id = {
            pile["applicationId"]: _display_vertices_mm(connection, pile)
            for pile in _objects(
                connection, closure, "json_extract(content, '$.ifcType') = 'IfcPile'"
            )
        }
        if piles_by_id:
            return piles_by_id

        # Projected from a bundle: InstanceProxy -> definition -> def-geo DataObjects
        definitions = {
            definition["applicationId"]: definition["objects"]
            for definition in root["instanceDefinitionProxies"]
        }
        # A def-geo-N id is on both a DataObject wrapper and its Mesh; take the Mesh
        meshes = {
            mesh["applicationId"]: mesh
            for mesh in _objects(
                connection,
                closure,
                "json_extract(content, '$.speckle_type') = 'Objects.Geometry.Mesh' "
                "AND json_extract(content, '$.applicationId') LIKE 'def-geo-%'",
            )
        }
        proxies = _objects(
            connection,
            closure,
            "json_extract(content, '$.speckle_type') = 'Speckle.Core.Models.Instances.InstanceProxy' "
            "AND json_extract(content, '$.applicationId') IN (SELECT value FROM json_each(?))",
            json.dumps(piles["global_id"].to_list()),
        )
        vertices = {}
        for proxy in proxies:
            assert proxy["units"] == "m"
            transform = np.array(proxy["transform"]).reshape(4, 4)  # row-major
            transform[:3, 3] *= 1000  # translation m -> mm, like the vertices
            local = np.vstack(
                [
                    _vertices_mm(connection, meshes[mesh_id])
                    for mesh_id in definitions[proxy["definitionId"]]
                ]
            )
            placed = np.c_[local, np.ones(len(local))] @ transform.T
            vertices.setdefault(proxy["applicationId"], []).append(placed[:, :3])
        return {global_id: np.vstack(parts) for global_id, parts in vertices.items()}


    _rows = []
    with closing(sqlite3.connect(f"file:{speckle_db.as_posix()}?mode=ro", uri=True)) as _connection:
        for _source, _version_id in SPECKLE_VERSIONS.items():
            (_root_id,) = _connection.execute(
                "SELECT v3_root_id FROM versions WHERE version_id = ?", (_version_id,)
            ).fetchone()
            for _global_id, _xyz in _pile_vertices_mm(_connection, _root_id).items():
                _x, _y = (_xyz[:, :2].min(axis=0) + _xyz[:, :2].max(axis=0)) / 2
                _rows.append(
                    {
                        "source": _source,
                        "global_id": _global_id,
                        "speckle_head_x_mm": _x,
                        "speckle_head_y_mm": _y,
                        "speckle_head_z_mm": _xyz[:, 2].max(),
                        "speckle_tip_x_mm": _x,
                        "speckle_tip_y_mm": _y,
                        "speckle_tip_z_mm": _xyz[:, 2].min(),
                    }
                )
    speckle_piles = pl.DataFrame(_rows)
    speckle_piles
    return SPECKLE_VERSIONS, speckle_db, speckle_piles


@app.cell
def _(SPECKLE_VERSIONS, mo, piles, pl, speckle_piles):
    _columns = [f"{_end}_{_axis}_mm" for _end in ("head", "tip") for _axis in "xyz"]
    _differences = [f"d_{_column}" for _column in _columns]
    pile_comparison = pl.concat(
        [
            piles.join(
                speckle_piles.filter(pl.col("source") == _source),
                on="global_id",
                how="full",
                coalesce=True,
            ).select(
                pl.lit(_source).alias("source"),
                "global_id",
                "name",
                *(
                    (pl.col(f"speckle_{_column}") - pl.col(_column)).alias(f"d_{_column}")
                    for _column in _columns
                ),
            )
            for _source in SPECKLE_VERSIONS
        ]
    )
    # Per Speckle copy: matched piles and the largest |Speckle - IFC| in mm
    pile_summary = pile_comparison.group_by("source", maintain_order=True).agg(
        matched=pl.col("d_head_x_mm").is_not_null().sum(),
        missing=pl.col("d_head_x_mm").is_null().sum(),
        *(pl.col(_column).abs().max() for _column in _differences),
    )
    mo.vstack([pile_summary, pile_comparison])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Speckle viewer on local objects

    `SpeckleViewer` renders a version straight from `v3_objects.db`, without a server. It
    runs Speckle's own viewer (`@speckle/viewer`, the npm package behind the Speckle web
    app) in an anywidget. The objects of one version (its root first, then its
    `__closure`) go to the browser as gzipped JSON, and a `SpeckleLoader` subclass hands them
    to `ObjectLoader2Factory.createFromObjects`, the in-memory object loader. The viewer's
    own `SpeckleOfflineLoader` would be the obvious choice, but in 2.31.14 it ignores the
    objects it is given.
    """)
    return


@app.cell
def _(Path, anywidget, closing, gzip, json, sqlite3, traitlets):
    SPECKLE_VIEWER_ESM = """
    import {
      CameraController,
      DefaultViewerParams,
      Extension,
      ObjectLayers,
      SelectionExtension,
      SpeckleLoader,
      Viewer,
      ViewerEvent,
    } from "https://esm.sh/@speckle/viewer@2.31.14";
    // The viewer's own three.js module (same URL), so our objects share its classes
    import * as THREE from "https://esm.sh/three@^0.140.0?target=es2022";
    import maplibregl from "https://esm.sh/maplibre-gl@5.24.0";
    // 0.3.46 is the last 3d-tiles-renderer for the viewer's three.js 0.140; built against
    // three@0.140.2 it shares the viewer's three.js module
    import { TilesRenderer } from "https://esm.sh/3d-tiles-renderer@0.3.46?deps=three@0.140.2";
    import { GLTFLoader } from "https://esm.sh/three@0.140.2/examples/jsm/loaders/GLTFLoader?target=es2022";
    import { MeshoptDecoder } from "https://esm.sh/three@0.140.2/examples/jsm/libs/meshopt_decoder.module?target=es2022";
    // Same specifier as the viewer's own import, so esm.sh serves one module instance
    import { ObjectLoader2Factory } from "https://esm.sh/@speckle/objectloader2@^2.31.14";

    // SpeckleLoader that reads objects from memory instead of a Speckle server
    class MemoryLoader extends SpeckleLoader {
      constructor(tree, objects) {
        super(tree, `memory/${objects[0].id}`, undefined, undefined, objects);
      }
      initObjectLoader(_resource, _authToken, _enableCaching, objects) {
        return ObjectLoader2Factory.createFromObjects(objects);
      }
    }

    // Geometry and child references are left out of the selected objects sent to Python
    const NOT_SELECTED = new Set(["displayValue", "elements", "__closure"]);

    async function gunzipJson(buffer) {
      const bytes = new Uint8Array(buffer.buffer ?? buffer, buffer.byteOffset ?? 0, buffer.byteLength);
      const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
      return JSON.parse(await new Response(stream).text());
    }

    const OSM_STYLE = {
      version: 8,
      sources: {
        osm: {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          maxzoom: 19,
        },
      },
      layers: [{ id: "osm", type: "raster", source: "osm" }],
    };

    // An OpenStreetMap snapshot on a plane at the site's ground level. MapLibre renders the
    // map once, off-screen and north up, over groundMap.bounds; the plane's corners are those
    // bounds through groundMap.lnglat_to_world, an affine transform from lon/lat to world.
    async function groundMapMesh(groundMap) {
      const { bounds, width, height, lnglat_to_world: t, z, opacity } = groundMap;
      const div = document.createElement("div");
      div.style.cssText = `position: fixed; left: ${-2 * width}px; top: 0; width: ${width}px; height: ${height}px;`;
      document.body.appendChild(div);
      const map = new maplibregl.Map({
        container: div,
        style: OSM_STYLE,
        bounds,
        fitBoundsOptions: { padding: 0 },
        interactive: false,
        attributionControl: false,
        pixelRatio: 1,
        fadeDuration: 0,
        canvasContextAttributes: { preserveDrawingBuffer: true },
      });
      await new Promise((resolve) => map.once("idle", resolve));
      // Copy the map into a 2D canvas, so MapLibre and its WebGL context can go
      const image = document.createElement("canvas");
      image.width = map.getCanvas().width;
      image.height = map.getCanvas().height;
      image.getContext("2d").drawImage(map.getCanvas(), 0, 0);
      const shown = map.getBounds();
      map.remove();
      div.remove();

      const world = (lng, lat) => [t[0] * lng + t[1] * lat + t[2], t[3] * lng + t[4] * lat + t[5], z];
      const corners = [
        world(shown.getWest(), shown.getSouth()),
        world(shown.getEast(), shown.getSouth()),
        world(shown.getEast(), shown.getNorth()),
        world(shown.getWest(), shown.getNorth()),
      ];
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute(corners.flat(), 3));
      geometry.setAttribute("uv", new THREE.Float32BufferAttribute([0, 0, 1, 0, 1, 1, 0, 1], 2));
      geometry.setIndex([0, 1, 2, 0, 2, 3]);
      const texture = new THREE.CanvasTexture(image);
      texture.encoding = THREE.sRGBEncoding;
      const material = new THREE.MeshBasicMaterial({
        map: texture,
        side: THREE.DoubleSide,
        transparent: opacity < 1,
        opacity,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.layers.set(ObjectLayers.PROPS);
      return mesh;
    }

    // The camera controller fits the near and far planes to the model alone; this keeps the
    // ground map inside the far plane
    class GroundInView extends Extension {
      ground = null;

      onLateUpdate() {
        const camera = this.viewer.getRenderer().renderingCamera;
        if (!this.ground || !camera) return;
        const corners = this.ground.geometry.attributes.position;
        const corner = new THREE.Vector3();
        let farthest = 0;
        for (let i = 0; i < corners.count; i++) {
          farthest = Math.max(farthest, camera.position.distanceTo(corner.fromBufferAttribute(corners, i)));
        }
        if (camera.far < 1.05 * farthest) {
          camera.far = 1.05 * farthest;
          camera.updateProjectionMatrix();
        }
      }
    }

    // Even-odd point in polygon over all rings, so a point in a hole is outside
    function insidePolygon(x, y, rings) {
      let inside = false;
      for (const ring of rings) {
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          const [xi, yi] = ring[i];
          const [xj, yj] = ring[j];
          if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
        }
      }
      return inside;
    }

    // The factor that takes an attribute's stored values to its values: three.js 0.140 returns
    // quantized (normalized integer) attributes as stored
    function denormalizeScale(attribute) {
      if (!attribute.normalized) return 1;
      const array = attribute.array;
      if (array instanceof Int8Array) return 1 / 127;
      if (array instanceof Uint8Array) return 1 / 255;
      if (array instanceof Int16Array) return 1 / 32767;
      if (array instanceof Uint16Array) return 1 / 65535;
      return 1;
    }

    // Drops the triangles of every feature (EXT_mesh_features id) with more than half of its
    // vertices inside one of the polygons. matrix takes the mesh to the viewer's world.
    function hideFeaturesWithin(mesh, matrix, polygons) {
      const geometry = mesh.geometry;
      const featureIds = geometry.getAttribute("_feature_id_0");
      if (!featureIds || !geometry.index) return;
      const position = geometry.getAttribute("position");
      const scale = denormalizeScale(position);
      const vertex = new THREE.Vector3();
      const counts = new Map(); // feature id: [vertices inside, vertices]
      for (let i = 0; i < position.count; i++) {
        const id = featureIds.getX(i);
        if (!counts.has(id)) counts.set(id, [0, 0]);
        const count = counts.get(id);
        vertex.fromBufferAttribute(position, i).multiplyScalar(scale).applyMatrix4(matrix);
        if (polygons.some((rings) => insidePolygon(vertex.x, vertex.y, rings))) count[0]++;
        count[1]++;
      }
      const hidden = new Set();
      for (const [id, [inside, total]] of counts) if (inside > total / 2) hidden.add(id);
      if (!hidden.size) return;
      const index = geometry.index.array;
      const kept = index.filter((_, i) => !hidden.has(featureIds.getX(index[i - (i % 3)])));
      geometry.setIndex(new THREE.BufferAttribute(kept, 1));
    }

    // 3D Tiles in the viewer's world. Each entry holds a tileset (its JSON, with absolute
    // content URLs) and ecef_to_world, a column-major 4x4 from ECEF (where the tiles are) to
    // the viewer's world. Features mostly inside one of the hide_within polygons (rings of
    // [x, y] in the viewer's world) are left out, to make room for the model itself. The
    // tiles are updated for the viewer's camera every frame and request a render when a tile
    // arrives.
    class ContextTiles extends Extension {
      tilesets = [];

      setTilesets(tilesets) {
        const scene = this.viewer.getRenderer().scene;
        for (const tiles of this.tilesets) {
          scene.remove(tiles.group);
          tiles.dispose();
          URL.revokeObjectURL(tiles.rootURL);
        }
        this.tilesets = tilesets.map(({ tileset, ecef_to_world, hide_within = [] }) => {
          const tiles = new TilesRenderer(
            URL.createObjectURL(new Blob([JSON.stringify(tileset)], { type: "application/json" }))
          );
          // PDOK's tiles need EXT_meshopt_compression
          const gltfLoader = new GLTFLoader(tiles.manager);
          gltfLoader.setMeshoptDecoder(MeshoptDecoder);
          tiles.manager.addHandler(/\.(gltf|glb)$/g, gltfLoader);
          tiles.group.matrixAutoUpdate = false;
          tiles.group.matrix.fromArray(ecef_to_world);
          tiles.addEventListener("load-model", ({ scene: tileScene }) => {
            tileScene.traverse((object) => {
              object.layers.set(ObjectLayers.PROPS);
              if (object.isMesh && hide_within.length) {
                // The tile's scene is not under tiles.group yet
                object.updateWorldMatrix(true, false);
                const toWorld = tiles.group.matrix.clone().multiply(object.matrixWorld);
                hideFeaturesWithin(object, toWorld, hide_within);
              }
            });
            this.viewer.requestRender();
          });
          scene.add(tiles.group);
          return tiles;
        });
        this.viewer.requestRender();
      }

      onEarlyUpdate() {
        const renderer = this.viewer.getRenderer();
        const camera = renderer.renderingCamera;
        if (!camera) return;
        for (const tiles of this.tilesets) {
          tiles.setCamera(camera);
          tiles.setResolutionFromRenderer(camera, renderer.renderer);
          camera.updateMatrixWorld();
          tiles.group.updateMatrixWorld(true);
          tiles.update();
        }
      }
    }

    async function render({ model, el }) {
      const container = document.createElement("div");
      container.style.cssText = `position: relative; width: 100%; height: ${model.get("height")}px;`;
      el.appendChild(container);

      const viewer = new Viewer(container, { ...DefaultViewerParams, verbose: false });
      await viewer.init();
      viewer.createExtension(CameraController);
      const selection = viewer.createExtension(SelectionExtension);
      const groundInView = viewer.createExtension(GroundInView);
      const contextTiles = viewer.createExtension(ContextTiles);
      viewer.on(ViewerEvent.ObjectClicked, () => {
        // Read the extension's selection once it has handled the click (shift adds to it)
        setTimeout(() => {
          const objects = selection.getSelectedObjects();
          model.set(
            "selected",
            JSON.parse(JSON.stringify(objects, (key, value) => (NOT_SELECTED.has(key) ? undefined : value)))
          );
          model.save_changes();
        });
      });

      async function load() {
        const buffer = model.get("objects_gz");
        if (!buffer || buffer.byteLength === 0) return;
        const objects = await gunzipJson(buffer);
        await viewer.unloadAll();
        await viewer.loadObject(new MemoryLoader(viewer.getWorldTree(), objects), true);
      }
      model.on("change:objects_gz", load);
      await load();

      let ground = null;
      const attribution = document.createElement("div");
      attribution.style.cssText =
        "position: absolute; right: 4px; bottom: 2px; font: 11px sans-serif; color: #555; pointer-events: none;";
      container.appendChild(attribution);
      function updateAttribution() {
        const credits = [
          ...(model.get("ground_map").bounds ? ["\u00a9 OpenStreetMap contributors"] : []),
          ...model.get("tilesets").map((entry) => entry.attribution).filter(Boolean),
        ];
        attribution.textContent = credits.join(" | ");
      }
      async function placeGroundMap() {
        if (ground) {
          viewer.getRenderer().scene.remove(ground);
          ground = groundInView.ground = null;
        }
        const groundMap = model.get("ground_map");
        updateAttribution();
        if (!groundMap.bounds) return viewer.requestRender();
        ground = groundInView.ground = await groundMapMesh(groundMap);
        viewer.getRenderer().scene.add(ground);
        viewer.requestRender();
      }
      model.on("change:ground_map", placeGroundMap);
      await placeGroundMap();

      contextTiles.setTilesets(model.get("tilesets"));
      model.on("change:tilesets", () => {
        contextTiles.setTilesets(model.get("tilesets"));
        updateAttribution();
      });
      return () => viewer.dispose();
    }

    export default { render };
    """


    class SpeckleViewer(anywidget.AnyWidget):
        """Speckle's web viewer, fed with v3 objects instead of a server URL."""

        _esm = SPECKLE_VIEWER_ESM
        objects_gz = traitlets.Bytes(b"").tag(sync=True)
        height = traitlets.Int(600).tag(sync=True)
        # Raw data of the selected objects (without displayValue, elements, __closure).
        # Shift-click adds to the selection; a click on nothing clears it.
        selected = traitlets.List([]).tag(sync=True)
        # Optional OSM map under the model: bounds [west, south, east, north], width and
        # height in pixels, lnglat_to_world (an affine [a, b, c, d, e, f]: x = a lon + b lat + c,
        # y = d lon + e lat + f), z and opacity. Empty: no map.
        ground_map = traitlets.Dict({}).tag(sync=True)
        # Optional 3D Tiles: [{"tileset": tileset JSON, "ecef_to_world": column-major 4x4,
        # "attribution": credit line, "hide_within": [polygon as rings of [x, y] in world]}]
        tilesets = traitlets.List([]).tag(sync=True)


    def speckle_objects_gz(db_path, version_id):
        """One version's v3 objects from v3_objects.db as gzipped JSON, root first."""
        with closing(sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)) as connection:
            (root_id,) = connection.execute(
                "SELECT v3_root_id FROM versions WHERE version_id = ?", (version_id,)
            ).fetchone()
            (root,) = connection.execute(
                "SELECT content FROM objects WHERE hash = ?", (root_id,)
            ).fetchone()
            children = [
                content
                for (content,) in connection.execute(
                    "SELECT content FROM objects WHERE hash IN (SELECT value FROM json_each(?))",
                    (json.dumps(list(json.loads(root)["__closure"])),),
                )
            ]
        return gzip.compress(("[" + ",".join([root, *children]) + "]").encode())

    return SpeckleViewer, speckle_objects_gz


@app.cell(expand_output=True)
def _(SPECKLE_VERSIONS, SpeckleViewer, mo, speckle_db, speckle_objects_gz):
    # NL Eindhoven Sixty5 / str from speckle.bedrock.engineer: 4498 objects, ~25 MB of JSON
    sixty5_str_viewer = mo.ui.anywidget(
        SpeckleViewer(
            objects_gz=speckle_objects_gz(
                speckle_db, SPECKLE_VERSIONS["speckle.bedrock.engineer"]
            ),
            height=600,
        )
    )
    sixty5_str_viewer
    return (sixty5_str_viewer,)


@app.cell
def _(sixty5_str_viewer):
    sixty5_str_viewer.value["selected"]
    return


@app.cell
def _(Path, closing, json, np, pl, shapely, sqlite3):
    def _read_objects(connection, object_ids):
        """object id -> parsed v3 object, for the given ids."""
        return {
            object_id: json.loads(content)
            for object_id, content in connection.execute(
                "SELECT hash, content FROM objects WHERE hash IN (SELECT value FROM json_each(?))",
                (json.dumps(list(object_ids)),),
            )
        }


    def speckle_elements(db_path, version_id):
        """One row per DataObject (what the viewer selects) of a version in v3_objects.db.

        The object's own fields become columns and `properties` stays a nested Struct.
        `displayValue` holds the references to the element's meshes; `__closure` is left out.
        """
        with closing(sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)) as connection:
            (root_id,) = connection.execute(
                "SELECT v3_root_id FROM versions WHERE version_id = ?", (version_id,)
            ).fetchone()
            root = _read_objects(connection, [root_id])[root_id]
            objects = _read_objects(connection, root["__closure"])
        rows = [
            {key: value for key, value in obj.items() if key != "__closure"}
            for obj in objects.values()
            if obj["speckle_type"] == "Objects.Data.DataObject"
        ]
        # infer_schema_length=None: merge every element's property tree into one Struct schema
        return pl.DataFrame(rows, infer_schema_length=None)


    def speckle_display_geometries(db_path, display_values):
        """A MULTIPOLYGON Z per displayValue list, one polygon per mesh face, in mm.

        mm are the units of the Engineering CRS. An empty list gives None.
        """
        with closing(sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)) as connection:
            meshes = _read_objects(
                connection, {ref["referencedId"] for refs in display_values for ref in refs}
            )
            # Long arrays are detached into DataChunks
            chunks = _read_objects(
                connection,
                {
                    item["referencedId"]
                    for mesh in meshes.values()
                    for key in ("vertices", "faces")
                    for item in mesh[key]
                    if isinstance(item, dict)
                },
            )

        def resolve(items):
            values = []
            for item in items:
                if isinstance(item, dict):
                    values += chunks[item["referencedId"]]["data"]
                else:
                    values.append(item)
            return values

        def face_polygons_mm(mesh):
            assert mesh["units"] == "m"
            xyz = 1000 * np.array(resolve(mesh["vertices"])).reshape(-1, 3)
            faces = resolve(mesh["faces"])
            polygons, i = [], 0
            while i < len(faces):
                n = faces[i] + 3 if faces[i] < 3 else faces[i]  # 0 and 1: legacy triangle, quad
                polygons.append(shapely.Polygon(xyz[faces[i + 1 : i + 1 + n]]))
                i += n + 1
            return polygons

        geometries = []
        for refs in display_values:
            polygons = [
                polygon for ref in refs for polygon in face_polygons_mm(meshes[ref["referencedId"]])
            ]
            geometries.append(shapely.MultiPolygon(polygons) if polygons else None)
        return geometries

    return speckle_display_geometries, speckle_elements


@app.cell(hide_code=True)
def _(SPECKLE_VERSIONS, speckle_db, speckle_elements):
    sixty5_str_elements = speckle_elements(
        speckle_db, SPECKLE_VERSIONS["speckle.bedrock.engineer"]
    )
    sixty5_str_elements
    return (sixty5_str_elements,)


@app.cell(hide_code=True)
def _(pl, sixty5_str_elements, sixty5_str_viewer):
    # The rows of the elements selected in the viewer
    sixty5_str_elements.filter(
        pl.col("id").is_in([obj["id"] for obj in sixty5_str_viewer.value["selected"]])
    )
    return


@app.cell(hide_code=True)
def _(
    engineering_crs,
    gpd,
    sixty5_str_elements,
    speckle_db,
    speckle_display_geometries,
):
    # The elements' display meshes as a GeoDataFrame in the Engineering CRS; id joins it
    # back to sixty5_str_elements
    sixty5_str_elements_gdf = gpd.GeoDataFrame(
        sixty5_str_elements.select("id", "applicationId", "name", "ifcType").to_pandas(),
        geometry=speckle_display_geometries(
            speckle_db, sixty5_str_elements["displayValue"].to_list()
        ),
        crs=engineering_crs,
    )
    sixty5_str_elements_gdf
    return (sixty5_str_elements_gdf,)


@app.cell(hide_code=True)
def _(sixty5_str_elements_gdf, sixty5_str_viewer):
    # The geometry of the elements selected in the viewer
    _selected = sixty5_str_elements_gdf[
        sixty5_str_elements_gdf["id"].isin(
            [obj["id"] for obj in sixty5_str_viewer.value["selected"]]
        )
    ]
    # Tops and bottoms of a closed mesh wind in opposite directions in plan, so under
    # Leaflet's fill rules they cancel out. Make every triangle counter-clockwise first.
    _selected.set_geometry(_selected.geometry.orient_polygons()).explore(
        style_kwds={"fillRule": "nonzero"}
    )
    return


@app.cell
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
    | anything else | `POINT Z`, the center of the bounding box |

    The result is a polars DataFrame with one row per element. `profile`, `body` and `bbox`
    are Structs; `geom` (Engineering CRS, mm) and `geog` (OGC:CRS84h) are WKB, so the table
    goes to GeoParquet or DuckDB as it is. `geom_source` says how each feature was derived:
    cuts (clippings, openings) are ignored, and Breps fall back to their principal axes.

    GEOS works in 2D, so it sees a vertical wall or column as a collapsed geometry.
    `plan()` gives the 2D view: a wall's trace and a column's point.
    """)
    return


@app.cell
def _(ifcopenshell, math, np, pl, shapely):
    # One 3D simple feature per building element, with the thickness reduced the way a
    # structural analysis model does it: members become a line through the centroid of their
    # profile, slabs and footings a horizontal surface, walls a vertical surface in their
    # midplane. Any other element becomes the center of its bounding box.
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


    def ifc_body_items(product):
        """(placement matrix, geometric item, clipped) for each item of the Body representation.

        Mapped items are resolved, and boolean results (clippings, CSG) are reduced to their
        first operand: the solid before anything was cut away.
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


    def _trim_angle(trim, matrix, scale):
        """A trimming point's angle on the circle, in radians: its parameter value, else its position."""
        for value in trim:
            if value.is_a("IfcParameterValue"):
                return value.wrappedValue * scale
        x, y = np.linalg.solve(matrix[:2, :2], np.subtract(trim[0].Coordinates[:2], matrix[:2, 3]))
        return math.atan2(y, x)


    def _arc_points(circle, start, end):
        angles = np.linspace(start, end, max(2, math.ceil(abs(end - start) / math.radians(11.25)) + 1))
        matrix = ifcopenshell.util.placement.get_axis2placement(circle.Position)
        local = circle.Radius * np.c_[np.cos(angles), np.sin(angles)]
        return (local @ matrix[:2, :2].T + matrix[:2, 3]).tolist()


    def ifc_curve_points(curve):
        """2D points along an IfcPolyline, IfcCircle, IfcTrimmedCurve on a circle, or an
        IfcCompositeCurve of those. Arcs get a point every 11.25 degrees."""
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


    def ifc_profile_outline(profile):
        """The swept area as a shapely Polygon in the extrusion's xy plane."""
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


    def ifc_brep_faces(item):
        """Outer loops of an IfcFacetedBrep or IfcFaceBasedSurfaceModel, as lists of 3D points."""
        shells = [item.Outer] if item.is_a("IfcFacetedBrep") else item.FbsmFaces
        return [
            [point.Coordinates for point in bound.Bound.Polygon]
            for shell in shells
            for face in shell.CfsFaces
            for bound in face.Bounds
            if bound.is_a("IfcFaceOuterBound") or len(face.Bounds) == 1
        ]


    def _site(matrix, xyz):
        return np.asarray(xyz, dtype=float) @ matrix[:3, :3].T + matrix[:3, 3]


    def _extrusion_feature(kind, matrix, solid, outline):
        direction = np.array(solid.ExtrudedDirection.DirectionRatios, dtype=float)
        sweep = solid.Depth * direction / np.linalg.norm(direction)

        def lift(xy, along):  # profile coordinates, a fraction along the sweep -> site
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


    def _principal_axis(points):
        """First principal axis of a point cloud. Within 5 degrees of a site axis it snaps to
        that axis: vertices bunched up at notches and chamfers tilt it slightly."""
        axis = np.linalg.svd(points - points.mean(axis=0))[2][0]
        nearest = np.argmax(np.abs(axis))
        if abs(axis[nearest]) > math.cos(math.radians(5)):
            axis = np.eye(len(axis))[nearest]
        return axis


    def _fallback_feature(kind, points, faces):
        """From the vertices of a Brep: principal axes instead of a profile."""
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


    def bim_simple_features(model, to_crs84h):
        """One row per building element of an IFC model, with its simple feature.

        geom is in the model's Engineering CRS (site coordinates, model units); geog is the
        same feature in OGC:CRS84h, each vertex through to_crs84h (a pyproj Transformer from
        the Engineering CRS to lon, lat, ellipsoidal height). Both are WKB.
        """
        rows, geoms = [], []
        for element in model.by_type("IfcBuildingElement"):
            if not element.Representation:
                continue
            kind = SIMPLE_FEATURE_KINDS.get(element.is_a(), "point")
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
            if kind == "point":
                geom, geom_source = shapely.Point((points.min(axis=0) + points.max(axis=0)) / 2), "bounding box center"
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
def _(shapely):
    def plan(geoms):
        """2D view of 3D simple features: vertical surfaces become their trace, vertical lines a point.

        The tolerances are in the units of the CRS: mm here.
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


@app.cell(expand_output=True)
def _(bim_simple_features, mo, model, to_etrs89):
    sixty5_str_features = bim_simple_features(model, to_etrs89)
    mo.vstack(
        [
            sixty5_str_features.group_by("ifc_class", "kind", "geom_source")
            .len("elements")
            .sort("ifc_class", "geom_source"),
            sixty5_str_features,
        ]
    )
    return (sixty5_str_features,)


@app.cell
def _(
    engineering_crs,
    gpd,
    pl,
    plan,
    shapely,
    sixty5_str_features,
    sixty5_str_viewer,
):
    # The simple features in plan, in the 2D site grid. With elements selected in the
    # Speckle viewer above, only those (its applicationId is the IFC GlobalId).
    _selected_ids = [obj["applicationId"] for obj in sixty5_str_viewer.value["selected"]]
    _features = (
        sixty5_str_features.filter(pl.col("global_id").is_in(_selected_ids))
        if _selected_ids
        else sixty5_str_features
    )
    gpd.GeoDataFrame(
        _features.select("global_id", "ifc_class", "name", "kind", "geom_source").to_pandas(),
        geometry=plan(shapely.from_wkb(_features["geom"].to_numpy())),
        crs=engineering_crs.sub_crs_list[0],
    ).explore(column="ifc_class")
    return


@app.cell
def _(pl, shapely, sixty5_str_elements_gdf, sixty5_str_features):
    # Check against the Speckle meshes of the same elements (applicationId = GlobalId), all in
    # site mm. bbox_diff: the IFC solids' bounding box against the mesh's. Cuts make the mesh
    # smaller than the uncut solids. outside: how far the simple feature sticks out of the mesh's
    # bounding box.
    def _bbox_3d(geoms, ids):
        xyz, index = shapely.get_coordinates(geoms, include_z=True, return_index=True)
        return (
            pl.DataFrame({"i": index, "x": xyz[:, 0], "y": xyz[:, 1], "z": xyz[:, 2]})
            .group_by("i")
            .agg(
                [getattr(pl.col(axis), stat)().alias(f"{axis}{stat}") for stat in ("min", "max") for axis in "xyz"]
            )
            .join(pl.DataFrame({"i": range(len(ids)), "global_id": ids}, schema_overrides={"i": pl.Int64}), on="i")
            .drop("i")
        )


    _mesh = _bbox_3d(
        sixty5_str_elements_gdf.geometry.to_numpy(), sixty5_str_elements_gdf["applicationId"].to_list()
    )
    _feature = _bbox_3d(
        shapely.from_wkb(sixty5_str_features["geom"].to_numpy()), sixty5_str_features["global_id"].to_list()
    )
    _corners = ["xmin", "ymin", "zmin", "xmax", "ymax", "zmax"]
    feature_check = (
        sixty5_str_features.select("global_id", "ifc_class", "geom_source", "bbox")
        .unnest("bbox")
        .join(_mesh, on="global_id", suffix="_mesh")
        .join(_feature, on="global_id", suffix="_feature")
        .with_columns(
            bbox_diff=pl.max_horizontal([(pl.col(c) - pl.col(f"{c}_mesh")).abs() for c in _corners]),
            outside=pl.max_horizontal(
                [pl.col(f"{a}min_mesh") - pl.col(f"{a}min_feature") for a in "xyz"]
                + [pl.col(f"{a}max_feature") - pl.col(f"{a}max_mesh") for a in "xyz"]
                + [pl.lit(0.0)]
            ),
        )
    )
    feature_check.group_by("ifc_class", "geom_source").agg(
        pl.len().alias("elements"),
        pl.col("bbox_diff").median().round(1).alias("bbox_diff_median_mm"),
        pl.col("bbox_diff").max().round(1).alias("bbox_diff_max_mm"),
        pl.col("outside").max().round(1).alias("outside_max_mm"),
    ).sort("ifc_class", "geom_source")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Simple features in the Speckle viewer

    The simple features go back into the same Speckle viewer, without a server: each row
    becomes a Speckle `DataObject` (applicationId = GlobalId, the other columns as
    properties), serialized in memory to the v3 objects the viewer loads. Points, lines and
    polylines are drawn as they are. A polygon has to be cut into triangles before WebGL can
    fill it, so slabs, footings and walls get a display mesh, triangulated with earcut on the
    polygon's own vertices. That mesh only exists in the Speckle objects, not in the table.
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
    Collection,
    ColorProxy,
    MemoryTransport,
    RenderMaterial,
    RenderMaterialProxy,
    earcut,
    gzip,
    np,
    operations,
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
    def _speckle_color(rgb):
        """RGB in 0..1 -> Speckle's signed 32-bit ARGB int."""
        red, green, blue = (round(255 * channel) for channel in rgb)
        return ((0xFF << 24) | (red << 16) | (green << 8) | blue) - (1 << 32)


    def _polygon_mesh(polygon, units):
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


    def speckle_display_value(geom, units):
        """The Speckle geometry the viewer draws for a 3D simple feature."""
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


    def simple_features_to_speckle(features, name, units, colors, default_color=(0.6, 0.6, 0.6)):
        """A Speckle Collection of the simple features, one sub-collection per IFC class.

        Colors per class go into color proxies (points, lines) and render material proxies
        (meshes), keyed on the DataObjects' applicationIds.
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


    def speckle_base_objects_gz(base):
        """A Speckle Base serialized to v3 objects (ids, __closure) as gzipped JSON, root first.

        The same format speckle_objects_gz reads from v3_objects.db, without a server.
        """
        with warnings.catch_warnings():  # the v3 send pipeline is deprecated since 2026.9
            warnings.simplefilter("ignore", DeprecationWarning)
            transport = MemoryTransport()
            root_id = operations.send(base, transports=[transport], use_default_cache=False)
        children = [content for object_id, content in transport.objects.items() if object_id != root_id]
        return gzip.compress(("[" + ",".join([transport.objects[root_id], *children]) + "]").encode())

    return simple_features_to_speckle, speckle_base_objects_gz


@app.cell
def _(math, mo, np, shapely, sixty5_str_features, to_etrs89):
    # An OpenStreetMap snapshot under the model in the Speckle viewer: lon/lat bounds around
    # the model with a margin, and one affine transform from lon/lat to the viewer's world
    # (site coordinates in m; the viewer converts the mm). Over a few hundred meters one
    # affine is enough; the residual against the exact transformation says how good.
    _site_xy = shapely.get_coordinates(shapely.from_wkb(sixty5_str_features["geom"].to_numpy()))
    _margin = 150_000  # mm
    _x = [_site_xy[:, 0].min() - _margin, _site_xy[:, 0].max() + _margin]
    _y = [_site_xy[:, 1].min() - _margin, _site_xy[:, 1].max() + _margin]
    _lon, _lat, _ = to_etrs89.transform(
        [_x[0], _x[1], _x[1], _x[0]], [_y[0], _y[0], _y[1], _y[1]], [0, 0, 0, 0]
    )
    _west, _east, _south, _north = min(_lon), max(_lon), min(_lat), max(_lat)

    _lon_grid, _lat_grid = (
        _grid.ravel() for _grid in np.meshgrid(np.linspace(_west, _east, 21), np.linspace(_south, _north, 21))
    )
    _ellh = to_etrs89.transform(0, 0, 0)[2]
    _site_x, _site_y, _ = to_etrs89.transform(
        _lon_grid, _lat_grid, np.full(_lon_grid.size, _ellh), direction="INVERSE"
    )
    _design = np.c_[_lon_grid, _lat_grid, np.ones(_lon_grid.size)]
    _affine_x = np.linalg.lstsq(_design, np.asarray(_site_x) / 1000, rcond=None)[0]
    _affine_y = np.linalg.lstsq(_design, np.asarray(_site_y) / 1000, rcond=None)[0]
    _residual_mm = 1000 * np.hypot(_design @ _affine_x - np.asarray(_site_x) / 1000, _design @ _affine_y - np.asarray(_site_y) / 1000)

    # Pixels in proportion to the bounds in Web Mercator, so MapLibre fills them exactly
    _mercator_y = [math.log(math.tan(math.pi / 4 + math.radians(_phi) / 2)) for _phi in (_south, _north)]
    _width = 2048
    sixty5_ground_map = {
        "bounds": [_west, _south, _east, _north],
        "width": _width,
        "height": round(_width * (_mercator_y[1] - _mercator_y[0]) / math.radians(_east - _west)),
        "lnglat_to_world": [*_affine_x, *_affine_y],
        "z": 0.0,  # site z = 0: the AHN ground level at the nulpunt
        "opacity": 0.85,
    }
    mo.md(
        f"Ground map: {(_x[1] - _x[0]) / 1000:.0f} x {(_y[1] - _y[0]) / 1000:.0f} m of site, "
        f"{sixty5_ground_map['width']} x {sixty5_ground_map['height']} px. One affine transform from "
        f"lon/lat to site is off by at most **{_residual_mm.max():.1f} mm** over the map."
    )
    return (sixty5_ground_map,)


@app.cell
def _(
    json,
    math,
    mo,
    np,
    shapely,
    site_to_ecef,
    sixty5_ground_map,
    sixty5_str_features,
    to_etrs89,
    urllib,
):
    def site_3d_tiles(tileset_url, bounds):
        """A small tileset with only the finest tiles of tileset_url that overlap bounds.

        bounds is [west, south, east, north] in degrees. The tree is walked only along tiles
        whose region overlaps the bounds, fetching just the external tilesets on that path.
        The result is one level: an empty root over the content tiles, each with its
        accumulated transform and an absolute content URL. 3d-tiles-renderer 0.3.46 marks
        every child of a tile without content as used, in view or not, so on the full PDOK
        tree it would fetch the external tilesets of half the country.
        """
        west, south, east, north = (math.radians(value) for value in bounds)

        def overlaps(region):
            return region[0] <= east and region[2] >= west and region[1] <= north and region[3] >= south

        def fetch(url):
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.load(response)

        leaves = []

        def walk(tile, base_url, transform):
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


    def bag_panden_under(footprint, to_crs84h):
        """The BAG panden with more than half of their area inside footprint.

        footprint is a 2D (multi)polygon in site coordinates and to_crs84h takes site
        coordinates to lon, lat, h. Returns {identificatie: polygon in site coordinates},
        from PDOK's BAG OGC API.
        """
        _, _, ground_h = to_crs84h.transform(0, 0, 0)

        def to_site(lonlat):
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


    # PDOK's 3D Basisvoorziening buildings (LoD 2.2) under the ground map. The tiles are in
    # ECEF; the inverse of site_to_ecef brings them into the viewer's world (site m).
    PDOK_3D_BUILDINGS = (
        "https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/gebouwen/3dtiles?f=json"
    )
    _tileset = site_3d_tiles(PDOK_3D_BUILDINGS, sixty5_ground_map["bounds"])

    # Sixty5 itself is in the 3D BAG too. Its BAG pand, found under the footprint of the slabs
    # and footings, hides it there; 0.5 m extra catches the vertices on its outline.
    _surfaces = sixty5_str_features["kind"].is_in(["midplane", "bottom"]).to_numpy()
    _footprint = shapely.union_all(
        shapely.force_2d(shapely.from_wkb(sixty5_str_features["geom"].to_numpy()[_surfaces]))
    )
    _hidden = bag_panden_under(_footprint, to_etrs89)
    _hide_within = [
        [(np.asarray(_ring.coords) / 1000).tolist() for _ring in [_polygon.exterior, *_polygon.interiors]]
        for _polygon in (_pand.buffer(500) for _pand in _hidden.values())
    ]
    sixty5_tilesets = [
        {
            "tileset": _tileset,
            "ecef_to_world": np.linalg.inv(site_to_ecef).flatten(order="F").tolist(),
            "attribution": "3D Basisvoorziening \u00a9 Kadaster (CC BY 4.0)",
            "hide_within": _hide_within,
        }
    ]
    mo.md(
        f"3D Basisvoorziening under the ground map: {len(_tileset['root']['children'])} content tiles: "
        + ", ".join(f"`{child['content']['uri'].split('gebouwen/')[-1]}`" for child in _tileset["root"]["children"])
        + ". Hidden, as the BIM model takes its place: BAG pand "
        + ", ".join(f"`{_identificatie}`" for _identificatie in _hidden)
    )
    return (sixty5_tilesets,)


@app.cell
def _(
    IFC_TYPE_COLORS,
    SpeckleViewer,
    mo,
    simple_features_to_speckle,
    sixty5_ground_map,
    sixty5_str_features,
    sixty5_tilesets,
    speckle_base_objects_gz,
):
    sixty5_str_features_viewer = mo.ui.anywidget(
        SpeckleViewer(
            objects_gz=speckle_base_objects_gz(
                simple_features_to_speckle(
                    sixty5_str_features, "Sixty5 structure: simple features", "mm", IFC_TYPE_COLORS
                )
            ),
            height=550,
            ground_map=sixty5_ground_map,
            tilesets=sixty5_tilesets,
        )
    )
    sixty5_str_features_viewer
    return (sixty5_str_features_viewer,)


@app.cell
def _(pl, sixty5_str_features, sixty5_str_features_viewer):
    # The rows of the simple features selected in the viewer above
    sixty5_str_features.filter(
        pl.col("global_id").is_in(
            [obj["applicationId"] for obj in sixty5_str_features_viewer.value["selected"]]
        )
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The model in CesiumJS

    CesiumJS works in ECEF (EPSG:4978). The meshes stay in local site metres, as in
    `v3_objects.db`, and a single 4x4 model matrix places them on the globe. That matrix is
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
def _(
    math,
    mo,
    np,
    pl,
    shapely,
    site_mm_to_ecef,
    site_to_ecef,
    sixty5_str_elements_gdf,
    theta,
    to_etrs89,
):
    # Is the nulpunt's position enough to place the model? Compare four placements with the
    # exact chain at the corners of the model's bounding box (piles included).
    _lon, _lat, _h = to_etrs89.transform(0, 0, 0)
    _lam, _phi = math.radians(_lon), math.radians(_lat)
    # East, north, up at the nulpunt: Cesium's Transforms.eastNorthUpToFixedFrame
    _enu = np.column_stack(
        [
            [-math.sin(_lam), math.cos(_lam), 0],
            [-math.sin(_phi) * math.cos(_lam), -math.sin(_phi) * math.sin(_lam), math.cos(_phi)],
            [math.cos(_phi) * math.cos(_lam), math.cos(_phi) * math.sin(_lam), math.sin(_phi)],
        ]
    )
    _axes_enu = _enu.T @ site_to_ecef[:3, :3]  # site x, y, z axes in east, north, up
    _angle = math.atan2(_axes_enu[1, 0], _axes_enu[0, 0])
    _scale = float(np.linalg.norm(_axes_enu[:2, 0]))
    _rotation = np.array(
        [
            [math.cos(_angle), -math.sin(_angle), 0],
            [math.sin(_angle), math.cos(_angle), 0],
            [0, 0, 1],
        ]
    )

    _coords = shapely.get_coordinates(
        shapely.get_parts(sixty5_str_elements_gdf.geometry.dropna().to_numpy()), include_z=True
    )
    _corners_mm = np.array(
        [
            [_x, _y, _z]
            for _x in (_coords[:, 0].min(), _coords[:, 0].max())
            for _y in (_coords[:, 1].min(), _coords[:, 1].max())
            for _z in (_coords[:, 2].min(), _coords[:, 2].max())
        ]
    )
    _exact = site_mm_to_ecef(_corners_mm)
    _local_m = np.c_[_corners_mm / 1000, np.ones(len(_corners_mm))]
    _origin = site_to_ecef[:3, 3]
    _placements = {
        "nulpunt only, site x = east": _enu,
        f"nulpunt + rotation ({math.degrees(_angle):.3f} deg)": _enu @ _rotation,
        f"nulpunt + rotation + scale ({_scale:.7f})": _enu @ (_rotation * [_scale, _scale, 1]),
        "site_to_ecef (full 4x4)": site_to_ecef[:3, :3],
    }
    placement_errors = pl.DataFrame(
        [
            {
                "placement": _name,
                "max_error_mm": float(
                    np.linalg.norm(_origin + _local_m[:, :3] @ _axes.T - _exact, axis=1).max() * 1000
                ),
            }
            for _name, _axes in _placements.items()
        ]
    )
    mo.vstack(
        [
            mo.md(
                f"The nulpunt is at lon {_lon:.8f}, lat {_lat:.8f}, h {_h:.3f} m (ellipsoidal). "
                f"Site x points {math.degrees(_angle):.3f} deg from east: the map conversion's "
                f"{math.degrees(theta):.3f} deg plus the meridian convergence of "
                f"{math.degrees(_angle - theta):.3f} deg between RD grid north and true north. "
                f"The model spans {np.ptp(_coords, axis=0).round(-2) / 1000} m."
            ),
            placement_errors,
        ]
    )
    return


@app.cell
def _(json, np, struct):
    def triangles_glb(groups):
        """Binary glTF (z up, metres) with one flat-shaded primitive per group.

        `groups` maps a name to (triangles, rgb), with triangles an (n, 3, 3) array of
        corner coordinates.
        """
        buffer, buffer_views, accessors, primitives, materials = bytearray(), [], [], [], []

        def add_vec3(array):
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

    return (triangles_glb,)


@app.cell
def _(IFC_TYPE_COLORS, mo, shapely, sixty5_str_elements_gdf, triangles_glb):
    def _triangles_m(geometries):
        """MULTIPOLYGON Z triangles in mm -> (n, 3, 3) corners in metres."""
        coords = shapely.get_coordinates(
            shapely.get_parts(geometries.to_numpy()), include_z=True
        ).reshape(-1, 4, 3)  # closed rings: 3 corners plus the repeated first one
        return coords[:, :3] / 1000


    sixty5_str_glb = triangles_glb(
        {
            _ifc_type: (
                _triangles_m(_group.geometry.dropna()),
                IFC_TYPE_COLORS.get(_ifc_type, (0.7, 0.7, 0.7)),
            )
            for _ifc_type, _group in sixty5_str_elements_gdf.groupby("ifcType")
            if _group.geometry.notna().any()
        }
    )
    mo.md(f"`sixty5_str_glb`: {len(sixty5_str_glb) / 1e6:.1f} MB of binary glTF")
    return (sixty5_str_glb,)


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


@app.cell(expand_output=True)
def _(CesiumModelViewer, mo, site_to_ecef, sixty5_str_glb):
    sixty5_str_cesium = mo.ui.anywidget(
        CesiumModelViewer(
            glb=sixty5_str_glb,
            model_matrix=site_to_ecef.flatten(order="F").tolist(),  # Cesium is column-major
            height=600,
        )
    )
    sixty5_str_cesium
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
