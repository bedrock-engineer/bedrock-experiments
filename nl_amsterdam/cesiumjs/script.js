// Set the Cesium Ion token to `null` to avoid warnings
Cesium.Ion.defaultAccessToken = null;

// ----- Terrain Providers -----
let terrainViewModels = [];

terrainViewModels.push(
  new Cesium.ProviderViewModel({
    name: "AHN Quantized Mesh DTM",
    tooltip:
      "Digital Terrain Model (DTM) of the Netherlands generated from the Actueel Hoogtebestand Nederland (AHN) provided by PDOK as a Quantized Mesh. More info:\nhttps://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaalterreinmodel",
    iconUrl:
      "https://cuatro.sim-cdn.nl/ahn/uploads/2023-03/wsh-logo-actueel-hoogtebestand-nederland2.svg",
    creationFunction: function () {
      return Cesium.CesiumTerrainProvider.fromUrl(
        "https://api.pdok.nl/kadaster/3d-basisvoorziening/ogc/v1/collections/digitaalterreinmodel/quantized-mesh"
      );
    },
  })
);
terrainViewModels.push(
  new Cesium.ProviderViewModel({
    name: "WGS84 Ellipsoid",
    tooltip: "World Geodetic System 1984 (WGS84) Ellipsoid - no terrain",
    iconUrl:
      "https://cesium.com/downloads/cesiumjs/releases/1.135/Build/Cesium/Widgets/Images/TerrainProviders/Ellipsoid.png",
    creationFunction: function () {
      return Cesium.EllipsoidTerrainProvider();
    },
  })
);


// ----- Imagery Basemap Tile Providers -----
let imageryViewModels = [];

imageryViewModels.push(
  new Cesium.ProviderViewModel({
    name: "Google Satellite",
    tooltip: "Google Satellite Imagery Tiles Basemap",
    iconUrl: "http://mt.google.com/vt/lyrs=s&hl=en&x=15&y=12&z=5",
    creationFunction: function () {
      return new Cesium.UrlTemplateImageryProvider({
        url: "http://mt.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}",
        credit: "Imagery © Google",
        minimumLevel: 0,
        maximumLevel: 18,
      });
    },
  })
);
imageryViewModels.push(
  new Cesium.ProviderViewModel({
    name: "OpenStreetMap",
    tooltip:
      "OpenStreetMap (OSM) is a collaborative project to create a free editable map of the world.\nhttp://www.openstreetmap.org",
    iconUrl: Cesium.buildModuleUrl(
      "Widgets/Images/ImageryProviders/openStreetMap.png"
    ),
    creationFunction: function () {
      return new Cesium.UrlTemplateImageryProvider({
        url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        subdomains: "abc",
        minimumLevel: 0,
        maximumLevel: 19,
      });
    },
  })
);
imageryViewModels.push(
  new Cesium.ProviderViewModel({
    name: "Positron",
    tooltip: "CartoDB Positron basemap",
    iconUrl: "http://a.basemaps.cartocdn.com/light_all/5/15/12.png",
    creationFunction: function () {
      return new Cesium.UrlTemplateImageryProvider({
        url: "http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        // Per Carto's website regarding basemap attribution: https://carto.com/help/working-with-data/attribution/#basemaps
        credit:
          'Map tiles by <a href="https://carto.com">Carto</a>, under CC BY 3.0. Data by <a href="https://www.openstreetmap.org/">OpenStreetMap</a>, under ODbL.',
        minimumLevel: 0,
        maximumLevel: 18,
      });
    },
  })
);


// ----- Initialize & Configure CesiumJS Viewer -----
const viewer = new Cesium.Viewer("cesium-container", {
  selectedTerrainProviderViewModel: terrainViewModels[0],
  terrainProviderViewModels: terrainViewModels,
  imageryProviderViewModels: imageryViewModels,
  selectedImageryProviderViewModel: imageryViewModels[0],
  animation: false,
  timeline: false,
  infoBox: false,
  geocoder: false,
  fullscreenButton: false,
  selectionIndicator: false,
  msaaSamples: 4, // Anti-aliasing can help reduce visual artifacts
  homeButton: true,
  creditContainer: document.createElement(null),
});

// Configure globe for underground visualization
// https://cesium.com/blog/2020/06/16/visualizing-underground/
const initAlpha = 0.7;
const { globe } = viewer.scene;
globe.translucency.enabled = true;
globe.depthTestAgainstTerrain = true;
globe.translucency.frontFaceAlpha = initAlpha;
// Solid color to block view to opposite side of globe
globe.undergroundColor = Cesium.Color.fromCssColorString("#e8e4e0");
// Keep back face opaque so we don't see the opposite side of the globe
globe.translucency.backFaceAlpha = 1.0;
// So we can move the camera below the surface
viewer.scene.screenSpaceCameraController.enableCollisionDetection = false;
// Limit how far out the camera can zoom (in meters)
viewer.scene.screenSpaceCameraController.maximumZoomDistance = 50000;

// Make the viewer object globally accessible for debugging purposes
window.viewer = viewer;


// ----- Set Initial Camera Position & Implement getCameraPosition function -----
// Overhoeks, Amsterdam initial camera view
const initialCameraView = {
  destination: Cesium.Cartesian3.fromDegrees(4.9061, 52.3871, 217),
  orientation: {
    heading: 3.65,
    pitch: -0.53,
  },
};
viewer.camera.setView(initialCameraView);

// Add event listener to the home button, such that it flies you back to the initial camera view.
document.querySelector(".cesium-home-button").addEventListener("click", () => {
  viewer.camera.flyTo(initialCameraView);
});

// Function that makes it easy set the initialCameraView
function getCameraPosition() {
  const pos = Cesium.Ellipsoid.WGS84.cartesianToCartographic(
    viewer.scene.camera.positionWC
  );
  return {
    destination: {
      lon: Number(Cesium.Math.toDegrees(pos.longitude).toFixed(4)),
      lat: Number(Cesium.Math.toDegrees(pos.latitude).toFixed(4)),
      height: Number(pos.height.toFixed(1)),
    },
    orientation: {
      heading: Number(viewer.scene.camera.heading.toFixed(2)),
      pitch: Number(viewer.scene.camera.pitch.toFixed(2)),
    },
  };
}
window.getCameraPosition = getCameraPosition;


// ----- Add 3D Buildings & other "primitives" to the viewer -----
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
