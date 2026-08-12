"""Ch8.2 — cross-dataset transfer heat-map.

Reads `results/ch8_cross_dataset.json` (written by `analysis/ch8_error_analysis.py`)
and renders the 5 x 4 train/test F1 grid the chapter cites. No model is
re-fitted here, so the figure cannot drift from the numbers in the table: both
read the same file.

Writes: report/figures/ch8_transfer_heatmap.png
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                             # noqa: E402
import numpy as np                                          # noqa: E402
import seaborn as sns                                       # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "results" / "ch8_cross_dataset.json"
OUT = ROOT / "report" / "figures" / "ch8_transfer_heatmap.png"

# Row order = in-domain leaderboard, so the eye reads the collapse top-to-bottom.
MODELS = ["xgboost_hybrid", "cnn1d", "random_forest", "xgboost",
          "isolation_forest"]
CELLS = [("dataset1", "dataset1", "D1 → D1\n(in-domain)"),
         ("dataset2", "dataset2", "D2 → D2\n(in-domain)"),
         ("dataset1", "dataset2", "D1 → D2\n(cross)"),
         ("dataset2", "dataset1", "D2 → D1\n(cross)")]

# 1:3 attack:benign => flag-everything scores F1 = 0.400 (see Ch. 3).
DO_NOTHING_F1 = 0.400


def main() -> None:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    grid = np.array([[data[f"{m}|train={tr}|test={te}"]["f1"]
                      for tr, te, _ in CELLS] for m in MODELS])

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    sns.heatmap(grid, annot=True, fmt=".3f", cmap="RdYlGn", vmin=0.0, vmax=1.0,
                linewidths=0.6, linecolor="white",
                xticklabels=[lbl for _, _, lbl in CELLS],
                yticklabels=MODELS, cbar_kws={"label": "F1"}, ax=ax)
    # Separate the in-domain block from the two transfer columns.
    ax.axvline(2, color="black", lw=2.5)
    ax.set_title(f"Cross-dataset transfer (F1); do-nothing floor = "
                 f"{DO_NOTHING_F1:.3f}")
    ax.tick_params(axis="y", rotation=0)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")

    below = [(m, lbl, grid[i, j])
             for i, m in enumerate(MODELS)
             for j, (_, _, lbl) in enumerate(CELLS)
             if grid[i, j] < DO_NOTHING_F1]
    print(f"cells below the {DO_NOTHING_F1} floor: {len(below)} / {grid.size}")


if __name__ == "__main__":
    main()
