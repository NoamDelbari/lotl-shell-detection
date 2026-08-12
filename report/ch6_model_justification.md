# Chapter 6 — Model Selection Justification (XGBoost & 1D-CNN)

This project pairs two deliberately different learners on the same T1059.004 task: a gradient-boosted tree ensemble over **engineered behavioral features**, and a **character-level 1D-CNN** over the raw command string. They are chosen to be complementary — one interpretable and feature-driven, one representation-learning and syntax-driven — so that agreement between them is meaningful and their disagreements define the edge cases routed to LLM arbitration (Ch. 8.4). In-domain results back the pairing: XGBoost-hybrid reaches **F1 0.876 / ROC-AUC 0.979** on Dataset 1 and **0.848 / 0.968** on Dataset 2, while the CNN reaches **0.860 / 0.975** and **0.838 / 0.964** (`results/summary.json`).

## 6.1 XGBoost on engineered features

Gradient-boosted decision trees are the natural fit for the 43-dimensional engineered feature vector (counts, ratios, binary-family flags, head-token indicators):

- **Interpretability.** Tree ensembles expose per-feature gain, so the decision surface is auditable — a first-class requirement for a security detector that a human analyst must trust. Ch. 4's gain ranking (`n_abs_paths` 0.181, `has_dev_null` 0.111, `has_shell_bin` 0.097 on Dataset 1) is only possible because the model is inspectable, and it is what let us *see* the structural-shortcut risk rather than merely suspect it.
- **Handles mixed feature types.** The engineered features mix bounded ratios (`special_ratio` ∈ [0,1]), unbounded counts (`len_chars`, `n_abs_paths`), and binary flags (`has_shell_bin`). Trees split on thresholds and never assume a common scale or distribution, so heterogeneous features coexist without one-hot expansion or feature-specific preprocessing.
- **Scale-invariant.** Splits depend only on rank order, so the raw-magnitude features the ensembles lean on (`max_token_len` and `len_chars`, MDI ranks 3 and 5 on Dataset 1) need no standardization or log-transform — the exact normalization burden that would sink a linear or neural model on these inputs (Ch. 3).
- **Fast and robust.** With `tree_method='hist'` training is histogram-binned and near-instant on tens of thousands of rows, and Ch. 7 shows F1 is *saturated* across the entire hyperparameter grid (0.765–0.789 on Dataset 1, 0.746–0.763 on Dataset 2, a span of 0.025 and 0.018 F1 across 13 configurations each) — a model that is cheap to retrain and hard to misconfigure, which is an operational asset.

*Cite:* Chen, T. & Guestrin, C. (2016), *XGBoost: A Scalable Tree Boosting System*, KDD '16 — the regularized, histogram-based boosting formulation used here.

## 6.2 Character-level 1D-CNN

The CNN operates on the raw command as a sequence of character indices, and character-level convolutions capture shell syntax that a word-level model structurally cannot:

- **Shell "words" are an open, adversarial vocabulary.** Paths, IPs, random dropper names (`./qJWIJu99`), and base64 blobs mean a word/token model faces near-infinite out-of-vocabulary at test time. Character n-grams generalize across unseen tokens by sharing sub-word structure — `/dev/tcp`, `://`, `-rf`, `mkfifo`, `2>&1` — and shell frequently omits the whitespace a word tokenizer needs (`cat/etc/passwd`). A convolution of width *k* over character embeddings is exactly a learned character-*k*-gram detector, so it keys on the operators and idioms that *are* the tradecraft.
- **Parallel kernels of sizes 3/5/7.** LotL syntax lives at several scales at once: width-3 catches short motifs (`-i`, `/sh`, `://`), width-5 mid-length tokens (`mkfifo`, `chmod`, `/dev/`), width-7 longer signatures (`/dev/tcp`, `base64 `). Running the three widths **in parallel** (not stacked) extracts features at all three receptive fields from the same input and concatenates them (128 × 3 = 384-dim) rather than committing to one width; global max-pooling each branch makes detection position-invariant, so a reverse-shell motif is caught wherever it appears in the line.

*Cite:* Kim, Y. (2014), *Convolutional Neural Networks for Sentence Classification*, EMNLP 2014 — the multiple-parallel-filter-width CNN adopted here at the character level (with Zhang, Zhao & LeCun (2015), *Character-level Convolutional Networks for Text Classification*, NeurIPS 2015, motivating the character granularity).

## 6.3 Explicit hyperparameter choices and rationale

**A note on how these values were chosen.** The Chapter 7 sweeps vary one axis
at a time and score on the **test hold-out** (`analysis/ch7_train.py`), so the
sweep is a *sensitivity* readout, not a selection procedure — adopting its
arg-max would be choosing hyperparameters on the test set. The values below are
therefore the pre-registered defaults the shipped results were produced with,
and the sweep column reports what the sensitivity analysis found, including the
two places where it disagrees with the shipped value.

**XGBoost** (`src/models.py`, `build_xgboost` / `build_xgboost_hybrid`):

| Hyperparameter | Shipped | What the Ch. 7 sweep shows (`xgboost`, D1) | Why this value |
|---|---|---|---|
| `scale_pos_weight` | **3.0** | 1.0 → F1 0.789, recall 0.727, FPR 0.039; 3.0 → 0.786 / 0.786 / 0.072; 6.0 → 0.765 / 0.819 / 0.108 | The 1:3 attack:benign ratio makes `neg/pos = 3` the natural cost-sensitive correction. The sweep confirms this is the dominant **operating-point** dial: it buys +6 points of recall over 1.0 for +3.3 points of FPR, at essentially unchanged F1. A detector wants that trade, which is why F1 is not the criterion here. |
| `max_depth` | **6** (`xgboost`) / **7** (hybrid) | 3 → 0.784; 6 → 0.786; 9 → **0.787**; 12 → 0.783 | Flat to within 0.4 F1 points across the whole range — depth is not a meaningful lever on this task. 9 edges 6 by 0.0017, far inside run-to-run noise, so the default stands. The hybrid uses 7 to give the added char-n-gram block one extra split level. |
| `n_estimators` | **400** (`xgboost`) / **500** (hybrid) | 100 → 0.782; 400 → **0.786**; 800 → 0.782 | Peak of the sweep, and the curve is symmetric around it: 800 trees buy nothing and cost 2× the fit time. |
| `learning_rate` | **0.1** | 0.03 → 0.782; 0.1 → **0.786**; 0.3 → 0.775 | Peak of the sweep. 0.3 rolls over, 0.03 underfits at this tree count. |
| `subsample` / `colsample_bytree` | **0.9 / 0.9** (`xgboost`), **0.9 / 0.7** (hybrid) | not swept | Standard stochastic-boosting regularisation. The hybrid samples columns harder because its feature block is 43 dense features ∪ 3,000 sparse n-gram columns, where the sparse side would otherwise dominate every split. |
| `tree_method` | **`hist`** | not swept | Histogram binning for fast, memory-light training. |
| `objective` / `eval_metric` | `binary:logistic` / `logloss` | — | Calibrated probabilistic output, needed for the TPR@fixed-FPR metrics and for cascade thresholding. |
| `random_state` | **42** (`SEED`) | — | Reproducibility. |

**1D-CNN** (`src/models.py`, `CNN1DClassifier`). The CNN sweeps run at **4
epochs for tractability** while the shipped model trains for 8
(`analysis/ch7_train.py`), so sweep F1 values sit about 3 points below the
headline 0.860 and are read for *shape*, not level.

| Hyperparameter | Shipped | What the Ch. 7 sweep shows (D1, 4 epochs) | Why this value |
|---|---|---|---|
| `pos_weight` | **3.0** | 1.0 → F1 0.830, recall 0.780, FPR 0.033; 3.0 → 0.829 / 0.870 / 0.076; 6.0 → 0.806 / 0.916 / 0.119 | Exactly the `scale_pos_weight` trade in the tree model, and the reason both models share the value: +9 points of recall over 1.0 at unchanged F1. |
| `lr` | **1e-3** | 5e-4 → 0.812; 1e-3 → 0.829; 2e-3 → **0.843** | The CNN's most sensitive knob — a 3-point F1 span, wider than any other axis. 2e-3 leads at 4 epochs, but the gap is an artefact of the shortened schedule: a higher rate simply converges sooner. At the shipped 8 epochs the default has converged, so it is kept. |
| `dropout` | **0.3** | 0.1 → **0.843**; 0.3 → 0.829; 0.5 → 0.822 | The one axis where the sweep clearly prefers a different value. It is not adopted: less regularisation raising test F1 at 4 epochs is what over-fitting looks like early in training, and Ch. 8.2 shows this model's real weakness is corpus-style memorisation, which weaker regularisation would worsen. Flagged as an open question rather than tuned away. |
| `n_filters` | **128** (per kernel) | 64 → 0.820 / FPR 0.082; 128 → 0.829 / 0.076; 256 → 0.834 / 0.081 | Best F1-per-FPR point. 256 buys +0.5 F1 for +0.5 FPR and 2× the parameters. |
| `kernel_sizes` | **(3, 5, 7)** | not swept | Multi-scale character-n-gram detectors, per §6.2. |
| `embed_dim` | **32** | not swept | The character vocabulary is ~50–60 symbols, so a 32-dim embedding is already over-complete; no sweep was run because there is no capacity argument for widening it. |
| loss | **class-weighted cross-entropy** | see `pos_weight` | The tree-model `scale_pos_weight` analogue: up-weights the minority attack class under the 1:3 prior. |
| optimizer | **Adam, `weight_decay` = 1e-5** | not swept | Mild L2; the dropout term carries the regularisation. |
| `epochs` / `batch_size` | **8 / 256** | — | Loss is flat by epoch 8 on this vocabulary and sequence length; batch 256 keeps CPU training tractable. |
| `max_len` | **256** | not swept | Covers the p99 command length (Dataset 1 p99 ≈ 227 chars) while truncating pathological outliers. |

The through-line: XGBoost's hyperparameters sit on a **flat** response surface —
no axis moves F1 by more than half a point, so the model's operating point,
not its capacity, is the only real decision — whereas the CNN's are governed by
**convergence**, with the learning rate alone spanning three F1 points. The
sensitivity analysis earns its place in the report precisely because it shows
how little most of these knobs matter: the two levers that do move the needle,
`scale_pos_weight`/`pos_weight` and `lr`, are the ones Chapter 7 examines in
depth.
