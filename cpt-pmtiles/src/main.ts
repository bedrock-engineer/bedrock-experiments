import { scaleThreshold } from "d3-scale";
import { schemeYlOrRd } from "d3-scale-chromatic";
import { debounce } from "es-toolkit";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Protocol } from "pmtiles";

let protocol = new Protocol();
maplibregl.addProtocol("pmtiles", protocol.tile);

const standards = {
  ISO22476D1: "#e41a1c",
  ISO22476D12: "#377eb8",
  NEN3680: "#256923",
  NEN5140: "#984ea3",
  onbekend: "#999999",
};

// Define decade scale using d3
const decadeDomain = [1980, 1990, 2000, 2010, 2020, 2030];
const decadeScale = scaleThreshold<number, string>()
  .domain(decadeDomain.slice(1, -1)) // Thresholds: [1990, 2000, 2010, 2020]
  .range(schemeYlOrRd[6]);

type ColorMode = "standard" | "decade";
let currentColorMode: ColorMode = "standard";
const selectedDecades = new Set([1980, 1990, 2000, 2010, 2020]); // All enabled by default
const selectedStandards = new Set(Object.keys(standards)); // All enabled by default

// Helper to convert d3 threshold scale to MapLibre expression
function thresholdScaleToMapLibreExpression(
  scale: ReturnType<typeof scaleThreshold<number, string>>,
  valueExpression: any
): any {
  const domain = scale.domain();
  const range = scale.range();

  const expression: any = ["case"];

  // Add conditions for each threshold
  domain.forEach((threshold, i) => {
    expression.push(["<", valueExpression, threshold], range[i]);
  });

  // Fallback to last color
  expression.push(range[range.length - 1]);

  return expression;
}

// Basemap configurations
type BasemapConfig =
  | { type: "raster"; source: maplibregl.RasterSourceSpecification }
  | { type: "vector-style"; styleUrl: string; attribution: string };

const basemaps: Record<string, BasemapConfig> = {
  brt: {
    type: "vector-style",
    styleUrl:
      "https://api.pdok.nl/kadaster/brt-achtergrondkaart/ogc/v1/styles/standaard__webmercatorquad?f=mapbox",
    attribution: "Kaartgegevens: © Kadaster",
  },
  luchtfoto: {
    type: "raster",
    source: {
      type: "raster",
      tiles: [
        "https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z}/{x}/{y}.jpeg",
      ],
      tileSize: 256,
      attribution: "Luchtfoto's: © Kadaster",
    },
  },
  // bag: {}
  // bgt: {
  //   type: "vector-style",
  //   styleUrl:
  //     "https://api.pdok.nl/lv/bgt/ogc/v1/styles/bgt_achtergrondvisualisatie__webmercatorquad",
  //   attribution: "BGT: © Kadaster",
  // },
};

// Track current basemap layers for removal
let currentBasemapLayers: string[] = [];

// Function to load a basemap (raster or vector)
async function loadBasemap(basemapId: string) {
  // Remove existing basemap layers and sources
  currentBasemapLayers.forEach((layerId) => {
    if (map.getLayer(layerId)) {
      map.removeLayer(layerId);
    }
  });

  const sourcesToRemove = new Set<string>();
  currentBasemapLayers.forEach((layerId) => {
    const layer = map.getStyle().layers?.find((l) => l.id === layerId);
    if (layer && "source" in layer && typeof layer.source === "string") {
      sourcesToRemove.add(layer.source);
    }
  });

  sourcesToRemove.forEach((sourceId) => {
    if (map.getSource(sourceId)) {
      map.removeSource(sourceId);
    }
  });

  currentBasemapLayers = [];

  const basemapConfig = basemaps[basemapId];
  if (!basemapConfig) return;

  if (basemapConfig.type === "raster") {
    // Handle raster basemap
    const sourceId = `basemap-${basemapId}`;
    map.addSource(sourceId, basemapConfig.source);
    map.addLayer(
      {
        id: `${sourceId}-layer`,
        type: "raster",
        source: sourceId,
      },
      "cpt-points"
    );
    currentBasemapLayers.push(`${sourceId}-layer`);
  } else if (basemapConfig.type === "vector-style") {
    // Handle vector style basemap
    try {
      const response = await fetch(basemapConfig.styleUrl);
      const style = await response.json();

      // Add sources from the style
      for (const [sourceId, sourceSpec] of Object.entries(
        style.sources || {}
      )) {
        const prefixedSourceId = `basemap-${basemapId}-${sourceId}`;
        map.addSource(prefixedSourceId, sourceSpec as any);
      }

      // Add layers from the style, updating source references
      const beforeLayer = "cpt-points";
      for (const layer of style.layers || []) {
        const prefixedLayer = {
          ...layer,
          id: `basemap-${basemapId}-${layer.id}`,
          source: `basemap-${basemapId}-${layer.source}`,
        };

        // Handle source-layer if it exists
        if ("source-layer" in layer) {
          (prefixedLayer as any)["source-layer"] = layer["source-layer"];
        }

        map.addLayer(prefixedLayer as any, beforeLayer);
        currentBasemapLayers.push(prefixedLayer.id);
      }
    } catch (error) {
      console.error(`Failed to load basemap style for ${basemapId}:`, error);
    }
  }
}

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    sources: {
      "cpt-netherlands": {
        type: "vector",
        url: "pmtiles://./public/cpt_netherlands.pmtiles",
      },
    },
    layers: [
      {
        id: "cpt-points",
        type: "circle",
        source: "cpt-netherlands",
        "source-layer": "cpt_locationsfgb",
        paint: {
          "circle-color": [
            "match",
            ["get", "cpt_standard"],
            "ISO22476D1",
            "#e41a1c", // Red
            "ISO22476D12",
            "#377eb8", // Blue
            "NEN3680",
            "#256923", // Green
            "NEN5140",
            "#984ea3", // Purple
            "onbekend",
            "#999999", // Gray for unknown
            "#999999",
          ],
          "circle-radius": [
            "interpolate",
            ["exponential", 2],
            ["zoom"],
            5,
            0.25, // Netherlands overview
            8,
            1, // regional view
            10,
            2, // city view
            14,
            4, // street level
          ],
          "circle-opacity": 0.6,
        },
      },
    ],
  },
  center: [5.37713395149355, 52.157630219877774], // [lng, lat]
  zoom: 7,
  minZoom: 5,
  maxZoom: 16,
  maxBounds: [
    [2.5, 50.0], // Southwest corner [lng, lat]
    [8.0, 54.5], // Northeast corner [lng, lat]
  ],
});

// Load initial basemap after map loads
map.on("load", async () => {
  await loadBasemap("brt");
});

// Add popup on click
map.on("click", "cpt-points", (e) => {
  if (!e.features || e.features.length === 0) return;

  const feature = e.features[0];
  const props = feature.properties;

  const html = `
    <div style="font-family: sans-serif;">
      <h3 style="margin: 0 0 8px 0; font-size: 14px;">${
        props.bro_id || "Unknown"
      }</h3>
      <table style="font-size: 12px; border-collapse: collapse;">
        <tr><td style="padding: 2px 8px 2px 0;"><strong>Standard:</strong></td><td>${
          props.cpt_standard || "-"
        }</td></tr>
        <tr><td style="padding: 2px 8px 2px 0;"><strong>Purpose:</strong></td><td>${
          props.survey_purpose || "-"
        }</td></tr>
        <tr><td style="padding: 2px 8px 2px 0;"><strong>Date:</strong></td><td>${
          props.research_report_date || "-"
        }</td></tr>
        <tr><td style="padding: 2px 8px 2px 0;"><strong>Context:</strong></td><td>${
          props.delivery_context || "-"
        }</td></tr>
        <tr><td style="padding: 2px 8px 2px 0;"><strong>Quality:</strong></td><td>${
          props.quality_regime || "-"
        }</td></tr>
      </table>
    </div>
  `;

  new maplibregl.Popup().setLngLat(e.lngLat).setHTML(html).addTo(map);
});

// Change cursor to pointer on hover
map.on("mouseenter", "cpt-points", () => {
  map.getCanvas().style.cursor = "pointer";
});

map.on("mouseleave", "cpt-points", () => {
  map.getCanvas().style.cursor = "";
});

// Update legend based on color mode
function updateLegend() {
  const legendItems = document.getElementById("legend-items");
  if (!legendItems) return;

  legendItems.innerHTML = "";

  if (currentColorMode === "standard") {
    const standardLabels: Record<string, string> = {
      ISO22476D1: "ISO 22476-1",
      ISO22476D12: "ISO 22476-12",
      NEN3680: "NEN 3680",
      NEN5140: "NEN 5140",
      onbekend: "Unknown",
    };

    // Standard legend with checkboxes
    Object.entries(standards).forEach(([standard, color]) => {
      const item = document.createElement("div");
      item.className = "legend-item";
      const checked = selectedStandards.has(standard) ? "checked" : "";
      item.innerHTML = `
        <input type="checkbox" id="standard-${standard}" value="${standard}" ${checked}>
        <div class="legend-color" style="background-color: ${color}"></div>
        <label for="standard-${standard}" style="cursor: pointer;">${standardLabels[standard]}</label>
      `;
      legendItems.appendChild(item);

      // Add event listener for checkbox
      const checkbox = item.querySelector(
        `#standard-${standard}`
      ) as HTMLInputElement;
      checkbox.addEventListener("change", (e) => {
        const target = e.target as HTMLInputElement;
        const standard = target.value;

        if (target.checked) {
          selectedStandards.add(standard);
        } else {
          selectedStandards.delete(standard);
        }

        updateFilter();
      });
    });
  } else {
    // Decade legend with checkboxes
    decadeDomain.slice(0, -1).forEach((decade, i) => {
      const color = decadeScale.range()[i];
      const item = document.createElement("div");
      item.className = "legend-item";
      const checked = selectedDecades.has(decade) ? "checked" : "";
      item.innerHTML = `
        <input type="checkbox" id="decade-${decade}" value="${decade}" ${checked}>
        <div class="legend-color" style="background-color: ${color}"></div>
        <label for="decade-${decade}" style="cursor: pointer;">${decade}s</label>
      `;
      legendItems.appendChild(item);

      // Add event listener for checkbox
      const checkbox = item.querySelector(
        `#decade-${decade}`
      ) as HTMLInputElement;
      checkbox.addEventListener("change", (e) => {
        const target = e.target as HTMLInputElement;
        const decade = parseInt(target.value);

        if (target.checked) {
          selectedDecades.add(decade);
        } else {
          selectedDecades.delete(decade);
        }

        updateFilter();
      });
    });
  }
}

// Update filter based on selected standards or decades
function updateFilter() {
  if (currentColorMode === "standard") {
    // Filter by standards
    if (selectedStandards.size === 0) {
      map.setFilter("cpt-points", [
        "==",
        ["get", "cpt_standard"],
        "___NONE___",
      ]); // Show nothing
      return;
    }

    if (selectedStandards.size === Object.keys(standards).length) {
      map.setFilter("cpt-points", null); // Show all
      return;
    }

    // Build filter expression for selected standards
    const filterExpression: any = ["match", ["get", "cpt_standard"]];
    selectedStandards.forEach((standard) => {
      filterExpression.push(standard, true);
    });
    filterExpression.push(false); // Fallback for non-matching standards
    map.setFilter("cpt-points", filterExpression);
  } else {
    // Filter by decades
    if (selectedDecades.size === 0) {
      map.setFilter("cpt-points", [
        "==",
        ["get", "research_report_date"],
        "___NONE___",
      ]); // Show nothing
      return;
    }

    if (selectedDecades.size === 5) {
      map.setFilter("cpt-points", null); // All decades selected, no filter needed
      return;
    }

    // Build filter expression for selected decades
    const filterExpression: Array<unknown> = ["any"];

    selectedDecades.forEach((decade) => {
      const decadeIndex = decadeDomain.indexOf(decade);
      const nextDecade = decadeDomain[decadeIndex + 1];
      filterExpression.push([
        "all",
        ["!=", ["get", "research_report_date"], null],
        [
          ">=",
          ["to-number", ["slice", ["get", "research_report_date"], 0, 4]],
          decade,
        ],
        [
          "<",
          ["to-number", ["slice", ["get", "research_report_date"], 0, 4]],
          nextDecade,
        ],
      ]);
    });

    map.setFilter("cpt-points", filterExpression);
  }
}

// Switch color mode
function setColorMode(mode: ColorMode) {
  currentColorMode = mode;

  if (mode === "standard") {
    map.setPaintProperty("cpt-points", "circle-color", [
      "match",
      ["get", "cpt_standard"],
      "ISO22476D1",
      "#e41a1c",
      "ISO22476D12",
      "#377eb8",
      "NEN3680",
      "#256923",
      "NEN5140",
      "#984ea3",
      "onbekend",
      "#999999",
      "#999999",
    ]);
    updateFilter();
  } else {
    // Use d3 scale to create MapLibre expression for decade coloring
    const yearValue = [
      "to-number",
      ["slice", ["get", "research_report_date"], 0, 4],
    ];

    const yearExpression = [
      "case",
      // Check for null or invalid dates
      [
        "any",
        ["==", ["get", "research_report_date"], null],
        ["<", ["length", ["get", "research_report_date"]], 4],
      ],
      "#999999", // Unknown/null/invalid dates
      thresholdScaleToMapLibreExpression(decadeScale, yearValue),
    ];

    map.setPaintProperty("cpt-points", "circle-color", yearExpression);
    updateFilter();
  }

  updateLegend();
}

// Initialize legend
updateLegend();

// Add event listener for color mode toggle
document.getElementById("color-mode")?.addEventListener("change", (e) => {
  const mode = (e.target as HTMLSelectElement).value as ColorMode;
  setColorMode(mode);
});

// Geocoder functionality using PDOK Locatieserver
const searchInput = document.getElementById("search-input") as HTMLInputElement;
const searchResults = document.getElementById(
  "search-results"
) as HTMLDivElement;

const performSearch = debounce(async (query: string) => {
  try {
    const response = await fetch(
      `https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?q=${encodeURIComponent(
        query
      )}&rows=10`
    );
    const data = await response.json();

    if (data.response.docs.length === 0) {
      searchResults.style.display = "none";
      return;
    }

    searchResults.innerHTML = "";
    searchResults.style.display = "block";

    data.response.docs.forEach((doc: any) => {
      const item = document.createElement("div");
      item.className = "search-result-item";

      const title = document.createElement("div");
      title.className = "search-result-title";
      title.textContent = doc.weergavenaam;

      const type = document.createElement("div");
      type.className = "search-result-type";
      type.textContent = doc.type;

      item.appendChild(title);
      item.appendChild(type);

      item.addEventListener("click", () => {
        // PDOK returns coordinates in centroide_ll as "POINT(lng lat)" or just "lng lat"
        let lng: number;
        let lat: number;

        if (doc.centroide_ll) {
          // Format: "POINT(5.12345 52.12345)" or "5.12345 52.12345"
          const coordString = doc.centroide_ll
            .replace("POINT(", "")
            .replace(")", "");
          const coords = coordString.trim().split(/\s+/);
          lng = parseFloat(coords[0]);
          lat = parseFloat(coords[1]);
        } else if (doc.centroide_rd) {
          // Fallback to RD coordinates if available (would need conversion)
          console.warn("Only RD coordinates available, need WGS84");
          return;
        } else {
          console.error("No coordinates found in result", doc);
          return;
        }

        if (Number.isNaN(lng) || Number.isNaN(lat)) {
          console.error("Invalid coordinates:", lng, lat);
          return;
        }

        map.flyTo({
          center: [lng, lat],
          zoom: 14,
          duration: 1000,
          essential: true,
        });
        searchInput.value = doc.weergavenaam;
        searchResults.style.display = "none";
      });

      searchResults.appendChild(item);
    });
  } catch (error) {
    console.error("Search error:", error);
    searchResults.style.display = "none";
  }
}, 300);

searchInput?.addEventListener("input", (e) => {
  const query = (e.target as HTMLInputElement).value;

  if (query.length < 2) {
    searchResults.style.display = "none";
    return;
  }

  performSearch(query);
});

// Close search results when clicking outside
document.addEventListener("click", (e) => {
  if (!(e.target as HTMLElement).closest("#search-container")) {
    searchResults.style.display = "none";
  }
});

// Basemap switching
const basemapSelect = document.getElementById(
  "basemap-select"
) as HTMLSelectElement;

basemapSelect?.addEventListener("change", async (e) => {
  const basemapId = (e.target as HTMLSelectElement).value;

  if (basemapId === "none") {
    // Remove all basemap layers
    currentBasemapLayers.forEach((layerId) => {
      if (map.getLayer(layerId)) {
        map.removeLayer(layerId);
      }
    });

    // Remove sources after layers are removed
    await new Promise((resolve) => setTimeout(resolve, 0));

    const sourcesToRemove = new Set<string>();
    currentBasemapLayers.forEach((layerId) => {
      const layer = map.getStyle().layers?.find((l) => l.id === layerId);
      if (layer && "source" in layer && typeof layer.source === "string") {
        sourcesToRemove.add(layer.source);
      }
    });

    sourcesToRemove.forEach((sourceId) => {
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    });

    currentBasemapLayers = [];
  } else {
    await loadBasemap(basemapId);
  }
});
