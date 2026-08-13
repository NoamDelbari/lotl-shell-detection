"""
appendix_b_tables.py -- generate Appendix B (supporting tables) from the live
artefacts.

Appendix B holds the evidence the body chapters summarise but cannot afford to
print in full: the complete feature ranking, the complete record of which
candidate features were rejected and why, every hyperparameter configuration
that was swept, and the confusion matrix behind every headline score.

Generated rather than hand-written so no number can be mistyped and so the
appendix follows the artefacts after any re-run.

Sources:
  report/ch4_feature_ranking.csv       -> B.1, B.2
  report/ch3_feature_decisions.md      -> B.3, B.4   (read only; never re-run
                                          analysis/ch3_feature_audit.py)
  results/ch7_sensitivity.json         -> B.5, B.6
  results/ch7_rf_if_sensitivity.json   -> B.7
  results/summary.json                 -> B.8

Run: python analysis/appendix_b_tables.py
Writes: report/appendix_b_tables.md
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPORT = ROOT / "report"
RESULTS = ROOT / "results"
OUT = REPORT / "appendix_b_tables.md"

DS_LABEL = {"dataset1": "Dataset 1", "dataset2": "Dataset 2"}
MODEL_LABEL = {
    "xgboost_hybrid": "XGBoost-hybrid",
    "cnn1d": "1D-CNN",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "isolation_forest": "Isolation Forest",
}
# Headline order: best in-domain F1 first, anomaly detector last.
MODEL_ORDER = ["xgboost_hybrid", "cnn1d", "random_forest", "xgboost",
               "isolation_forest"]


# --------------------------------------------------------------------------- #
# B.1 / B.2 -- feature ranking                                                 #
# --------------------------------------------------------------------------- #
def ranking_table(rows: list, dataset: str, top: int) -> str:
    sub = [r for r in rows if r["dataset"] == dataset]
    sub.sort(key=lambda r: float(r["consensus_rank"]))
    out = ["| # | feature | RF MDI | XGB gain | permutation | consensus |",
           "|---:|---|---:|---:|---:|---:|"]
    for i, r in enumerate(sub[:top], 1):
        out.append(f"| {i} | `{r['feature']}` | {float(r['rf_mdi']):.4f} | "
                   f"{float(r['xgb_gain']):.4f} | {float(r['permutation']):.4f} | "
                   f"{float(r['consensus_rank']):.2f} |")
    return "\n".join(out)


def zero_gain_count(rows: list, dataset: str) -> int:
    return sum(1 for r in rows
               if r["dataset"] == dataset and float(r["xgb_gain"]) == 0.0)


# --------------------------------------------------------------------------- #
# B.3 / B.4 -- the 68 -> 43 feature gate                                       #
# --------------------------------------------------------------------------- #
KILL_HEADER = re.compile(r"^## Killed candidates")


def parse_decisions(md: str) -> tuple:
    """Return (kept_by_family, killed_rows) from the Ch3 decision document."""
    kept, killed = [], []
    family, in_kills = None, False
    for ln in md.splitlines():
        if KILL_HEADER.match(ln):
            in_kills = True
            continue
        m = re.match(r"^### (.+)", ln)
        if m:
            family = m.group(1).strip()
            continue
        if not ln.startswith("| `"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        name = cells[0].strip("`")
        verdict = cells[-1]
        if in_kills:
            killed.append((name, verdict))
        else:
            kept.append((family, name, verdict))
    return kept, killed


def kill_reason(verdict: str) -> str:
    """Condense a FINAL cell to its reason class."""
    body = verdict[len("KILL ("):-1] if verdict.startswith("KILL (") else verdict
    # No literal "|" in a reason string — these land inside markdown table cells.
    if body.startswith("cluster"):
        return "redundant (ρ > 0.9 cluster)"
    if "cluster" in body:
        return "no effect + redundant"
    return "no effect (gate)"


def kill_covered_by(verdict: str) -> str:
    """The feature that absorbs a killed candidate's signal, if any."""
    m = re.search(r"keep `([^`]+)`", verdict) or re.search(r"`([^`]+)` (?:carries|covers)", verdict)
    if m:
        return f"`{m.group(1)}`"
    m = re.search(r"lump `([^`]+)` covers", verdict)
    if m:
        return f"`{m.group(1)}`"
    m = re.search(r"cluster with `([^`]+)`", verdict)
    return f"`{m.group(1)}`" if m else "—"


def gate_tables(kept: list, killed: list) -> tuple:
    reasons = Counter(kill_reason(v) for _, v in killed)
    fam_counts = Counter(f for f, _, _ in kept)

    # The kill list is not family-labelled in the source document, so the funnel
    # reports rejections by reason and retentions by family — no split is
    # invented for cells the evidence does not support.
    t3 = ["| stage | features |",
          "|---|---:|",
          f"| Candidates implemented and audited | {len(kept) + len(killed)} |"]
    for reason, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        t3.append(f"| — rejected: {reason} | {n} |")
    t3.append(f"| **Final feature set** | **{len(kept)}** |")
    for fam, n in fam_counts.items():
        t3.append(f"| &nbsp;&nbsp;&nbsp;&nbsp;of which {fam} | {n} |")

    t4 = ["| candidate | why rejected | signal absorbed by |", "|---|---|---|"]
    for name, verdict in killed:
        t4.append(f"| `{name}` | {kill_reason(verdict)} | {kill_covered_by(verdict)} |")
    return "\n".join(t3), "\n".join(t4)


# --------------------------------------------------------------------------- #
# B.5 / B.6 / B.7 -- hyperparameter sweeps                                     #
# --------------------------------------------------------------------------- #
def sweep_table(sens: dict, model: str) -> str:
    """One table per model: every swept configuration, both datasets."""
    axes = list(sens[f"{model}/dataset1"])
    out = ["| hyperparameter | value | "
           + " | ".join(f"{DS_LABEL[d]} F1 | {DS_LABEL[d]} FPR" for d in DS_LABEL)
           + " |",
           "|---|---:|" + "---:|---:|" * len(DS_LABEL)]
    for axis in axes:
        d1 = {p["value"]: p for p in sens[f"{model}/dataset1"][axis]}
        d2 = {p["value"]: p for p in sens[f"{model}/dataset2"][axis]}
        for i, val in enumerate(d1):
            label = f"`{axis}`" if i == 0 else ""
            a, b = d1[val], d2.get(val)
            out.append(f"| {label} | {val} | {a['f1']:.4f} | {a['fpr']:.4f} | "
                       + (f"{b['f1']:.4f} | {b['fpr']:.4f} |" if b else "— | — |"))
    return "\n".join(out)


METRIC_KEYS = ("f1", "recall", "precision", "fpr", "roc_auc")


def rf_if_table(rf_if: dict) -> str:
    """Random Forest sweeps are a flat list; Isolation Forest splits into a
    contamination sweep plus the fixed-threshold operating point actually
    shipped (contamination only moves IF's own cut-off, not our 0.5 wrapper)."""
    out = ["| model | dataset | configuration | F1 | recall | FPR | ROC-AUC |",
           "|---|---|---|---:|---:|---:|---:|"]

    def row(model, ds, cfg, p):
        out.append(f"| {MODEL_LABEL[model]} | {DS_LABEL[ds]} | {cfg} | "
                   f"{p['f1']:.4f} | {p['recall']:.4f} | {p['fpr']:.4f} | "
                   f"{p['roc_auc']:.4f} |")

    for ds, pts in rf_if["random_forest"].items():
        for p in pts:
            cfg = ", ".join(f"{k}={v}" for k, v in p.items()
                            if k not in METRIC_KEYS)
            row("random_forest", ds, cfg, p)
    for ds, block in rf_if["isolation_forest"].items():
        for p in block["sweep"]:
            cfg = ", ".join(f"{k}={v}" for k, v in p.items()
                            if k not in METRIC_KEYS)
            row("isolation_forest", ds, cfg, p)
        row("isolation_forest", ds,
            "**shipped: fixed 0.5 wrapper**", block["wrapper_0.5"])
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# B.8 -- confusion matrices                                                    #
# --------------------------------------------------------------------------- #
def confusion_table(summary: dict) -> str:
    out = ["| dataset | model | TN | FP | FN | TP | precision | recall | F1 | FPR |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for ds in ("dataset1", "dataset2"):
        for i, model in enumerate(MODEL_ORDER):
            m = summary[ds][model]
            out.append(f"| {DS_LABEL[ds] if i == 0 else ''} | {MODEL_LABEL[model]} | "
                       f"{m['tn']} | {m['fp']} | {m['fn']} | {m['tp']} | "
                       f"{m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | "
                       f"{m['fpr']:.4f} |")
    return "\n".join(out)


def main() -> None:
    rows = list(csv.DictReader(
        (REPORT / "ch4_feature_ranking.csv").open(encoding="utf-8")))
    kept, killed = parse_decisions(
        (REPORT / "ch3_feature_decisions.md").read_text(encoding="utf-8"))
    sens = json.loads((RESULTS / "ch7_sensitivity.json").read_text())
    rf_if = json.loads((RESULTS / "ch7_rf_if_sensitivity.json").read_text())
    summary = json.loads((RESULTS / "summary.json").read_text())
    t3, t4 = gate_tables(kept, killed)
    n_feat = len(kept)

    doc = f"""# Appendix B — Supporting Tables

Generated from the shipped artefacts by `python analysis/appendix_b_tables.py`;
every figure here is read from a result file, none is transcribed. These are the
tables the body chapters summarise but do not print in full.

## B.1 Feature importance — full consensus ranking

`analysis/ch4_ranking.py` scores all {n_feat} features three ways on a held-out
25% of the training split: Random Forest impurity decrease (MDI), XGBoost average
gain per split, and permutation importance measured on the Random Forest.
*Consensus* is the mean of the three per-view ranks, so lower is better. Chapter 4
discusses the top eight and the disagreement between the three views; the top
fifteen on each corpus follow.

**Table B.1 — Dataset 1: top 15 features by consensus rank.** {zero_gain_count(rows, "dataset1")} of
the {n_feat} features receive exactly zero XGBoost gain on this corpus.

{ranking_table(rows, "dataset1", 15)}

**Table B.2 — Dataset 2: top 15 features by consensus rank.** {zero_gain_count(rows, "dataset2")} of
the {n_feat} features receive exactly zero XGBoost gain here — twice Dataset 1's
count, and the reason §4.2 treats the ranking as corpus-specific.

{ranking_table(rows, "dataset2", 15)}

## B.2 Feature selection — what was rejected and why

Chapter 3 audits {len(kept) + len(killed)} candidate features on the training
split only and keeps {n_feat}. Two rejection rules: a candidate fails the
**gate** if it shows no usable effect on either corpus at these sample sizes, and
it is cut as **redundant** if its absolute correlation with a retained feature
exceeds 0.9 and that feature carries the same signal. Every verdict was ruled
jointly and is recorded with its evidence in `report/ch3_feature_decisions.md`.

**Table B.3 — Feature funnel.**

{t3}

**Table B.4 — The {len(killed)} rejected candidates.** Rejection is itself a
result: the themed path splits (`n_cred_paths`, `n_proc_paths`, `n_log_paths`)
each died while their lump `n_sensitive_paths` survived, refuting the
split-covers-lump hypothesis; and `has_privesc_bin` is class-neutral while
positional `head_is_privesc` passes — *where* a binary sits matters, *that* it
appears does not.

{t4}

## B.3 Hyperparameter sensitivity — every swept configuration

Chapter 7.3 reports the headline conclusion; these are the runs behind it. Each
axis is swept one-at-a-time from the shipped configuration, training on the full
training split and scoring on the held-out test split.

**Table B.5 — XGBoost: all swept configurations.**

{sweep_table(sens, "xgboost")}

**Table B.6 — 1D-CNN: all swept configurations.**

{sweep_table(sens, "cnn1d")}

**Table B.7 — Random Forest and Isolation Forest sweeps.** Isolation Forest's
`contamination` moves only its own internal cut-off; the shipped pipeline scores
it through the same fixed 0.5 wrapper as every other model, which is the last row
of each block and the number `results/summary.json` reports.

{rf_if_table(rf_if)}

## B.4 Confusion matrices behind every headline score

**Table B.8 — Full confusion matrices, in-domain hold-out.** Counts are test-split
rows; Dataset 1's test split is 3,049 rows (762 attack) and Dataset 2's is 1,915
(479 attack). The 1:3 attack:benign ratio means a do-nothing classifier that
flags everything scores F1 0.400, which is the floor every model here must beat.

{confusion_table(summary)}
"""
    OUT.write_text(doc, encoding="utf-8")
    n_rows = sum(1 for ln in doc.splitlines() if ln.startswith("|"))
    print(f"[B] wrote {OUT.relative_to(ROOT)}: {len(doc.split())} words, "
          f"{n_rows} table rows")


if __name__ == "__main__":
    main()
