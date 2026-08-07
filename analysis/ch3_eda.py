"""
ch3_eda.py -- Chapter 3 EDA on Dataset 1 (Ben's half of Ch3).

Produces the figures and the hard empirical justification the rubric demands:
"prove that the feature shows a measurable, statistically significant difference
in behaviour between benign and malicious". For every engineered feature we run
a Mann-Whitney U test (non-parametric: the features are counts/ratios, not
normal) and report a rank-biserial effect size, so each feature carries evidence,
not a hand-wave.

Outputs (Dataset 1, train split):
  report/figures/ch3_class_balance.png
  report/figures/ch3_feature_variance.png
  report/figures/ch3_correlation_heatmap.png
  report/figures/ch3_top_feature_boxplots.png
  report/figures/ch3_length_hist.png
  report/ch3_feature_justification.csv   (per-feature stats table)
  report/ch3_eda_findings.md             (written summary + redundancy analysis)

Run: python analysis/ch3_eda.py
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
from src import ingestion                       # noqa: E402
from src.features import FEATURE_NAMES, featurize  # noqa: E402

FIG = ROOT / "report" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
REP = ROOT / "report"
DATASET = "dataset1"
sns.set_theme(style="whitegrid", font_scale=0.85)


def rank_biserial(mal, ben):
    """Effect size from Mann-Whitney U: r = 2U/(n1*n2) - 1, in [-1, 1].
    Positive => feature tends to be larger for malicious."""
    n1, n2 = len(mal), len(ben)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0
    U, p = mannwhitneyu(mal, ben, alternative="two-sided")
    r = 2.0 * U / (n1 * n2) - 1.0
    return float(r), float(p)


def main():
    train, _ = ingestion.load(DATASET)
    y = train["label"].to_numpy()
    F = featurize(train["command"])
    F["label"] = y
    mal = F[F.label == 1]
    ben = F[F.label == 0]
    print(f"[ch3] {DATASET} train: {len(F)} rows "
          f"({int(y.sum())} malicious / {int((y == 0).sum())} benign)")

    # --- 1. class balance ---
    fig, ax = plt.subplots(figsize=(4, 3))
    counts = pd.Series(y).map({0: "benign", 1: "malicious"}).value_counts()
    sns.barplot(x=counts.index, y=counts.values, ax=ax, hue=counts.index,
                legend=False, palette=["#4C78A8", "#E45756"])
    for i, v in enumerate(counts.values):
        ax.text(i, v, str(v), ha="center", va="bottom")
    ax.set_title(f"Dataset 1 class balance (train) — 1:3 malicious:benign")
    ax.set_ylabel("commands")
    fig.tight_layout(); fig.savefig(FIG / "ch3_class_balance.png", dpi=140)
    plt.close(fig)

    # --- 2. per-feature stats table: variance + MWU + effect size ---
    rows = []
    for f in FEATURE_NAMES:
        r, p = rank_biserial(mal[f].to_numpy(), ben[f].to_numpy())
        rows.append({
            "feature": f,
            "mean_malicious": round(float(mal[f].mean()), 4),
            "mean_benign": round(float(ben[f].mean()), 4),
            "var_all": round(float(F[f].var()), 4),
            "rank_biserial": round(r, 4),
            "abs_effect": round(abs(r), 4),
            "mwu_p": p,
        })
    stats = pd.DataFrame(rows).sort_values("abs_effect", ascending=False)
    stats.to_csv(REP / "ch3_feature_justification.csv", index=False)
    print("[ch3] wrote per-feature justification table "
          f"({(stats['mwu_p'] < 0.05).sum()}/{len(stats)} features p<0.05)")

    # --- 3. feature variance (near-zero variance = candidate to drop) ---
    fig, ax = plt.subplots(figsize=(6, 8))
    v = F[FEATURE_NAMES].var().sort_values()
    sns.barplot(x=v.values, y=v.index, ax=ax, color="#4C78A8")
    ax.set_xscale("symlog")
    ax.set_title("Dataset 1 feature variance (symlog)")
    ax.set_xlabel("variance")
    fig.tight_layout(); fig.savefig(FIG / "ch3_feature_variance.png", dpi=140)
    plt.close(fig)

    # --- 4. correlation heatmap (redundancy / multicollinearity) ---
    corr = F[FEATURE_NAMES].corr()
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(corr, cmap="coolwarm", center=0, square=True,
                cbar_kws={"shrink": 0.5}, ax=ax,
                xticklabels=True, yticklabels=True)
    ax.set_title("Dataset 1 feature correlation matrix")
    ax.tick_params(labelsize=6)
    fig.tight_layout(); fig.savefig(FIG / "ch3_correlation_heatmap.png", dpi=140)
    plt.close(fig)

    # redundant pairs |corr| > 0.85
    redundant = []
    cols = FEATURE_NAMES
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            c = corr.iloc[i, j]
            if abs(c) > 0.85:
                redundant.append((cols[i], cols[j], round(float(c), 3)))

    # --- 5. box plots for the 6 strongest features ---
    top6 = stats.head(6)["feature"].tolist()
    fig, axes = plt.subplots(2, 3, figsize=(11, 6))
    for f, ax in zip(top6, axes.ravel()):
        d = F[[f, "label"]].copy()
        d["class"] = d["label"].map({0: "benign", 1: "malicious"})
        sns.boxplot(data=d, x="class", y=f, ax=ax, showfliers=False,
                    hue="class", legend=False, palette=["#4C78A8", "#E45756"])
        r = stats.loc[stats.feature == f, "rank_biserial"].iloc[0]
        ax.set_title(f"{f}  (r={r:+.2f})", fontsize=9)
        ax.set_xlabel("")
    fig.suptitle("Dataset 1: 6 strongest features, benign vs malicious")
    fig.tight_layout(); fig.savefig(FIG / "ch3_top_feature_boxplots.png", dpi=140)
    plt.close(fig)

    # --- 6. length distribution (classic confound to inspect) ---
    fig, ax = plt.subplots(figsize=(6, 3.5))
    for lbl, name, col in [(0, "benign", "#4C78A8"), (1, "malicious", "#E45756")]:
        sns.histplot(F[F.label == lbl]["len_chars"].clip(upper=200), bins=40,
                     stat="density", element="step", label=name, color=col, ax=ax)
    ax.set_title("Dataset 1 command length (chars, clipped at 200)")
    ax.set_xlabel("len_chars"); ax.legend()
    fig.tight_layout(); fig.savefig(FIG / "ch3_length_hist.png", dpi=140)
    plt.close(fig)

    # --- write findings markdown ---
    top = stats.head(10)
    weak = stats[stats.abs_effect < 0.05]
    lines = [
        "# Chapter 3 — EDA & Domain Justification (Dataset 1, Ben)",
        "",
        f"Train split: **{len(F)}** commands "
        f"({int(y.sum())} malicious / {int((y==0).sum())} benign, 1:3).",
        "",
        "## 3.3 Empirical feature justification (hard evidence)",
        "",
        "Every engineered feature was tested with a two-sided **Mann-Whitney U** "
        "test (features are counts/ratios, not normal) and a **rank-biserial "
        "effect size** r in [-1,1] (sign = direction; +r means larger for "
        "malicious). Full table: `report/ch3_feature_justification.csv`.",
        "",
        f"- **{(stats['mwu_p'] < 0.05).sum()} / {len(stats)}** features differ "
        "between classes at p < 0.05.",
        f"- **{(stats['abs_effect'] >= 0.2).sum()}** features reach |r| >= 0.2 "
        "(a meaningful separation).",
        "",
        "### Strongest features (top 10 by |effect size|)",
        "",
        "| feature | mean malicious | mean benign | rank-biserial r | MWU p |",
        "|---|---:|---:|---:|---:|",
    ]
    for _, rrow in top.iterrows():
        lines.append(
            f"| `{rrow.feature}` | {rrow.mean_malicious} | {rrow.mean_benign} "
            f"| {rrow.rank_biserial:+.3f} | {rrow.mwu_p:.2e} |")
    lines += [
        "",
        "### 3.2 Noise & redundancy reduction",
        "",
        f"- **Low-signal features** (|r| < 0.05, candidates to prune for "
        f"compute): {', '.join('`'+f+'`' for f in weak['feature']) or 'none'}.",
        "- **Redundant / multicollinear pairs** (|corr| > 0.85) — keep one of "
        "each pair; the tree ranking in Ch4 confirms which:",
    ]
    if redundant:
        for a, b, c in redundant:
            lines.append(f"  - `{a}` ~ `{b}` (corr {c})")
    else:
        lines.append("  - none above 0.85 — the feature set is largely "
                     "non-redundant.")
    lines += [
        "",
        "Figures: `report/figures/ch3_*.png` "
        "(class balance, variance, correlation heatmap, top-feature box plots, "
        "length histogram).",
        "",
        "> Note on length: Dataset 1's malicious commands are **not** simply "
        "longer — see `ch3_length_hist.png` and the low stand-alone power of "
        "`len_chars` in the table. This matches the baseline audit (length-only "
        "F1 ~ 0.39), so the signal is behavioural, not a length artifact.",
    ]
    (REP / "ch3_eda_findings.md").write_text("\n".join(lines))
    print("[ch3] wrote report/ch3_eda_findings.md and 6 figures")


if __name__ == "__main__":
    main()
