"""
ch4_ranking.py -- Chapter 4 tree-based feature ranking (Ben's code + chart).

Lets a tree ensemble score the engineered features so Ch4 can reconcile the
algorithmic ranking against the Ch3 domain intuition, and Noam can write the
discrepancy analysis (leakage / multicollinearity / latent-pattern).

We report THREE importance views per dataset because MDI (Gini) is biased toward
high-cardinality features -- a leakage magnet -- and the assignment explicitly
asks us to check for that:
  * Random Forest MDI (mean decrease in impurity)
  * XGBoost gain importance
  * Permutation importance on a held-out split (model-agnostic, unbiased)

Outputs:
  report/figures/ch4_ranking_dataset1.png / _dataset2.png  (horizontal bars)
  report/ch4_feature_ranking.csv        (all three scores, both datasets)
  report/ch4_ranking_notes.md           (intuition-vs-ranking seed for Noam)

Run: python analysis/ch4_ranking.py
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
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import SEED, ingestion                    # noqa: E402
from src.features import FEATURE_NAMES, featurize   # noqa: E402

FIG = ROOT / "report" / "figures"
REP = ROOT / "report"
sns.set_theme(style="whitegrid", font_scale=0.8)


def rankings_for(dataset: str) -> pd.DataFrame:
    train, _ = ingestion.load(dataset)
    X = featurize(train["command"]).to_numpy(dtype=float)
    y = train["label"].to_numpy()
    Xtr, Xva, ytr, yva = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=SEED)

    # RF MDI
    rf = RandomForestClassifier(n_estimators=400, max_depth=24,
                                class_weight="balanced_subsample",
                                n_jobs=-1, random_state=SEED).fit(Xtr, ytr)
    mdi = rf.feature_importances_

    # permutation importance (unbiased, on the held-out split)
    perm = permutation_importance(rf, Xva, yva, n_repeats=10,
                                  random_state=SEED, n_jobs=-1).importances_mean

    # XGBoost gain
    from xgboost import XGBClassifier
    xgb = XGBClassifier(n_estimators=400, max_depth=6, learning_rate=0.1,
                        subsample=0.9, colsample_bytree=0.9,
                        scale_pos_weight=3.0, eval_metric="logloss",
                        tree_method="hist", random_state=SEED).fit(Xtr, ytr)
    gain = xgb.feature_importances_

    df = pd.DataFrame({
        "feature": FEATURE_NAMES,
        "rf_mdi": mdi,
        "xgb_gain": gain,
        "permutation": perm,
    })
    # consensus rank = mean of per-view ranks (1 = most important)
    for col in ("rf_mdi", "xgb_gain", "permutation"):
        df[col + "_rank"] = df[col].rank(ascending=False)
    df["consensus_rank"] = df[[c + "_rank" for c in
                               ("rf_mdi", "xgb_gain", "permutation")]].mean(axis=1)
    df["dataset"] = dataset
    return df.sort_values("consensus_rank")


def plot(df: pd.DataFrame, dataset: str):
    top = df.sort_values("rf_mdi", ascending=True).tail(20)
    fig, ax = plt.subplots(figsize=(7, 8))
    ax.barh(top["feature"], top["rf_mdi"], color="#4C78A8")
    ax.set_title(f"{dataset}: Random Forest feature importance (MDI, top 20)")
    ax.set_xlabel("mean decrease in impurity")
    fig.tight_layout()
    fig.savefig(FIG / f"ch4_ranking_{dataset}.png", dpi=140)
    plt.close(fig)


def main():
    frames = []
    for ds in ingestion.available_datasets():
        df = rankings_for(ds)
        plot(df, ds)
        frames.append(df)
        top5 = df.head(5)["feature"].tolist()
        print(f"[ch4] {ds}: top-5 consensus features = {top5}")
    alldf = pd.concat(frames, ignore_index=True)
    alldf.to_csv(REP / "ch4_feature_ranking.csv", index=False)

    # seed the discrepancy notes (Noam expands into the Ch4 essay)
    d1 = frames[0]
    lines = [
        "# Chapter 4 — Tree-based feature ranking (Ben's code + chart)",
        "",
        "Three importance views per dataset (RF MDI, XGBoost gain, permutation "
        "on held-out split). Full scores: `report/ch4_feature_ranking.csv`. "
        "Charts: `report/figures/ch4_ranking_dataset{1,2}.png`.",
        "",
        "Permutation importance is included specifically because MDI is biased "
        "toward high-cardinality features (a leakage magnet); where MDI and "
        "permutation disagree sharply, Ch4's discrepancy analysis (Noam) should "
        "look for a leakage or multicollinearity cause.",
        "",
        "## Dataset 1 — top 10 by consensus rank",
        "",
        "| rank | feature | RF MDI | XGB gain | permutation |",
        "|---:|---|---:|---:|---:|",
    ]
    for i, (_, r) in enumerate(d1.head(10).iterrows(), 1):
        lines.append(f"| {i} | `{r.feature}` | {r.rf_mdi:.4f} | "
                     f"{r.xgb_gain:.4f} | {r.permutation:.4f} |")
    lines += [
        "",
        "**For the intuition-vs-ranking reconciliation (cross-ref Ch3):** the "
        "Ch3 top features by effect size were `special_ratio`, `max_token_len`, "
        "`char_entropy`, `n_redirects`, `len_chars`, `digit_ratio`. Compare "
        "against the tree ranking above and flag: (a) features the trees rank "
        "high that Ch3 rated weak (possible latent pattern or leakage), "
        "(b) domain features Ch3 rated strong that the trees ignore (possible "
        "multicollinearity — a correlated feature absorbed the signal).",
    ]
    (REP / "ch4_ranking_notes.md").write_text("\n".join(lines))
    print("[ch4] wrote report/ch4_feature_ranking.csv + ch4_ranking_notes.md")


if __name__ == "__main__":
    main()
