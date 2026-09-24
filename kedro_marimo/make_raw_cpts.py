# /// script
# requires-python = ">=3.13"
# dependencies = ["numpy", "pandas>=3.0"]
# ///
"""Write a tiny synthetic raw CPT table to `data/01_raw/cpts.csv`.

Three CPTs, 0 to 12 m at 0.1 m, through sand over clay over peat over sand,
with a few negative, missing and repeated readings for the cleaning step to
remove. Deterministic (fixed seed), so the committed CSV can be regenerated.
"""

from pathlib import Path

import numpy as np
import pandas as pd

# (top [m], qc [MPa], Rf [%], u2 [MPa per m depth]) per layer
LAYERS = [
    (0.0, 8.0, 0.6, 0.002),  # sand
    (3.0, 0.8, 3.5, 0.030),  # clay
    (6.5, 0.2, 8.0, 0.020),  # peat
    (7.5, 14.0, 0.5, 0.004),  # dense sand
]


def make_raw_cpts(seed: int = 42) -> pd.DataFrame:
    """Return a synthetic raw CPT table with some bad readings."""
    rng = np.random.default_rng(seed)
    frames = []
    for i, shift in enumerate([0.0, 0.4, -0.3]):
        depth = np.round(np.arange(0.0, 12.0, 0.1), 2)
        tops = np.array([top for top, *_ in LAYERS]) + shift
        layer = np.clip(np.searchsorted(tops, depth, side="right") - 1, 0, None)
        qc = np.array([LAYERS[k][1] for k in layer]) * rng.lognormal(0, 0.15, depth.size)
        rf = np.array([LAYERS[k][2] for k in layer]) * rng.lognormal(0, 0.1, depth.size)
        u2 = np.array([LAYERS[k][3] for k in layer]) * depth
        frames.append(
            pd.DataFrame(
                {
                    "cpt_id": f"CPT{i + 1:02d}",
                    "depth": depth,
                    "qc": qc.round(3),
                    "fs": (qc * rf / 100).round(4),
                    "u2": u2.round(4),
                }
            )
        )
    raw = pd.concat(frames, ignore_index=True)
    # Bad readings for the cleaning step.
    raw.loc[[5, 130, 250], "qc"] = -0.05
    raw.loc[[40, 300], "fs"] = np.nan
    raw.loc[[77], "u2"] = np.nan
    raw = pd.concat([raw, raw.iloc[[10, 200]]], ignore_index=True)
    return raw


if __name__ == "__main__":
    out = Path(__file__).parent / "data" / "01_raw" / "cpts.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    raw = make_raw_cpts()
    raw.to_csv(out, index=False)
    print(f"wrote {len(raw)} rows to {out}")
