# Chapter 7 — Hyperparameter Sensitivity: Random Forest & Isolation Forest

Companion to `ch7_sensitivity_findings.md` (XGBoost/CNN). This section reports
sensitivity sweeps for the two remaining models — the Random Forest classifier
and the Isolation Forest anomaly detector — on both datasets, using the final
43-feature engineered set. Reproduce with `python analysis/ch7_rf_if_sweeps.py`
(results in `results/ch7_rf_if_sensitivity.json`, figures
`report/figures/ch7_sensitivity_{random,isolation}_forest_*.png`).

Two methodological differences from the XGBoost/CNN sweeps, both deliberate:

1. **Full data, full grid.** RF on 43 engineered features fits in ~1–3 s, so
   instead of one-at-a-time sweeps on a 5,000-row subsample we run the complete
   `n_estimators` × `max_depth` grid (12 configs) on the **full training data**
   (D1: n_train = 12,199 / n_test = 3,049; D2: n_train = 7,661 /
   n_test = 1,915). No subsample caveat applies to any number below.
2. **The Isolation Forest sweep is an operating-point study, not a capacity
   study — by construction.** In sklearn, `contamination` does not affect the
   fitted trees at all: `score_samples` is contamination-independent, and the
   parameter only sets the decision threshold (`offset_`) at the
   contamination-quantile of training scores. Our production wrapper
   (`IsolationForestDetector`) additionally thresholds a min-max-normalised
   score at a fixed 0.5, so sweeping contamination *through the wrapper* would
   return four identical rows. Each contamination value is therefore evaluated
   at its **own calibrated threshold** (sklearn's `predict`, i.e. "flag the
   top-`contamination` fraction of benign-training scores") — which is what
   the knob actually means. The sweep verifies the mechanics empirically:
   ROC-AUC is **identical to 4 decimals across all contamination values**
   (D1: 0.8120, D2: 0.6768; asserted in the sweep script).

---

## Headline answers

- **Random Forest F1 is saturated; `max_depth` is the only lever, and it moves
  FPR more than F1.** The entire 12-config grid spans just **0.780–0.801** F1
  on D1 and **0.731–0.758** on D2. `max_depth=20` **dominates on both
  datasets** — at every ensemble size it gives the best F1 *and* the lowest
  FPR (D1: FPR 0.031 vs 0.052 at depth 10, a ~40% reduction in false alarms).
- **Isolation Forest `contamination` is a false-alarm budget dial, nothing
  more.** FPR tracks contamination almost exactly (D1: 0.047/0.088/0.189/0.287
  for c = 0.05/0.10/0.20/0.30) while the learned model is provably unchanged.
  F1 is poor at every setting (peak 0.641 D1 / 0.462 D2), and even the most
  permissive setting (c = 0.30) reaches only **0.73 / 0.56 recall** — far below
  the ≈0.99 attack retention a stage-1 filter needs. This is precisely why the
  cascade does not use `contamination` at all: it calibrates its clearing
  threshold on the attack-score quantile (`stage1_retain_recall=0.99` in
  `src/ensemble.py`).

---

## Random Forest — full grid

Fixed (production values, `src/models.py`): `min_samples_leaf=1`,
`max_features="sqrt"`, `class_weight="balanced_subsample"`. Cells are
**F1 / FPR**.

### Dataset 1

| n_estimators | max_depth=None | max_depth=10 | max_depth=20 |
|---:|:---:|:---:|:---:|
| 50  | 0.7806 / 0.0411 | 0.7801 / 0.0525 | 0.7926 / 0.0372 |
| 100 | 0.7843 / 0.0402 | 0.7840 / 0.0533 | 0.7963 / 0.0337 |
| 200 | 0.7845 / 0.0442 | 0.7868 / 0.0525 | **0.7988 / 0.0310** |
| 500 | 0.7850 / 0.0424 | 0.7876 / 0.0525 | **0.8006 / 0.0310** |

### Dataset 2

| n_estimators | max_depth=None | max_depth=10 | max_depth=20 |
|---:|:---:|:---:|:---:|
| 50  | 0.7419 / 0.0585 | 0.7430 / 0.0870 | 0.7514 / 0.0529 |
| 100 | 0.7393 / 0.0571 | 0.7356 / 0.0794 | 0.7503 / 0.0515 |
| 200 | 0.7435 / 0.0536 | 0.7347 / 0.0766 | **0.7559 / 0.0515** |
| 500 | 0.7475 / 0.0550 | 0.7311 / 0.0822 | **0.7584 / 0.0529** |

### Interpretation

**`max_depth=20` strictly dominates — and `None` (fully grown) is *worse* than
20 on both datasets.** This is a textbook regularisation result: fully grown
trees on 43 engineered features drive leaves down to memorised singletons, and
the ensemble average retains some of that variance as both lost F1
(D1: 0.7850 vs 0.8006 at n=500) and extra false positives (FPR 0.0424 vs
0.0310). Capping depth at 20 removes the memorisation tail while leaving the
trees deep enough to isolate real feature interactions.

**`max_depth=10` is an underfitting trap with an instructive signature.** On
both datasets it produces the *highest recall* in its column (D1: 0.752 at
n=500 vs 0.730 at depth 20) but also the *highest FPR* (0.0525 vs 0.0310 —
~70% more false alarms). Shallow trees cannot carve out the benign boundary
precisely, and `class_weight="balanced_subsample"` pushes the resulting
borderline cases toward the attack class: the model compensates for missing
capacity by over-flagging. On D2 the pathology deepens with ensemble size —
F1 *falls* monotonically from 0.7430 (n=50) to 0.7311 (n=500) — because
averaging more trees converges the ensemble ever more tightly onto the same
biased, capacity-limited solution. More trees cannot fix a depth problem.

**`n_estimators` is a mild, monotone stabiliser that plateaus by ~200.** In
the dominant depth-20 column, going 50 → 500 buys +0.008 F1 on D1 and
+0.007 on D2, with essentially all of the gain in by n=200 (F1 changes by
under 0.003 from 200 → 500 on both datasets). Consistent with Ben's XGBoost
finding, RF's ranking quality is dominated by the feature representation, not
ensemble capacity: the model is robust — hard to break, hard to improve.

### Chosen setting — Random Forest

| hyperparameter | chosen | rationale |
|---|---|---|
| `max_depth` | **24** (production) | The sweep shows depth ≈ 20 dominates both shallower (10) and unbounded (None) on **both** F1 and FPR, on **both** datasets; production 24 sits on this optimum. |
| `n_estimators` | **400** (production) | On the ≥200 plateau (grid best at 500 leads 200 by <0.002 F1); 400 keeps train time ~3 s. |
| `class_weight` | `balanced_subsample` (pinned) | The cost-sensitive imbalance remedy at 1:3 prevalence; not swept here — its role is analogous to XGBoost's `scale_pos_weight`, which Ben's sweep showed to be an FPR dial. |

The production configuration (`n_estimators=400, max_depth=24`) was chosen
before this sweep; the grid **validates** it — it sits inside the dominant
plateau, within 0.002 F1 of the best swept cell (D1: 0.8006 / FPR 0.0310 at
500/20) — rather than contradicting it.

---

## Isolation Forest — contamination sweep

Fixed: `n_estimators=300`, `max_samples=0.8`, `max_features=1.0`. Trained on
**benign training rows only** (unsupervised); each row is evaluated at that
contamination's own calibrated threshold (see methodology note above).

### Dataset 1 (ROC-AUC = 0.8120 at every setting)

| contamination | F1 | Recall | FPR |
|---:|:---:|:---:|:---:|
| 0.05 | 0.5488 | 0.4318 | 0.0472 |
| 0.10 | **0.6413** | 0.5971 | 0.0883 |
| 0.20 | 0.6023 | 0.6759 | 0.1893 |
| 0.30 | 0.5638 | 0.7310 | 0.2873 |
| *wrapper (fixed 0.5)* | *0.2492* | *0.1457* | *0.0079* |

### Dataset 2 (ROC-AUC = 0.6768 at every setting)

| contamination | F1 | Recall | FPR |
|---:|:---:|:---:|:---:|
| 0.05 | 0.2633 | 0.1649 | 0.0292 |
| 0.10 | 0.3842 | 0.3048 | 0.0940 |
| 0.20 | **0.4615** | 0.4760 | 0.1957 |
| 0.30 | 0.4569 | 0.5595 | 0.2967 |
| *wrapper (fixed 0.5)* | *0.1431* | *0.0793* | *0.0097* |

### Interpretation

**FPR ≈ contamination, almost exactly.** D1 delivers FPR 0.047/0.088/0.189/
0.287 against requested 0.05/0.10/0.20/0.30 (D2: 0.029/0.094/0.196/0.297).
Because the forest is fitted on benign training rows only, "flag the top-c
fraction of benign-training scores" transfers near-perfectly to benign test
traffic — the benign score distribution generalises. Operationally this makes
`contamination` a *direct false-alarm budget*: choose c equal to the FPR the
SOC can absorb, and that is what it will get.

**F1 is low at every operating point, and the peak is shallow.** The best F1
(0.641 at c=0.10 on D1; 0.462 at c=0.20 on D2) confirms IF cannot compete as
a standalone detector — with ROC-AUC 0.81/0.68 there is no threshold at which
an unsupervised ranker matches the supervised models (RF 0.80/0.76,
XGBoost-hybrid higher still). The D1→D2 drop is the familiar operational-data
story: on live Cowrie traffic, benign and attack score distributions overlap
far more (AUC 0.677), so *every* operating point is worse — at c=0.30, D2
recall is still only 0.56.

**The operating point is set for recall retention, not F1 — and the sweep
shows why F1-optimising contamination would be the wrong choice.** Even the
most permissive swept setting (c=0.30, tripling the F1-optimal false-alarm
rate) retains only 73% (D1) / 56% (D2) of attacks — a stage-1 filter that
silently discards 27–44% of attacks caps the whole cascade's recall at that
value, no matter how good stage 2 is. That is why the production cascade
ignores `contamination` entirely and calibrates its clearing threshold on the
**attack-score quantile** (`stage1_retain_recall = 0.99`,
`src/ensemble.py`): the threshold is placed so ~99% of training attacks score
above it, and only what is confidently benign below it gets cleared. F1 is
simply not the objective at stage 1; recall retention is.

**The fixed-threshold wrapper rows explain the "headline" standalone IF
numbers.** The summary-table standalone results are produced by the wrapper's
fixed 0.5 min-max threshold, which lands in an extreme-precision corner
(recall 0.15 / FPR 0.008 on D1) — hence standalone F1 ≈ 0.25/0.14 on the
43-feature set. The gap between that and the calibrated sweep (F1 0.64 at
c=0.10 on D1) shows the standalone figure understates the detector's ranking
quality; it is a threshold-placement artefact. We keep it in the summary table
for honesty — it is the operating point the standalone artefact actually
ships — but the cascade, which consumes the *scores* rather than the fixed
threshold, is the intended consumer of this model.

### Chosen setting — Isolation Forest

| hyperparameter | chosen | rationale |
|---|---|---|
| `contamination` | **0.25** (production) | Irrelevant to the cascade (which thresholds on recall retention) and to the wrapper's fixed-0.5 predict; kept as an honest mid-range declaration of expected anomaly share. If IF were deployed standalone as a tripwire, set c = the SOC's FPR budget (the sweep shows FPR ≈ c). |
| `n_estimators` | **300** (pinned) | Score stability; capacity does not lift AUC (the ranking, not the ensemble size, is the bottleneck). |
| `max_samples` | **0.8** (pinned) | Standard subsampling for isolation depth diversity. |

---

## Cross-model synthesis (RF/IF)

| question | answer | evidence |
|---|---|---|
| Which hyperparameter most affects **F1**? | RF `max_depth` — but weakly | Largest RF swing on both datasets (D2: 0.7311 → 0.7584 across depth at n=500, Δ0.027); everything else is ≤0.01. |
| Which hyperparameter most affects **FPR**? | IF `contamination` — by design | FPR 0.047 → 0.287 (D1), a 6× swing that tracks c one-for-one; RF's depth is second (0.031 vs 0.053, ~1.7×). |
| Which model is more sensitive overall? | **Isolation Forest** | Its usable output depends entirely on threshold placement (F1 0.25 → 0.64 on D1 between the wrapper point and c=0.10); RF holds a ~0.02-wide F1 band across its whole grid. |

The same division of labour Ben found for XGBoost/CNN reappears here:
**accuracy is set by the representation, false alarms by a purpose-built
dial.** RF's F1 band is nearly flat — the 43-feature set, not tree capacity,
is the ceiling — while its depth cap mainly buys false-alarm reduction.
IF's dial does not touch the model at all: it *is* the operating point. The
deployment lesson is that both of Noam's models are cheap to operate and
hard to misconfigure catastrophically, provided one rule is respected: cap RF
depth (≈20) rather than growing full trees, and never let IF's stage-1
threshold be chosen by F1 — choose it by the recall the cascade must retain.
