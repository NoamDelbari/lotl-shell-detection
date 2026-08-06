"""
evaluate_baseline.py -- reference baseline + shortcut audit for the two datasets.

This is not the project's model. It is the honesty check that has to pass before
any reported number means anything: a strong-but-dumb TF-IDF baseline, plus
ablations that remove each confound we know about and re-measure, plus four
permanent regression probes that fail loudly if a fixed problem comes back.

A dataset "passes" if the score SURVIVES the ablations. A score that collapses
when addresses are stripped or lengths are matched was never measuring
maliciousness.

Reporting rules enforced here (see KNOWN_ISSUES.md P1-P8):
  * F1 is not on an absolute scale -- it depends on prevalence p. A model that
    shouts MALICIOUS at everything scores 2p/(1+p). EVERY row of every table
    therefore carries n, n_malicious, p, that do-nothing floor, and F1 both
    above the floor (raw difference) and normalised by the headroom (1 - floor).
  * Every row in every table is built by ONE function, `make_row()`, and turned
    into markdown by ONE function, `md_table()`. Nothing is hand-formatted, so a
    floor can never again go missing from a row.
  * Per-source rates are reported as k/n with a WILSON 95% interval, for BOTH
    datasets, and any pair of malicious sources whose intervals overlap is
    flagged in a machine-checkable block so prose cannot claim one source beats
    another when the data does not support it.
  * Four probes run on every build and roll up to a PASS/FAIL/INFO table:
      P1  RE_MAL_MARKERS as a classifier   -- it must NOT score like the model,
          because that is what a keyword-defined label looks like.
      P2  rows-per-shape per source        -- ~1.0 on a template-generated
          source is shape() having stopped normalising the randomised parts.
      P3/P5 single-feature shortcuts       -- how far one dumb feature gets.
      P8  source separability              -- can a model tell which PILE a
          command came from, ignoring the label entirely?

ASCII only. This machine's console is cp1252 and main() prints the assembled
markdown; a typographic minus or arrow in the emitted text crashes the script in
print() AFTER it has written the files. Use `-`, `->`, `+/-`.

Writes ../docs/BASELINE.md and ../docs/baseline_metrics.json; reads the split
files in ../dataset/ and the counts in ../docs/stats.json.
Run: python evaluate_baseline.py   (from scripts/)
"""
from __future__ import annotations
import json
import math
import re
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)

# Deliberate coupling: the P2 probe asserts that build_dataset's shape() is still
# collapsing template-generated sources, and the P1 probe scores build_dataset's
# selection regex. A probe that re-implemented either could not detect the real
# one regressing. Cost: this file will not import if build_dataset.py has a
# syntax error, and it inherits build_dataset's RequestsDependencyWarning.
from build_dataset import RE_MAL_MARKERS, shape as build_shape

HERE = Path(__file__).resolve().parent          # final_project/scripts/
PROJECT = HERE.parent                           # final_project/
DATA = PROJECT / "dataset"                      # train/test splits
DOCS = PROJECT / "docs"                         # stats.json in, BASELINE.md etc. out
SEED = 42
THRESHOLD = 0.5

# z for a two-sided 95% interval. Hard-coded so the reporting code has no
# scipy dependency; equals scipy.stats.norm.ppf(0.975) to 1e-15.
Z95 = 1.959963984540054

# Below this many test samples a per-source rate is labelled "indicative only".
# 30 is the conventional cut for the normal approximation to be trustworthy; we
# use Wilson precisely because it still behaves below it, but at n < 30 the
# interval is wide enough that the point estimate should not be quoted at all.
# The flag exists to stop that happening. No example width is baked in here: the
# report measures the actual smallest source and prints its actual interval, so
# the illustration cannot go stale when the build changes.
SMALL_N = 30

# length matching tolerance: a benign partner counts as "the same length" if it
# is within max(5 chars, 10% of the malicious command's length).
LEN_TOL_ABS = 5
LEN_TOL_FRAC = 0.10

RE_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
RE_HOST = re.compile(r"h[0-9a-f]{8}\.example\.net")


def strip_addresses(s: str) -> str:
    return RE_HOST.sub("HOST", RE_IP.sub("ADDR", s))


# ---------------------------------------------------------------------------
# statistics helpers  (P3: the floor;  P4: Wilson)
# ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion k/n.

    Not the normal approximation: at the sample sizes the small sources give
    (n in the tens) the normal interval is both too narrow and can run past 1.0.
    Wilson is the standard small-n replacement and is four lines of arithmetic,
    so we implement it rather than add a dependency.

        centre = (p^ + z^2/2n) / (1 + z^2/n)
        half   = z/(1 + z^2/n) * sqrt( p^(1-p^)/n + z^2/4n^2 )

    Returns (lo, hi), clipped to [0, 1]. n == 0 -> (0.0, 1.0) (no information).
    """
    if n <= 0:
        return (0.0, 1.0)
    p_hat = k / n
    denom = 1.0 + z * z / n
    centre = (p_hat + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p_hat * (1.0 - p_hat) / n + z * z / (4.0 * n * n))
    # at k == 0 the lower bound and at k == n the upper bound are exactly 0 and 1
    # in real arithmetic; pin them so float error cannot print 0.99999999999.
    lo = 0.0 if k == 0 else max(0.0, centre - half)
    hi = 1.0 if k == n else min(1.0, centre + half)
    return (lo, hi)


def intervals_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """True if two closed intervals share at least one point."""
    return a[0] <= b[1] and b[0] <= a[1]


def do_nothing_f1(p: float) -> float:
    """F1 of the model that ignores its input and predicts MALICIOUS always.

    Recall 1.0, precision p, so F1 = 2p/(1+p). This is the floor any reported
    F1 must be read against: F1 0.95 at p = 0.83 (floor 0.908) is a worse result
    than F1 0.85 at p = 0.25 (floor 0.400).

    THE ONLY definition of the floor in this file. The probe spec drafted a
    second one taking labels instead of a prevalence (`floor(y)`); two spellings
    of one formula is how they drift apart, so callers holding labels pass
    `do_nothing_f1(float(np.mean(y)))` and there is nothing to keep in sync.
    """
    return 0.0 if p <= 0 else 2.0 * p / (1.0 + p)


# ---------------------------------------------------------------------------
# the single row builder -- every table row in this file goes through it
# ---------------------------------------------------------------------------
def make_row(dataset: str, setting: str, y_true, y_score=None, y_pred=None,
             note: str = "", extra: dict | None = None) -> dict:
    """Score one (test set, predictor) pair and return a fully-populated row.

    Exactly one of y_score (probabilities/decision values) or y_pred (hard 0/1)
    must be given. With y_score, the hard prediction is y_score > THRESHOLD and
    ROC-AUC / PR-AUC are reported; with y_pred (single-feature probe rules) the
    AUCs are not defined and come back None.

    Every row carries prevalence and the do-nothing floor, so no caller can
    report an F1 without the ruler it was measured on.
    """
    y_true = np.asarray(pd.Series(y_true).values, dtype=int)
    n = int(y_true.size)
    n_mal = int(y_true.sum())
    p = n_mal / n if n else float("nan")
    floor = do_nothing_f1(p)

    if (y_score is None) == (y_pred is None):
        raise ValueError("make_row: give exactly one of y_score / y_pred")
    if y_score is not None:
        s = np.asarray(pd.Series(y_score).values, dtype=float)
        hard = (s > THRESHOLD).astype(int)
        both_classes = 0 < n_mal < n
        roc = float(roc_auc_score(y_true, s)) if both_classes else None
        pr = float(average_precision_score(y_true, s)) if both_classes else None
    else:
        hard = np.asarray(pd.Series(y_pred).values).astype(int)
        roc = pr = None

    f1 = float(f1_score(y_true, hard, zero_division=0))
    headroom = 1.0 - floor
    row = {
        "dataset": dataset,
        "setting": setting,
        "note": note,
        "n": n,
        "n_mal": n_mal,
        "p": p,
        "floor": floor,
        # precision and recall are carried on every row because the probe tables
        # need them to say WHICH way a rule is failing (the selection regex is a
        # recall story, the address rule a precision one). They are not shown in
        # the headline scores table, which is already 12 columns wide.
        "precision": float(precision_score(y_true, hard, zero_division=0)),
        "recall": float(recall_score(y_true, hard, zero_division=0)),
        "f1": f1,
        "f1_minus_floor": f1 - floor,
        # normalised: 0.0 = no better than always-malicious, 1.0 = perfect.
        # Can be negative (worse than do-nothing). None when floor == 1.
        "f1_norm": (f1 - floor) / headroom if headroom > 1e-12 else None,
        "roc_auc": roc,
        "pr_auc": pr,
        # a random ranker's average precision is the prevalence itself, so this
        # is the do-nothing floor for the PR-AUC column, on the same principle.
        "pr_auc_base": p,
    }
    if extra:
        row.update(extra)
    return row


def _f(x, nd=4) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:.{nd}f}"


def _sf(x, nd=4) -> str:
    """Signed format, for "distance above the floor" columns."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:+.{nd}f}"


# ---------------------------------------------------------------------------
# THE table builder. Every markdown table in this file and in BASELINE.md is
# produced here, from a list of dicts whose keys are the column headers. The two
# specs that fed this file each shipped their own builder (one generic, one with
# the score columns hard-coded); the generic one won and the other survives only
# as the `render_*` adapters below, which choose columns and formatting and then
# delegate. Hand-formatting a table row is what let a do-nothing floor go
# missing from every row of the old BASELINE.md.
# ---------------------------------------------------------------------------
_NUMISH = re.compile(r"^[-+]?[\d,]*\.?\d+%?$|^n/a$|^$")


def md_table(rows: list[dict], cols: list[str] | None = None) -> list[str]:
    """Render a list of dicts as a markdown table. Numeric columns right-align.
    Column order = key order of the first dict unless `cols` is given."""
    if not rows:
        return ["_(no rows)_"]
    cols = cols or list(rows[0])
    right = [all(_NUMISH.match(str(r.get(c, ""))) for r in rows) for c in cols]
    out = ["| " + " | ".join(cols) + " |",
           "|" + "|".join("---:" if r else "---" for r in right) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return out


def _score_cells(r: dict) -> dict:
    setting = r["setting"] + (f" <br/>*{r['note']}*" if r["note"] else "")
    return {"dataset": r["dataset"], "setting": setting,
            "test rows": f"{r['n']:,}", "n mal": f"{r['n_mal']:,}",
            "prevalence p": _f(r["p"]),
            "do-nothing floor 2p/(1+p)": _f(r["floor"]),
            "F1": _f(r["f1"]), "F1 - floor": _sf(r["f1_minus_floor"]),
            "(F1 - floor)/(1 - floor)": _sf(r["f1_norm"]),
            "ROC-AUC": _f(r["roc_auc"]), "PR-AUC": _f(r["pr_auc"]),
            "PR-AUC base (= p)": _f(r["pr_auc_base"])}


def render_table(rows: list[dict]) -> list[str]:
    """Scores table: one row per (test set, predictor)."""
    return md_table([_score_cells(r) for r in rows])


def _probe_cells(r: dict) -> dict:
    return {"probe": r["setting"], "scope": r["note"], "n": f"{r['n']:,}",
            "n mal": f"{r['n_mal']:,}", "prevalence p": _f(r["p"], 3),
            "floor": _f(r["floor"]), "precision": _f(r["precision"]),
            "recall": _f(r["recall"]), "F1": _f(r["f1"]),
            "F1 - floor": _sf(r["f1_minus_floor"]),
            "(F1 - floor)/(1 - floor)": _sf(r["f1_norm"]),
            "ROC-AUC": _f(r["roc_auc"])}


def render_probe_table(rows: list[dict]) -> list[str]:
    """Probe table: same rows, but precision/recall shown and the AUC pair
    dropped to one column, because most probe rules are hard 0/1 and have none."""
    return md_table([_probe_cells(r) for r in rows])


def render_source_table(src_rows: list[dict]) -> list[str]:
    cells = []
    for r in src_rows:
        lo, hi = r["ci"]
        cells.append({
            "dataset": r["dataset"], "source": f"`{r['source']}`",
            "class": r["class"], "metric": r["metric"],
            "k / n": f"{r['k']:,} / {r['n']:,}", "rate": _f(r["rate"], 3),
            "Wilson 95% CI": f"[{lo:.3f}, {hi:.3f}]", "width": f"{hi - lo:.3f}",
            "flag": f"**indicative only (n < {SMALL_N})**" if r["small_n"] else ""})
    return md_table(cells)


def verdict(ok, text: str) -> str:
    """One PASS / FAIL / INFO line. ok=None means informational (no assertion).
    ASCII only: BASELINE.md is also printed to a cp1252 console."""
    return f"**{'INFO' if ok is None else ('PASS' if ok else 'FAIL')}** - {text}"


# ---------------------------------------------------------------------------
# model
# ---------------------------------------------------------------------------
def fit_scorer(train: pd.DataFrame):
    """Fit the baseline once and return a scorer P(malicious) for any commands.

    Fitting once and handing back a closure keeps every number read off a single
    model; fit_predict delegates here so the probes and the transfer runs all
    share exactly one training path.
    """
    v = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3,
                        max_features=200_000, sublinear_tf=True)
    X = v.fit_transform(train["command"])
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced",
                             random_state=SEED).fit(X, train["label"])
    return lambda cmds: clf.predict_proba(v.transform(cmds))[:, 1]


def fit_predict(train: pd.DataFrame, test: pd.DataFrame) -> pd.Series:
    """Fit on train, return P(malicious) for test, indexed like test."""
    return pd.Series(fit_scorer(train)(test["command"]), index=test.index)


# ---------------------------------------------------------------------------
# P3: length matching that actually matches lengths
# ---------------------------------------------------------------------------
def length_match(test: pd.DataFrame, tol_abs: int = LEN_TOL_ABS,
                 tol_frac: float = LEN_TOL_FRAC) -> tuple[pd.DataFrame, dict]:
    """Build an exactly 1:1 length-matched subset of `test`.

    Each malicious row is paired with at most one unused benign row whose length
    is within max(tol_abs, tol_frac * L) characters. A malicious row that finds
    no such partner is DROPPED -- the old version kept it, which is why the
    "length-matched" Dataset 1 subset came out 83.1% malicious and its F1 was
    being read against a 0.908 floor instead of 0.400, and was then reported as
    an improvement over the full-test row. The old tolerance was also measured in
    ROWS of the sorted benign lengths (+/-40 rows), not characters, so the pairs
    it did make were badly mismatched: the class medians stayed 222 vs 75.

    Longest attacks are matched first, because long benign commands are the
    scarce resource; matching in that order maximises coverage. Within the
    tolerance the nearest length wins, and a running signed bias decides which
    side of a tie to take, so partners cannot drift systematically shorter than
    the attacks they are standing in for. Fully deterministic (no RNG).

    Note on the "label-independent filter" rule that governs build_dataset.py:
    it governs which strings may ENTER a dataset. This is an analysis-time
    ablation on the test set -- it deliberately conditions on the label in order
    to equalise a covariate, which is the entire point of the ablation, and it
    never touches the built data. Its cost is reported as coverage, not hidden.

    Returns (subset, info). `info` carries the coverage -- how many of the N
    malicious rows could actually be matched -- plus the before/after median and
    mean length per class and the per-pair length gaps, so a partial match can
    never be presented as a clean one. The subset keeps `test`'s index, so a
    probability vector computed on the full test set can be sliced with .loc
    instead of refitting the model.
    """
    if not test.index.is_unique:
        raise ValueError("length_match: test frame needs a unique index "
                         "(the subset is sliced by index afterwards)")
    lengths = test["command"].str.len()
    is_mal = test["label"].astype(int) == 1

    pool: dict[int, list] = defaultdict(list)
    for idx, L in lengths[~is_mal].items():
        pool[int(L)].append(idx)
    for v in pool.values():
        v.sort(reverse=True)          # pop() takes the smallest index -> stable

    mal_len = lengths[is_mal]
    # longest first; stable so equal lengths keep dataset order
    order = list(mal_len.sort_values(kind="mergesort", ascending=False).index)

    pairs, diffs = [], []
    bias = 0            # running sum of (partner length - attack length)
    for i in order:
        L = int(lengths.at[i])
        tol = max(tol_abs, int(round(tol_frac * L)))
        hit = None
        for d in range(tol + 1):
            if d == 0:
                cands = (L,)
            elif bias < 0:
                cands = (L + d, L - d)   # partners have been running short
            else:
                cands = (L - d, L + d)
            for cand in cands:
                if cand >= 0 and pool.get(cand):
                    hit = cand
                    break
            if hit is not None:
                break
        if hit is None:
            continue
        j = pool[hit].pop()
        pairs.append((i, j))
        diffs.append(abs(hit - L))
        bias += hit - L

    keep = set()
    for i, j in pairs:
        keep.add(i)
        keep.add(j)
    sub = test[test.index.isin(keep)]

    sub_len = sub["command"].str.len()
    sub_mal = sub["label"].astype(int) == 1
    n_mal = int(is_mal.sum())
    info = {
        "n_malicious": n_mal,
        "n_matched": len(pairs),
        "coverage": (len(pairs) / n_mal) if n_mal else float("nan"),
        "n_benign_pool": int((~is_mal).sum()),
        "tolerance": f"max({tol_abs} chars, {tol_frac:.0%} of length)",
        "median_len_mal_before": float(lengths[is_mal].median()),
        "median_len_ben_before": float(lengths[~is_mal].median()),
        "median_len_mal_after": float(sub_len[sub_mal].median()) if len(pairs) else float("nan"),
        "median_len_ben_after": float(sub_len[~sub_mal].median()) if len(pairs) else float("nan"),
        "mean_len_mal_after": float(sub_len[sub_mal].mean()) if len(pairs) else float("nan"),
        "mean_len_ben_after": float(sub_len[~sub_mal].mean()) if len(pairs) else float("nan"),
        "median_abs_pair_diff": float(np.median(diffs)) if diffs else float("nan"),
        "max_abs_pair_diff": float(max(diffs)) if diffs else float("nan"),
    }
    mm, mb = info["median_len_mal_after"], info["median_len_ben_after"]
    info["medians_matched"] = bool(
        len(pairs) and abs(mm - mb) <= max(tol_abs, tol_frac * max(mm, mb)))
    return sub, info


# ============================================================================
# PERMANENT REGRESSION PROBES  (KNOWN_ISSUES P1, P2, P7, P8 + the single-feature
# shortcut probes). Every probe is self-contained, emits a BASELINE.md section,
# and ends with one or more PASS / FAIL / INFO lines. No probe filters, relabels
# or drops any row -- they are read-only measurements.
# ============================================================================

# ===========================================================================
# PROBE 1 - selection-regex probe (P1's permanent guard)
# ===========================================================================
# Thresholds. Justification, so this is a test and not a rubber stamp:
#
# MAX_REGEX_RECALL. Recall is the direct measurement of "did the selection rule
#   define the label". Before the P1 fix it is 1.0000 on Dataset 2 by
#   construction. After the fix, honeypot commands are kept by SESSION
#   PROVENANCE, and the marker rate was measured on the rebuilt pool: of the
#   2,344 honeypot commands surviving fixed-shape dedup at 2 per shape, 392
#   (0.1672) match RE_MAL_MARKERS. Dataset 1 lands in the same place: its
#   per-source marker rates are quasarnix 0.398, slp 0.180, atomic 0.074,
#   gtfobins 0.042, which after the P2 collapse of QuasarNix (17,580 -> ~850
#   rows) weight out to ~0.17 as well. So the expected post-fix value is ~0.17
#   for both datasets and 0.50 sits ~3x above it: far enough that ordinary
#   sampling and split noise can never reach it, close enough that it trips long
#   before recall returns to the 1.0 of a keyword-defined label. A looser bar
#   (0.90, "must be below 1.0") would pass a build in which half the malicious
#   class was re-selected by keyword, which is exactly the regression to catch.
# WARN_REGEX_RECALL is 2x the expectation: not a failure, but something changed.
# MIN_MODEL_MARGIN. The point of the probe is that every report can state "beats
#   the keyword rule by X". 0.10 F1 is a floor on "the model does something a
#   20-token wordlist does not". It is deliberately low: the observed circular
#   build produced a margin of +0.0287, and a healthy build produces +0.50 or
#   more, so the band between them is empty in practice. WARN_MODEL_MARGIN
#   flags erosion before it becomes a failure.
MAX_REGEX_RECALL = 0.50
WARN_REGEX_RECALL = 0.30
MIN_MODEL_MARGIN = 0.10
WARN_MODEL_MARGIN = 0.25


def probe_selection_regex(tag: str, d: pd.DataFrame, model_f1: float):
    """RE_MAL_MARKERS run as if it were the classifier. If it scores like the
    trained model, the labels are the regex and the model learned nothing."""
    md, rows, cells = [], [], []
    hit = d["command"].map(lambda s: 1 if RE_MAL_MARKERS.search(s) else 0)
    t_rc = t_f1 = float("nan")
    t_k = t_n = 0
    for scope, mask in (("whole dataset", pd.Series(True, index=d.index)),
                        ("test split", d["split"] == "test")):
        y = d.loc[mask, "label"]
        yhat = hit[mask]
        k = int(((yhat == 1) & (y == 1)).sum())
        n_mal = int((y == 1).sum())
        fp = int(((yhat == 1) & (y == 0)).sum())
        lo, hi = wilson(k, n_mal)
        r = make_row(tag, "RE_MAL_MARKERS as the classifier", y, y_pred=yhat,
                     note=scope, extra={"ci": [lo, hi], "false_positives": fp})
        rows.append(r)
        cells.append({"scope": scope, "n": f"{r['n']:,}",
                      "prevalence": _f(r["p"], 3), "floor": _f(r["floor"]),
                      "precision": _f(r["precision"]), "recall": _f(r["recall"]),
                      "recall 95% CI": f"[{lo:.3f}, {hi:.3f}]",
                      "F1": _f(r["f1"]), "F1 - floor": _sf(r["f1_minus_floor"]),
                      "false positives": f"{fp:,}"})
        if scope == "test split":
            t_rc, t_f1, t_k, t_n = r["recall"], r["f1"], k, n_mal
    md += ["`RE_MAL_MARKERS` is the keyword filter that used to SELECT Dataset 2's "
           "malicious rows. It no longer decides any label (KNOWN_ISSUES P1); it "
           "survives only as this permanently reported baseline. Recall here is the "
           "circularity measurement: a value near 1.0 means the label is the regex.", ""]
    md += md_table(cells) + [""]
    margin = model_f1 - t_f1
    md += [f"Trained model F1 on the same test split: **{model_f1:.4f}**. "
           f"Keyword-rule F1: **{t_f1:.4f}**. "
           f"**The model beats the keyword rule by {margin:+.4f} F1.**", ""]
    ok_recall = t_rc < MAX_REGEX_RECALL
    ok_margin = margin >= MIN_MODEL_MARGIN
    md.append(verdict(ok_recall,
                      f"keyword-rule recall on the test split = {t_rc:.4f} ({t_k:,}/{t_n:,}); "
                      f"must stay below {MAX_REGEX_RECALL:.2f} (expected ~0.17 once labels "
                      f"come from provenance rather than the regex)."))
    if ok_recall and t_rc > WARN_REGEX_RECALL:
        md.append(verdict(None, f"recall {t_rc:.4f} is above the {WARN_REGEX_RECALL:.2f} "
                                f"watch line; the malicious class has become unusually "
                                f"marker-rich. Not a failure, but check what changed."))
    md.append(verdict(ok_margin, f"model F1 minus keyword-rule F1 = {margin:+.4f}; "
                                 f"must be at least {MIN_MODEL_MARGIN:+.2f}."))
    if ok_margin and margin < WARN_MODEL_MARGIN:
        md.append(verdict(None, f"margin {margin:+.4f} is below the {WARN_MODEL_MARGIN:+.2f} "
                                f"watch line: the trained model is barely out-scoring a "
                                f"20-token wordlist."))
    return md, (ok_recall and ok_margin), rows


# ===========================================================================
# PROBE 2 - rows-per-shape probe (P2's permanent guard, plus P7)
# ===========================================================================
# TEMPLATED_SOURCES: sources that are a small number of command TEMPLATES
#   instantiated with randomised values - QuasarNix's reverse-shell generator,
#   and botnet spam replayed across thousands of Cowrie sessions. For these, and
#   only these, rows-per-shape near 1.0 is diagnostic of shape() failing to
#   normalise the randomised parts, which is P2 exactly. Curated sources
#   (GTFOBins, SLP, Atomic Red Team) and the LLM-generated benign sets are
#   hand-written or one-off, so they legitimately sit near 1.0; asserting on them
#   would be a permanent false failure. There is no label-independent way to
#   infer "is this source template-generated" from the built CSV, so the set is
#   declared here, and must be extended if a new generator-backed source lands.
#   The `kind` column is not a proxy - bash_instruct/linlm/bash6k are `synthetic`
#   too, and are not templated.
# MIN_POOL_ROWS_PER_SHAPE: the KNOWN_ISSUES P2 acceptance criterion verbatim.
#   Measured on the source POOL (before the MAX_PER_SHAPE cap), and ONLY there -
#   see the note on the built column below. The broken shape() gave quasarnix
#   1.01; the first repair gave 535 (239,638 rows / 448 shapes); the current one,
#   after the scratch-path rule that collapses /tmp/<random>, gives 2,349
#   (239,638 / 102) and honeypot 166 (407,442 / 2,455).
#   WARN_POOL_ROWS_PER_SHAPE = 10.0 catches a PARTIAL regression: anything in
#   single digits means shape() has stopped normalising some family, long before
#   it decays all the way to the contractual 1.5.
# The BUILT (post-cap) rows/shape is NOT a usable assertion, and the report must
#   never silently switch to it: with the dedup at MAX_PER_SHAPE = 2 it is
#   bounded by 2, and because both pools have a long tail of singleton shapes the
#   healthy post-fix value is only ~1.1 - indistinguishable from the broken 1.01,
#   and below the 1.5 line the criterion states. Both columns are printed side by
#   side with the criterion named; the built column is used as a weak fallback
#   with a 1.05 floor only when stats.json carries no pool statistics at all.
TEMPLATED_SOURCES = {"quasarnix", "honeypot"}
MIN_POOL_ROWS_PER_SHAPE = 1.5
WARN_POOL_ROWS_PER_SHAPE = 10.0
MIN_BUILT_ROWS_PER_SHAPE = 1.05

# --- near-duplicate leakage, measured WITHOUT shape() ------------------------
# The straddle check above can only see leakage that shape() is able to express.
# When shape() under-collapses a family, a test row and a train row can be all
# but character-identical and the straddle count still reads 0. That is not
# hypothetical: before the scratch-path rule was added to shape(), 26.2% of the
# QuasarNix test rows had a train sibling at difflib ratio > 0.90 - differing
# only in a random /tmp file name - while this probe reported zero straddling
# groups. So the leakage question is asked a second time in a representation
# shape() has no say in: binary character 4-grams, Jaccard similarity, each test
# row against the nearest TRAIN row OF THE SAME SOURCE (cross-source similarity
# is not leakage, it is the task). Label-independent: it never looks at `label`.
# Two similarity lines, because one number would be misread. 4-gram Jaccard is
# stricter than the difflib ratio the original finding used, and the gap is
# measured, not assumed: changing one IPv4 octet in a 56-character command scores
# 0.846 here against difflib's 0.982; swapping an 8-character random file name at
# two sites in a 70-character command scores 0.759 (difflib 0.771). Both numbers
# are pinned by tests. So 0.90 on this metric means "all but identical", while
# 0.80 already means "recognisably the same command line with a value changed".
# Both columns are printed; the FAIL assertion is on the strict one and the loose
# one carries a watch line, so a reader can never take "share >= 0.90 is 0%" as
# "there are no near-duplicates".
NEARDUP_SIM = 0.90         # strict: the fail line is measured here
NEARDUP_LOOSE = 0.80       # loose: reported beside it, watch line only
NEARDUP_FAIL_SHARE = 0.10  # >10% of a source's test rows that close -> FAIL
NEARDUP_WARN_SHARE = 0.10  # same share on the loose column -> INFO, not FAIL

# The third column is the ORIGINAL finding's own ruler: difflib's sequence-match
# ratio at 0.90, which is what measured "26.2% of QuasarNix test rows have a
# near-duplicate train sibling" before the shape() repair. It is kept because
# dropping it would let the repair be reported on a friendlier metric than the
# one that found the bug. It is quadratic in Python, so the number of pairs is
# budgeted: past the budget the TEST rows are subsampled (seeded) while the whole
# train side is kept, which leaves each sampled row's nearest neighbour exact and
# makes the share a binomial estimate - reported with its Wilson interval and
# flagged as sampled. The FAIL assertion is NOT on this column: at these command
# lengths difflib calls `less /path/to/input-file` and `zless /path/to/input-file`
# 0.95 similar, and those are two different programs, so a threshold on it would
# be asserting something the metric cannot support. It is reported in full, with
# every source over the watch line named and the consequence spelled out.
NEARDUP_DIFFLIB_SIM = 0.90
NEARDUP_DIFFLIB_BUDGET = 1_500_000     # test x train comparisons per source


def _difflib_share(tr: list[str], te: list[str], sim: float = NEARDUP_DIFFLIB_SIM,
                   budget: int = NEARDUP_DIFFLIB_BUDGET) -> dict:
    """Share of test rows whose best difflib ratio against any train row is >= sim.
    quick_ratio/real_quick_ratio are upper bounds on ratio(), so pruning with them
    is exact, not approximate."""
    import difflib
    per = max(1, budget // max(1, len(tr)))
    idx = list(range(len(te)))
    if len(te) > per:
        idx = sorted(np.random.default_rng(SEED).choice(len(te), size=per,
                                                        replace=False).tolist())
    sm = difflib.SequenceMatcher()
    hits = 0
    for i in idx:
        sm.set_seq2(te[i])
        b = 0.0
        for r in tr:
            sm.set_seq1(r)
            if sm.real_quick_ratio() > b and sm.quick_ratio() > b:
                b = max(b, sm.ratio())
                if b >= 1.0:
                    break
        hits += int(b >= sim)
    return {"n": len(idx), "hits": hits, "share": hits / len(idx) if idx else None,
            "sampled": len(idx) < len(te), "ci": wilson(hits, len(idx))}


def nearest_train_neighbour(d: pd.DataFrame, sim: float = NEARDUP_SIM,
                            loose: float = NEARDUP_LOOSE) -> list[dict]:
    """Per source: the distribution of each test row's similarity to its most
    similar same-source TRAIN row. Char-4-gram binary Jaccard, computed exactly
    (no approximation, no sampling) via one sparse matrix product per source.

    Returns one dict per source with median, p90, max and the share at or above
    `sim`, plus the closest pair itself so the report can show what it found.
    """
    from sklearn.feature_extraction.text import CountVectorizer
    out = []
    for src, g in d.groupby("source"):
        tr = g.loc[g["split"] == "train", "command"].tolist()
        te = g.loc[g["split"] == "test", "command"].tolist()
        rec = {"source": src, "n_test": len(te), "n_train": len(tr)}
        if not tr or not te:
            rec.update({"median": None, "p90": None, "max": None, "share_ge": None,
                        "share_loose": None, "difflib": None, "pair": None})
            out.append(rec)
            continue
        # fit on train+test together: fitting on train alone would silently drop
        # the 4-grams unique to a test row, shrinking its set and INFLATING every
        # similarity. The vocabulary is shared, the neighbour search is not.
        v = CountVectorizer(analyzer="char", ngram_range=(4, 4), binary=True,
                            lowercase=False, min_df=1)
        v.fit(tr + te)
        Xtr, Xte = v.transform(tr), v.transform(te)
        ntr = np.asarray(Xtr.sum(axis=1)).ravel().astype(float)
        nte = np.asarray(Xte.sum(axis=1)).ravel().astype(float)
        best = np.zeros(len(te))
        arg = np.zeros(len(te), dtype=int)
        for i in range(0, len(te), 256):                     # chunked: |te|x|tr|
            inter = (Xte[i:i + 256] @ Xtr.T).toarray().astype(float)
            union = nte[i:i + 256, None] + ntr[None, :] - inter
            j = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
            best[i:i + 256] = j.max(axis=1)
            arg[i:i + 256] = j.argmax(axis=1)
        top = int(best.argmax())
        rec.update({"median": float(np.median(best)), "p90": float(np.quantile(best, 0.90)),
                    "max": float(best.max()),
                    "share_ge": float((best >= sim).mean()),
                    "share_loose": float((best >= loose).mean()),
                    "difflib": _difflib_share(tr, te),
                    "pair": (te[top], tr[arg[top]])})
        out.append(rec)
    return out


def pool_shape_stats(stats: dict) -> dict:
    """Per-source POOL rows and shapes, measured BEFORE the MAX_PER_SHAPE cap.

    build_dataset.py records this as `stats["shape_cap"][src]` with keys
    {"raw", "shapes", "kept", ...}. The probe spec asked for a second block,
    `stats["shape_stats"][src]` = {"rows", "shapes"}, holding the same two
    numbers; adding a duplicate measurement to the builder would only give the
    two copies a chance to disagree, so this reads whichever exists and
    normalises the names. Empty dict -> the probe falls back to the built
    rows/shape and says so in an INFO line, so a missing integration is visible
    rather than silent.
    """
    out = {}
    for src, v in (stats.get("shape_cap") or {}).items():
        if v.get("shapes"):
            out[src] = {"rows": int(v.get("raw", 0)), "shapes": int(v["shapes"])}
    for src, v in (stats.get("shape_stats") or {}).items():
        if v.get("shapes"):
            out[src] = {"rows": int(v.get("rows", 0)), "shapes": int(v["shapes"])}
    return out


def probe_rows_per_shape(tag: str, d: pd.DataFrame, stats: dict):
    """Rows per distinct shape, per source. ~1.0 on a template-generated source is
    the signature of the P2 bug returning. Also checks the dedup cap, the group
    split, and counts the P7 cross-label shapes."""
    md = []
    d = d.copy()
    d["shape"] = d["command"].map(build_shape)          # the LIVE shape()
    pool = pool_shape_stats(stats)
    cap = int(stats.get("config", {}).get("MAX_PER_SHAPE", 0)) or None

    rows, worst = [], {}
    for src, g in d.groupby("source"):
        n, k = len(g), int(g["shape"].nunique())
        worst[src] = int(g.groupby("shape").size().max())
        p = pool.get(src) or {}
        prs = (p["rows"] / p["shapes"]) if p.get("shapes") else None
        rows.append({"source": f"`{src}`",
                     "class": "malicious" if int(g["label"].iloc[0]) else "benign",
                     "rows": f"{n:,}", "shapes": f"{k:,}", "rows/shape": f"{n / k:.2f}",
                     "max rows in one shape": f"{worst[src]:,}",
                     "pool rows": f"{p['rows']:,}" if p else "n/a",
                     "pool shapes": f"{p['shapes']:,}" if p else "n/a",
                     "pool rows/shape": f"{prs:.2f}" if prs else "n/a"})
    rows.sort(key=lambda r: (r["class"], r["source"]))
    md += ["`shape()` blanks the volatile parts of a command so that near-identical "
           "commands group together, for dedup and for the group-aware split. Pool "
           "columns are measured before the MAX_PER_SHAPE cap and are the meaningful "
           "ones; built rows/shape is bounded by the cap.", ""]
    md += md_table(rows) + [""]

    # WHICH ruler the P2 criterion is being read on, stated before the verdict.
    # KNOWN_ISSUES writes the criterion as "rows-per-shape > 1.5"; that is a POOL
    # measurement and only a pool measurement. The built value cannot satisfy it
    # even in principle - MAX_PER_SHAPE caps it at 2 and the singleton tail pulls
    # it to ~1.1 - so quoting the built number against a 1.5 line would be a
    # category error in either direction. Both are printed, always, so the metric
    # can never be switched silently to whichever one passes.
    crit = []
    for src in sorted(TEMPLATED_SOURCES):
        g = d[d["source"] == src]
        if not len(g):
            continue
        p = pool.get(src) or {}
        crit.append({"source": f"`{src}`",
                     "pool rows/shape (the criterion)": f"{p['rows'] / p['shapes']:.2f}"
                                                        if p.get("shapes") else "n/a",
                     "built rows/shape (capped at "
                     f"{cap or '?'})": f"{len(g) / g['shape'].nunique():.2f}"})
    if crit:
        md += [f"P2's acceptance criterion is `rows-per-shape > {MIN_POOL_ROWS_PER_SHAPE}` "
               f"measured on the source POOL, before dedup. The built column is shown "
               f"beside it and is NOT the number the criterion is read against: with "
               f"MAX_PER_SHAPE = {cap} it is bounded by {cap} and a healthy source still "
               f"reads ~1.1, so it cannot distinguish a working shape() from a broken "
               f"one.", ""]
        md += md_table(crit) + [""]

    fails, warns = [], []
    for src, g in d.groupby("source"):
        if src not in TEMPLATED_SOURCES:
            continue
        p = pool.get(src) or {}
        if p.get("shapes"):
            rps, thr, where = p["rows"] / p["shapes"], MIN_POOL_ROWS_PER_SHAPE, "pool"
        else:
            rps, thr, where = len(g) / g["shape"].nunique(), MIN_BUILT_ROWS_PER_SHAPE, "built"
        if rps < thr:
            fails.append(f"`{src}` {where} rows/shape {rps:.2f} < {thr}")
        elif where == "pool" and rps < WARN_POOL_ROWS_PER_SHAPE:
            warns.append(f"`{src}` pool rows/shape {rps:.2f}")
    ok_shape = not fails
    md.append(verdict(ok_shape,
                      "on the POOL metric, template-generated sources ("
                      + ", ".join(f"`{s}`" for s in sorted(TEMPLATED_SOURCES))
                      + ") collapse into shapes"
                      + ("." if ok_shape else ": VIOLATED - " + "; ".join(fails)
                         + ". This is P2's signature: shape() has stopped normalising "
                           "the randomised parts, every command is its own group, and "
                           "both the diversity sampling and the anti-leakage split "
                           "silently do nothing.")))
    if not pool:
        md.append(verdict(None, "stats.json carries no per-source pool shape counts, so "
                                "this check fell back to the built (post-cap) rows/shape, "
                                "which is bounded by MAX_PER_SHAPE and is a weak test. "
                                "build_dataset.py should record `shape_cap`."))
    for w in warns:
        md.append(verdict(None, w + f" is below the {WARN_POOL_ROWS_PER_SHAPE:.0f} watch "
                                    f"line (measured post-fix values: quasarnix 2,349, "
                                    f"honeypot 166). shape() may be partially regressed."))

    if cap:
        over = {s: m for s, m in worst.items() if m > cap}
        ok_cap = not over
        md.append(verdict(ok_cap,
                          f"the dedup cap MAX_PER_SHAPE={cap} holds for every source"
                          + ("." if ok_cap else ": VIOLATED by "
                             + ", ".join(f"`{s}`={m:,}" for s, m in sorted(over.items()))
                             + ". Decision D2 requires the cap to be applied uniformly to "
                               "every source, not only to QuasarNix.")))
    else:
        ok_cap = True
        md.append(verdict(None, "MAX_PER_SHAPE absent from stats.json; cap check skipped."))

    # split integrity. `first` is only meaningful where nunique == 1, which the
    # straddle check itself asserts, so the P7 counts are exact whenever it passes.
    agg = d.groupby(["shape", "label"])["split"].agg(["nunique", "first"])
    straddle = int((agg["nunique"] > 1).sum())
    wide = agg["first"].unstack()
    both = opposite = 0
    if wide.shape[1] == 2:
        pair = wide.notna().all(axis=1)
        both = int(pair.sum())
        opposite = int((pair & (wide.iloc[:, 0] != wide.iloc[:, 1])).sum())
    ok_split = straddle == 0
    md.append(verdict(ok_split, f"{straddle:,} shape groups straddle train and test within "
                                f"a label; must be 0, otherwise near-identical commands sit "
                                f"on both sides of the split and the score is memorisation."))
    md.append(verdict(None, f"{both:,} shapes occur under BOTH labels (P7); in {opposite:,} "
                            f"of those the two labels sit on opposite sides of the split. "
                            f"Reported, not failed: it makes the task harder, not easier - "
                            f"the model sees the structure labelled benign in training and "
                            f"must call it malicious at test."))

    # --- the same question again, without shape() --------------------------
    nn = nearest_train_neighbour(d)
    md += ["", "**Near-duplicate leakage (independent of `shape()`).** The straddle count "
               "above is only as good as `shape()`: if a family fails to collapse, the "
               "count reads 0 while near-identical rows sit on both sides of the split. "
               "So each test row is also compared to its most similar same-source TRAIN "
               "row directly, as binary character 4-gram sets under Jaccard similarity. "
               "1.00 means the two commands share every 4-gram. This metric is stricter "
               "than the difflib ratio the original finding used: changing one IPv4 "
               "octet in a 56-character command scores 0.846 here against difflib's "
               f"0.982. So {NEARDUP_LOOSE:.2f}, not {NEARDUP_SIM:.2f}, is where "
               "'recognisably the same command line' shows up, and both columns are "
               "given. The fail line is on the strict column; the loose column carries "
               "a watch line. The last column repeats the measurement on difflib's "
               "ratio, the metric the original 26.2% QuasarNix finding was made with, "
               "so the repair is reported on the ruler that found the bug; it is "
               "sampled where the exact computation would be quadratic and too slow, "
               "and carries a Wilson interval when it is.", ""]
    nrows, nfail, nwarn, ndl = [], [], [], []
    for r in sorted(nn, key=lambda r: -(r["share_loose"] or 0)):
        dl = r.get("difflib")
        nrows.append({"source": f"`{r['source']}`", "test rows": f"{r['n_test']:,}",
                      "median sim": _f(r["median"], 3), "p90 sim": _f(r["p90"], 3),
                      "max sim": _f(r["max"], 3),
                      f"share >= {NEARDUP_LOOSE:.2f}":
                          "n/a" if r["share_loose"] is None else f"{r['share_loose']:.1%}",
                      f"share >= {NEARDUP_SIM:.2f}":
                          "n/a" if r["share_ge"] is None else f"{r['share_ge']:.1%}",
                      f"difflib >= {NEARDUP_DIFFLIB_SIM:.2f}":
                          "n/a" if not dl else
                          f"{dl['share']:.1%} [{dl['ci'][0]:.1%}, {dl['ci'][1]:.1%}]"
                          + (f" (sampled {dl['n']:,})" if dl["sampled"] else ""),
                      "flag": "indicative only (n < %d)" % SMALL_N
                              if r["n_test"] < SMALL_N else ""})
        if r["share_ge"] is None:
            continue
        if r["share_ge"] >= NEARDUP_FAIL_SHARE:
            nfail.append(f"`{r['source']}` {r['share_ge']:.1%}")
        if r["share_loose"] >= NEARDUP_WARN_SHARE:
            nwarn.append(f"`{r['source']}` {r['share_loose']:.1%} "
                         f"({int(round(r['share_loose'] * r['n_test']))}/{r['n_test']})")
        if dl and dl["share"] >= NEARDUP_WARN_SHARE:
            ndl.append(f"`{r['source']}` {dl['share']:.1%}")
    md += md_table(nrows) + [""]
    ok_nd = not nfail
    md.append(verdict(ok_nd,
                      f"no source has more than {NEARDUP_FAIL_SHARE:.0%} of its test rows "
                      f"within {NEARDUP_SIM:.2f} Jaccard of a train row of the same source"
                      + ("." if ok_nd else ": VIOLATED - " + "; ".join(nfail)
                         + ". Those test rows are answered by memorisation, and the "
                           "shape-straddle count cannot see it.")))
    if ndl:
        md.append(verdict(None,
                          f"on difflib - the ruler the original finding used - these "
                          f"sources have more than {NEARDUP_WARN_SHARE:.0%} of their test "
                          f"rows at ratio >= {NEARDUP_DIFFLIB_SIM:.2f} from a train row: "
                          + "; ".join(ndl) + ". This is reported, not failed: at these "
                          "command lengths difflib rates `less /path/to/input-file` and "
                          "`zless /path/to/input-file` about 0.95 similar, and those are "
                          "two different programs, so the number is an upper bound on "
                          "leakage rather than a measurement of it. What it does mean is "
                          "that per-source recall for those sources is substantially "
                          "recall on close variants of training commands, and must not be "
                          "read as recall on unseen technique. For contrast, this is the "
                          "metric on which `quasarnix` measured 26.2% before the shape() "
                          "repair."))
    for w in nwarn:
        md.append(verdict(None, w + f" of test rows are within the LOOSE {NEARDUP_LOOSE:.2f} "
                                    f"line of a train row, above the "
                                    f"{NEARDUP_WARN_SHARE:.0%} watch line. Not a failure - "
                                    f"the assertion is on the {NEARDUP_SIM:.2f} column - but "
                                    f"per-source recall for that source is partly recall on "
                                    f"variants of commands it has already seen."))
    top = max((r for r in nn if r["pair"]), key=lambda r: r["max"], default=None)
    if top:
        md += ["", f"Closest surviving pair, `{top['source']}` (similarity "
                   f"{top['max']:.3f}):", "", "```",
               "test : " + top["pair"][0][:200], "train: " + top["pair"][1][:200], "```", ""]
    return md, (ok_shape and ok_cap and ok_split and ok_nd), nn


# ===========================================================================
# PROBE 3 / 5 - single-feature shortcut probes, with do-nothing floors
# ===========================================================================
# This one function replaces BOTH the inline `notes` probes that used to sit in
# main() (address rule scored on train+test, length rule on test, so the two were
# comparable with neither each other nor the model) and the parallel spec's
# separate probe_rows(): they measured the same two features and would have
# printed two tables of the same numbers under different headings.
def probe_single_feature(tag: str, d: pd.DataFrame,
                         matched: pd.DataFrame | None = None):
    """How far does one dumb feature get on its own? Every row carries its own
    prevalence and do-nothing floor, because F1 is not on an absolute scale.

    All rows are scored on the SAME test split as the model rows in the scores
    table, so their F1 is read against the same floor. The address rule is
    additionally reported dataset-wide, because the two scopes can differ
    materially once whole shape groups move to one side of the split (measured:
    Dataset 2's address rule is 0.1639 dataset-wide and 0.3419 on the test split).
    """
    rows = []
    tr, te = d[d["split"] == "train"], d[d["split"] == "test"]

    rows.append(make_row(tag, "do-nothing (always malicious)", te["label"],
                         y_pred=np.ones(len(te), dtype=int), note="test split"))
    ip = d["command"].str.contains(RE_IP).astype(int)
    rows.append(make_row(tag, "'contains an IPv4' rule", d["label"],
                         y_pred=ip, note="whole dataset"))
    rows.append(make_row(tag, "'contains an IPv4' rule", te["label"],
                         y_pred=ip.loc[te.index], note="test split"))

    c = LogisticRegression(max_iter=1000, class_weight="balanced",
                           random_state=SEED).fit(
        tr["command"].str.len().values.reshape(-1, 1), tr["label"])

    def length_only(frame):
        return pd.Series(
            c.predict_proba(frame["command"].str.len().values.reshape(-1, 1))[:, 1],
            index=frame.index)

    rows.append(make_row(tag, "length-only classifier", te["label"],
                         y_score=length_only(te), note="test split"))
    if matched is not None and len(matched):
        # The acceptance test for length_match(): if the subset really is length
        # matched, the length-only classifier must collapse to the floor there,
        # i.e. (F1 - floor)/(1 - floor) near 0 and ROC-AUC near 0.5. This is a
        # stronger check than eyeballing two medians.
        rows.append(make_row(tag, "length-only classifier", matched["label"],
                             y_score=length_only(matched),
                             note="length-matched 1:1 subset (p = 0.5000)"))

    md = ["A single feature that separates the classes is a shortcut: it says the "
          "dataset can be split without understanding the command. Read the "
          "`F1 - floor` column, never the raw F1 - an F1 of 0.40 at 25% prevalence "
          "is what a model that shouts MALICIOUS at everything already scores, and "
          "the first row measures exactly that.", "",
          "The last row is the acceptance test for the length ablation: on a subset "
          "that really is length-matched, a length-only classifier must be "
          "uninformative. Read its **ROC-AUC** (0.5 = no signal left); its F1 is not "
          "the right readout there, because the probe's threshold was fitted at "
          "p = 0.25 and the subset is p = 0.50.", ""]
    md += render_probe_table(rows) + [""]
    md.append(verdict(None, "single-feature probes are descriptive, not pass/fail: they "
                            "size each shortcut. Compare each `F1 - floor` with the trained "
                            "model's `F1 - floor` on the same rows in the scores table."))
    return md, None, rows


# ===========================================================================
# PROBE 4 - source separability (P8)
# ===========================================================================
# SEP_FAIL = 0.90 comes straight from KNOWN_ISSUES P8 ("if sources are trivially
#   separable, say F1 > 0.9"). Two statistics are asserted on:
#     (a) the multiclass benign-source macro-F1, and
#     (b) the MEAN pairwise benign-vs-benign macro-F1.
#   (b) is included because for a dataset with only two benign sources the
#   multiclass problem IS the pairwise one, while for five sources the multiclass
#   macro-F1 is depressed by 5-way confusion and can hide the fact that every
#   individual pair is near-perfectly separable. The provenance-matching claim is
#   pairwise in nature ("the attack side and the normal side come from the same
#   KIND of source"), so the pairwise measure is the faithful one.
# A FAIL here is a standing property of the corpora, not a build regression; the
#   emitted text says so, and says what it costs the project.
# SEP_FAIL alone is not a ruler. Macro-F1 has a do-nothing floor exactly as
#   binary F1 does, and that floor moves with BOTH the class balance and the
#   number of classes: always-predict-majority scores (2q/(1+q))/k. On a balanced
#   2-class pair that is 0.3333; on the 5-class benign problem at q = 0.40 it is
#   0.1143. Reading a raw 0.90 against one fixed line therefore asks far more of
#   the 5-class problem than of the 2-class one - the [medium] defect. Every
#   separability number below is printed with its own floor and with the
#   headroom-normalised value (v - floor)/(1 - floor), and the verdict fires on
#   EITHER scale, so no FAIL can be erased by choosing the flattering one.
# SEP_FAIL_NORM = 0.85 is SEP_FAIL translated through the floor of the reference
#   case the 0.90 was written for: a balanced two-class pair, (0.90 - 1/3)/(1 - 1/3).
SEP_FAIL = 0.90
SEP_FAIL_NORM = 0.85
SEP_WARN = 0.75
SEP_CAP_PER_CLASS = 3000     # train rows per class, keeps the 20+ fits cheap
SEP_MIN_TRAIN = 25           # skip a pair with fewer than this per side
SEP_MIN_TEST = 10
SEP_BOOT = 2000              # bootstrap resamples for the interval on a mean of pairs


def do_nothing_macro_f1(q: float, k: int) -> float:
    """Macro-F1 of always predicting the majority class, at majority share q over
    k classes. The one non-empty class contributes do_nothing_f1(q); the other
    k-1 contribute 0, and macro-F1 averages over all k. Expressed through
    do_nothing_f1 so this file still has exactly one definition of the floor."""
    return do_nothing_f1(q) / k if k > 0 else 0.0


def _norm(v: float | None, floor: float) -> float | None:
    """Headroom-normalised score: 0.0 = no better than the do-nothing predictor,
    1.0 = perfect. The column to compare across problems with different floors."""
    if v is None or floor >= 1.0 - 1e-12:
        return None
    return (v - floor) / (1.0 - floor)


def _boot_mean(vals: list[float], n: int = SEP_BOOT) -> tuple[float, float]:
    """Percentile bootstrap interval for the mean of a handful of pair scores.
    With 10 pairs a mean sitting 0.0005 the wrong side of a threshold is noise,
    and the caller needs to be able to say so."""
    if len(vals) < 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(SEED)
    a = np.asarray(vals, dtype=float)
    m = rng.choice(a, size=(n, a.size), replace=True).mean(axis=1)
    return (float(np.quantile(m, 0.025)), float(np.quantile(m, 0.975)))


def _sep_cap(df: pd.DataFrame, col: str, n: int) -> pd.DataFrame:
    return pd.concat([g.sample(n=min(len(g), n), random_state=SEED)
                      for _, g in df.groupby(col)])


def _sep_fit(tr: pd.DataFrame, te: pd.DataFrame, col: str):
    """Same TF-IDF + LogReg recipe as fit_predict(); kept inline because that
    helper is binary-only and returns probabilities of class 1."""
    v = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=3,
                        max_features=200_000, sublinear_tf=True)
    X = v.fit_transform(tr["command"])
    clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced",
                             random_state=SEED).fit(X, tr[col])
    return clf.predict(v.transform(te["command"]))


def _sep_pairs(d: pd.DataFrame, a_srcs, b_srcs, col: str, same: bool) -> list[dict]:
    """One 2-class separability fit per source pair. Each result carries the
    majority share of its own test set and the resulting do-nothing macro-F1
    floor, so no pairwise number can be quoted without its ruler."""
    out = []
    for a in a_srcs:
        for b in b_srcs:
            if same and a >= b:
                continue
            sub = d[d["source"].isin((a, b))]
            tr, te = sub[sub["split"] == "train"], sub[sub["split"] == "test"]
            n_tr, n_te = tr["source"].value_counts(), te["source"].value_counts()
            q = float(te[col].value_counts(normalize=True).max()) if len(te) else float("nan")
            floor = do_nothing_macro_f1(q, 2) if q == q else float("nan")
            rec = {"a": a, "b": b, "n_test": int(len(te)), "q": q, "floor": floor,
                   "macro": None, "norm": None}
            if len(n_tr) < 2 or len(n_te) < 2 or n_tr.min() < SEP_MIN_TRAIN \
               or n_te.min() < SEP_MIN_TEST:
                out.append(rec)
                continue
            pred = _sep_fit(_sep_cap(tr, "source", SEP_CAP_PER_CLASS), te, col)
            v = float(f1_score(te[col], pred, average="macro", zero_division=0))
            rec["macro"] = v
            rec["norm"] = _norm(v, floor)
            out.append(rec)
    return out


def probe_source_separability(tag: str, d: pd.DataFrame):
    """Ignore the real labels: can a classifier tell which PILE a command came
    from? The provenance-matching design assumes it cannot."""
    md = []
    ben = sorted(d.loc[d["label"] == 0, "source"].unique())
    mal = sorted(d.loc[d["label"] == 1, "source"].unique())

    macro = macro_floor = macro_norm = float("nan")
    macro_q, macro_k, macro_n = float("nan"), 0, 0
    if len(ben) > 1:
        bd = d[d["label"] == 0]
        tr = _sep_cap(bd[bd["split"] == "train"], "source", SEP_CAP_PER_CLASS)
        te = bd[bd["split"] == "test"]
        pred = _sep_fit(tr, te, "source")
        macro = float(f1_score(te["source"], pred, average="macro", labels=ben,
                               zero_division=0))
        macro_k, macro_n = len(ben), int(len(te))
        macro_q = float(te["source"].value_counts(normalize=True).max())
        macro_floor = do_nothing_macro_f1(macro_q, macro_k)
        macro_norm = _norm(macro, macro_floor)
        md += [f"**(a) Which benign source did this command come from?** {len(ben)} benign "
               f"sources, same TF-IDF + LogReg recipe, same train/test split, trained on "
               f"the benign part of train (capped at {SEP_CAP_PER_CLASS:,} rows per source) "
               f"and scored on the {len(te):,} benign rows of test. The malicious/benign "
               f"label is never used.", ""]
        cm = confusion_matrix(te["source"], pred, labels=ben)
        crows = []
        for i, s in enumerate(ben):
            r = {"true \\ predicted": f"`{s}`"}
            r.update({f"`{t}`": f"{cm[i][j]:,}" for j, t in enumerate(ben)})
            r["test n"] = f"{cm[i].sum():,}"
            r["recall"] = f"{cm[i][i] / max(1, cm[i].sum()):.3f}"
            crows.append(r)
        md += md_table(crows) + [""]
        md += [f"benign-source macro-F1 = **{macro:.4f}** on n = {macro_n:,} test rows over "
               f"k = {macro_k} classes, largest class {macro_q:.1%}. Always predicting that "
               f"largest class scores (2q/(1+q))/k = **{macro_floor:.4f}**, so the "
               f"headroom-normalised value is **{_f(macro_norm)}** "
               f"(0 = no better than that, 1 = perfect). The normalised column is the one "
               f"comparable with the 2-class pairs in (b); the raw column is not."
               + (" Note that with exactly two benign sources this multiclass problem IS "
                  "the single ben-vs-ben pair in (b): the two statistics below are one "
                  "fit reported twice, not two pieces of evidence."
                  if macro_k == 2 else ""), ""]
    else:
        md += ["**(a)** skipped: this dataset has fewer than two benign sources.", ""]

    mb = _sep_pairs(d, mal, ben, "label", same=False)
    bb = _sep_pairs(d, ben, ben, "source", same=True)
    md += ["**(b) One source against one source.** `mal-vs-ben` is the detection task "
           "restricted to a single source on each side. `ben-vs-ben` involves no "
           "maliciousness at all - it is pure collection-style separability, and it is "
           "the control that tells you how to read the mal-vs-ben column.", ""]
    md += ["Every row carries the majority share of its own test set, the do-nothing "
           "macro-F1 floor q/(1+q) that follows from it, and the headroom-normalised "
           "score. A pair at 0.95 against a floor of 0.49 and a pair at 0.95 against a "
           "floor of 0.33 are not the same result.", ""]

    def _prow(fam, r):
        return {"family": fam, "source A": f"`{r['a']}`", "source B": f"`{r['b']}`",
                "test n": f"{r['n_test']:,}",
                "majority q": _f(r["q"], 3),
                "floor": _f(r["floor"], 4),
                "macro-F1": _f(r["macro"]),
                "above floor": _sf(None if r["macro"] is None else r["macro"] - r["floor"]),
                "normalised": _f(r["norm"])}
    prows = [_prow("mal-vs-ben", r) for r in mb] + [_prow("ben-vs-ben", r) for r in bb]
    md += md_table(prows) + [""]
    mv = [r["macro"] for r in mb if r["macro"] is not None]
    bv = [r["macro"] for r in bb if r["macro"] is not None]
    mn = [r["norm"] for r in mb if r["norm"] is not None]
    bn = [r["norm"] for r in bb if r["norm"] is not None]
    perfect = [r for r in mb + bb if r["macro"] is not None and r["macro"] >= 0.99995]
    if perfect:
        md += [f"{len(perfect)} pair(s) score an exact 1.0000 - every test row assigned to "
               f"the right pile, no exceptions: "
               + ", ".join(f"`{r['a']}` vs `{r['b']}`" for r in perfect)
               + ". An exact 1.0000 is not 'very separable', it is a giveaway token: some "
                 "feature present in one pile and absent from the other decides every row, "
                 "and a model can reach those rows without learning anything about attacks."
               + (" For `quasarnix` the token is identified: every one of its rows contains "
                  "an IPv4 literal, against 0.00%-1.94% of each benign Dataset 1 source "
                  "(`ipv4_share_by_source` in stats.json)."
                  if any("quasarnix" in (r["a"], r["b"]) for r in perfect) else ""), ""]
    if mv:
        md.append(f"mean mal-vs-ben macro-F1 = **{np.mean(mv):.4f}** raw "
                  f"(min {min(mv):.4f}, max {max(mv):.4f}), **{np.mean(mn):.4f}** "
                  f"normalised, over {len(mv)} pairs.")
    if bv:
        md.append(f"mean ben-vs-ben macro-F1 = **{np.mean(bv):.4f}** raw "
                  f"(min {min(bv):.4f}, max {max(bv):.4f}), **{np.mean(bn):.4f}** "
                  f"normalised, over {len(bv)} pairs.")
    gap = gap_norm = float("nan")
    if mv and bv:
        gap = float(np.mean(mv) - np.mean(bv))
        gap_norm = float(np.mean(mn) - np.mean(bn))
        md += ["", f"**Style gap** (mal-vs-ben minus ben-vs-ben) = **{gap:+.4f}** on the raw "
                   f"scale, **{gap_norm:+.4f}** normalised. The two families do not share a "
                   f"ruler - their pairs have different class balances, so different floors "
                   f"(mal-vs-ben mean floor {np.mean([r['floor'] for r in mb if r['macro'] is not None]):.4f}, "
                   f"ben-vs-ben mean floor {np.mean([r['floor'] for r in bb if r['macro'] is not None]):.4f}) "
                   f"- and subtracting two raw means across different floors measures partly "
                   f"the difference in floors. The normalised gap is the one to read."]
    md.append("")
    md += ["**How to read this, and what a bad result costs the project.** This probe "
           "never looks at the malicious/benign label; it asks only whether a command "
           "carries a fingerprint of the pile it was collected from. Both datasets are "
           "built provenance-matched (attack side and normal side drawn from the same "
           "KIND of source) precisely so the classes cannot be told apart on collection "
           f"style, and that defence is worth exactly what this number says. Macro-F1 "
           f"above {SEP_FAIL:.2f} raw, or above {SEP_FAIL_NORM:.2f} once its own "
           f"do-nothing floor is divided out, means 'which pile is this' is "
           f"trivially learnable, the "
           "provenance-matching argument is design intent rather than a verified "
           "property, and the headline F1 must be presented as an upper bound that is "
           "partly corpus identification. Concretely, a bad result means: (1) the "
           "headline F1 may not be quoted without the cross-dataset transfer result "
           "beside it, since transfer is then the only evidence of generalisation; "
           "(2) DATA_CARD's provenance-matching paragraph must be downgraded from a "
           "property to an intention; (3) the ablations become load-bearing rather than "
           "confirmatory. A SMALL style gap is the reassuring case: it says telling an "
           "attack pile from a benign pile is no easier than telling two benign piles "
           "apart, so the detection score is not merely pile identification. Dataset 2 "
           "is the one to watch - its benign side is one Linux hobbyist's history (git, "
           "sudo nano, apt) and its malicious side is botnet traffic (busybox, tftp, "
           "chmod +x), so vocabulary alone could carry the score.", ""]

    # The verdict fires on EITHER scale. Raw > SEP_FAIL is the KNOWN_ISSUES line
    # as written; normalised > SEP_FAIL_NORM is the same line carried onto a
    # problem with a different floor. Requiring both would let a high floor
    # launder a failure; requiring either means introducing the floor cannot
    # erase a FAIL that the original rule would have raised.
    ok_multi = ok_pair = True
    if macro == macro:
        ok_multi = (macro <= SEP_FAIL) and (macro_norm is None or macro_norm <= SEP_FAIL_NORM)
        md.append(verdict(ok_multi,
                          f"benign-source macro-F1 = {macro:.4f} raw (line {SEP_FAIL:.2f}) "
                          f"and {_f(macro_norm)} normalised against its floor "
                          f"{macro_floor:.4f} (line {SEP_FAIL_NORM:.2f}); k = {macro_k} "
                          f"classes, n = {macro_n:,}. Both must hold."))
        if ok_multi and macro > SEP_WARN:
            md.append(verdict(None, f"macro-F1 {macro:.4f} is in the {SEP_WARN:.2f}-"
                                    f"{SEP_FAIL:.2f} concern band: benign sources are "
                                    f"already largely identifiable by style alone."))
    boot = (float("nan"), float("nan"))
    if bv:
        mean_bv, mean_bn = float(np.mean(bv)), float(np.mean(bn))
        ok_pair = (mean_bv <= SEP_FAIL) and (mean_bn <= SEP_FAIL_NORM)
        boot = _boot_mean(bv)
        md.append(verdict(ok_pair, f"mean pairwise benign-vs-benign macro-F1 = "
                                   f"{mean_bv:.4f} raw (line {SEP_FAIL:.2f}) and "
                                   f"{mean_bn:.4f} normalised (line {SEP_FAIL_NORM:.2f}), "
                                   f"over {len(bv)} pair(s). Both must hold. A FAIL here is "
                                   f"a standing property of the source corpora, not a "
                                   f"regression introduced by the last build - it does not "
                                   f"go away by rerunning."))
        if len(bv) == 1:
            md.append(verdict(None, "that mean is a single pair: this dataset has only two "
                                    "benign sources, so there is no spread to report and the "
                                    "verdict rests on one fit."))
        elif boot[0] == boot[0]:
            inside = boot[0] <= SEP_FAIL <= boot[1]
            md.append(verdict(None,
                              f"bootstrap over the {len(bv)} pairs (percentile, "
                              f"{SEP_BOOT:,} resamples) puts the mean in "
                              f"[{boot[0]:.4f}, {boot[1]:.4f}]"
                              + (f" - the {SEP_FAIL:.2f} line falls INSIDE that interval, so "
                                 f"the verdict is BORDERLINE: the sign of the margin "
                                 f"({mean_bv - SEP_FAIL:+.4f}) is not resolved by "
                                 f"{len(bv)} pairs and should not be reported as a clean "
                                 f"result in either direction."
                                 if inside else
                                 f" - the {SEP_FAIL:.2f} line is outside it, so the verdict "
                                 f"is not an artefact of which pairs happen to exist.")))
    if gap_norm == gap_norm:
        if gap_norm < 0.10:
            md.append(verdict(None, f"normalised style gap {gap_norm:+.4f} is small (< 0.10): "
                                    f"separating the attack pile from a benign pile is "
                                    f"barely harder than separating two benign piles, so "
                                    f"little of the headline score can be attributed to "
                                    f"maliciousness specifically."))
        else:
            md.append(verdict(None, f"normalised style gap {gap_norm:+.4f} is NOT small "
                                    f"(>= 0.10), although the raw gap {gap:+.4f} would have "
                                    f"read as small. The raw gap understates it because the "
                                    f"two families sit on different floors; the normalised "
                                    f"number is the one that answers the question."))
    stats = {"benign_macro_f1": None if macro != macro else float(macro),
             "benign_macro_floor": None if macro_floor != macro_floor else float(macro_floor),
             "benign_macro_f1_norm": macro_norm,
             "benign_macro_k": macro_k, "benign_macro_n": macro_n,
             "mal_vs_ben_pairs": mb,
             "ben_vs_ben_pairs": bb,
             "mean_mal_vs_ben": float(np.mean(mv)) if mv else None,
             "mean_ben_vs_ben": float(np.mean(bv)) if bv else None,
             "mean_mal_vs_ben_norm": float(np.mean(mn)) if mn else None,
             "mean_ben_vs_ben_norm": float(np.mean(bn)) if bn else None,
             "ben_vs_ben_boot95": None if boot[0] != boot[0] else list(boot),
             "style_gap": None if gap != gap else gap,
             "style_gap_norm": None if gap_norm != gap_norm else gap_norm}
    return md, (ok_multi and ok_pair), stats


# ===========================================================================
# aggregator
# ===========================================================================
PROBE_TITLES = {"probe_selection_regex": "P1 - selection-regex probe",
                "probe_rows_per_shape": "P2/P7 - rows-per-shape probe",
                "probe_single_feature": "P3/P5 - single-feature shortcut probes",
                "probe_source_separability": "P8 - source-separability probe"}


def run_probes(tag: str, d: pd.DataFrame, stats: dict, model_f1: float,
               matched: pd.DataFrame | None = None):
    """Run every permanent probe for one dataset.
    Returns (markdown lines, [(tag, title, ok), ...], {extra artefacts})."""
    out, verdicts = [], []
    extras: dict = {}
    plan = ((probe_selection_regex, (tag, d, model_f1)),
            (probe_rows_per_shape, (tag, d, stats)),
            (probe_single_feature, (tag, d, matched)),
            (probe_source_separability, (tag, d)))
    for fn, args in plan:
        t0 = time.time()
        result = fn(*args)
        md, ok = result[0], result[1]
        if len(result) > 2:
            extras[fn.__name__] = result[2]
        title = PROBE_TITLES[fn.__name__]
        print(f"  {tag}: {title}: "
              f"{'INFO' if ok is None else ('PASS' if ok else 'FAIL')}  "
              f"({time.time() - t0:.0f}s)")
        verdicts.append((tag, title, ok))
        out += [f"### {title} - {tag}", ""] + md + [""]
    return out, verdicts, extras


def probe_summary(verdicts) -> list[str]:
    """Top-of-report roll-up so a human scanning BASELINE.md sees regressions."""
    fails = [(t, p) for t, p, ok in verdicts if ok is False]
    md = ["## Regression probe summary", "",
          "These probes exist so the problems listed in `KNOWN_ISSUES.md` cannot come "
          "back unnoticed. Any FAIL invalidates the scores above it. Full detail, "
          "including every threshold and why it is set where it is, is in "
          "**Regression probe detail** at the end of this file.", "",
          "| dataset | probe | verdict |", "|---|---|---|"]
    for tag, title, ok in verdicts:
        md.append(f"| {tag} | {title} | "
                  f"**{'INFO' if ok is None else ('PASS' if ok else 'FAIL')}** |")
    md += ["", verdict(not fails,
                       "all assertive probes pass." if not fails else
                       f"{len(fails)} probe(s) FAILED: "
                       + "; ".join(f"{t} / {p}" for t, p in fails)
                       + ". Do not quote any score in this report until they pass "
                         "or the failure is explained in the text."), ""]
    return md


# ---------------------------------------------------------------------------
# DATA_CARD.md write-back
# ---------------------------------------------------------------------------
# DATA_CARD.md is written by build_dataset.py, which runs BEFORE any score
# exists, so it cannot state a measured outcome without either hard-coding one
# (how the "~1% label noise" claim survived for so long) or leaving the reader to
# go and find it. It therefore emits an empty marker block saying "not yet
# measured", and this function fills it in from the run that actually measured
# it. Rebuilding resets the block to "not yet measured"; that is the intended
# behaviour, because after a rebuild the old scores no longer describe the data.
DC_BEGIN = "<!-- BEGIN measured-outcomes -->"
DC_END = "<!-- END measured-outcomes -->"


def update_data_card(rows: list[dict], sep_stats: dict, verdicts: list[tuple],
                     loso_rows: list[dict], nd: dict[str, list[dict]],
                     path: Path | None = None) -> bool:
    """Rewrite DATA_CARD.md's measured-outcomes block. Returns False (and touches
    nothing) if the file or its markers are absent."""
    path = path or (DOCS / "DATA_CARD.md")
    if not path.exists():
        return False
    txt = path.read_text(encoding="utf-8")
    if DC_BEGIN not in txt or DC_END not in txt:
        return False

    def find(ds, setting):
        for r in rows:
            if r["dataset"] == ds and r["setting"] == setting:
                return r
        return None

    body = [DC_BEGIN,
            f"_Measured by `evaluate_baseline.py` (seed {SEED}) against the current "
            f"`dataset/`. Every score is shown with the prevalence it was measured at and "
            f"the do-nothing floor 2p/(1+p) that follows from it._", ""]
    trows = []
    for ds in ("dataset1", "dataset2"):
        r = find(ds, "full test (in-distribution)")
        if r:
            trows.append({"setting": f"`{ds}` in-distribution test", "n": f"{r['n']:,}",
                          "prevalence p": _f(r["p"], 3), "do-nothing floor": _f(r["floor"]),
                          "F1": _f(r["f1"]), "fraction of headroom": _f(r["f1_norm"])})
    for a, b in (("dataset1", "dataset2"), ("dataset2", "dataset1")):
        r = find(f"{a} -> {b}", "transfer (all rows of target)")
        if r:
            trows.append({"setting": f"transfer `{a}` -> `{b}`", "n": f"{r['n']:,}",
                          "prevalence p": _f(r["p"], 3), "do-nothing floor": _f(r["floor"]),
                          "F1": _f(r["f1"]), "fraction of headroom": _f(r["f1_norm"])})
    body += md_table(trows) + [""]

    t12, t21 = find("dataset1 -> dataset2", "transfer (all rows of target)"), \
        find("dataset2 -> dataset1", "transfer (all rows of target)")
    if t12 and t21:
        body += [f"**Transfer is not symmetric, and neither direction is a pass.** "
                 f"`dataset1 -> dataset2` reaches F1 {t12['f1']:.4f} against a floor of "
                 f"{t12['floor']:.4f} - above the floor, but only "
                 f"{t12['f1_norm']:.1%} of the available headroom, against "
                 f"{find('dataset2', 'full test (in-distribution)')['f1_norm']:.1%} for a "
                 f"model trained on Dataset 2 itself. `dataset2 -> dataset1` reaches "
                 f"{t21['f1']:.4f} against a floor of {t21['floor']:.4f} "
                 f"({t21['f1_norm']:+.1%} of headroom). The earlier wording "
                 f"\"both directions sit near or below the do-nothing floor\" was wrong "
                 f"about the first direction; the accurate statement is that one "
                 f"direction is clearly above its floor while capturing a small "
                 f"fraction of the headroom, and the other is not.", ""]

    for ds, s in sep_stats.items():
        fails = [ok for t, p, ok in verdicts if t == ds and p.startswith("P8")]
        v = "FAILED" if (fails and fails[0] is False) else (
            "passed" if fails and fails[0] else "not run")
        parts = [f"**P8 source separability, `{ds}`: {v}.**"]
        if s.get("benign_macro_f1") is not None:
            parts.append(f"Benign-source macro-F1 {s['benign_macro_f1']:.4f} over "
                         f"k = {s['benign_macro_k']} classes on n = {s['benign_macro_n']:,} "
                         f"rows, against a do-nothing floor of "
                         f"{s['benign_macro_floor']:.4f} "
                         f"({s['benign_macro_f1_norm']:.1%} of headroom).")
        if s.get("mean_ben_vs_ben") is not None:
            parts.append(f"Mean pairwise benign-vs-benign macro-F1 "
                         f"{s['mean_ben_vs_ben']:.4f} raw / "
                         f"{s['mean_ben_vs_ben_norm']:.4f} normalised over "
                         f"{len(s['ben_vs_ben_pairs'])} pair(s), against the "
                         f"{SEP_FAIL:.2f} raw / {SEP_FAIL_NORM:.2f} normalised lines."
                         + (" With only two benign sources these two statistics are the "
                            "same fit reported twice, not independent evidence."
                            if s.get("benign_macro_k") == 2 else ""))
        if s.get("ben_vs_ben_boot95"):
            lo, hi = s["ben_vs_ben_boot95"]
            parts.append(f"Bootstrap over pairs: [{lo:.4f}, {hi:.4f}]"
                         + (f" - the {SEP_FAIL:.2f} line is inside it, so this verdict is "
                            f"BORDERLINE and rests on a margin smaller than the spread "
                            f"between pairs." if lo <= SEP_FAIL <= hi else "."))
        if s.get("style_gap") is not None:
            parts.append(f"Style gap (mal-vs-ben minus ben-vs-ben) "
                         f"{s['style_gap']:+.4f} raw, {s['style_gap_norm']:+.4f} "
                         f"normalised; the normalised value is the comparable one "
                         f"because the two families have different floors.")
        body += [" ".join(parts), ""]

    lost = [r for r in loso_rows if not r["skipped"] and r["k_out"] / r["n"] < 0.50]
    kept = [r for r in loso_rows if not r["skipped"] and r["k_out"] / r["n"] >= 0.90]
    if loso_rows:
        body += ["**Leave-one-source-out.** Retraining with a malicious source deleted "
                 "from the training set and rescoring that source's test rows: "
                 + ("; ".join(f"`{r['source']}` {r['k_full'] / r['n']:.3f} -> "
                              f"{r['k_out'] / r['n']:.3f}"
                              for r in loso_rows if not r["skipped"]) or "no eligible source")
                 + ". Sources that keep their recall are reachable from the rest of the "
                   "corpus; sources that collapse were being recognised rather than "
                   "detected."
                 + (f" Collapsing: {', '.join('`' + r['source'] + '`' for r in lost)}."
                    if lost else "")
                 + (f" Holding above 0.90: {', '.join('`' + r['source'] + '`' for r in kept)}."
                    if kept else ""), ""]

    worst = [(ds, r) for ds, lst in nd.items() for r in lst
             if r.get("share_ge") is not None]
    if worst:
        ds, r = max(worst, key=lambda x: x[1]["share_loose"])
        dlw = sorted(({**x, "ds": t} for t, lst in nd.items() for x in lst
                      if x.get("difflib") and x["difflib"]["share"] >= NEARDUP_WARN_SHARE),
                     key=lambda x: -x["difflib"]["share"])
        body += [f"**Near-duplicate leakage** (measured without `shape()`, so it catches "
                 f"what a shape-group straddle count structurally cannot): every test row "
                 f"is compared to the most similar TRAIN row of its own source as character "
                 f"4-gram sets. The worst source is `{r['source']}` in `{ds}`, with "
                 f"{r['share_loose']:.1%} of its {r['n_test']:,} test rows above the loose "
                 f"{NEARDUP_LOOSE:.2f} line and {r['share_ge']:.1%} above the strict "
                 f"{NEARDUP_SIM:.2f} line (median similarity {r['median']:.3f}). The "
                 f"assertion is on the strict line at {NEARDUP_FAIL_SHARE:.0%}; per-source "
                 f"recall for a source above the loose line is partly recall on variants of "
                 f"commands already seen in training."
                 + (f" On difflib's ratio - the metric on which `quasarnix` measured 26.2% "
                    f"before the `shape()` repair, and 2.5% after it - the sources above "
                    f"{NEARDUP_WARN_SHARE:.0%} are: "
                    + "; ".join(f"`{x['source']}` ({x['ds']}) {x['difflib']['share']:.1%}"
                                for x in dlw)
                    + ". Those are curated corpora of short commands that share payload "
                      "templates, so the number is an upper bound on leakage, not a "
                      "measurement of it - but their per-source recall may not be quoted "
                      "as recall on unseen technique." if dlw else ""), ""]

    body.append(DC_END)
    head, _, rest = txt.partition(DC_BEGIN)
    _, _, tail = rest.partition(DC_END)
    path.write_text(head + "\n".join(body) + tail, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    rows: list[dict] = []
    src_rows: list[dict] = []
    overlaps: list[dict] = []
    coverage: dict[str, dict] = {}
    probe_md: list[str] = []
    all_verdicts: list[tuple] = []
    probe_rows_out: list[dict] = []
    loso_rows: list[dict] = []
    sep_stats: dict[str, dict] = {}
    nd_stats: dict[str, list[dict]] = {}
    model_f1: dict[str, float] = {}
    matched: dict[str, pd.DataFrame] = {}

    stats_path = DOCS / "stats.json"
    stats = (json.loads(stats_path.read_text(encoding="utf-8"))
             if stats_path.exists() else {})
    if not stats:
        print("  NOTE: docs/stats.json not found; the rows-per-shape probe will "
              "fall back to the weak built-rows test.")

    # na_filter=False is load-bearing, not defensive tidiness. dataset2 contains
    # the literal one-token commands `nan` (honeypot, malicious) and `null`
    # (bash_history, benign). With pandas' default NA sentinels both parse to
    # NaN, and the previous `.astype(str)` repair then rewrote BOTH to the string
    # "nan" -- inventing a duplicate command carrying label 1 in test and label 0
    # in train, i.e. a self-inflicted train/test collision with contradictory
    # labels. Reading every field as text keeps the two strings distinct.
    # Any downstream consumer of dataset/*.csv must do the same.
    # Train and test live in separate files; re-sorting the concat by id
    # reconstructs the exact row order the build wrote (ids were assigned
    # sequentially over the shuffled frame), so every seeded subsample below
    # sees the same frame it did when the two sides shipped as one file.
    dsets = {t: (pd.concat([pd.read_csv(DATA / f"{t}_{part}.csv", na_filter=False)
                            for part in ("train", "test")], ignore_index=True)
                 .sort_values("id", kind="stable").reset_index(drop=True))
             for t in ("dataset1", "dataset2")}
    for t, d in dsets.items():
        d["command"] = d["command"].astype(str)
        n_dup = int(d["command"].duplicated().sum())
        n_blank = int((d["command"].str.strip() == "").sum())
        if n_dup or n_blank:
            raise ValueError(
                f"{t} train/test CSVs did not survive the round-trip: {n_dup} duplicate "
                f"and {n_blank} blank command strings. The build deduplicates by "
                f"exact string, so either is a reader bug, not a data bug.")

    for tag, d in dsets.items():
        tr, te = d[d.split == "train"], d[d.split == "test"]

        # --- as-built -----------------------------------------------------
        scorer = fit_scorer(tr)
        ps = pd.Series(scorer(te["command"]), index=te.index)
        rows.append(make_row(tag, "full test (in-distribution)", te["label"], y_score=ps))
        model_f1[tag] = rows[-1]["f1"]

        m, info = length_match(te)
        matched[tag] = m
        coverage[f"{tag}/length-matched"] = info
        rows.append(make_row(
            tag, "ablation: length-matched 1:1 test subset",
            m["label"], y_score=ps.loc[m.index],
            note=(f"PREVALENCE DIFFERS from the full-test row (0.5000 by "
                  f"construction); only {info['n_matched']:,}/{info['n_malicious']:,} "
                  f"attacks ({info['coverage']:.1%}) could be matched -- same model, "
                  f"subset of the same test set")))

        # --- addresses stripped from BOTH classes -------------------------
        a = d.copy()
        a["command"] = a["command"].map(strip_addresses)
        atr, ate = a[a.split == "train"], a[a.split == "test"]
        pa = fit_predict(atr, ate)
        rows.append(make_row(tag, "ablation: addresses stripped (full test)",
                             ate["label"], y_score=pa,
                             note="same rows and same prevalence as the full-test row"))

        m2, info2 = length_match(ate)
        coverage[f"{tag}/no-addresses+length-matched"] = info2
        rows.append(make_row(
            tag, "ablation: addresses stripped + length-matched 1:1",
            m2["label"], y_score=pa.loc[m2.index],
            note=(f"PREVALENCE DIFFERS from the full-test row (0.5000 by "
                  f"construction); {info2['n_matched']:,}/{info2['n_malicious']:,} "
                  f"attacks ({info2['coverage']:.1%}) matched")))

        # --- per-source behaviour (P4) ------------------------------------
        pred = (ps > THRESHOLD).astype(int)
        per = []
        for s, g in te.assign(pred=pred).groupby("source"):
            lb = int(g["label"].iloc[0])
            k, n = int(g["pred"].sum()), int(len(g))
            per.append({
                "dataset": tag, "source": s,
                "class": "malicious" if lb else "benign",
                "label": lb,
                "metric": "recall" if lb else "false-positive rate",
                "k": k, "n": n, "rate": k / n if n else float("nan"),
                "ci": wilson(k, n), "small_n": n < SMALL_N,
            })
        per.sort(key=lambda r: (-r["label"], r["source"]))
        src_rows.extend(per)

        # --- leave-one-source-out (is a source's recall memorisation?) ------
        # Per-source recall in the table above is measured with that source in
        # the training set, so a high number is consistent with two very
        # different worlds: the model learned something general that also covers
        # the source, or it memorised the source's templates. Retraining with the
        # source deleted from TRAIN and scoring the same test rows separates
        # them. This is the experiment behind any claim that a corpus is
        # "lexically distinct": if recall survives its own removal, the rows are
        # reachable from the other sources; if it collapses, they were not.
        for s in sorted(te.loc[te["label"] == 1, "source"].unique()):
            g = te[te["source"] == s]
            tr2 = tr[tr["source"] != s]
            if g.empty or tr2["label"].nunique() < 2:
                loso_rows.append({"dataset": tag, "source": s, "n": int(len(g)),
                                  "k_full": None, "k_out": None, "skipped":
                                  "removing it leaves train single-class"})
                continue
            k1 = int((ps.loc[g.index] > THRESHOLD).sum())
            k2 = int((fit_predict(tr2, g) > THRESHOLD).sum())
            loso_rows.append({"dataset": tag, "source": s, "n": int(len(g)),
                              "k_full": k1, "k_out": k2,
                              "train_rows_removed": int(len(tr) - len(tr2)),
                              "ci_full": wilson(k1, len(g)), "ci_out": wilson(k2, len(g)),
                              "skipped": None})

        mal = [r for r in per if r["label"] == 1]
        for i in range(len(mal)):
            for j in range(i + 1, len(mal)):
                a_, b_ = mal[i], mal[j]
                ov = intervals_overlap(a_["ci"], b_["ci"])
                overlaps.append({
                    "dataset": tag, "a": a_["source"], "b": b_["source"],
                    "a_k_n": [a_["k"], a_["n"]], "b_k_n": [b_["k"], b_["n"]],
                    "a_ci": list(a_["ci"]), "b_ci": list(b_["ci"]),
                    "overlap": bool(ov),
                })

    # --- cross-dataset transfer -------------------------------------------
    for src, dst in (("dataset1", "dataset2"), ("dataset2", "dataset1")):
        s, t = dsets[src], dsets[dst]
        pt = fit_predict(s[s.split == "train"], t)
        rows.append(make_row(f"{src} -> {dst}", "transfer (all rows of target)",
                             t["label"], y_score=pt,
                             note="target's own prevalence, not the source's"))

    # --- permanent regression probes ---------------------------------------
    print("running regression probes")
    for tag, d in dsets.items():
        md_lines, v, extras = run_probes(tag, d, stats, model_f1[tag],
                                         matched=matched.get(tag))
        probe_md += md_lines
        all_verdicts += v
        probe_rows_out += extras.get("probe_selection_regex", [])
        probe_rows_out += extras.get("probe_single_feature", [])
        if "probe_source_separability" in extras:
            sep_stats[tag] = extras["probe_source_separability"]
        if "probe_rows_per_shape" in extras:
            nd_stats[tag] = extras["probe_rows_per_shape"]

    # ------------------------------------------------------------------
    # report
    # ------------------------------------------------------------------
    md = [
        "# Baseline and shortcut audit",
        "",
        "TF-IDF (char_wb 3-5 grams) + logistic regression, decision threshold "
        f"{THRESHOLD}. Generated by `evaluate_baseline.py`, seed {SEED}. This is a "
        "deliberately simple model: it exists to expose shortcuts, not to be the "
        "project's detector.",
        "",
        "## How to read this table",
        "",
        "F1 has no absolute scale -- it depends on the prevalence *p* of the "
        "malicious class in whatever test set it was measured on. A model that "
        "ignores its input and predicts MALICIOUS every time scores "
        "**2p/(1 + p)**: 0.400 at p = 0.25, 0.667 at p = 0.50, 0.908 at p = 0.83. "
        "So an F1 of 0.99 on an 83%-malicious subset is a *weaker* result than "
        "0.985 on a 25%-malicious one. Two columns make this explicit:",
        "",
        "* **F1 - floor** -- raw distance above the do-nothing model, in F1 points. "
        "Comparable only against rows of the same prevalence.",
        "* **(F1 - floor)/(1 - floor)** -- the same distance as a fraction of the "
        "available headroom: 0 means \"no better than always-malicious\", 1 means "
        "perfect, negative means worse than do-nothing. This is the column to use "
        "when prevalences differ.",
        "",
        "PR-AUC gets the same treatment: a random ranker's average precision is "
        "exactly *p*, reported as **PR-AUC base**. ROC-AUC's baseline is always "
        "0.5 and is not tabulated.",
        "",
        "Rows whose prevalence differs from their dataset's full-test row say so "
        "in the setting cell.",
        "",
        "## Scores",
        "",
    ]
    md += render_table(rows)
    md += [""] + probe_summary(all_verdicts)

    md += ["", "## Length matching: coverage and whether the lengths actually matched", "",
           "The length ablation asks whether the model is separating the classes on "
           "command length. It can only answer that question over the attacks it "
           "could actually pair with a benign command of the same length. Attacks "
           "with no partner are dropped (making the subset exactly 1:1); the "
           "fraction dropped is the honest limit on what the ablation proves.", ""]
    md += md_table([{
        "subset": k,
        "matched / attacks": f"{i['n_matched']:,} / {i['n_malicious']:,}",
        "coverage": f"{i['coverage']:.1%}",
        "tolerance": i["tolerance"],
        "median len mal (before -> after)":
            f"{i['median_len_mal_before']:.0f} -> {i['median_len_mal_after']:.0f}",
        "median len benign (before -> after)":
            f"{i['median_len_ben_before']:.0f} -> {i['median_len_ben_after']:.0f}",
        "mean len after (mal / benign)":
            f"{i['mean_len_mal_after']:.1f} / {i['mean_len_ben_after']:.1f}",
        "median \\|delta\\| in a pair": f"{i['median_abs_pair_diff']:.0f}",
        "max \\|delta\\|": f"{i['max_abs_pair_diff']:.0f}",
        "medians matched?": "yes" if i["medians_matched"] else "**NO**",
    } for k, i in coverage.items()])
    low = [k for k, i in coverage.items() if i["coverage"] < 0.5]
    if low:
        md += ["", "> **Coverage warning.** " + "; ".join(
            f"`{k}` matched only {coverage[k]['coverage']:.1%} of its attacks"
            for k in low) + ". The benign pool does not contain enough long "
            "commands to pair with the long attacks, so the length ablation "
            "speaks only for the short end of the malicious class. Do not quote "
            "these rows as evidence that length is not a shortcut for the whole "
            "dataset."]

    # the width quoted in the paragraph below is measured, not remembered: the
    # old text hard-coded "n = 27 -> +/-0.14" from a build whose smallest source
    # no longer has 27 test rows.
    _smallest = min(src_rows, key=lambda r: r["n"]) if src_rows else None
    md += ["", "## Per-source behaviour on the test split", "",
           "Recall for malicious sources, false-positive rate for benign ones, as "
           "**k/n with a Wilson 95% interval**. A high headline F1 with weak recall "
           "outside the dominant generator means the model learned one source, not "
           "the technique. Point estimates from fewer than "
           f"{SMALL_N} samples are marked *indicative only*"
           + (f": the smallest source here is `{_smallest['source']}` at n = "
              f"{_smallest['n']}, whose Wilson interval is "
              f"[{_smallest['ci'][0]:.3f}, {_smallest['ci'][1]:.3f}], i.e. "
              f"+/-{(_smallest['ci'][1] - _smallest['ci'][0]) / 2:.3f} wide, so a third "
              f"decimal place is noise." if _smallest else "."), ""]
    md += render_source_table(src_rows)

    md += ["", "### Leave-one-source-out: is a source's recall memorisation?", "",
           "Each malicious source is deleted from the TRAINING set, the model is "
           "refit on what remains, and the same test rows of that source are scored "
           "again. `recall (in train)` is the number from the table above; `recall "
           "(source removed)` is what survives when nothing of that source was ever "
           "seen. A source that keeps its recall is reachable from the rest of the "
           "corpus; a source that collapses was being recognised, not detected. Read "
           "this beside the near-duplicate table in the P2/P7 probe: those two "
           "together are the evidence for or against 'this corpus is lexically "
           "distinct'.", ""]
    lrows = []
    for r in loso_rows:
        if r["skipped"]:
            lrows.append({"dataset": r["dataset"], "source": f"`{r['source']}`",
                          "test n": f"{r['n']:,}", "train rows removed": "n/a",
                          "recall (in train)": "n/a", "recall (source removed)": "n/a",
                          "delta": f"skipped: {r['skipped']}"})
            continue
        r1, r2 = r["k_full"] / r["n"], r["k_out"] / r["n"]
        lrows.append({"dataset": r["dataset"], "source": f"`{r['source']}`",
                      "test n": f"{r['n']:,}",
                      "train rows removed": f"{r['train_rows_removed']:,}",
                      "recall (in train)":
                          f"{r1:.3f} [{r['ci_full'][0]:.3f}, {r['ci_full'][1]:.3f}]",
                      "recall (source removed)":
                          f"{r2:.3f} [{r['ci_out'][0]:.3f}, {r['ci_out'][1]:.3f}]",
                      "delta": f"{r2 - r1:+.3f}"})
    md += md_table(lrows) + [""]
    _kept = [r for r in loso_rows if not r["skipped"] and r["k_out"] / r["n"] >= 0.90]
    if _kept:
        md += ["Sources holding recall >= 0.90 with themselves removed from training: "
               + ", ".join(f"`{r['source']}` ({r['k_out'] / r['n']:.3f})" for r in _kept)
               + ". For those sources the score is not self-memorisation - though it can "
                 "still be memorisation of a *different* source that resembles them, "
                 "which is what the near-duplicate table checks.", ""]
    _lost = [r for r in loso_rows if not r["skipped"] and r["k_out"] / r["n"] < 0.50]
    if _lost:
        md += ["> **Sources whose recall collapses without themselves in training:** "
               + "; ".join(f"`{r['source']}` {r['k_full'] / r['n']:.3f} -> "
                           f"{r['k_out'] / r['n']:.3f}" for r in _lost)
               + ". Their contribution to the headline F1 is recognition of their own "
                 "corpus, and the headline must not be quoted as evidence that the model "
                 "generalises to those techniques.", ""]

    md += ["", "### Pairwise separability of malicious sources (machine-checkable)", "",
           "One line per pair of malicious sources within a dataset. `OVERLAP` "
           "means the two Wilson intervals intersect and **no claim that one "
           "source scores better than the other is supported**. Grep this block "
           "before writing any comparative sentence.", "", "```"]
    for o in overlaps:
        mark = "OVERLAP  " if o["overlap"] else "SEPARATED"
        md.append(f"{mark} {o['dataset']} {o['a']}[{o['a_ci'][0]:.3f},{o['a_ci'][1]:.3f}]"
                  f" vs {o['b']}[{o['b_ci'][0]:.3f},{o['b_ci'][1]:.3f}]")
    if not overlaps:
        md.append("(no dataset has two or more malicious sources)")
    md += ["```", ""]

    md += ["## Regression probe detail", ""] + probe_md

    (DOCS / "BASELINE.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (DOCS / "baseline_metrics.json").write_text(json.dumps({
        "seed": SEED, "threshold": THRESHOLD, "z95": Z95, "small_n": SMALL_N,
        "scores": rows, "probes": probe_rows_out, "per_source": [
            {**r, "ci": list(r["ci"])} for r in src_rows],
        "source_pairs": overlaps, "length_matching": coverage,
        "probe_verdicts": [{"dataset": t, "probe": p, "verdict":
                            "INFO" if ok is None else ("PASS" if ok else "FAIL")}
                           for t, p, ok in all_verdicts],
        "source_separability": sep_stats,
        "leave_one_source_out": [
            {**r, "ci_full": list(r.get("ci_full") or []),
             "ci_out": list(r.get("ci_out") or [])} for r in loso_rows],
        "near_duplicate": {t: [{k: v for k, v in r.items() if k != "pair"} for r in lst]
                           for t, lst in nd_stats.items()},
        "thresholds": {"MAX_REGEX_RECALL": MAX_REGEX_RECALL,
                       "WARN_REGEX_RECALL": WARN_REGEX_RECALL,
                       "MIN_MODEL_MARGIN": MIN_MODEL_MARGIN,
                       "WARN_MODEL_MARGIN": WARN_MODEL_MARGIN,
                       "MIN_POOL_ROWS_PER_SHAPE": MIN_POOL_ROWS_PER_SHAPE,
                       "WARN_POOL_ROWS_PER_SHAPE": WARN_POOL_ROWS_PER_SHAPE,
                       "MIN_BUILT_ROWS_PER_SHAPE": MIN_BUILT_ROWS_PER_SHAPE,
                       "NEARDUP_SIM": NEARDUP_SIM, "NEARDUP_LOOSE": NEARDUP_LOOSE,
                       "NEARDUP_DIFFLIB_SIM": NEARDUP_DIFFLIB_SIM,
                       "NEARDUP_DIFFLIB_BUDGET": NEARDUP_DIFFLIB_BUDGET,
                       "NEARDUP_FAIL_SHARE": NEARDUP_FAIL_SHARE,
                       "NEARDUP_WARN_SHARE": NEARDUP_WARN_SHARE,
                       "SEP_FAIL": SEP_FAIL, "SEP_FAIL_NORM": SEP_FAIL_NORM,
                       "SEP_WARN": SEP_WARN,
                       "TEMPLATED_SOURCES": sorted(TEMPLATED_SOURCES)},
    }, indent=2, default=float), encoding="utf-8")
    wrote_card = update_data_card(rows, sep_stats, all_verdicts, loso_rows, nd_stats)
    print("\n".join(md))
    print("\nwrote docs/BASELINE.md and docs/baseline_metrics.json"
          + (" and updated DATA_CARD.md's measured-outcomes block" if wrote_card else
             "; DATA_CARD.md has no measured-outcomes markers, left untouched"))


if __name__ == "__main__":
    main()
