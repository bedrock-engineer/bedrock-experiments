"""
Convert BRO Digitaal Geologisch Model (DGM) Erdas Imagine rasters to
Cloud Optimized GeoTIFFs (COG).

Each geological unit becomes one multi-band COG:
  Band 1  top_elevation      – top of formation, m NAP (central estimate)
  Band 2  bottom_elevation   – bottom of formation, m NAP (central estimate)
  Band 3  thickness          – formation thickness, m (central estimate)
  Band 4  top_quality        – top surface quality layer (1–6 scale)
  Band 5  bottom_quality     – bottom surface quality layer
  Band 6  thickness_quality  – thickness quality layer
  Band 7  quality_value      – overall quality value (0–1)

The maaiveld (ground surface) raster is written as a separate single-band COG.

Metadata embedded per file:
  - Unit code, Dutch name, stratigraphic order (SEQ_NR)
  - RGB colour from the DGM legend
  - Vertical datum (NAP), source dataset, horizontal CRS
"""

import subprocess
import tempfile
from pathlib import Path

import numpy as np
import openpyxl
import rasterio
from rasterio.enums import Resampling

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

IMG_DIR = Path("data/brodgm/Model_DGM000000000022/DGM_v02r2s1/img")
REF_XLSX = Path(
    "data/brodgm/Model_DGM000000000022/DGM_v02r2s1/basisdata/REF_DGM_STR_UNIT.xlsx"
)
OUT_DIR = Path("data/brodgm/cog")

# ---------------------------------------------------------------------------
# Band layout
# ---------------------------------------------------------------------------

# Each tuple: (suffix_in_filename, band_name, long_description, units)
BAND_SPEC = [
    ("t-c",  "top_elevation",     "Top of formation (central estimate)",      "m NAP"),
    ("b-c",  "bottom_elevation",  "Bottom of formation (central estimate)",    "m NAP"),
    ("d-c",  "thickness",         "Formation thickness (central estimate)",    "m"),
    ("t-ql", "top_quality",       "Top surface quality layer (1=low, 6=high)", "score"),
    ("b-ql", "bottom_quality",    "Bottom surface quality layer",              "score"),
    ("d-ql", "thickness_quality", "Thickness quality layer",                   "score"),
    ("qv",   "quality_value",     "Overall formation quality value",           "0-1"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_unit_metadata(xlsx_path: Path) -> dict[str, dict]:
    """Return {unit_code: {description, seq_nr, r, g, b}} from the reference XLSX."""
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    units = {}
    for row in ws.iter_rows(values_only=True):
        if row[0] == "STR_UNIT_CD":   # header row
            continue
        code, desc, seq, r, g, b = row
        units[str(code)] = {
            "description": desc,
            "seq_nr": int(seq),
            "r": int(r),
            "g": int(g),
            "b": int(b),
        }
    return units


def discover_units(img_dir: Path) -> list[str]:
    """Return sorted list of unit codes that have at least one band file."""
    codes = set()
    for p in img_dir.glob("*.img"):
        name = p.stem
        if name == "mv":
            continue
        # Unit code is everything before the last '-c'/'-ql'/'-qv' segment(s)
        # Filenames look like: UNIT-t-c, UNIT-b-ql, UNIT-qv
        # where UNIT can itself contain hyphens (e.g. NUBR-VI, NUPZ-WA, NUKR1).
        # Strategy: strip the known suffixes from the right.
        for suffix in ("-t-c", "-b-c", "-d-c", "-t-ql", "-b-ql", "-d-ql", "-qv"):
            if name.endswith(suffix):
                codes.add(name[: -len(suffix)])
                break
    return sorted(codes, key=str.lower)


def read_band(path: Path) -> tuple[np.ndarray, dict, float]:
    """Read a single-band .img; return (array, profile, nodata)."""
    with rasterio.open(path) as src:
        data = src.read(1)
        profile = src.profile.copy()
        nodata = src.nodata
    return data, profile, nodata


def write_cog(
    out_path: Path,
    arrays: list[np.ndarray],
    band_names: list[str],
    band_descriptions: list[str],
    band_units: list[str],
    base_profile: dict,
    nodata: float,
    file_tags: dict[str, str],
) -> None:
    """Write a multi-band Cloud Optimized GeoTIFF with full metadata."""
    n_bands = len(arrays)

    profile = base_profile.copy()
    profile.update(
        driver="GTiff",
        count=n_bands,
        dtype="float32",
        nodata=nodata,
        compress="DEFLATE",
        zlevel=6,
        tiled=True,
        blockxsize=512,
        blockysize=512,
        interleave="band",
    )

    # Write to a temp file first, then gdal_translate to produce a true COG
    # (overviews must be embedded before the image data for HTTP range reads).
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with rasterio.open(tmp_path, "w", **profile) as dst:
            # File-level metadata
            dst.update_tags(**file_tags)

            for i, (arr, name, desc, unit) in enumerate(
                zip(arrays, band_names, band_descriptions, band_units), start=1
            ):
                dst.write(arr.astype("float32"), i)
                dst.update_tags(i, name=name, description=desc, units=unit)

        # Build overviews on the temp file
        with rasterio.open(tmp_path, "r+") as dst:
            dst.build_overviews([2, 4, 8, 16, 32], Resampling.average)
            dst.update_tags(ns="rio_overview", resampling="average")

        # gdal_translate -of COG reorders the file so overviews come first
        out_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "gdal_translate",
                "-of", "COG",
                "-co", "COMPRESS=DEFLATE",
                "-co", "ZLEVEL=6",
                "-co", "BLOCKSIZE=512",
                "-co", "OVERVIEWS=FORCE_USE_EXISTING",
                str(tmp_path),
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Per-unit conversion
# ---------------------------------------------------------------------------

def convert_unit(
    unit_code: str,
    meta: dict,
    img_dir: Path,
    out_dir: Path,
) -> None:
    arrays = []
    band_names = []
    band_descs = []
    band_units_list = []
    base_profile = None
    nodata = None

    for suffix, bname, bdesc, bunit in BAND_SPEC:
        img_path = img_dir / f"{unit_code}-{suffix}.img"
        if not img_path.exists():
            print(f"  WARNING: missing {img_path.name}, skipping band '{bname}'")
            continue
        arr, prof, nd = read_band(img_path)
        if base_profile is None:
            base_profile = prof
            nodata = nd
        arrays.append(arr)
        band_names.append(bname)
        band_descs.append(bdesc)
        band_units_list.append(bunit)

    if not arrays:
        print(f"  No bands found for {unit_code}, skipping.")
        return

    file_tags = {
        "UNIT_CODE":        unit_code,
        "UNIT_DESCRIPTION": meta["description"],
        "SEQ_NR":           str(meta["seq_nr"]),
        "LEGEND_COLOR_RGB": f"{meta['r']},{meta['g']},{meta['b']}",
        "LEGEND_COLOR_HEX": "#{:02X}{:02X}{:02X}".format(meta["r"], meta["g"], meta["b"]),
        "SOURCE":           "BRO Digitaal Geologisch Model (DGM) v2.2.1",
        "VERTICAL_DATUM":   "NAP (Normaal Amsterdams Peil)",
        "VERTICAL_UNITS":   "metres",
        "HORIZONTAL_CRS":   "RD New (EPSG:28992)",
        "BAND_COUNT":       str(len(arrays)),
    }

    out_path = out_dir / f"{unit_code}.tif"
    write_cog(
        out_path,
        arrays,
        band_names,
        band_descs,
        band_units_list,
        base_profile,
        nodata,
        file_tags,
    )
    print(f"  -> {out_path}  ({len(arrays)} bands)")


# ---------------------------------------------------------------------------
# Maaiveld (ground surface)
# ---------------------------------------------------------------------------

def convert_maaiveld(img_dir: Path, out_dir: Path) -> None:
    img_path = img_dir / "mv.img"
    arr, profile, nodata = read_band(img_path)

    file_tags = {
        "UNIT_CODE":        "mv",
        "UNIT_DESCRIPTION": "Maaiveld (ground surface elevation)",
        "SOURCE":           "BRO Digitaal Geologisch Model (DGM) v2.2.1",
        "VERTICAL_DATUM":   "NAP (Normaal Amsterdams Peil)",
        "VERTICAL_UNITS":   "metres",
        "HORIZONTAL_CRS":   "RD New (EPSG:28992)",
        "BAND_COUNT":       "1",
    }

    write_cog(
        out_dir / "mv.tif",
        [arr],
        ["ground_surface_elevation"],
        ["Ground surface (maaiveld) elevation"],
        ["m NAP"],
        profile,
        nodata,
        file_tags,
    )
    print(f"  -> {out_dir / 'mv.tif'}  (1 band)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading unit reference table …")
    unit_meta = load_unit_metadata(REF_XLSX)

    print("Discovering units …")
    unit_codes = discover_units(IMG_DIR)
    print(f"  Found {len(unit_codes)} units: {', '.join(unit_codes)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nConverting maaiveld …")
    convert_maaiveld(IMG_DIR, OUT_DIR)

    print(f"\nConverting {len(unit_codes)} geological units …")
    for code in unit_codes:
        meta = unit_meta.get(code)
        if meta is None:
            print(f"  WARNING: {code} not in reference table, using defaults")
            meta = {"description": code, "seq_nr": 9999, "r": 128, "g": 128, "b": 128}
        print(f"  {code:12s}  seq={meta['seq_nr']:3d}  {meta['description']}")
        convert_unit(code, meta, IMG_DIR, OUT_DIR)

    print("\nDone. Output in:", OUT_DIR)


if __name__ == "__main__":
    main()
