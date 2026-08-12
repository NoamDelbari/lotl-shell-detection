# 7.2 — Class Imbalance Strategy and Validation Framework

Both datasets are held at an exact **1 attack : 3 benign** ratio (Dataset 1
3,812 / 11,436; Dataset 2 2,394 / 7,182), so attack prevalence is **0.250**.
The ratio is deliberate: malicious commands are rare in real host telemetry, and
a balanced corpus would overstate precision (`docs/DATA_CARD.md`). It has two
consequences that shape everything below — a classifier that predicts "benign"
for every input scores **75% accuracy**, and the do-nothing floor for F1 is
**0.400**, which is why accuracy is not reported as a headline anywhere in this
report and why two of our models must be read against that floor rather than
against each other.

## Imbalance strategy: cost-sensitive reweighting, not resampling

Every supervised model carries an explicit, per-model imbalance remedy; none is
left to a library default.

| Model | Remedy | Value | Reference |
|---|---|---|---|
| XGBoost (engineered) | `scale_pos_weight` | 3.0 = n_neg/n_pos | `src/models.py:53` |
| XGBoost-hybrid | `scale_pos_weight` | 3.0 | `src/models.py:95` |
| Random Forest | `class_weight` | `"balanced_subsample"` — reweighted per bootstrap draw | `src/models.py:139` |
| 1D-CNN | class-weighted cross-entropy | positive class up-weighted; "the sequence analogue of `scale_pos_weight`" | `src/models.py:227` |
| Isolation Forest | none — trained benign-only | `contamination` sets the operating point, not a class prior | `src/models.py:172-182` |

`scale_pos_weight = 3.0` multiplies the gradient of the positive class so the
3:1 benign majority does not pull the decision boundary toward "benign."

**We deliberately do not resample.** Every model is wrapped in imblearn's
`ImbPipeline` rather than sklearn's `Pipeline` precisely so that adding SMOTE or
random oversampling would be a one-line, leakage-safe change
(`src/models.py:30-33`) — but no sampler is enabled. The reason is specific to
this corpus: the data is already capped at **at most 2 commands per distinct
command shape** and still carries measured near-duplicate leakage between train
and test (worst case `slp`/Dataset 1, 17.4% of test rows above a 0.80 character
4-gram similarity to a training row). Synthesising or duplicating minority
command strings would amplify exactly the near-duplicate structure that the
shape cap and the grouped split were built to suppress, inflating recall on
variants of commands the model has already seen. Reweighting changes the loss
without adding a single new row, so it cannot manufacture leakage.

## Validation framework

Three nested controls, each closing a different leakage channel:

| Level | Mechanism | What it prevents |
|---|---|---|
| Hold-out | 80/20 train/test, **grouped by command shape** — an identical structure never straddles the split; materialised into `dataset/dataset{1,2}_{train,test}.csv` at build time (`scripts/build_dataset.py`) | Memorising a command in training and "detecting" the same structure at test |
| Cross-validation | `StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)`, a **fresh model built per fold** (`src/evaluation.py:64-69`) | Class-ratio drift between folds; state carried across folds |
| In-fold fitting | Every learned transform — scaler statistics, char n-gram vocabulary, a sampler if one were added — sits *inside* the pipeline, so it is fit on the training fold only (`src/models.py:14-18`) | The classic scaler/vectoriser-fit-on-all-data leak |

Stratification is on the label, so each fold reproduces the 0.250 prevalence and
per-fold metrics stay commensurable. The seed is fixed project-wide
(`src/SEED`), and the tree models are deterministic under it, so every number in
this report is reproducible from a clean checkout.

**How much the grouping actually costs — measured.** The two controls differ in
one respect that matters: the hold-out is grouped by command shape, while the
cross-validation folds are stratified but *ungrouped*, and run inside the
training split. Comparing them therefore prices the grouping directly. Note that
these are two different questions, not a discrepancy: CV estimates
generalisation to a *new sample of the same corpus*, the grouped hold-out to a
*new command structure*. The gap between them is the leakage the grouping
removes.

**Table 7.2.1 — 5-fold stratified CV against the grouped hold-out (F1).**
Positive Δ means the ungrouped protocol scored higher.

| Model | Corpus | CV F1 (mean ± sd) | Grouped hold-out F1 | Δ (CV − hold-out) |
|---|---|---:|---:|---:|
| XGBoost-hybrid | Dataset 1 | 0.8715 ± 0.0049 | 0.8761 | −0.0046 |
| XGBoost-hybrid | Dataset 2 | 0.8752 ± 0.0092 | 0.8482 | **+0.0271** |
| XGBoost | Dataset 1 | 0.7978 ± 0.0078 | 0.7856 | +0.0122 |
| XGBoost | Dataset 2 | 0.7970 ± 0.0126 | 0.7557 | **+0.0412** |
| 1D-CNN | Dataset 1 | 0.8365 ± 0.0125 | 0.8495 | −0.0131 |
| 1D-CNN | Dataset 2 | 0.8262 ± 0.0104 | 0.8249 | +0.0012 |

Sources: `results/cv_xgboost_hybrid_dataset{1,2}.json`,
`results/holdout_xgboost_hybrid_dataset{1,2}.json`, `results/ch7_{cv,holdout}.json`.
The CNN rows use the Chapter 7 sweep-base configuration (`max_len=192`, 6
epochs), so their level is not comparable with the shipped CNN's 0.8603 — only
the CV-versus-hold-out difference within each row is.

The result splits by corpus. On **Dataset 1** the two protocols agree to within
±0.013 F1 — the curated corpus is already structurally diverse, so grouping
removes little. On **Dataset 2** the ungrouped estimate is **2.7 to 4.1 points
optimistic** for both tree models. That is the honeypot register showing its
hand: automated attack sessions replay near-identical command structures, so an
ungrouped fold routinely trains on one instance of a structure and tests on
another. Reporting the CV number as the headline would have overstated Dataset 2
performance by roughly the margin that separates our XGBoost from our
XGBoost-hybrid. **Every headline figure in this report is the grouped hold-out
number**, which is the conservative one on the corpus where the choice matters.

**Metric set.** Chosen for the prevalence rather than convention: Precision,
Recall, F1, ROC-AUC and FPR as mandated, plus **PR-AUC** and **TPR at fixed
FPR = 1% and 0.1%**. The last is the one that matters operationally and the one
aggregate scores hide — the XGBoost-hybrid's ROC-AUC of 0.979 falls to a
**TPR of 0.567 at FPR = 0.1%**, i.e. roughly half of attacks are missed once
false alarms are held to 1-in-1000.

**Residual risk, disclosed.** Shape-grouping is exact but `shape()` is lossy, so
it cannot catch near-duplicates that differ structurally. These were measured
separately rather than assumed away: the per-source character 4-gram audit in
`docs/DATA_CARD.md` reports every source above the 10% line, and per-source
recall for those sources is not quoted anywhere in this report as recall on
unseen technique.
