"""
3D visualisation of BRO Digitaal Geologisch Model (DGM) using PyVista.

Each geological formation's top surface is rendered as a coloured 3D mesh
using the official DGM legend colours (from REF_DGM_STR_UNIT.xlsx).
Formations are drawn deepest-first so shallower units paint on top.

Usage:
    uv run python src/visualize_dgm.py [--scale N] [--vert-exag V] [--opacity O]
        --scale N       downsample factor (default 8 → ~350×406 grid)
        --vert-exag V   vertical exaggeration (default 20)
        --opacity O     surface opacity 0-1 (default 0.8)
"""

import argparse
from pathlib import Path

import numpy as np
import openpyxl
import pyvista as pv
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

COG_DIR = Path("data/brodgm/cog")
REF_XLSX = Path(
    "data/brodgm/Model_DGM000000000022/DGM_v02r2s1/basisdata/REF_DGM_STR_UNIT.xlsx"
)

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def load_unit_metadata(xlsx_path: Path) -> dict[str, dict]:
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    units = {}
    for row in ws.iter_rows(values_only=True):
        if row[0] == "STR_UNIT_CD":
            continue
        code, desc, seq, r, g, b = row
        units[str(code)] = dict(
            description=desc, seq_nr=int(seq), r=int(r), g=int(g), b=int(b)
        )
    return units


# ---------------------------------------------------------------------------
# Raster reading
# ---------------------------------------------------------------------------


def read_surface(cog_path: Path, band: int = 1, scale: int = 8):
    """Read one band at reduced resolution.

    Returns (z, x1d, y1d, nodata) where z has shape (ny, nx),
    x1d increases east, y1d increases south (raster convention).
    """
    with rasterio.open(cog_path) as src:
        h = max(2, src.height // scale)
        w = max(2, src.width // scale)
        z = src.read(band, out_shape=(h, w), resampling=Resampling.average).astype(
            np.float64
        )
        nodata = src.nodata
        # Pixel-centre coordinates for the downsampled grid
        t: Affine = src.transform * Affine.scale(src.width / w, src.height / h)
        x1d = t.c + (np.arange(w) + 0.5) * t.a  # t.a > 0 → east
        y1d = t.f + (np.arange(h) + 0.5) * t.e  # t.e < 0 → south
    return z, x1d, y1d, nodata


# ---------------------------------------------------------------------------
# Mesh construction
# ---------------------------------------------------------------------------


def make_surface_mesh(
    z: np.ndarray,
    x1d: np.ndarray,
    y1d: np.ndarray,
    nodata: float,
    vert_exag: float,
) -> pv.UnstructuredGrid | None:
    """Build a masked PyVista surface from a 2D elevation array.

    nodata cells are removed so formations with partial coverage
    (e.g. chalk only in south NL) show their natural outline.
    """
    z = z.copy()
    if nodata is not None:
        z[z < -1e30] = np.nan  # -3.4e38 sentinel → NaN
    if np.all(np.isnan(z)):
        return None

    ny, nx = z.shape
    xx, yy = np.meshgrid(x1d, y1d)  # shape (ny, nx)

    valid = (~np.isnan(z)).astype(np.float32)
    z[np.isnan(z)] = 0.0  # NaN in coords crashes VTK

    grid = pv.StructuredGrid(xx, yy, z * vert_exag)

    # PyVista StructuredGrid from (ny, nx) arrays uses F-order point indexing
    grid.point_data["valid"] = valid.ravel(order="F")

    result = grid.threshold(0.5, scalars="valid")
    return result if result.n_cells > 0 else None


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------


def build_scene(
    scale: int,
    vert_exag: float,
    opacity: float,
) -> pv.Plotter:
    # Disable MSAA and smooth-shading to avoid VTK crashes on macOS/Metal
    pv.global_theme.multi_samples = 1

    print("Loading unit metadata …")
    unit_meta = load_unit_metadata(REF_XLSX)

    # Deepest (highest seq_nr) first → painter's order so shallow covers deep
    ordered = sorted(unit_meta.items(), key=lambda kv: -kv[1]["seq_nr"])

    pl = pv.Plotter(window_size=(1400, 900))
    pl.set_background("#1a1a2e")  # dark background shows colours well

    n_loaded = 0
    for code, meta in ordered:
        cog_path = COG_DIR / f"{code}.tif"
        if not cog_path.exists():
            continue

        print(f"  {code:12s}  seq={meta['seq_nr']:3d}  {meta['description']}")
        z, x1d, y1d, nodata = read_surface(cog_path, band=1, scale=scale)
        mesh = make_surface_mesh(z, x1d, y1d, nodata, vert_exag)
        if mesh is None:
            print("    → (empty, skipped)")
            continue

        color = (meta["r"] / 255.0, meta["g"] / 255.0, meta["b"] / 255.0)
        pl.add_mesh(
            mesh,
            color=color,
            opacity=opacity,
            smooth_shading=False,
            show_scalar_bar=False,
            label=f"{code}  {meta['description']}",
        )
        n_loaded += 1

    # Maaiveld (ground surface) as a semi-transparent reference
    mv_path = COG_DIR / "mv.tif"
    if mv_path.exists():
        print("  mv            ground surface (maaiveld)")
        z_mv, x1d, y1d, nodata = read_surface(mv_path, band=1, scale=scale)
        mv_mesh = make_surface_mesh(z_mv, x1d, y1d, nodata, vert_exag)
        if mv_mesh is not None:
            pl.add_mesh(
                mv_mesh,
                color=(0.6, 0.78, 0.6),
                opacity=0.35,
                smooth_shading=False,
                label="mv  Maaiveld",
            )

    print(f"\n{n_loaded} formation surfaces loaded.")

    pl.add_text(
        "BRO Digitaal Geologisch Model — formation tops\n"
        f"Vertical exaggeration ×{vert_exag:.0f}  |  RD New (EPSG:28992)",
        position="upper_left",
        font_size=10,
        color="white",
    )
    pl.add_axes(line_width=3, color="white")

    # Legend (scrollable if many entries)
    pl.add_legend(
        size=(0.22, 0.80),
        loc="lower right",
        background_opacity=0.6,
        face="rectangle",
    )

    return pl


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scale", type=int, default=8, help="Downsample factor (default 8)"
    )
    parser.add_argument(
        "--vert-exag",
        type=float,
        default=20.0,
        help="Vertical exaggeration (default 20)",
    )
    parser.add_argument(
        "--opacity", type=float, default=0.8, help="Surface opacity 0–1 (default 0.8)"
    )
    args = parser.parse_args()

    pl = build_scene(
        scale=args.scale,
        vert_exag=args.vert_exag,
        opacity=args.opacity,
    )
    pl.show()


if __name__ == "__main__":
    main()
