"""
ch3_eda_figures.py -- regenerate the per-dataset Ch3 EDA figures on the FINAL
43-feature set (both datasets).

The dataset-suffixed Ch3 figures (ch3_length_hist_*, ch3_variance_by_label_*,
ch3_corr_heatmap_*) were originally produced ad hoc (commit 9b58ddb) on the old
38-feature featurize() and their generator was never committed. This script is
that generator, committed and parameterised, running on the current
src/features.py. It writes FIGURES ONLY -- it never touches any findings
markdown (ch3_eda.py owns report/ch3_eda_findings.md).

One deliberate change from the originals: the variance-by-label chart uses a
symlog y-axis (same convention as ch3_eda.py's variance figure). On a linear
axis char_count's variance (~10^4) flattens every other bar to invisible.

Outputs, per dataset:
  report/figures/ch3_length_hist_<dataset>.png
  report/figures/ch3_variance_by_label_<dataset>.png
  report/figures/ch3_corr_heatmap_<dataset>.png
Plus the per-feature evidence table for the Dataset 2 write-up:
  report/ch3_d2_feature_stats.csv

Run: python analysis/ch3_eda_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                           # noqa: E402
from src.features import FEATURE_NAMES, featurize   # noqa: E402

FIG = ROOT / "report" / "figures"
REP = ROOT / "report"
sns.set_theme(style="whitegrid", font_scale=0.85)

# Okabe-Ito benign/attack pair (colorblind-safe, validated)
C_BENIGN, C_ATTACK = "#0072B2", "#E69F00"


def rank_biserial(mal, ben):
    n1, n2 = len(mal), len(ben)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    U, p = mannwhitneyu(mal, ben, alternative="two-sided")
    return float(2.0 * U / (n1 * n2) - 1.0), float(p)


def length_hist(ds, train):
    lengths = train["command"].str.len()
    y = train["label"].to_numpy()
    hi = float(np.quantile(lengths, 0.99))
    fig, ax = plt.subplots(figsize=(6.4, 4))
    for label, color, name in ((0, C_BENIGN, "benign (0)"),
                               (1, C_ATTACK, "attack (1)")):
        ax.hist(lengths[y == label].clip(upper=hi), bins=60, range=(0, hi),
                density=True, alpha=0.65, color=color, label=name)
    ax.set_xlabel("command length (chars)")
    ax.set_ylabel("density")
    ax.set_title(f"Command length by label — {ds} (clipped at p99)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / f"ch3_length_hist_{ds}.png", dpi=140)
    plt.close(fig)


def variance_by_label(ds, F):
    mal = F[F.label == 1][FEATURE_NAMES].var()
    ben = F[F.label == 0][FEATURE_NAMES].var()
    top = (mal - ben).abs().sort_values(ascending=False).head(15).index
    x = np.arange(len(top))
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    ax.bar(x - 0.2, ben[top], width=0.4, color=C_BENIGN, label="benign var")
    ax.bar(x + 0.2, mal[top], width=0.4, color=C_ATTACK, label="attack var")
    ax.set_yscale("symlog", linthresh=0.01)
    ax.set_xticks(x)
    ax.set_xticklabels(top, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("variance (symlog)")
    ax.set_title(f"Per-feature variance by label (top 15 gap) — {ds}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / f"ch3_variance_by_label_{ds}.png", dpi=140)
    plt.close(fig)


def corr_heatmap(ds, F):
    corr = F[FEATURE_NAMES].corr()
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(corr, cmap="coolwarm", center=0, vmin=-1, vmax=1, square=True,
                cbar_kws={"shrink": 0.5}, ax=ax,
                xticklabels=True, yticklabels=True)
    ax.set_title(f"Feature correlation — {ds}")
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(FIG / f"ch3_corr_heatmap_{ds}.png", dpi=140)
    plt.close(fig)


def d2_stats_table(F):
    mal = F[F.label == 1]
    ben = F[F.label == 0]
    rows = []
    for f in FEATURE_NAMES:
        r, p = rank_biserial(mal[f].to_numpy(), ben[f].to_numpy())
        rows.append({"feature": f,
                     "mean_malicious": round(float(mal[f].mean()), 4),
                     "mean_benign": round(float(ben[f].mean()), 4),
                     "var_malicious": round(float(mal[f].var()), 4),
                     "var_benign": round(float(ben[f].var()), 4),
                     "rank_biserial": round(r, 4),
                     "abs_effect": round(abs(r), 4),
                     "mwu_p": p})
    stats = pd.DataFrame(rows).sort_values("abs_effect", ascending=False)
    stats.to_csv(REP / "ch3_d2_feature_stats.csv", index=False)
    n_sig = int((stats["mwu_p"] < 0.05).sum())
    print(f"[ch3-fig] dataset2 evidence table: {n_sig}/{len(stats)} features "
          f"p<0.05; top effect {stats.iloc[0]['feature']} "
          f"(r={stats.iloc[0]['rank_biserial']:+.3f})")


def main():
    for ds in ingestion.available_datasets():
        train, _ = ingestion.load(ds)
        F = featurize(train["command"])
        F["label"] = train["label"].to_numpy()
        print(f"[ch3-fig] {ds}: {len(F)} rows, {len(FEATURE_NAMES)} features")
        length_hist(ds, train)
        variance_by_label(ds, F)
        corr_heatmap(ds, F)
        if ds == "dataset2":
            d2_stats_table(F)
    print("[ch3-fig] wrote 6 figures + report/ch3_d2_feature_stats.csv")


if __name__ == "__main__":
    main()
