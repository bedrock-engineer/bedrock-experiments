import { UserConfig } from "vite";
import cesium from "vite-plugin-cesium";
import path from "path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

const cesiumRoot = require.resolve("cesium").replace("/index.cjs", "/Build");
const cesiumBuildPath = path.resolve(cesiumRoot, "Cesium");

const config: UserConfig = {
  // override the cache dir because we don't have a node_modules folder with yarn PnP
  cacheDir: path.join(__dirname, ".vite"),
  build: {
    sourcemap: true,
  },
  define: {
    "process.env": {
      NODE_DEBUG: false,
    },
  },
  envPrefix: "MAPBOX_",
  envDir: path.join(__dirname, ".."),
  plugins: [cesium({ cesiumBuildPath, cesiumBuildRootPath: cesiumRoot })],
};

console.log("Vite config:", config);

export default config;
