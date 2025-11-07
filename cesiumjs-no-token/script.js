import {
  MartiniTerrainProvider,
  DefaultHeightmapResource,
  WorkerFarmTerrainDecoder,
} from "https://esm.run/@macrostrat/cesium-martini"

// Set the Cesium Ion token to `null` to avoid warnings
Cesium.Ion.defaultAccessToken = null;

/* Per Carto's website regarding basemap attribution: https://carto.com/help/working-with-data/attribution/#basemaps */
let CartoAttribution = 'Map tiles by <a href="https://carto.com">Carto</a>, under CC BY 3.0. Data by <a href="https://www.openstreetmap.org/">OpenStreetMap</a>, under ODbL.'

// Create ProviderViewModel based on different imagery sources
// - these can be used without Cesium Ion
var imageryViewModels = [];

imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'OpenStreetMap',
    iconUrl: Cesium.buildModuleUrl('Widgets/Images/ImageryProviders/openStreetMap.png'),
    tooltip: 'OpenStreetMap (OSM) is a collaborative project to create a free editable \
map of the world.\nhttp://www.openstreetmap.org',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        subdomains: 'abc',
        minimumLevel: 0,
        maximumLevel: 19
    });
    }
}));
imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'Positron',
    tooltip: 'CartoDB Positron basemap',
    iconUrl: 'http://a.basemaps.cartocdn.com/light_all/5/15/12.png',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'http://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
        credit: CartoAttribution,
        minimumLevel: 0,
        maximumLevel: 18
    });
    }
}));
imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'Positron without labels',
    tooltip: 'CartoDB Positron without labels basemap',
    iconUrl: 'http://a.basemaps.cartocdn.com/rastertiles/light_nolabels/5/15/12.png',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}.png',
        credit: CartoAttribution,
        minimumLevel: 0,
        maximumLevel: 18
    });
    }
}));
imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'Dark Matter',
    tooltip: 'CartoDB Dark Matter basemap',
    iconUrl: 'http://a.basemaps.cartocdn.com/rastertiles/dark_all/5/15/12.png',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png',
        credit: CartoAttribution,
        minimumLevel: 0,
        maximumLevel: 18
    });
    }
}));
imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'Dark Matter without labels',
    tooltip: 'CartoDB Dark Matter without labels basemap',
    iconUrl: 'http://a.basemaps.cartocdn.com/rastertiles/dark_nolabels/5/15/12.png',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/dark_nolabels/{z}/{x}/{y}.png',
        credit: CartoAttribution,
        minimumLevel: 0,
        maximumLevel: 18
    });
    }
}));
imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'Voyager',
    tooltip: 'CartoDB Voyager basemap',
    iconUrl: 'http://a.basemaps.cartocdn.com/rastertiles/voyager_labels_under/5/15/12.png',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_labels_under/{z}/{x}/{y}.png',
        credit: CartoAttribution,
        minimumLevel: 0,
        maximumLevel: 18
    });
    }
}));
imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'Voyager without labels',
    tooltip: 'CartoDB Voyager without labels basemap',
    iconUrl: 'http://a.basemaps.cartocdn.com/rastertiles/voyager_nolabels/5/15/12.png',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}.png',
        credit: CartoAttribution,
        minimumLevel: 0,
        maximumLevel: 18
    });
    }
}));
imageryViewModels.push(new Cesium.ProviderViewModel({
    name: 'Google Satellite',
    iconUrl: 'http://mt.google.com/vt/lyrs=s&hl=en&x=15&y=12&z=5',
    creationFunction: function() {
    return new Cesium.UrlTemplateImageryProvider({
        url: 'http://mt.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}',
        credit: 'Imagery © Google',
        minimumLevel: 0,
        maximumLevel: 16
    });
    }
}));


// ----------------------------------------------------------------------------
// Create Cesium Martini Terrain Provider
const terrariumWorker = new Worker(
  new URL("./mapterhorn.worker", import.meta.url),
  { type: "module" },
);

const terrainResource = new DefaultHeightmapResource({
  url: "https://tiles.mapterhorn.com/{z}/{x}/{y}.webp",
//   skipOddLevels: true,
  maxZoom: 12,
});

// Terrarium format utilises a different encoding scheme to Mapbox Terrain-RGB
// See also QGIS XYZ-Tiles options
const terrainDecoder = new WorkerFarmTerrainDecoder({
  worker: terrariumWorker,
});

// Construct terrain provider with Mapzen datasource and custom RGB decoding
const martiniTerrainProvider = new MartiniTerrainProvider({
  resource: terrainResource,
  decoder: terrainDecoder,
});


// ----------------------------------------------------------------------------
// Initialize the viewer - this works without a token!
const viewer = new Cesium.Viewer('cesiumContainer', {
    imageryProviderViewModels: imageryViewModels,
    selectedImageryProviderViewModel: imageryViewModels[1],
    animation: false,
    timeline: false,
    infoBox: false,
    homeButton: false,
    fullscreenButton: false,
    selectionIndicator: false,
});

// Set the terrain provider to the Martini terrain provider
console.log(terrainResource)
viewer.terrainProvider = martiniTerrainProvider;
console.log(martiniTerrainProvider)

// Remove the Terrain section of the baseLayerPicker
viewer.baseLayerPicker.viewModel.terrainProviderViewModels.removeAll()
