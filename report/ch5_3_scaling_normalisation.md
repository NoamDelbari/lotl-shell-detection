# Chapter 5.3 — Feature Scaling and Normalisation

> Sources: `src/models.py`, `src/preprocessing.py`, `scripts/build_dataset.py`,
> `report/ch6_rf_if_justification.md` §6.4.

## The rule: every fitted transform lives inside the pipeline

The assignment requires that any sampling or scaling be fit strictly on the
training fold. This project satisfies that structurally rather than by
discipline: no *fitted* transform is ever applied to a dataframe and then split.
Each
model is an `imblearn` `Pipeline` whose first stages are the transforms —

```python
ImbPipeline([("features", EngineeredFeatures()),
             ("scale",    StandardScaler()),
             ("clf",      clf)])
```

— so `StandardScaler` learns its 43 means and standard deviations from whatever
rows the pipeline is handed. Under `StratifiedKFold` cross-validation that is
the training fold of each split, refitted once per fold; under holdout
evaluation it is the training split alone. The test rows are never seen by
`fit`. The same
property covers the two learned representations in the project that genuinely
could leak. The char n-gram TF-IDF vocabulary (`CharNgramFeatures`) is a
`FeatureUnion` stage inside the hybrid pipeline; the CNN's character index table
(`CharSequenceEncoder`) is fitted inside `CNN1DClassifier.fit` itself
(`src/models.py:276`), as is the Isolation Forest's internal transform pipeline.
Different mechanics, one guarantee: a vocabulary is only ever built from rows the
model is allowed to see.

## Why a scaler is the default, and where it is actually used

The 43 engineered features are on wildly incompatible scales by construction.
Measured on Dataset 1's training split, per-feature standard deviation runs from
0.0157 (`has_ifs_expansion`, a flag firing on a fraction of a percent of rows) to
34.2 (`len_chars`) — a spread of **2,182×**, and observed value ranges from well
under 1 (the density ratios) to 546 (`len_chars`).
For any learner whose objective depends on Euclidean distance or on gradient
magnitude, that disparity alone would decide the model.

The scaler is not applied uniformly, and the exceptions are deliberate:

| pipeline | scaler | why |
|---|---|---|
| `xgboost` (engineered) | `StandardScaler` | uniform contract |
| `random_forest` | `StandardScaler` | uniform contract |
| `isolation_forest` | `StandardScaler` | uniform contract |
| `xgboost_hybrid` | **none** | the char n-gram block is a sparse 3,000-column TF-IDF matrix; mean-centering it would densify it at no benefit, and trees are scale-invariant |
| `cnn1d` | **none** | the input is integer character indices consumed by a learned embedding layer; the embedding *is* the normalisation |

## The honest result: for these models the scaler does nothing

Rather than assert scale-invariance, it was measured. Refitting the production
Random Forest with the scaler removed changes F1 by **0.0017** (Dataset 1) and
**0.0003** (Dataset 2), and ROC-AUC by 0.0001 on both. The same ablation on the
Isolation Forest returns scores that are **bit-identical** — maximum absolute
difference exactly 0.0.

Both results follow from the mechanism. A decision tree's split search evaluates
candidate thresholds by the partition they induce, so it depends only on the
*rank order* of each feature's values, and an affine transform `(x − μ)/σ`
preserves rank order exactly; the residual 0.0017 is floating-point noise in
sklearn's threshold enumeration, not a modelling effect. The Isolation Forest is
even cleaner: it draws its split points uniformly at random across each
feature's observed range, and an affine map carries that uniform draw onto
itself, so the same seed produces the same forest on scaled and unscaled input.

The honest framing is therefore that **the scaler is a preprocessing contract,
not a modelling decision.** Its value is that every pipeline consuming the
engineered matrix has one identical shape, so a scale-sensitive learner —
logistic regression, an SVM, a kNN baseline — can be added to the registry
without anyone having to remember to attach a scaler and risk fitting it outside
the fold. It costs approximately
nothing and it buys uniformity. Claiming it improved the tree models would be
false, and the ablation above is reported precisely so that the claim is not
made.

## A scaling subtlety that Section 5.2 makes real

There is one place where "scaled correctly" and "scaled usefully" come apart. In
the cross-dataset evaluation, a model trained on Dataset 1 and applied to
Dataset 2 carries its **Dataset 1 scaler** with it. That is the correct
behaviour — a deployed detector ships with its own preprocessing, and refitting
the scaler on the target corpus at test time would be leakage — but given the
covariate shift measured in Section 5.2, it means Dataset 2's commands are being
centred on Dataset 1's means and divided by Dataset 1's standard deviations.
Where `len_chars` has a different mean and a different class relationship
entirely, the transformed values are not comparable to anything the model saw in
training.

For the models in this project that costs exactly nothing, by the same
rank-invariance argument. It is recorded because it is a genuine and easily
missed failure mode: had the headline detector been distance- or
gradient-based, a share of the transfer degradation reported in Chapter 8.2
would have been attributable to a stale scaler rather than to the underlying
distribution shift, and the two would have been very difficult to separate after
the fact.

## Text normalisation, and why it is not leakage

One normalisation happens outside any pipeline: the command strings themselves
are normalised once at build time (`scripts/build_dataset.py`) — IPv4 addresses
and URL hosts replaced by a value derived from a hash of the original, smart
quotes folded to ASCII, control bytes stripped, whitespace collapsed. This runs
before the train/test split, on both corpora identically.

That ordering is safe because the transform is **stateless and per-row**: each
string's output depends only on that string, never on any statistic aggregated
over the corpus, so no information crosses from test rows to training rows. It
is applied to both classes and both datasets by the same code path, so it cannot
introduce a label-correlated artefact — with one documented exception carried
forward from Chapter 1.1: hashing addresses per value removed the constant
`1.1.1.1` token that an earlier build had made a near-perfect classifier, but
"contains an IPv4 address at all" remains a real correlation on Dataset 1, and is
reported as the `P8-source-fingerprint` probe rather than normalised away.

Beyond these, nothing is normalised: no target encoding, no per-source
adjustment, and no per-dataset constant anywhere in the pipeline. Consistent
with Section 5.1, every difference between the two corpora's results is a
difference in the data.
