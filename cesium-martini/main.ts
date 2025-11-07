import TerrainProvider from "@macrostrat/cesium-martini";
import { buildExample } from "./build-example";

const accessToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
console.log(import.meta);

// // @ts-ignore
const terrainProvider = new TerrainProvider({
  requestVertexNormals: false,
  requestWaterMask: false,
  accessToken: accessToken,
  highResolution: true,
  skipZoomLevels(z: number) {
    return z % 3 != 0;
  },
});

buildExample(terrainProvider, accessToken);
