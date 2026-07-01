# /// script
# dependencies = [
#     "marimo",
#     "numpy==2.5.0",
#     "plotly[express]==6.8.0",
# ]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.23.11"
app = marimo.App(width="medium")


@app.cell
def _():
    brewin_path_lon = 114.154869
    brewin_path_lat = 22.273951
    return brewin_path_lat, brewin_path_lon


@app.cell(hide_code=True)
def _(brewin_path_lat, brewin_path_lon, mo):
    maplibre_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link href="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css" rel="stylesheet" />
    <script src="https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js"></script>
    <style>html,body,#map{{margin:0;height:100%;width:100%}}</style>
    </head>
    <body>
    <div id="map"></div>
    <script>
    const map = new maplibregl.Map({{
        container: "map",
        zoom: 15,
        pitch: 70,
        maxPitch: 85,
        center: [{brewin_path_lon}, {brewin_path_lat}],
        style: "https://tiles.openfreemap.org/styles/liberty",
        maxZoom: 19
    }});

    map.addControl(new maplibregl.NavigationControl({{ visualizePitch: true }}));

    map.on("load", () => {{
        // --- 3D terrain (raster-dem) ---
        map.addSource("terrainSource", {{
            type: "raster-dem",
            url: "https://tiles.mapterhorn.com/tilejson.json"
        }});
        map.addSource("hillshadeSource", {{
            type: "raster-dem",
            url: "https://tiles.mapterhorn.com/tilejson.json"
        }});
        map.addLayer({{
            id: "hills",
            type: "hillshade",
            source: "hillshadeSource",
            layout: {{ visibility: "visible" }},
            paint: {{ "hillshade-shadow-color": "#473B24" }}
        }});
        map.setTerrain({{ source: "terrainSource", exaggeration: 1.5 }});
        map.setSky({{}});
        map.addControl(
            new maplibregl.TerrainControl({{ source: "terrainSource", exaggeration: 1.5 }})
        );

        // --- 3D buildings (fill-extrusion from the openmaptiles vector source) ---
        // insert beneath the first text label so labels stay readable
        const layers = map.getStyle().layers;
        let labelLayerId;
        for (const layer of layers) {{
            if (layer.type === "symbol" && layer.layout && layer.layout["text-field"]) {{
                labelLayerId = layer.id;
                break;
            }}
        }}
        map.addLayer({{
            id: "3d-buildings",
            source: "openmaptiles",
            "source-layer": "building",
            type: "fill-extrusion",
            minzoom: 14,
            paint: {{
                "fill-extrusion-color": "#cfd2d6",
                "fill-extrusion-height": [
                    "interpolate", ["linear"], ["zoom"],
                    14, 0,
                    15.5, ["get", "render_height"]
                ],
                "fill-extrusion-base": ["get", "render_min_height"],
                "fill-extrusion-opacity": 0.9
            }}
        }}, labelLayerId);

        new maplibregl.Marker()
            .setLngLat([{brewin_path_lon}, {brewin_path_lat}])
            .addTo(map);
    }});
    </script>
    </body>
    </html>
    """

    terrain_map = mo.iframe(maplibre_html, height="580px")
    terrain_map
    return


@app.cell(hide_code=True)
def _(brewin_path_lat, brewin_path_lon, mo):
    deckgl_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <script src="https://unpkg.com/deck.gl@9/dist.min.js"></script>
    <style>html,body{{margin:0;height:100%;width:100%}}#map{{position:relative;height:100%;width:100%;background:#0b1021}}</style>
    </head>
    <body>
    <div id="map"></div>
    <script>
    const TERRARIUM = {{ rScaler: 256, gScaler: 1, bScaler: 1 / 256, offset: -32768 }};

    // Mapterhorn DEM only exists to z12 -> cap maxZoom so deck.gl over-zooms the
    // z12 tile instead of requesting missing tiles (which caused holes + spikes).
    const terrain = new deck.TerrainLayer({{
        id: "terrain",
        minZoom: 0,
        maxZoom: 12,
        elevationDecoder: TERRARIUM,
        elevationData: "https://tiles.mapterhorn.com/{{z}}/{{x}}/{{y}}.webp",
        texture: "https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png",
        meshMaxError: 1,
        operation: "terrain+draw"
    }});

    // TerrainExtension in "offset" mode lifts each building's base onto the terrain.
    const buildings = new deck.MVTLayer({{
        id: "buildings",
        data: "https://tiles.openfreemap.org/planet/20260621_080001_pt/{{z}}/{{x}}/{{y}}.pbf",
        minZoom: 0,
        maxZoom: 14,
        loadOptions: {{ mvt: {{ layers: ["building"] }} }},
        extruded: true,
        wireframe: false,
        getElevation: f => f.properties.render_height || 3,
        getFillColor: f => (f.properties.render_height ? [205, 208, 214, 255] : [0, 0, 0, 0]),
        getLineColor: [0, 0, 0, 0],
        lineWidthMinPixels: 0,
        pointType: "circle",
        getPointRadius: 0,
        material: {{ ambient: 0.5, diffuse: 0.6, shininess: 32, specularColor: [60, 64, 70] }},
        extensions: [new deck._TerrainExtension()],
        terrainDrawMode: "offset"
    }});

    new deck.DeckGL({{
        container: "map",
        initialViewState: {{
            longitude: {brewin_path_lon},
            latitude: {brewin_path_lat},
            zoom: 15,
            pitch: 65,
            bearing: 30,
            maxPitch: 85
        }},
        controller: true,
        layers: [terrain, buildings]
    }});
    </script>
    </body>
    </html>
    """

    deckgl_map = mo.iframe(deckgl_html, height="580px")
    deckgl_map
    return


@app.cell(hide_code=True)
def _(brewin_path_lat, brewin_path_lon, mo):
    cesium_template = r"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <script>window.CESIUM_BASE_URL = "https://unpkg.com/cesium@1/Build/Cesium/";</script>
    <script src="https://unpkg.com/cesium@1/Build/Cesium/Cesium.js"></script>
    <link href="https://unpkg.com/cesium@1/Build/Cesium/Widgets/widgets.css" rel="stylesheet" />
    <script src="https://unpkg.com/osmtogeojson@3.0.0-beta.5/osmtogeojson.js"></script>
    <style>html,body,#cesium{margin:0;padding:0;height:100%;width:100%;overflow:hidden}</style>
    </head>
    <body>
    <div id="cesium"></div>
    <script>
    window.__dbg = { stage: "start" };
    const LON = __LON__, LAT = __LAT__;
    const SAMPLES = 64;
    const MAX_DEM_Z = 12;  // Mapterhorn 404s above z12
    const decodeCanvas = document.createElement("canvas");

    // Mapterhorn terrarium tiles -> Cesium custom heightmap, clamped to z12.
    async function decodeTile(x, y, level) {
      let sl = level, sx = x, sy = y, span = 1, ox = 0, oy = 0;
      if (level > MAX_DEM_Z) {
        const dz = level - MAX_DEM_Z;
        sl = MAX_DEM_Z; sx = x >> dz; sy = y >> dz;
        span = 1 << dz; ox = x - (sx << dz); oy = y - (sy << dz);
      }
      let bmp;
      try {
        const resp = await fetch("https://tiles.mapterhorn.com/" + sl + "/" + sx + "/" + sy + ".webp");
        if (!resp.ok) return undefined;
        bmp = await createImageBitmap(await resp.blob());
      } catch (e) { return undefined; }
      const c = decodeCanvas;
      c.width = bmp.width; c.height = bmp.height;
      const ctx = c.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(bmp, 0, 0);
      const img = ctx.getImageData(0, 0, bmp.width, bmp.height).data;
      const heights = new Float32Array(SAMPLES * SAMPLES);
      for (let j = 0; j < SAMPLES; j++) {
        for (let i = 0; i < SAMPLES; i++) {
          const u = (ox + i / (SAMPLES - 1)) / span;
          const v = (oy + j / (SAMPLES - 1)) / span;
          const px = Math.min(bmp.width - 1, Math.round(u * (bmp.width - 1)));
          const py = Math.min(bmp.height - 1, Math.round(v * (bmp.height - 1)));
          const o = (py * bmp.width + px) * 4;
          heights[j * SAMPLES + i] = img[o] * 256 + img[o + 1] + img[o + 2] / 256 - 32768;
        }
      }
      return heights;
    }

    const terrain = new Cesium.CustomHeightmapTerrainProvider({
      width: SAMPLES, height: SAMPLES,
      tilingScheme: new Cesium.WebMercatorTilingScheme(),
      callback: (x, y, level) => decodeTile(x, y, level)
    });

    const viewer = new Cesium.Viewer("cesium", {
      baseLayer: new Cesium.ImageryLayer(
        new Cesium.UrlTemplateImageryProvider({
          url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
          credit: "(c) OpenStreetMap contributors"
        })
      ),
      terrainProvider: terrain,
      baseLayerPicker: false, geocoder: false, timeline: false, animation: false,
      sceneModePicker: false, homeButton: false, navigationHelpButton: false,
      fullscreenButton: false, infoBox: false, selectionIndicator: false
    });
    viewer.scene.globe.depthTestAgainstTerrain = true;
    window.__dbg.stage = "viewer-created";

    // Brewin path marker
    viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(LON, LAT),
      point: { pixelSize: 12, color: Cesium.Color.RED,
               outlineColor: Cesium.Color.WHITE, outlineWidth: 2,
               heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
               disableDepthTestDistance: Number.POSITIVE_INFINITY },
      label: { text: "Brewin path", font: "14px sans-serif",
               fillColor: Cesium.Color.WHITE,
               style: Cesium.LabelStyle.FILL_AND_OUTLINE, outlineWidth: 3,
               verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
               pixelOffset: new Cesium.Cartesian2(0, -16),
               heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
               disableDepthTestDistance: Number.POSITIVE_INFINITY }
    });

    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(LON, LAT - 0.012, 1800),
      orientation: { heading: Cesium.Math.toRadians(20),
                     pitch: Cesium.Math.toRadians(-30), roll: 0 }
    });

    // OSM buildings via Overpass -> GeoJSON -> extruded, draped on terrain.
    async function loadBuildings() {
      const d = 0.008;
      const s = LAT - d, n = LAT + d, w = LON - d, e = LON + d;
      const q = "[out:json][timeout:25];(way[\"building\"](" + s + "," + w + "," + n + "," + e +
                ");relation[\"building\"](" + s + "," + w + "," + n + "," + e + "););out body;>;out skel qt;";
      let osm;
      try {
        const resp = await fetch("https://overpass-api.de/api/interpreter",
          { method: "POST", body: "data=" + encodeURIComponent(q) });
        window.__dbg.overpassStatus = resp.status;
        osm = await resp.json();
      } catch (err) { window.__dbg.overpassError = String(err); return; }

      window.__dbg.osmElements = (osm.elements || []).length;
      const gj = osmtogeojson(osm);
      const ds = await Cesium.GeoJsonDataSource.load(gj, { clampToGround: false });
      await viewer.dataSources.add(ds);

      const ents = ds.entities.values.filter(en => en.polygon);
      window.__dbg.polygons = ents.length;

      const carto = ents.map(en => {
        const pos = en.polygon.hierarchy.getValue(Cesium.JulianDate.now()).positions;
        return Cesium.Cartographic.fromCartesian(Cesium.BoundingSphere.fromPoints(pos).center);
      });
      let sampled = null;
      try { sampled = await Cesium.sampleTerrain(terrain, MAX_DEM_Z, carto.map(c => c.clone())); }
      catch (err) { window.__dbg.sampleError = String(err); }
      window.__dbg.sampled = !!sampled;

      ents.forEach((en, idx) => {
        const p = en.properties;
        const getv = k => (p && p[k] ? p[k].getValue() : undefined);
        let h = 10;
        const hgt = parseFloat(getv("height"));
        const lvls = parseFloat(getv("building:levels"));
        if (!isNaN(hgt)) h = hgt; else if (!isNaN(lvls)) h = lvls * 3.2;
        let base = 0;
        if (sampled && sampled[idx] && !isNaN(sampled[idx].height)) base = sampled[idx].height;
        en.polygon.perPositionHeight = false;
        en.polygon.height = base;
        en.polygon.extrudedHeight = base + h;
        en.polygon.material = Cesium.Color.fromBytes(205, 208, 214);
        en.polygon.outline = false;
      });
      window.__dbg.stage = "buildings-done";
    }
    loadBuildings().catch(err => { window.__dbg.buildErr = String(err); });
    </script>
    </body>
    </html>
    """

    cesium_html = cesium_template.replace("__LON__", repr(brewin_path_lon)).replace("__LAT__", repr(brewin_path_lat))
    cesium_map = mo.iframe(cesium_html, height="580px")
    cesium_map
    return


@app.cell
def _(brewin_path_lat, brewin_path_lon, px):
    fig = px.scatter_map(
        lat=[brewin_path_lat],
        lon=[brewin_path_lon],
        zoom=13,
    )
    fig.update_layout(map_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
    fig
    return


@app.cell
def _():
    import marimo as mo
    import plotly.express as px

    return mo, px


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Comparing the MatTiler deck.gl example to the example above

    https://docs.maptiler.com/deck-gl/examples/3d-terrain/

    ### Claude

    ```sh
    I got the actual maptiler example code (./npm/main.js). It is deck.gl's TerrainLayer — same approach as ours, not a MapLibre overlay. So you're right: nothing stops us using mapterhorn this way. Here's the concrete diff:

    // MapTiler example                          // Our notebook (mapterhorn)
    TERRAIN_IMAGE = ".../terrain-rgb-v2/...webp" elevationData = ".../mapterhorn/...webp"
    ELEVATION_DECODER = {                        elevationDecoder = {
      rScaler: 6553.6,  // = 65536 * 0.1           rScaler: 256,
      gScaler: 25.6,    // = 256   * 0.1           gScaler: 1,
      bScaler: 0.1,                                bScaler: 1/256,
      offset: -10000                               offset: -32768
    }                                            }
    maxZoom: 12                                  maxZoom: 12
    // view zoom 11.5, terrain-only             // view zoom 15, + buildings layer

    Main differences

    ┌──────────────┬─────────────────────────────┬─────────────────────────┐
    │              │      MapTiler example       │      Our notebook       │
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ Format       │ .webp
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ Encoding     │ Mapbox terrain-RGB
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ Decoder      │ {6553.6, 25.6, 0.1, -10000}
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ maxZoom      │ 12
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ View zoom    │ 11.5 (≤ maxZoom)
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ Layers       │ terrain only
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ meshMaxError │ default (4.0)
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ Texture      │ satellite .jpg
    ├──────────────┼─────────────────────────────┼─────────────────────────┤
    │ Terrain      │ isolated volcano
    └──────────────┴─────────────────────────────┴─────────────────────────┘

    What this tells us

    1. The decoder must match the encoding, and ours does. mapterhorn is Terrarium, maptiler is Mapbox — different
    formulas. We correctly use the Terrarium decer's {6553.6,...} decoder onto mapterhorntiles, every pixel would be off by thousands of metres — instant spikes. That's a common footgun, but not our bug.)
    2. .webp is not the culprit — both use it, awed a mapterhorn tile decoding cleanly. So Ican drop the webp-lossiness theory.                                                                            3. The standout operational difference is ov sits at zoom 11.5, at/below its maxZoom: 12, so every visible tile is one consistent LOD — TerrainLayer looks clean. Our default view is zoom 15, ~3 levels the z12 cap, panned across many tiles. That'f skirts/cross-LOD stitching tends to show.This is the most likely spike trigger and the cleanest thing to test.
    The honest correction to my earlier explainer: deck.gl's TerrainLayer can do exactly what the example does — I overstated its limitations. The likely issueDEM's native zoom.

    The decisive test is to match the example: trror, and a view at zoom ≤ 12, and see if the spikes vanish. You've interrupted my renders twice — do you want me to run that one comparison render, or would you rather just set the notebook's deck.gl view ve yourself?
    ```
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Why the deck.gl & Cesium terrain has spikes (but MapLibre doesn't)

    **It is not the elevation data.** I pulled a Mapterhorn z12 tile and checked it
    pixel-by-pixel: it decodes cleanly with the Terrarium formula
    `height = R*256 + G + B/256 - 32768`, alpha is a constant 255, browser
    colour-management changes *nothing*, and neighbouring heights never jump more
    than ~30 m. The DEM itself is smooth and correct, so the spikes are created
    when each engine turns that raster into 3D geometry, not by the source data.
    (Confirmed it is the *terrain*: the spikes remain in deck.gl even with the
    buildings layer removed.)

    **The cause: a raster-DEM meshed per-tile, without skirts or stitching.**
    Mapterhorn serves a **raster-DEM** -- a `.webp` image where colour *encodes*
    height. That format is meant to be sampled on the GPU by a *dedicated* terrain
    engine. deck.gl's `TerrainLayer` and our hand-rolled Cesium
    `CustomHeightmapTerrainProvider` are **not** that: each one re-meshes every tile
    into its own grid of triangles, independently of its neighbours, with **no
    skirts** (the vertical walls that hide tile edges) and **no LOD stitching**
    (matching vertices where two tiles, or two zoom levels, meet). Wherever those
    independently-built meshes touch, their edge vertices don't line up and the
    seam tears into spikes / thin walls. This happens at any zoom -- and requesting
    zoom levels past Mapterhorn's max (z12) makes it worse, because the mesher is
    then stretching and guessing beyond real data.

    **Why MapLibre is immune:** it *is* a purpose-built terrain renderer. It decodes
    the exact same tiles on the GPU and automatically adds skirts, stitches LOD
    boundaries, and over-zooms natively, so the seams never appear.

    ### What would actually fix it
    | Engine | Fix |
    |---|---|
    | **deck.gl** | Run deck.gl as a `MapboxOverlay` *on top of* MapLibre and let MapLibre own the terrain; or switch to Google **Photorealistic 3D Tiles** (`Tile3DLayer`). |
    | **Cesium** | Feed it real **quantized-mesh** terrain (Cesium ion, or a self-hosted tiler such as `cesium-terrain-builder`) instead of a raster-DEM; or add skirts + edge-stitching to the custom provider. |
    | **Both** | A raster-DEM is the wrong input for a generic mesh layer; it shines in a renderer that decodes it on the GPU (MapLibre). |
    """)
    return


if __name__ == "__main__":
    app.run()
