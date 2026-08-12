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
