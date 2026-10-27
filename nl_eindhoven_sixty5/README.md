# Sixty5, Strijp-S, Eindhoven

Test dataset for defining an Engineering CRS in a geospatial database (PostGIS, DuckDB spatial, GeoPackage).

`sixty5_piles.py` is a marimo notebook that extracts the 146 foundation piles from the Sixty5 structural IFC model with ifcopenshell, defines the model's Engineering CRS (millimetres) as a derived compound CRS on EPSG:7415 (RD New + NAP height), and converts the pile heads to RD New + NAP and ETRS89.

```bash
uvx marimo edit --sandbox sixty5_piles.py
```

The notebook downloads the IFC model from R2 into `data/` on first run. The RD New + NAP → ETRS89 step needs the NSGI RDNAPTRANS™2018 grids, which PROJ fetches from its CDN when network access is enabled.
