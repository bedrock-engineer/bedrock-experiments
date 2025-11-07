import * as Cesium from "cesium";
import MapboxTerrainProvider from "@macrostrat/cesium-martini";
import {
  MartiniTerrainProvider,
  DefaultHeightmapResource,
  WorkerFarmTerrainDecoder,
} from "@macrostrat/cesium-martini";

// Set the Cesium Ion token to `null` to avoid warnings
Cesium.Ion.defaultAccessToken = null;

const mapboxAccessToken = import.meta.env.MAPBOX_API_TOKEN;

// ----- Terrain Provider -----
const terrainProvider = new MapboxTerrainProvider({
  requestVertexNormals: false,
  requestWaterMask: false,
  accessToken: mapboxAccessToken,
  highResolution: true,
  skipZoomLevels(z: number) {
    return z % 3 != 0;
  },
});

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
  terrainProvider,
  imageryProviderViewModels: imageryViewModels,
  selectedImageryProviderViewModel: imageryViewModels[0],
  animation: false,
  timeline: false,
  infoBox: false,
  homeButton: false,
  fullscreenButton: false,
  selectionIndicator: false,
});

// Remove the Terrain section of the baseLayerPicker
viewer.baseLayerPicker.viewModel.terrainProviderViewModels = [];

// Configure globe for underground visualization
// https://cesium.com/blog/2020/06/16/visualizing-underground/
const initAlpha = 0.7;
const { globe } = viewer.scene;
globe.translucency.enabled = true;
globe.depthTestAgainstTerrain = true;
globe.translucency.frontFaceAlpha = initAlpha;
globe.undergroundColor = Cesium.Color.fromCssColorString("#e8e4e0"); // Solid color to block view to opposite side of globe
globe.translucency.backFaceAlpha = 1.0; // Keep back face opaque so we don't see the opposite side of the globe

// So we can move the camera below the surface
viewer.scene.screenSpaceCameraController.enableCollisionDetection = false;

// Limit how far out the camera can zoom (in meters)
viewer.scene.screenSpaceCameraController.maximumZoomDistance = 50000;
