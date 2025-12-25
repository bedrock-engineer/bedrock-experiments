# Rust experiments for Bedrock.engineer

## GeoRust

  - https://book.georust.org
  - https://github.com/georust

## `bedrock-engineer` monorepo

bedrock-engineer
    - src/parsers - a lib per GI data format (AGS3, AGS4, GEF, IMBROXML, DIGGS, ect) that parse single GI data files to DuckDB (rust such that it can be used in Python as well as web env? 
    - src/bedrock-gi - allows for 1. combining / merging multiple GI DuckDBs (initially only from the same GI data format) into a single GI DuckDB; 2. converting to 3D geospatial vector data. From GI DuckDB to GI GeoDuckDB 
