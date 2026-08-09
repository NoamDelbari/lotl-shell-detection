# Chapter 6 — Model Selection Justification (XGBoost & 1D-CNN)

This project pairs two deliberately different learners on the same T1059.004 task: a gradient-boosted tree ensemble over **engineered behavioral features**, and a **character-level 1D-CNN** over the raw command string. They are chosen to be complementary — one interpretable and feature-driven, one representation-learning and syntax-driven — so that agreement between them is meaningful and their disagreements define the edge cases routed to LLM arbitration (Ch. 8.4). In-domain results back the pairing: XGBoost-hybrid reaches **F1 0.871 / ROC-AUC 0.978** on Dataset 1 and **0.846 / 0.965** on Dataset 2, while the CNN reaches **0.853 / 0.976** and **0.841 / 0.960** (`results/summary.json`).

## 6.1 XGBoost on engineered features

Gradient-boosted decision trees are the natural fit for the 43-dimensional engineered feature vector (counts, ratios, entropies, binary-family flags):

- **Interpretability.** Tree ensembles expose per-feature gain, so the decision surface is auditable — a first-class requirement for a security detector that a human analyst must trust. Ch. 4's gain ranking (`shell_bins` 0.194, `redirect_count` 0.130, `pipe_count` 0.076) is only possible because the model is inspectable, and it is what let us *see* the structural-shortcut risk rather than merely suspect it.
- **Handles mixed feature types.** The engineered features mix bounded ratios (`special_ratio` ∈ [0,1]), unbounded counts (`char_count`), and binary flags (`shell_bins`). Trees split on thresholds and never assume a common scale or distribution, so heterogeneous features coexist without one-hot expansion or feature-specific preprocessing.
- **Scale-invariant.** Splits depend only on rank order, so the raw-magnitude features that dominate the variance ranking (`char_count`, `token_len_max`) need no standardization or log-transform — the exact normalization burden that would sink a linear or neural model on these inputs (Ch. 3).
- **Fast and robust.** With `tree_method='hist'` training is histogram-binned and near-instant on tens of thousands of rows, and Ch. 7 shows F1 is *saturated* across almost the entire hyperparameter grid (~0.71–0.735) — a model that is cheap to retrain and hard to misconfigure, which is an operational asset.

*Cite:* Chen, T. & Guestrin, C. (2016), *XGBoost: A Scalable Tree Boosting System*, KDD '16 — the regularized, histogram-based boosting formulation used here.

## 6.2 Character-level 1D-CNN

The CNN operates on the raw command as a sequence of character indices, and character-level convolutions capture shell syntax that a word-level model structurally cannot:

- **Shell "words" are an open, adversarial vocabulary.** Paths, IPs, random dropper names (`./qJWIJu99`), and base64 blobs mean a word/token model faces near-infinite out-of-vocabulary at test time. Character n-grams generalize across unseen tokens by sharing sub-word structure — `/dev/tcp`, `://`, `-rf`, `mkfifo`, `2>&1` — and shell frequently omits the whitespace a word tokenizer needs (`cat/etc/passwd`). A convolution of width *k* over character embeddings is exactly a learned character-*k*-gram detector, so it keys on the operators and idioms that *are* the tradecraft.
- **Parallel kernels of sizes 3/5/7.** LotL syntax lives at several scales at once: width-3 catches short motifs (`-i`, `/sh`, `://`), width-5 mid-length tokens (`mkfifo`, `chmod`, `/dev/`), width-7 longer signatures (`/dev/tcp`, `base64 `). Running the three widths **in parallel** (not stacked) extracts features at all three receptive fields from the same input and concatenates them (128 × 3 = 384-dim) rather than committing to one width; global max-pooling each branch makes detection position-invariant, so a reverse-shell motif is caught wherever it appears in the line.

*Cite:* Kim, Y. (2014), *Convolutional Neural Networks for Sentence Classification*, EMNLP 2014 — the multiple-parallel-filter-width CNN adopted here at the character level (with Zhang, Zhao & LeCun (2015), *Character-level Convolutional Networks for Text Classification*, NeurIPS 2015, motivating the character granularity).

## 6.3 Explicit hyperparameter choices and rationale

**XGBoost** (`src/models.py`, `build_xgboost*`):

| Hyperparameter | Value | Why |
|---|---|---|
| `scale_pos_weight` | **3.0** | The data is 1:3 attack:benign, so there are 3× more negatives; setting the positive-class gradient weight to `neg/pos = 3` rebalances the loss so the minority attack class is learned instead of being swamped. Ch. 7 shows this is the dominant **FPR** dial (FPR 0.049 → 0.145 from 1.0 → 5.0) with F1 flat — i.e. it sets the operating point, and 3.0 is the recall-favoring default a detector wants. |
| `max_depth` | **12** | The best-F1 point in the Ch. 7 sweep (0.7354 at 12 vs 0.7329 at 6), adopted after full-data re-validation: the deeper trees lift the full XGBoost-hybrid from F1 0.853 (depth 6) → **0.871** on Dataset 1. The trade-off is transfer robustness (§8.2) — the extra capacity fits corpus style harder, so depth-12 also transfers worst. |
| `n_estimators` | **200** | Peak F1 in the sweep; 400 mildly overfits (0.733 → 0.725). |
| `learning_rate` | **0.1** | Peak F1 (0.733); 0.01 underfits (0.685), 0.3 rolls over (0.718). |
| `tree_method` | **`hist`** | Histogram binning for fast, memory-light training. |
| `objective` / `eval_metric` | `binary:logistic` / `logloss` | Calibrated probabilistic output needed for the TPR@fixed-FPR metrics and for cascade thresholding. |
| `random_state` | **42** | Reproducibility. |

**1D-CNN** (`src/models.py`, `CNNClassifier`):

| Hyperparameter | Value | Why |
|---|---|---|
| `embed_dim` | **32** | Character vocabulary is small (~50–60 symbols); Ch. 7 shows 32 is the saturation point (16 underfits at F1 0.805, 64 adds cost and FPR without F1 gain). |
| `num_filters` | **128** (per kernel) | Best F1/FPR balance (0.830 / 0.055); 256 nudges F1 up but raises FPR (0.070). |
| `kernel_sizes` | **(3, 5, 7)** | Multi-scale character-n-gram detectors, per §6.2. |
| `dropout` | **0.3** | Regularizes the 384-dim concatenation before the linear head; kept as the conservative default (0.1 edged higher on the subsample but reads as a small-data artifact per Ch. 7). |
| loss | **class-weighted cross-entropy** | The tree-model `scale_pos_weight` analog: inverse-frequency class weights up-weight the minority attack class under the 1:3 prior. |
| optimizer | **Adam, lr = 1e-3, weight_decay = 1e-4** | `learning_rate` is by far the CNN's most sensitive knob (Ch. 7: F1 0.713 → 0.851 across the range); 1e-3 is a safe converging default, with 3e-3 the sweep optimum to adopt only after full-data confirmation. `weight_decay=1e-4` adds mild L2 regularization. |
| `epochs` / `batch_size` | **8 / 256** | 8 epochs is sufficient given the small character vocabulary and short sequences (Ch. 7's curves are already converged by then); batch 256 keeps training fast on CPU. |
| `max_len` | **256** | Covers the p99 command length (Dataset 1 p99 ≈ 227 chars) while truncating pathological outliers. |

The through-line: XGBoost's hyperparameters are tuned for a **stable, low-FPR operating point** on interpretable features, while the CNN's are tuned for **convergence** of a multi-scale character representation — and Ch. 7's sensitivity analysis is what justifies each specific value rather than a default guess.
