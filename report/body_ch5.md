# Chapter 5 — Data Harmonization

## 5.1 One dataset-aware module, enforced by a test

**`src/ingestion.py` is the only module in `src/` permitted to know a dataset by
name, and `test_downstream_is_dataset_agnostic` (`tests/test_pipeline.py:43-50`)
fails the build otherwise** — it matches `dataset1|dataset2` against every file
in `src/` bar `ingestion.py`, the name→CSV registry returning `command` (the sole
model input), `label`, and `source`, a tag **never passed to a model**.

**Table 5.1 — The harmonization contract and its enforcement.**

<!-- cols: 1.00 2.85 2.65 -->

| Layer | What both corpora share | Enforced by |
|---|---|---|
| Schema | `command`, `label`, `source`; empty commands and bad labels raise at load | `test_pipeline_runs_on_any_registered_dataset` fits and predicts unchanged |
| Features | The same 43 numbers from fixed regexes; `EngineeredFeatures.fit()` learns nothing | Rows featurized after fitting on disjoint folds must match |
| Selection | One pre-registered gate, fit on **training splits only**, applied to both | Passing **one** corpus suffices: 22 both, 16 D1, 5 D2, 0 neither; requiring both deletes `has_dev_tcp` |
| Lexical | **Nothing** — the char n-gram vocabulary is fitted per fold, corpus-bound | Unobtainable; the asymmetry behind Chapter 8.2 |

## 5.2 The disagreement harmonization makes measurable

**Both corpora traverse the same stateless extractor, so every difference below
belongs to the data, not the processing** — no domain adaptation or per-corpus
feature was added, so Chapter 8.2 reads the transfer collapse as a finding, not a
defect.

**Table 5.2 — Three compounding shifts across all 43 features.** Effects are
rank-biserial; consensus rank is Chapter 4's three-view aggregate.

<!-- cols: 1.05 2.00 3.45 -->

| Shift | What was measured | Result |
|---|---|---|
| Direction | Class leaning reverses sign | **15 of 43**, a superset of Chapter 3's three, led by `len_chars` +0.247 / −0.171 and `len_tokens` +0.135 / −0.207 |
| Strength | Mean \|effect\| across the 43 | 0.0867 (D1) vs **0.0617** (D2); the two 43-vectors correlate at Pearson *r* = 0.317 |
| Reliance | Consensus rankings' agreement | Spearman 0.596 / Kendall τ 0.417 |

## 5.3 No data leakage: every fitted transform is fit inside the fold

**No fitted transform is ever applied to a frame and then split.** Every pipeline
puts `EngineeredFeatures` and `StandardScaler` ahead of the classifier
(`src/models.py:79-83`, `:150-154`, `:177-180`), so the scaler learns its 43
means and deviations from the rows `fit` receives — the training fold under
`StratifiedKFold`, the training split under hold-out. `CharNgramFeatures`
(`src/preprocessing.py:64-69`, `:83-88`) and `CNN1DClassifier`
(`src/models.py:276`) likewise fit their TF-IDF vocabulary and character index
inside their own `fit`; `tests/test_pipeline.py:66-83` asserts two disjoint folds
yield **different** vocabularies. The upstream 80/20 split is grouped by command
shape, so no near-duplicate straddles it.

**The one pre-split transform is stateless, which is why it is not leakage.**
`normalize()` (`scripts/build_dataset.py:240-247`) folds smart quotes, strips
control bytes, hashes IPv4 addresses and URL hosts; its output depends on that
row alone, on no corpus statistic.

**Scaling lives in the pipeline, as §3.5 required, and changes nothing for the
shipped models.** Removing the scaler moves Random Forest F1 by 0.0017 (D1) and
0.0003 (D2) and leaves Isolation Forest scores bit-identical: tree splits depend
only on rank order, which (*x*−μ)/σ preserves. One residue: under transfer a
Dataset-1 model keeps its Dataset-1 scaler, centring Dataset-2 commands on the
wrong means. Refitting on the target would be leakage, so that is correct — but
on a distance-based detector part of Chapter 8.2's degradation would be a stale
scaler, not the shift.
