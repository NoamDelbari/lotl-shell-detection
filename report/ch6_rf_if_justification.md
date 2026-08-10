# Chapter 6 — Model Selection Justification (Random Forest & Isolation Forest)

> Companion to `ch6_model_justification.md` (XGBoost / 1D-CNN, Ben). Section
> numbers continue his: §6.1–6.3 are his two models, §6.4–6.6 below are the two
> models Noam owns. Every hyperparameter quoted here is the production value in
> `src/models.py`; every sensitivity claim is proved in
> `report/ch7_rf_if_sensitivity_findings.md` — **Chapter 6 states the choice,
> Chapter 7 proves it.** The one exception is the Isolation Forest sub-sample
> result in §6.6, which was run for this chapter and is reproducible via
> `analysis/ch6_if_subsample_probe.py` (→ `results/ch6_if_subsample_probe.json`).
> Holdout metrics are read from `results/summary.json` (43-feature set).

The four-model portfolio is chosen to span **three learning paradigms** rather
than three tunings of the same idea: boosting (XGBoost), representation
learning (1D-CNN), bagging (Random Forest), and unsupervised anomaly detection
(Isolation Forest). The last of those is the important one — Random Forest and
XGBoost disagree about *how* to combine trees, but Isolation Forest disagrees
about what the problem *is*. It never sees an attack label, so it cannot fail in
the way the whole supervised stack shares: it cannot memorise the style of our
attack corpus. That is what makes it worth carrying despite the weakest
standalone numbers in the project.

## 6.4 Random Forest on engineered features

Random Forest is the **bagging** counterpart to Ben's boosted trees: many deep,
decorrelated trees fitted on bootstrap samples with a random feature subset at
each split, averaged. Its case on this task rests on four properties, three of
which we could check rather than assert.

*Cite:* Breiman, L. (2001), *Random Forests*, Machine Learning 45(1):5–32,
doi:10.1023/A:1010933404324 — the bootstrap-plus-random-subspace construction and
the `max_features` decorrelation argument used below. Alasmary, H., Anwar, A.,
Abusnaina, A., Alabduljabbar, A., Abuhamad, M., Wang, A., Nyang, D., Awad, A. &
Mohaisen, D. (2022), *ShellCore: Automating Malicious IoT Software Detection Using
Shell Commands Representation*, IEEE Internet of Things Journal 9(4):2485–2496,
doi:10.1109/JIOT.2021.3086398 (preprint arXiv:2103.14221) — direct precedent for
Random Forest on *shell commands* specifically, and the paper Chapter 2 takes as
our closest comparator. Their Table 4 reports RF at 99.78% accuracy / 99.78 F-1 /
0.19 FPR for character-level command detection, i.e. essentially at ceiling. We
read that as corroborating Chapter 3 and Chapter 8 rather than as a target to
chase: their own ablation shows the same RF falling to 84.96 F-1 (term-level) when
the vector space is rebuilt from malware commands alone, which is the same lesson
our cross-dataset transfer collapse teaches — on curated command corpora the score
is a property of the representation and the corpus at least as much as of the
classifier.

**It is robust to the heavy tails Chapter 3 documented, because trees never
extrapolate.** The engineered features are severely right-skewed: on Dataset 1
attack commands carry 2.5× the benign variance in `len_chars` (2055 vs 822) and
4.3× in `b64_run_len`, driven by a small number of enormous encoded payloads. A
linear or distance-based model has to be defended against those points because
its output is unbounded in the feature value; an axis-aligned tree simply routes
a 5,000-character payload into the same terminal leaf as a 300-character one.
Outliers change which leaf a sample lands in, never how far the prediction is
dragged. Bootstrap aggregation then averages away the residual variance that a
single deep tree would inherit from those tails.

**It is auditable, and its audit independently corroborates Chapter 3.** Gini
importance over the fitted production forest gives, on Dataset 1:
`n_abs_paths` 0.134, `special_ratio` 0.117, `max_token_len` 0.085,
`mean_token_len` 0.073, `len_chars` 0.072, `digit_ratio` 0.063,
`has_shell_bin` 0.057, `n_pipes` 0.051. Compare that with the model-free
rank-biserial ranking computed in Chapter 3 — `n_abs_paths` (+0.452),
`special_ratio` (+0.318), `max_token_len` (+0.303), `len_chars` (+0.247),
`digit_ratio` (+0.238). The top two agree in **both identity and order**, and
they were derived by completely independent routes: one a Mann-Whitney U
statistic on single features, the other a multivariate impurity accounting
inside a fitted ensemble. A security detector whose learned attention matches
the univariate evidence is one an analyst can be asked to trust.

**The importance mass is spread, which is evidence against a structural
shortcut.** All 43 features are used (non-zero importance) and the top eight
account for only 65% (Dataset 1) and 64% (Dataset 2) of total importance. This
matters because
the project's documented risk (`KNOWN_ISSUES` P3/P8) is that a model latches
onto a corpus artefact — length, or the presence of a particular binary — and
reports a spuriously high score. A forest that distributes its splits across the
whole feature set is not riding one shortcut. The Dataset 2 ordering shifts
sensibly rather than collapsing (`len_chars` 0.107, `special_ratio` 0.101,
`mean_token_len` 0.088, `digit_ratio` 0.085), consistent with Chapter 3's
finding that operational data carries weaker per-feature signal.

**It needs no feature scaling — verified, not assumed.** The pipeline in
`src/models.py` does include a `StandardScaler`, but only so that all model
pipelines share one preprocessing contract. Refitting the production forest with
the scaler removed changes F1 by 0.0017 (Dataset 1) and 0.0003 (Dataset 2) and
ROC-AUC by 0.0001 on both — floating-point noise in sklearn's split search, not
a modelling effect, exactly as expected for a learner whose splits depend only
on rank order. The same test on the Isolation Forest returns scores that are
**bit-identical** (maximum absolute difference 0.0), since its random split
points are drawn uniformly across each feature's range and a per-feature affine
transform maps that draw onto itself.

Class imbalance (1:3 attack:benign) is handled by
`class_weight="balanced_subsample"`, which reweights the loss **per bootstrap
sample**. This is deliberately a cost-sensitive remedy rather than a resampling
one: no synthetic shell commands are fabricated, so the model is never trained
on a command no attacker ever typed — the same principle Ben applies with
`scale_pos_weight`.

**What Random Forest is actually for here — and what it is not.** It is not the
headline detector: at F1 0.7963 (Dataset 1) / 0.7531 (Dataset 2) it sits below
the XGBoost-hybrid (0.8761 / 0.8482) and the CNN. Its value is a different
operating profile. On Dataset 1 it produces the **lowest false-alarm rate of any
supervised model in the project** (FPR 0.0337, against 0.0415 for the hybrid,
0.0555 for the CNN and 0.0717 for plain XGBoost) at the **highest precision**
(0.8782), buying that with the lowest recall (0.7283). On Dataset 2 the picture
is more even — FPR 0.0515 against the hybrid's 0.0494, precision 0.8186 against
0.8508 — so the low-false-alarm advantage should be claimed for Dataset 1 and
not generalised. A conservative, high-precision, fully auditable model is the
right complement to a high-recall boosted ensemble, and Chapter 7 shows it is
also the hardest model in the project to misconfigure: its entire 12-cell
hyperparameter grid spans just 0.021 F1 on Dataset 1 and 0.027 on Dataset 2.

## 6.5 Isolation Forest as an unsupervised stage-1 filter

Isolation Forest is the only model in the portfolio trained **without attack
labels** — it is fitted on the benign training rows alone
(`IsolationForestDetector.fit`, `src/models.py`) and scores a command by how few
random axis-aligned partitions are needed to isolate it. Anomalies need fewer,
because they sit in sparse regions.

*Cite:* Liu, F. T., Ting, K. M. & Zhou, Z.-H. (2008), *Isolation Forest*, ICDM
2008, pp. 413–422, doi:10.1109/ICDM.2008.17, extended as *Isolation-Based Anomaly
Detection*, ACM TKDD 6(1), art. 3, pp. 1–39 (2012), doi:10.1145/2133360.2133363 —
the isolation principle itself, the linear-time/low-memory argument quoted in
reason 3 below, and the sub-sampling analysis we test against production in §6.6.

**Why carry an unsupervised model at all.** Three reasons, in order of
importance to this project:

1. **Labelled attacks are the scarce resource.** A supervised detector can only
   recognise tradecraft its labels covered. Our attack corpus is finite and
   partly template-derived, so a model that defines "suspicious" as "unlike
   normal traffic" rather than "like my 3,050 known attacks" is the only
   component with a mechanism for catching a technique nobody labelled.
2. **It cannot inherit the failure mode the rest of the stack shares.** The
   central methodological worry recorded across Chapter 2 and `KNOWN_ISSUES` is
   corpus-style memorisation — every supervised model here is trained on the
   same attack corpus and can learn its idiom rather than its behaviour.
   Isolation Forest never reads that corpus. Its errors are therefore
   structurally, not just statistically, decorrelated from the others, which is
   what makes the cascade's first stage informative instead of redundant.
3. **It is cheap enough to sit in front of everything.** Scoring a command is
   essentially constant-time — 300 root-to-leaf traversals of depth ~log ψ — and
   needs no labels and no gradient steps, which is exactly the profile a
   first-pass filter over high-volume command telemetry needs. One caveat we
   should state rather than inherit: Liu et al.'s linear-time, low-memory
   guarantee assumes a *fixed small* sub-sample, and our `max_samples=0.8` gives
   that asymptotic property up (see §6.6). At this corpus size it does not
   matter — the fit takes ≈2 s — but it would matter at telemetry scale, and the
   §6.6 sweep shows the escape hatch is cheap if it ever does: reverting to the
   paper's full default (ψ=256, t=100) costs 0.0137 ROC-AUC on Dataset 1 and
   0.0137 on Dataset 2.

**Its weakness is real and we report it at face value.** Standalone, the shipped
detector reaches only **F1 0.2492 / ROC-AUC 0.8120** on Dataset 1 and **F1
0.1431 / ROC-AUC 0.6768** on Dataset 2 — by a wide margin the weakest numbers in
the project. Two separate things cause that, and Chapter 7 separates them:

- *Threshold placement.* The production wrapper thresholds a min-max-normalised
  score at a fixed 0.5, which lands in an extreme-precision corner (recall 0.146,
  FPR 0.008 on Dataset 1). Re-evaluated at sklearn's own calibrated threshold the
  same forest reaches F1 0.641 (Dataset 1) / 0.462 (Dataset 2). Most of the ugly
  headline is where the threshold sits, not how well the model ranks.
- *Genuine ranking limits.* Even at its best operating point it is far below the
  supervised models, and Dataset 2 is much worse than Dataset 1 (AUC 0.677 vs
  0.812). This is the honest finding, and it is the expected one: on operational
  Cowrie traffic "anomalous" and "malicious" come apart, because unusual-but-benign
  commands are common in real telemetry in a way they are not in a curated corpus.

**So it is deployed as stage 1 of the cascade and nowhere else.** In
`src/ensemble.py` the first stage's job is to clear obvious benign traffic
cheaply and pass everything else to the XGBoost-hybrid — a filter, not a
detector. The metric that matters for that job is not F1 but **attack
retention**, and the two are in direct conflict: Chapter 7 shows that even the
most permissive swept setting (`contamination=0.30`) retains only 73% (Dataset 1)
/ 56% (Dataset 2) of attacks, and a stage-1 filter that silently discards a
quarter of the attacks caps the entire cascade's recall no matter how strong
stage 2 is. The production cascade therefore ignores `contamination` altogether
and calibrates its clearing threshold on the **attack-score quantile**
(`stage1_retain_recall=0.99`), placing it so ~99% of training attacks survive
stage 1. Choosing a stage-1 threshold by F1 would be a design error, and the
sweep is what demonstrates that rather than asserting it.

## 6.6 Explicit hyperparameter choices and rationale

**Random Forest** (`src/models.py`, `build_random_forest`) — swept in Chapter 7
as a full 12-cell `n_estimators` × `max_depth` grid on full training data.

| Hyperparameter | Value | Why |
|---|---|---|
| `n_estimators` | **400** | On the plateau: the swept grid gains only 0.0017 (D1) / 0.0025 (D2) F1 going from 200 to 500 trees, so anything ≥200 is equivalent. 400 buys the variance reduction of a large ensemble while keeping a fit to ~3 s. Bagging cannot overfit in the ensemble size, so erring high is free apart from compute. |
| `max_depth` | **24** | The one hyperparameter that moves the model. Chapter 7 finds depth 20 **dominates both** shallower (10) and unbounded (`None`) on F1 *and* FPR on *both* datasets; production 24 sits on that optimum, bracketed by the swept plateau cells. `None` is worse (D1 F1 0.7850 vs 0.8006 at n=500) because fully grown trees memorise singleton leaves; depth 10 is an underfitting trap that raises recall but inflates FPR by ~70%. |
| `class_weight` | **`balanced_subsample`** | Cost-sensitive imbalance handling at the 1:3 prior, reweighted per bootstrap sample rather than once globally, so each tree sees a correctly balanced loss. Chosen over resampling so that no synthetic commands enter training. |
| `min_samples_leaf` | **1** | Left at the sklearn default: with `max_depth=24` already capping capacity, a second regulariser would confound the depth result Chapter 7 reports. |
| `max_features` | **`"sqrt"`** | The standard Random Forest setting (≈6 of 43 features per split). This is what decorrelates the trees — the whole point of bagging — and matters more here than usual because Chapter 3 found strongly collinear pairs (`len_chars`~`len_tokens` 0.897); sampling features per split stops every tree opening on the same size feature. |
| `n_jobs` / `random_state` | **-1 / 42** | Parallel fit; fixed seed for reproducibility. |

**Isolation Forest** (`src/models.py`, `IsolationForestDetector`) — swept in
Chapter 7 over `contamination` on both datasets, and over `max_samples` /
`n_estimators` here (`analysis/ch6_if_subsample_probe.py`).

| Hyperparameter | Value | Why |
|---|---|---|
| `contamination` | **0.25** | Deliberately inert in production, and Chapter 7 proves it: in sklearn `contamination` does not affect the fitted trees at all (`score_samples` is contamination-independent; it only sets `offset_`), ROC-AUC is identical to four decimals across 0.05–0.30, and both consumers of this model bypass it — the wrapper thresholds at a fixed 0.5, the cascade calibrates on recall retention. It is kept as an honest declaration of the expected anomaly share. If the detector were ever deployed standalone as a tripwire, set it to the SOC's false-alarm budget directly: the sweep shows FPR ≈ contamination (D1 delivered 0.047/0.088/0.189/0.287 against requested 0.05/0.10/0.20/0.30). |
| `n_estimators` | **300** | Score stability, not capacity. Liu et al. take t=100 as their default; raising it to 300 moves ROC-AUC by +0.0027 (D1) and −0.0032 (D2) at fixed ψ — i.e. in opposite directions and within noise. Extra trees buy reproducible scores rather than better ones, because ranking quality is set by the 43-feature representation. |
| `max_samples` | **0.8** | Kept, but the textbook justification does **not** survive contact with our data. Liu et al. recommend a small fixed sub-sample (ψ=256) on the argument that it reduces *swamping* and *masking*; production instead uses 0.8 of the benign training rows (ψ≈7,319 on D1, ≈4,596 on D2), ~30× larger. We swept it: ψ=256 is the **worst** cell on both datasets (ROC-AUC 0.7983 D1 / 0.6631 D2) and production is within 0.003 of the best (best: ψ=1024 → 0.8149 on D1; ψ=all → 0.6782 on D2, vs production 0.8120 / 0.6768). The entire axis spans 0.017 AUC, so sub-sample size is a weak dial here and the published default is not transferable to this feature space. The likely reason is that swamping and masking are contamination effects — they presuppose anomalies *in the training sample* — and this detector is fitted on benign rows only, so there are none to protect against. What a 256-row sub-sample does instead is under-cover a strongly multi-modal benign distribution, leaving rare-but-legitimate commands as easy to isolate as attacks. Production is retained as a near-optimal, already-validated setting; §6.5's honest conclusion stands that the ceiling is the representation, not this parameter. |
| `max_features` | **1.0** | All 43 features available per tree. Unlike the supervised forest we are not trying to decorrelate an ensemble of predictors, and the anomaly signal is a conjunction across obfuscation, path and network features that per-tree feature subsetting would dilute. |
| fitted on | **benign rows only** | The design commitment: `fit()` drops all rows with `label == 1` before fitting, so the model's notion of "normal" is defined by benign traffic alone and no attack label leaks in. This is what earns the model its place in the portfolio (§6.5). |
| `random_state` | **42** | Reproducibility. |

The through-line for both models mirrors the one Ben reports for XGBoost and the
CNN: **the representation sets the accuracy and a single purpose-built dial sets
the false-alarm rate.** Random Forest's F1 barely moves across its whole grid
because 43 engineered features, not tree capacity, are the ceiling; its depth cap
buys false-alarm reduction rather than accuracy. The Isolation Forest's dial does
not touch the model at all — it *is* the operating point. Both are consequently
cheap to run and hard to misconfigure catastrophically, subject to the two rules
Chapter 7 establishes: cap Random Forest depth rather than growing full trees,
and never let the Isolation Forest's stage-1 threshold be chosen by F1.
