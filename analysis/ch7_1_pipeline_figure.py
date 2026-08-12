"""
ch7_1_pipeline_figure.py -- render the Chapter 7.1 pipeline block diagram.

report/ch7_pipeline_diagram.md holds the same diagram as a Mermaid block, which
is readable on GitHub but cannot be placed in the .docx. This script renders the
identical topology to a PNG so the rubric-required architecture figure is a
committed artefact produced by code, not a screenshot from a web renderer.

Thresholds are read from the shipped defaults so the figure cannot drift from
the implementation: CascadeDetector(stage2_uncertain=(0.35, 0.65)) in
src/ensemble.py, passed explicitly at analysis/ch8_4_cascade.py:63. The stage-1
cut is deliberately not a number -- stage1_retain_recall=0.99 overwrites it at
fit() time with the 1st-percentile anomaly score of the training attacks
(src/ensemble.py:52-60), so the node names a calibrated threshold instead.

Usage:
    python analysis/ch7_1_pipeline_figure.py
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.ensemble import CascadeDetector               # noqa: E402

OUT = ROOT / "report" / "figures" / "ch7_pipeline.png"

STAGE = dict(fc="#e7f0fb", ec="#2a6fb0")
DECIDE = dict(fc="#fdf3d8", ec="#c8a02c")
ATTACK = dict(fc="#f8d7da", ec="#c0392b")
BENIGN = dict(fc="#d4edda", ec="#27ae60")
INPUT = dict(fc="#ececec", ec="#666666")


def _band() -> tuple[float, float]:
    """The shipped (low, high) stage-2 uncertainty band, read from the source."""
    lo, hi = inspect.signature(CascadeDetector).parameters["stage2_uncertain"].default
    return float(lo), float(hi)


def _box(ax, xy, w, h, text, style, fontsize=9, weight="normal"):
    x, y = xy
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        linewidth=1.4, zorder=2, **style))
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            weight=weight, zorder=3, linespacing=1.45)


def _arrow(ax, a, b, label=None, label_dx=0.0, label_dy=0.0, fontsize=7.6):
    ax.add_patch(FancyArrowPatch(
        a, b, arrowstyle="-|>", mutation_scale=11, linewidth=1.1,
        color="#444444", shrinkA=0, shrinkB=0, zorder=1))
    if label:
        mx, my = (a[0] + b[0]) / 2 + label_dx, (a[1] + b[1]) / 2 + label_dy
        ax.text(mx, my, label, ha="center", va="center", fontsize=fontsize,
                color="#222222", zorder=4,
                bbox=dict(boxstyle="round,pad=0.16", fc="white",
                          ec="none", alpha=0.92))


def main() -> None:
    lo, hi = _band()

    fig, ax = plt.subplots(figsize=(8.4, 8.0), dpi=220)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 11.6)
    ax.axis("off")

    _box(ax, (6.0, 11.10), 4.4, 0.62, "Raw shell command string", INPUT)

    _box(ax, (6.0, 9.90), 5.0, 0.80,
         "Stage 1 · Isolation Forest\n(unsupervised anomaly score)", STAGE)
    _box(ax, (6.0, 8.60), 4.0, 0.72,
         "score below calibrated\nthreshold?", DECIDE, fontsize=8.6)
    _box(ax, (1.80, 8.60), 3.0, 0.72,
         "BENIGN — cleared\n(bulk benign filter)", BENIGN, fontsize=8.4)

    _box(ax, (6.0, 7.30), 5.0, 0.80,
         "Stage 2 · XGBoost-hybrid\nP(attack)", STAGE)
    _box(ax, (6.0, 6.10), 2.4, 0.60, "P(attack)?", DECIDE)

    _box(ax, (1.50, 5.00), 2.6, 0.74,
         "BENIGN\n(high confidence)", BENIGN, fontsize=8.4)
    _box(ax, (10.50, 5.00), 2.6, 0.74,
         "ATTACK\n(high confidence)", ATTACK, fontsize=8.4)

    _box(ax, (6.0, 4.30), 4.6, 0.80,
         "Stage 3 · LLM arbitration\n(Llama 3.1-8B)", STAGE)
    _box(ax, (6.0, 3.05), 2.4, 0.60, "final verdict", DECIDE)
    _box(ax, (4.00, 1.85), 2.2, 0.66, "BENIGN", BENIGN, fontsize=8.6)
    _box(ax, (8.00, 1.85), 2.2, 0.66, "ATTACK", ATTACK, fontsize=8.6)

    _arrow(ax, (6.0, 10.79), (6.0, 10.30))
    _arrow(ax, (6.0, 9.50), (6.0, 8.96))
    _arrow(ax, (4.00, 8.60), (3.30, 8.60), "yes", label_dy=0.26)
    _arrow(ax, (6.0, 8.24), (6.0, 7.70), "no (anomalous)", label_dx=1.42)

    _arrow(ax, (6.0, 6.90), (6.0, 6.40))
    _arrow(ax, (4.80, 6.10), (2.40, 5.37),
           f"0.00 – {lo:.2f}", label_dy=0.28)
    _arrow(ax, (7.20, 6.10), (9.60, 5.37),
           f"{hi:.2f} – 1.00", label_dy=0.28)
    _arrow(ax, (6.0, 5.80), (6.0, 4.70),
           f"{lo:.2f} – {hi:.2f}\n(edge case)", label_dx=1.10)

    _arrow(ax, (6.0, 3.90), (6.0, 3.35))
    _arrow(ax, (4.80, 3.05), (4.30, 2.18), "benign",
           label_dx=-0.52, label_dy=0.12)
    _arrow(ax, (7.20, 3.05), (7.70, 2.18), "malicious",
           label_dx=0.58, label_dy=0.12)

    ax.text(6.0, 0.85,
            "Stage-1 threshold is calibrated, not fixed: stage1_retain_recall=0.99 sets it to the\n"
            "1st-percentile anomaly score of the training attacks at fit() time (src/ensemble.py:52-60).",
            ha="center", va="center", fontsize=7.0, style="italic", color="#555555",
            linespacing=1.5)

    fig.tight_layout(pad=0.3)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {OUT} (band read from source: {lo} / {hi})")


if __name__ == "__main__":
    main()
