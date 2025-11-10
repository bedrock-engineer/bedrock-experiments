import json

import ghpythonlib.treehelpers as th
import Rhino.Geometry as rg


def geojson_to_rhino_geometry(geom):
    """Convert a single GeoJSON geometry to Rhino geometry."""
    geom_type = geom["type"]
    coords = geom["coordinates"]

    if geom_type == "Point":
        return rg.Point3d(coords[0], coords[1], coords[2] if len(coords) > 2 else 0)

    elif geom_type == "LineString":
        points = [rg.Point3d(c[0], c[1], c[2] if len(c) > 2 else 0) for c in coords]
        return rg.PolylineCurve(points)

    elif geom_type == "Polygon":
        print(coords)
        # Exterior ring
        exterior = [
            rg.Point3d(c[0], c[1], c[2] if len(c) > 2 else 0) for c in coords[0]
        ]
        exterior_curve = rg.PolylineCurve(exterior)

        # Create planar surface
        breps = rg.Brep.CreatePlanarBreps([exterior_curve], 0.01)
        if not breps:
            return None
        brep = breps[0]

        # Handle holes (interior rings)
        if len(coords) > 1:
            for hole in coords[1:]:
                hole_pts = [
                    rg.Point3d(c[0], c[1], c[2] if len(c) > 2 else 0) for c in hole
                ]
                hole_curve = rg.PolylineCurve(hole_pts)
                hole_brep = rg.Brep.CreatePlanarBreps([hole_curve], 0.01)
                if hole_brep:
                    diff = rg.Brep.CreateBooleanDifference([brep], hole_brep, 0.01)
                    if diff:
                        brep = diff[0]

        return brep

    else:
        return None


with open(json_path, "r") as f:
    geojson = json.load(f)

features = geojson["features"]

geometries = []
property_keys = []
property_values = []
for feat in features:
    geom = feat["geometry"]
    geometries.append([geojson_to_rhino_geometry(geom)])

    properties = feat["properties"]
    property_keys.append(list(properties.keys()))
    property_values.append(list(properties.values()))

geometries = th.list_to_tree(geometries)
property_keys = th.list_to_tree(property_keys)
property_values = th.list_to_tree(property_values)
