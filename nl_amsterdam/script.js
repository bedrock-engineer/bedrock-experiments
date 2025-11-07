// Your access token can be found at: https://ion.cesium.com/tokens.
// Replace `your_access_token` with your Cesium ion access token.
Cesium.Ion.defaultAccessToken = null;

// Initialize the Cesium Viewer in the HTML element with the `cesiumContainer` ID.
const viewer = new Cesium.Viewer("cesiumContainer", {
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
  destination: Cesium.Cartesian3.fromDegrees(4.903831, 52.385499, 100),
  orientation: {
    heading: 3.115321511892013,
    pitch: -0.24478081612082314,
    roll: 6.283098181620492,
  },
};

// Set initial camera position immediately
viewer.camera.setView(initialCameraView);

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
