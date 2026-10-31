# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anywidget==0.11.0",
#     "bimpolars[ifc]",
#     "folium>=0.12",
#     "geopandas==1.2.0",
#     "ifcopenshell==0.9.0.post1",
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
# bimpolars = { git = "https://github.com/bedrock-engineer/bimpolars" }
# specklewidgets = { git = "https://github.com/bedrock-engineer/specklestuff" }
# ///

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import math
    import warnings

    import anywidget
    import bimpolars as bpl
    import geopandas as gpd
    import ifcopenshell as ifc
    import mapbox_earcut as earcut
    import marimo as mo
    import numpy as np
    import polars as pl
    import pyproj
    import shapely
    import traitlets
    from specklepy.api import operations
    from specklepy.objects import geometry as sgeo
    from specklepy.objects.proxies import ColorProxy
    from specklepy.transports.memory import MemoryTransport
    from specklewidgets import GeoSpeckleViewer
    from specklewidgets.bim import bim_collection
    from specklewidgets.geo import bag_panden_under, osm_ground_map, pdok_3d_buildings

    return (
        ColorProxy,
        GeoSpeckleViewer,
        MemoryTransport,
        anywidget,
        bag_panden_under,
        bim_collection,
        bpl,
        earcut,
        gpd,
        ifc,
        json,
        math,
        mo,
        np,
        operations,
        osm_ground_map,
        pdok_3d_buildings,
        pl,
        pyproj,
        sgeo,
        shapely,
        traitlets,
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

    1. defines the model's georeferenced BIM CRS: a compound of derived CRSs on RD New + NAP (EPSG:7415) that keeps the model's millimeters
    2. turns every building element into a 3D simple feature, with `geom` in the georeferenced BIM CRS and `geog` in OGC:CRS84h
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
def _(bpl):
    # The bimpolars test data: fetch downloads the IFC from the bimpolars bucket on first use,
    # or finds it in BIMPOLARS_DATA_DIR
    ifc_path = bpl.data.fetch("sixty5_O-S1-CON-structural-engineering.ifc")
    return (ifc_path,)


@app.cell
def _(ifc, ifc_path):
    model = ifc.open(ifc_path)
    _site = model.by_type("IfcSite")[0]
    {
        "schema": model.schema,
        "IfcSite.RefLatitude": _site.RefLatitude,
        "IfcSite.RefLongitude": _site.RefLongitude,
        "IfcPile count": len(model.by_type("IfcPile")),
    }
    return (model,)


@app.cell
def _(bpl, model):
    # Every product of the IFC as one row: its mesh tessellated by ifcopenshell in the model's
    # millimeters, its property sets as Structs, its storey as container
    bim = bpl.read_ifc(model)
    bim
    return (bim,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The georeferenced BIM CRS

    The georeferencing comes from the IFC-GeoReferencer export of the *architectural* model of the same project (`O-S1-BWK-BIM architectural - BIM bouwkundig.ifcgref.json` in the ifc-georeferencer-workshop repo). This assumes that the structural model shares the architectural model's project origin.

    The georeferenced BIM CRS is a compound of two derived CRSs:

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
    bim,
    bpl,
    math,
    pyproj,
):
    # RD New + NAP to ETRS89 follows RDNAPTRANS2018 only with the NSGI grids, which PROJ fetches. On here,
    # in the cell every geo cell depends on, so no transformation runs before it with NAP as ellipsoidal height
    pyproj.network.set_network_enabled(True)
    # The rotation from grid north, as IfcMapConversion gives it: the direction of the site x-axis
    # in the grid
    ROTATION = math.degrees(math.atan2(X_AXIS_ORDINATE, X_AXIS_ABSCISSA))
    bim_crs = bpl.georeferenced_bim_crs(
        "EPSG:7415", EASTINGS, NORTHINGS, ORTHOGONAL_HEIGHT, ROTATION, unit=bim, name="Sixty5"
    )
    {"model unit": bim.crs.axis_info[0].unit_name, "rotation from grid north [deg]": ROTATION, "CRS type": bim_crs.type_name}
    return (bim_crs,)


@app.cell
def _(mo, bim_crs):
    mo.accordion(
        {
            "WKT2": mo.md(f"```\n{bim_crs.to_wkt(pretty=True)}\n```"),
            "PROJJSON": mo.md(f"```json\n{bim_crs.to_json(pretty=True)}\n```"),
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
def _(bpl, math, mo, pyproj, bim_crs):
    _to_etrs89 = pyproj.Transformer.from_crs(bim_crs, 4937, always_xy=True, allow_ballpark=False)
    assert math.isfinite(_to_etrs89.transform(0, 0, 0)[0]), (
        "RDNAPTRANS grids unavailable: install them or allow PROJ network access"
    )
    # One 4x4 from site meters to ECEF meters (WGS 84 geocentric, which EPSG takes as equal to
    # ETRS89) for Cesium, linearized at the nulpunt (site 0, 0, 0)
    site_to_ecef = bpl.linearized_site_to_ecef(bim_crs)
    mo.vstack([mo.md(f"`to_etrs89`: {_to_etrs89.description}"), site_to_ecef])
    return (site_to_ecef,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## BIM to simple features

    bimpolars' `simple_features` gives every element two simple features next to its mesh:

    - `footprint`: the outline of its mesh in plan, at the level of its storey
    - `lightbim`: the structural-analysis reduction of [LightBIM](https://github.com/bedrock-engineer/bimpolars): the axis of a column, beam or pile as a `LINESTRING Z`, the midplane of a slab or wall and the bearing plane of a footing as a `POLYGON Z`

    `lightbim_kind` says what each member is, and `lightbim_qa` how its reduction was found: from the extrusion in the IFC (`native_geom`, with cuts ignored) or from the mesh, and how far the mesh lies from it. `with_geog` adds `geog`, the footprint in OGC:CRS84h. The geometry columns are WKB, so the table goes to GeoParquet or DuckDB as it is.
    """)
    return


@app.cell(hide_code=True)
def _(ifc, mo, model, pl):
    # Which shape representations does the IFC carry per element class? Body is the 3D
    # volume; Axis (centreline), FootPrint (2D outline), Box and Surface are the simple
    # geometries an exporter may add. Mapped items (type geometry) are resolved one level.
    def _item_types(representation: ifc.entity_instance) -> str:
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
def _(bim, bpl, pl, bim_crs):
    sixty5 = bpl.with_geog(bpl.simple_features(bpl.set_crs(bim, bim_crs), lightbim=True))
    sixty5.frame.filter(pl.col("lightbim").is_not_null()).group_by(
        "class",
        member=pl.col("lightbim_kind").struct.field("member"),
        source=pl.col("lightbim_qa").struct.field("source"),
    ).len("elements").sort("class", "source")
    return (sixty5,)


@app.cell
def _(gpd, pl, shapely, sixty5):
    # Every element's footprint as bimpolars' geog: in longitude, latitude and ellipsoidal height
    # (OGC:CRS84h), what web maps and GeoJSON take
    _rows = sixty5.frame.filter(
        pl.col("geog").is_not_null(), pl.col("class") != "IfcOpeningElement"
    )
    features_plan = gpd.GeoDataFrame(
        _rows.select("id", "class", "name").to_pandas(),
        geometry=shapely.from_wkb(_rows["geog"].to_numpy()),
        crs="OGC:CRS84h",
    )
    features_plan.explore()
    return (features_plan,)


@app.cell(hide_code=True)
def _(pl, sixty5):
    # Per element: its class, name, property sets, storey and LightBIM kind, without the geometry
    # and its CRS
    element_data = sixty5.frame.filter(pl.col("mesh").is_not_null() & (pl.col("class") != "IfcOpeningElement")).drop(
        "mesh", "bbox", "native_geom", "footprint", "lightbim", "geog", "bim_crs"
    )
    element_data
    return (element_data,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## GeoSpeckle Viewer

    Speckle's viewer shows the model on an OpenStreetMap ground map, among the buildings of PDOK's 3D Basisvoorziening (the 3D BAG). Sixty5 itself is in the 3D BAG too: its BAG pand, found under the model's slabs and footings, is left out to make room for the model. specklewidgets builds both.

    The switch shows either the IFC's own geometry, colored by its surface styles, or the LightBIM features, colored by IFC class. specklewidgets draws meshes only, so `lightbim_objects` takes the elements as specklewidgets builds them and swaps their display geometry for the LightBIM lines and polygons. A polygon has to be cut into triangles before WebGL can fill it, so slabs, footings and walls get a display mesh there, triangulated with earcut on the polygon's own vertices.

    Click an element to select it; shift-click adds to the selection. The map and the tables below follow the selection.
    """)
    return


@app.cell
def _(bag_panden_under, mo, osm_ground_map, pdok_3d_buildings, pl, sixty5):
    # The surroundings in the viewer's world (site meters): an OpenStreetMap snapshot 150 m
    # around the model, and the 3D BAG over the same area without Sixty5's own building, the BAG
    # pand under the slabs and footings
    ground_map = osm_ground_map(sixty5)
    _panden = bag_panden_under(
        sixty5.with_frame(
            sixty5.frame.filter(
                pl.col("class").is_in(["IfcSlab", "IfcFooting"])
            )
        )
    )
    context_tilesets = [
        pdok_3d_buildings(
            sixty5, ground_map["bounds"], hide_within=_panden.values()
        )
    ]
    mo.md(
        f"Ground map: {ground_map['width']} x {ground_map['height']} px. "
        f"3D BAG: {len(context_tilesets[0]['tileset']['root']['children'])} tiles, without BAG pand "
        + ", ".join(f"`{_identificatie}`" for _identificatie in _panden)
        + "."
    )
    return context_tilesets, ground_map


@app.cell
def _(lightbim_objects, sixty5):
    # The two geometries the viewer can show: the BimDataFrame itself, and the LightBIM features
    # as v3 objects
    viewer_models = {"IFC geometry": sixty5, "LightBIM": lightbim_objects(sixty5)}
    return (viewer_models,)


@app.cell
def _(mo, viewer_models):
    geometry_choice = mo.ui.radio(list(viewer_models), value="IFC geometry", inline=True)
    geometry_choice
    return (geometry_choice,)


@app.cell(hide_code=True)
def _(
    GeoSpeckleViewer,
    context_tilesets,
    geometry_choice,
    ground_map,
    mo,
    viewer_models,
):
    geospeckle_widget = mo.ui.anywidget(
        GeoSpeckleViewer(viewer_models[geometry_choice.value], ground_map=ground_map, tilesets=context_tilesets)
    )
    geospeckle_widget
    return (geospeckle_widget,)


@app.cell(hide_code=True)
def _(features_plan, geospeckle_widget):
    # All elements in plan in gray, the selected ones on top in color and in view
    _map = features_plan.explore(
        color="#9a9a9a",
        tooltip=["class", "name"],
        style_kwds={"weight": 1, "fill": False},
        name="All elements",
    )
    selected_ids = [
        _obj["applicationId"] for _obj in geospeckle_widget.value["selected"]
    ]
    _selected = features_plan[features_plan["id"].isin(selected_ids)]
    if len(_selected):
        _selected.explore(
            m=_map,
            column="class",
            tooltip=["class", "name", "id"],
            name="Selected",
        )
        _west, _south, _east, _north = _selected.total_bounds
        _map.fit_bounds([[_south, _west], [_north, _east]], max_zoom=21)
    _map
    return (selected_ids,)


@app.cell(hide_code=True)
def _(mo, pl, selected_ids, sixty5):
    # A BimDataFrame shows its CRS name once, above a table without the bim_crs column
    selected_elements_bdf = sixty5.filter(
        pl.col("id").is_in(selected_ids)
    )
    mo.vstack(
        [
            mo.md(f"**Selected elements**: {len(selected_elements_bdf)}"),
            selected_elements_bdf,
        ]
    )
    return


@app.cell(hide_code=True)
def _(element_data, mo):
    mo.vstack([mo.md(f"**All elements**: {element_data.height}"), element_data])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## CesiumJS GeoBIM Viewer

    CesiumJS works in ECEF (EPSG:4978). The meshes stay in local site metres, as ifcopenshell
    tessellates them, and a single 4x4 model matrix places them on the globe. That matrix is
    the exact chain (georeferenced BIM CRS, RD New + NAP, RDNAPTRANS to ETRS89, ECEF) linearised at
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
def _(bpl, mo, sixty5):
    cesium_glb = bpl.element_meshes_glb(sixty5)
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
def _(
    ColorProxy,
    MemoryTransport,
    bim_collection,
    earcut,
    json,
    np,
    operations,
    pl,
    sgeo,
    shapely,
    warnings,
):
    # The LightBIM features as Speckle v3 objects, for the viewer. specklewidgets builds the
    # elements: one DataObject per row with its properties, and a color per IFC class. Their
    # display geometry becomes the LightBIM feature: points, lines and polylines as they are, and
    # a POLYGON Z as a display mesh triangulated in its own plane, since Speckle has no polygon
    # type the viewer fills. That mesh exists only here, not in the table.
    def _polygon_mesh(polygon: shapely.Polygon, units: str) -> sgeo.Mesh:
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
        return sgeo.Mesh(vertices=vertices.ravel().tolist(), faces=faces.ravel().tolist(), units=units)


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
            return [sgeo.Point(x=geom.x, y=geom.y, z=geom.z, units=units)]
        if geom.geom_type == "LineString":
            coords = np.array(geom.coords)
            if len(coords) == 2:
                start, end = (sgeo.Point(x=x, y=y, z=z, units=units) for x, y, z in coords)
                return [sgeo.Line(start=start, end=end, units=units)]
            return [sgeo.Polyline(value=coords.ravel().tolist(), units=units)]
        if geom.geom_type == "Polygon":
            return [_polygon_mesh(geom, units)]
        raise NotImplementedError(geom.geom_type)


    def lightbim_objects(bdf) -> list[dict]:
        """The LightBIM features of a model as the v3 objects of one Speckle model, root first.

        Args:
            bdf: A BimDataFrame with the lightbim column of bpl.simple_features(..., lightbim=True).

        Returns:
            The parsed objects, as models_gz takes them.
        """
        members = bdf.with_frame(bdf.frame.filter(pl.col("lightbim").is_not_null()))
        root = bim_collection(members, color="class", name=f"{bdf.crs.name} LightBIM")
        geoms = dict(zip(members.frame["id"], shapely.from_wkb(members.frame["lightbim"].to_numpy())))
        for collection in root.elements:
            for element in collection.elements:
                element.displayValue = speckle_display_value(geoms[element.applicationId], root["units"])
        # Meshes take their color from the RenderMaterialProxies, points and lines from ColorProxies
        root["colorProxies"] = [
            ColorProxy(name=proxy.value.name, value=proxy.value.diffuse, objects=proxy.objects)
            for proxy in root["renderMaterialProxies"]
        ]
        with warnings.catch_warnings():  # the v3 send pipeline is deprecated since 2026.9
            warnings.simplefilter("ignore", DeprecationWarning)
            transport = MemoryTransport()
            root_id = operations.send(root, transports=[transport], use_default_cache=False)
        return [
            json.loads(transport.objects[root_id]),
            *(json.loads(text) for object_id, text in transport.objects.items() if object_id != root_id),
        ]

    return (lightbim_objects,)


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
