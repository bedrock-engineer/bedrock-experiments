# All BRO CPT Locations with PMTiles

GeoPackage with all CPT locations from [PDOK Atom Feed](https://service.pdok.nl/bzk/brocptvolledigeset/atom/v1_0/index.xml)

## Data Processing

1. Convert GeoPackage to flatgeobuf using `ogr2ogr` from [GDAL](https://gdal.org/en).

```sh
ogr2ogr -f FlatGeobuf \
    cpt_locations.fgb \
    brocptvolledigeset_v2_0.gpkg \
    geotechnical_cpt_survey
```

2. Convert from flatgeobuf to [PMTiles](https://docs.protomaps.com/pmtiles/) using [Tippecanoe](https://github.com/felt/tippecanoe)

```sh
tippecanoe -o cpt_netherlands.pmtiles \
            -Z 5 -z 14 \
            --cluster-distance=10 \
            cpt_locations.fgb
```
