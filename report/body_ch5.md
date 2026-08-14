# Chapter 5 — Data Harmonization

## 5.1 One dataset-aware module, enforced by a test

**`src/ingestion.py` is the only module in `src/` permitted to know a dataset by
name, and a test fails the build if that changes.**
`test_downstream_is_dataset_agnostic` (`tests/test_pipeline.py:43-50`) matches
`dataset1|dataset2` against the `read_text()` of every file in `src/`, skipping
exactly one — `ingestion.py` — so a dataset name in a **comment** fails as surely
as one in code. It is a name→CSV registry returning one frame: `command` (the
sole model input), `label`, and `source`, a tag **never passed to a model**. A
third corpus is one registry entry, and nothing downstream changes.

**Table 5.1 — The harmonization contract: what both corpora are forced to share,
and what enforces each guarantee.**

<!-- cols: 1.00 2.85 2.65 -->

| Layer | What both corpora share | Enforced by |
|---|---|---|
| Schema | `command` / `label` / `source`; empty commands and bad labels raise at load | `test_pipeline_runs_on_any_registered_dataset` fits and predicts on every registered dataset unchanged |
| Features | The same 43 numbers from fixed regexes; `EngineeredFeatures.fit()` learns nothing | Asserted: rows featurized after fitting on disjoint folds must match |
| Selection | One pre-registered gate, fit on **training splits only**, applied to both unmodified | Passing **one** corpus suffices: 22 both, 16 D1, 5 D2, 0 neither. Requiring both deletes `has_dev_tcp` |
| Lexical | **Nothing** — the hybrid's char n-gram vocabulary is fitted per fold, corpus-bound by construction | Unobtainable; the asymmetry behind Chapter 8.2 |

## 5.2 The disagreement harmonization makes measurable

**Because both corpora traverse the same stateless extractor, every difference
below is a property of the data, not of the processing** — that attribution is
the entire return on §5.1. No domain adaptation or per-corpus feature was added,
so Chapter 8.2 reports the transfer collapse as a finding, not a processing
defect.

**Table 5.2 — Three compounding shifts, measured over all 43 features.** Effects
are rank-biserial; consensus rank is Chapter 4's three-view aggregate.

<!-- cols: 1.05 2.15 3.30 -->

| Shift | What was measured | Result |
|---|---|---|
| Direction | Class leaning reverses sign | **15 of 43**, a superset of Chapter 3's three, led by `len_chars` +0.247 / −0.171 and `len_tokens` +0.135 / −0.207 |
| Strength | Mean \|effect\| across the 43 | 0.0867 (D1) vs **0.0617** (D2); the two 43-vectors correlate at only Pearson *r* = 0.317 |
| Reliance | Agreement of the two consensus rankings | Spearman 0.596 / Kendall τ 0.417 |

## 5.3 No data leakage: every fitted transform is fit inside the fold

**No fitted transform is ever applied to a frame and then split.** Every pipeline
over the engineered matrix puts `EngineeredFeatures` and `StandardScaler` ahead
of the classifier (`src/models.py:79-83`, `:150-154`, `:177-180`), so the scaler
learns its 43 means and deviations from whatever rows `fit` receives — the
training fold under `StratifiedKFold`, the training split under hold-out. The two
learned representations obey the same rule: `CharNgramFeatures` fits its TF-IDF
vocabulary as a `FeatureUnion` stage *inside* the hybrid pipeline
(`src/preprocessing.py:64-69`, `:83-88`), and `CNN1DClassifier` fits its
character index table inside its own `fit` (`src/models.py:276`).
`tests/test_pipeline.py:66-83` asserts that a vectorizer fitted on two disjoint
folds yields **different** vocabularies — an identical one is the signature of a
global fit. Upstream, the 80/20 split is grouped by command shape, so no
near-duplicate straddles it.

**The one transform preceding the split is stateless, which is exactly why it is
not leakage.** `normalize()` (`scripts/build_dataset.py:240-247`) folds smart
quotes, strips control bytes and hashes IPv4 addresses and URL hosts; its output
depends on that row alone and on no corpus statistic, so nothing crosses from
test rows into training.

**§3.5 required scale to be handled in the pipeline rather than assumed away; it
is, and for the shipped models it changes nothing.** Removing the scaler moves
Random Forest F1 by 0.0017 (D1) and 0.0003 (D2) and leaves Isolation Forest
scores bit-identical: tree splits depend only on rank order, which (*x*−μ)/σ
preserves. It is a preprocessing contract, not a modelling decision — kept so a
scale-sensitive learner can join the registry without anyone remembering to
attach one inside the fold. One residue: under transfer a Dataset-1 model keeps
its Dataset-1 scaler, centring Dataset-2 commands on the wrong means. Refitting
on the target would be leakage, so that is correct and rank invariance makes it
free — but on a distance-based detector, part of Chapter 8.2's degradation would
be a stale scaler rather than the shift.
