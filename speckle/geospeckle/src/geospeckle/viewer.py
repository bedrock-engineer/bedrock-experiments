"""Speckle's web viewer in a notebook, with the model's surroundings.

`GeoSpeckleViewer` runs Speckle's own viewer (`@speckle/viewer`, the npm package behind the
Speckle web app) in an anywidget, without a Speckle server. The v3 objects of one or more
models (each its root first, then its `__closure`) go to the browser as gzipped JSON, and a
`SpeckleLoader` subclass hands them to `ObjectLoader2Factory.createFromObjects`, the
in-memory object loader. The viewer's own `SpeckleOfflineLoader` would be the obvious
choice, but in 2.31.14 it ignores the objects it is given.

Around the model the viewer can show an OpenStreetMap ground map, 3D Tiles such as PDOK's
3D BAG, and labeled axes at named points.
"""

import gzip
from pathlib import Path

import anywidget
import traitlets


class GeoSpeckleViewer(anywidget.AnyWidget):
    """Speckle's web viewer, fed with v3 objects instead of a server URL.

    Clicking an element selects it; shift-click adds to the selection and a click on nothing
    clears it. A click on an instance selects its InstanceProxy, whose applicationId is the
    element's.
    """

    _esm = Path(__file__).with_name("viewer.js")
    # Gzipped JSON of one or more models, each an array of v3 objects, root first; see models_gz
    objects_gz = traitlets.Bytes(b"").tag(sync=True)
    # Height in pixels; None: the height follows the notebook's width by aspect_ratio
    height = traitlets.Int(None, allow_none=True).tag(sync=True)
    # Width over height, when height is None
    aspect_ratio = traitlets.Float(16 / 9).tag(sync=True)
    # Raw data of the selected objects (without displayValue, elements, __closure)
    selected = traitlets.List([]).tag(sync=True)
    # Optional OSM map under the model: bounds [west, south, east, north], width and height
    # in pixels, lnglat_to_world (an affine [a, b, c, d, e, f]: x = a lon + b lat + c,
    # y = d lon + e lat + f), z and opacity. Empty: no map.
    ground_map = traitlets.Dict({}).tag(sync=True)
    # Optional 3D Tiles: [{"tileset": tileset JSON, "ecef_to_world": column-major 4x4,
    # "attribution": credit line, "hide_within": [polygon as rings of [x, y] in world]}]
    tilesets = traitlets.List([]).tag(sync=True)
    # Optional axes with a label: [{"name": label, "position": [x, y, z] in world, "size": m}]
    markers = traitlets.List([]).tag(sync=True)


def models_gz(*models: str) -> bytes:
    """Packs models for GeoSpeckleViewer.objects_gz.

    Args:
        *models: Each model's v3 objects as JSON array text, root first.

    Returns:
        Gzipped JSON: an array of the models.
    """
    return gzip.compress(("[" + ",".join(models) + "]").encode())
