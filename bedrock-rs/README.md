# Rust experiments for Bedrock.engineer

## GeoRust

- https://book.georust.org
- https://github.com/georust

### Developing (Geo)Rust on Windows

In order to develop Rust applications on Windows, you'll need Visual Studio C++ Build tools ([see these rustup book docs](https://rust-lang.github.io/rustup/installation/windows-msvc.html)) or install from Command Prompt with:

```cmd
winget install Microsoft.VisualStudio.2022.BuildTools --force --override "--wait --passive --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.26100"
```

GeoRust requires some C libraries like PROJ, when using `cargo build` these C libraries require `cmake`, `vcpkg` and `sqlite3`. All three packages can be installed with scoop:

```cmd
scoop install cmake vcpkg sqlite
```

## `bedrock-engineer` monorepo

bedrock-engineer
    - src/parsers - a lib per GI data format (AGS3, AGS4, GEF, IMBROXML, DIGGS, ect) that parse single GI data files to DuckDB (rust such that it can be used in Python as well as web env? 
    - src/bedrock-gi - allows for 1. combining / merging multiple GI DuckDBs (initially only from the same GI data format) into a single GI DuckDB; 2. converting to 3D geospatial vector data. From GI DuckDB to GI GeoDuckDB 
