// Your access token can be found at: https://ion.cesium.com/tokens.
// Replace `your_access_token` with your Cesium ion access token.
Cesium.Ion.defaultAccessToken = null;

// Initialize the Cesium Viewer in the HTML element with the `cesium-container` ID.
const viewer = new Cesium.Viewer("cesium-container", {
  animation: false,
  timeline: false,
  fullscreenButton: false,
  vrButton: false,
  sceneModePicker: false,
  baseLayerPicker: false,
  navigationHelpButton: false,
  geocoder: false,
  homeButton: false,
  msaaSamples: 4, // Anti-aliasing can help reduce visual artifacts
});
// Overhoeks, Amsterdam initial camera view
const initialCameraView = {
  destination: Cesium.Cartesian3.fromDegrees(4.9044, 52.3889, 280),
  orientation: {
    heading: 3.3709,
    pitch: -0.3042,
  },
};
viewer.camera.setView(initialCameraView);

// Create a camera position object, to make is easier to set the initialCameraView
function getCameraPosition() {
  const pos = Cesium.Ellipsoid.WGS84.cartesianToCartographic(
    viewer.scene.camera.positionWC
  );
  return {
    destination: {
      lon: Number(Cesium.Math.toDegrees(pos.longitude).toFixed(4)),
      lat: Number(Cesium.Math.toDegrees(pos.latitude).toFixed(4)),
      height: Number(pos.height.toFixed(4)),
    },
    orientation: {
      heading: Number(viewer.scene.camera.heading.toFixed(4)),
      pitch: Number(viewer.scene.camera.pitch.toFixed(4)),
    },
  };
}
// Make the viewer and getCameraPosition globally accessible for debugging purposes
window.viewer = viewer;
window.getCameraPosition = getCameraPosition;

// Terrain from the AHN gebaseerde DTM van Nederland (Quantized-Mesh)
const ahnTerrainProvider = await Cesium.CesiumTerrainProvider.fromUrl(
  "https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaalterreinmodel/quantized-mesh"
);

// Ellipsoidal "terrain"
const ellipsoidTerrainProvider = new Cesium.EllipsoidTerrainProvider();

// Assign terrain provider to viewer
viewer.terrainProvider = ahnTerrainProvider;

// Disable any terrain and hide the globe entirely
// viewer.terrain = undefined;
// viewer.scene.globe.show = false;

try {
  const tileset_3dbag = await Cesium.Cesium3DTileset.fromUrl(
    "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json"
  );
  viewer.scene.primitives.add(tileset_3dbag);

  // 3D basisvoorziening terreinen
  // const tileset_3dbgt = await Cesium.Cesium3DTileset.fromUrl(
  //   "https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1_0/collections/terreinen/3dtiles"
  // );
  // viewer.scene.primitives.add(tileset_3dbgt);
} catch (error) {
  // Handle errors
  console.log(`There was an error while creating the 3D tileset. ${error}`);
}
