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

// Definition objects by applicationId, mapped to the InstanceProxy that places them, for the
// definitions with a single placement: the viewer draws such an instance as the
// definition's own objects, so a click on it selects those
function singlePlacements(objects) {
  const placements = new Map();
  for (const obj of objects) {
    if (obj.speckle_type?.endsWith("InstanceProxy")) {
      placements.set(obj.definitionId, [...(placements.get(obj.definitionId) ?? []), obj]);
    }
  }
  const placedBy = new Map();
  for (const definition of objects[0].instanceDefinitionProxies ?? []) {
    const placed = placements.get(definition.applicationId) ?? [];
    if (placed.length === 1) for (const member of definition.objects) placedBy.set(member, placed[0]);
  }
  return placedBy;
}

// The element a selected node belongs to. An instance drawn as instanced geometry hangs
// under its InstanceProxy; one drawn as its definition's objects is found in placedBy.
// Nested instances resolve to the outermost InstanceProxy.
function elementOf(node, placedBy) {
  let element = node.model.raw;
  for (let parent = node.parent; parent; parent = parent.parent) {
    if (parent.model?.raw?.speckle_type?.endsWith("InstanceProxy")) element = parent.model.raw;
  }
  for (let depth = 0; placedBy.has(element.applicationId) && depth < 16; depth++) {
    element = placedBy.get(element.applicationId);
  }
  return element;
}

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

// Axes (x red, y green, z blue) and a label at a named point in the viewer's world, drawn
// on top of the model
function markerObject({ name, position, size = 5 }) {
  const group = new THREE.Group();
  group.position.fromArray(position);
  const axes = new THREE.AxesHelper(size);
  axes.material.depthTest = false;
  group.add(axes);
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");
  context.font = "28px sans-serif";
  canvas.width = Math.ceil(context.measureText(name).width) + 16;
  canvas.height = 40;
  context.font = "28px sans-serif";
  context.fillStyle = "rgba(255, 255, 255, 0.85)";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#222";
  context.fillText(name, 8, 29);
  const label = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(canvas), depthTest: false })
  );
  label.scale.set(canvas.width / canvas.height, 1, 1).multiplyScalar(size / 4);
  label.position.set(0, 0, size * 1.2);
  group.add(label);
  group.traverse((object) => {
    object.layers.set(ObjectLayers.PROPS);
    object.renderOrder = 10;
  });
  return group;
}

async function render({ model, el }) {
  const container = document.createElement("div");
  // A fixed height, or one that follows the notebook's width
  const height = model.get("height");
  container.style.cssText = height
    ? `position: relative; width: 100%; height: ${height}px;`
    : `position: relative; width: 100%; aspect-ratio: ${model.get("aspect_ratio")};`;
  el.appendChild(container);

  const viewer = new Viewer(container, { ...DefaultViewerParams, verbose: false });
  await viewer.init();
  const camera = viewer.createExtension(CameraController);
  const selection = viewer.createExtension(SelectionExtension);
  const groundInView = viewer.createExtension(GroundInView);
  const contextTiles = viewer.createExtension(ContextTiles);
  let placedBy = new Map();
  viewer.on(ViewerEvent.ObjectClicked, () => {
    // Read the extension's selection once it has handled the click (shift adds to it)
    setTimeout(() => {
      const objects = selection.getSelectedNodes().map((node) => elementOf(node, placedBy));
      model.set(
        "selected",
        JSON.parse(JSON.stringify(objects, (key, value) => (NOT_SELECTED.has(key) ? undefined : value)))
      );
      model.save_changes();
    });
  });

  async function load() {
    // Other objects: the old selection no longer applies
    if (model.get("selected").length) {
      model.set("selected", []);
      model.save_changes();
    }
    await viewer.unloadAll();
    const buffer = model.get("objects_gz");
    if (!buffer || buffer.byteLength === 0) return;
    // One or more models, each its v3 objects with the root first
    placedBy = new Map();
    for (const objects of await gunzipJson(buffer)) {
      for (const [member, instance] of singlePlacements(objects)) placedBy.set(member, instance);
      await viewer.loadObject(new MemoryLoader(viewer.getWorldTree(), objects), false);
    }
    camera.setCameraView(undefined, false);
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

  let markers = [];
  function placeMarkers() {
    const scene = viewer.getRenderer().scene;
    for (const marker of markers) scene.remove(marker);
    markers = model.get("markers").map(markerObject);
    for (const marker of markers) scene.add(marker);
    viewer.requestRender();
  }
  model.on("change:markers", placeMarkers);
  placeMarkers();

  contextTiles.setTilesets(model.get("tilesets"));
  model.on("change:tilesets", () => {
    contextTiles.setTilesets(model.get("tilesets"));
    updateAttribution();
  });
  // The viewer itself only follows the window's size, not its container's
  const resizing = new ResizeObserver(() => viewer.resize());
  resizing.observe(container);
  return () => {
    resizing.disconnect();
    viewer.dispose();
  };
}

export default { render };
