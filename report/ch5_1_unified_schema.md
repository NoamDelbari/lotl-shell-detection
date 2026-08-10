# Chapter 5.1 — The Unified Feature Schema

> Every number in this section is measured against the current build. Sources:
> `src/ingestion.py`, `src/features.py`, `src/preprocessing.py`,
> `results/ch3_feature_audit.json`, `docs/DATA_CARD.md`.

## What has to be reconciled

The two corpora are not two samples of one population. Dataset 1 is assembled
from published attack catalogues and a payload generator on the malicious side
(HackTricks, GTFOBins, Atomic Red Team, QuasarNix, SLP, InternalAllTheThings)
and from documentation and instruction corpora on the benign side (tldr,
bash-instruct, nl2bash, LinLM, bash_command_6k). Dataset 2 is real capture on
both sides: attacker input from Cowrie SSH honeypot sessions, benign input from
harvested `.bash_history` files and commandlinefu. They are 15,248 and 9,576
rows, they share **no source at all**, their licences differ, and one is written
by people documenting commands while the other is typed by people running them.

What they do share is the artefact. Both, ultimately, are lists of Linux shell
command lines, and that is the level at which the project harmonises them.

## One column, one contract

The unified representation is the raw `command` string. `src/ingestion.py` is by
design **the only dataset-aware module in the pipeline**: it holds a registry
mapping a dataset name to its two CSVs, and it returns every corpus in one
enforced three-column schema —

| column | type | role |
|---|---|---|
| `command` | `str` | the sole model input |
| `label` | `int ∈ {0,1}` | 1 = malicious, provenance-derived |
| `source` | `str` | provenance tag, **evaluation only, never an input** |

The loader coerces types, rejects empty command strings and rejects labels
outside `{0,1}` on the way through, so a malformed corpus fails at load rather
than silently at fit time. Nothing downstream ever learns which dataset it is
reading — dataset names are banned from every other module in `src/`, including
in comments, and that ban is enforced by a test. The practical consequence is
the one the assignment asks for: a third corpus can be registered in one place
and the entire pipeline runs on it unchanged.

Both datasets are additionally held to the same experimental protocol rather
than merely the same column names: 1 attack to 3 benign in each, an 80/20
train/test split **grouped by command shape** so no structural near-duplicate
straddles the split (verified: zero shape groups appear on both sides of either
split, in either label), and therefore the same do-nothing F1 floor of 0.400
against which every score in this report is read.

## Why the schema is genuinely shared, and where it is not

A common column name is cheap. The substantive claim is that feature *k* means
the same thing in both corpora, and that holds here because the extractor is
**stateless**. `featurize()` (`src/features.py:280`) maps a command string to
the same 43 numbers through fixed regexes and fixed threat-mapped binary lists;
`EngineeredFeatures.fit()` (`src/preprocessing.py:34`) learns nothing at all and
exists as a transformer only so that a downstream `StandardScaler` can be the
component that fits fold-local statistics. No vocabulary, no quantile, no
per-corpus constant is carried in. `has_dev_tcp` is the same predicate on a
honeypot line as on a GTFOBins line, which is precisely what makes the
cross-dataset comparison of effect sizes and importances in Section 5.2 a
comparison rather than a coincidence.

The honest qualification is that the hybrid model's *second* representation does
not have this property. `CharNgramFeatures` (`src/preprocessing.py:48`, unioned
in at `build_hybrid_features`, `:75`) fits a character n-gram TF-IDF vocabulary
on the training fold — correctly leakage-safe, but corpus-bound by construction.
Fitted separately on the two training splits at the same 3,000-feature cap, the
two vocabularies share only **1,789 n-grams (Jaccard 0.425)**: 40.4% of what
each corpus considers its most informative character patterns has no counterpart
in the other. The hybrid therefore carries one harmonised block and one
un-harmonisable one, and that asymmetry is the mechanism behind the transfer
results in Chapter 8.2 — it is stated here rather than discovered there.

## The selection protocol is the real harmonisation

The strongest sense in which the two corpora are treated identically is not the
schema but the way the feature set was *chosen*. Sixty-eight candidates were
proposed from the threat model in Chapter 1.2 and reduced to 43 by a single
pre-registered gate, computed on each corpus's **training split only** and
applied to both without modification:

> Mann–Whitney *p* < 0.01 **and** (|Cliff's δ| ≥ 0.10 for continuous features, or
> odds ratio ≥ 1.5 / ≤ 0.667 for binary ones), followed by a Spearman |ρ| > 0.90
> redundancy cull that keeps one representative per correlated cluster.

Survival requires passing on **at least one** corpus, not both, and the resulting
split is itself a result worth stating plainly. Of the 43 features kept, **22
clear the gate on both datasets, 16 on Dataset 1 only, 5 on Dataset 2 only, and
none on neither**. Half the feature set is therefore corpus-specific evidence.

That threshold was a deliberate choice against the stricter alternative.
Requiring both corpora would have produced a 22-feature set and would have
deleted, among others, `has_dev_tcp` — the sharpest signal in the project at OR
559 on Dataset 1. It fails on Dataset 2 not because it reverses (its odds ratio
there is still 9.0) but because it is too rare to reach significance: it fires
on 2.95% of Dataset 1's attacks and 0.05% of Dataset 2's, since real intruders
fetch a payload with `wget` rather than opening bash's `/dev/tcp` redirect —
`has_fetch_bin` correspondingly rises from 6.3% to 21.9% of the malicious class.
The same rule would have deleted `head_is_privesc`, the only surviving encoding
of the sudo behaviour in Section 1.2, for the mirror-image reason: it is
significant but near-neutral on Dataset 1 (OR 0.77) and strong on Dataset 2
(OR 3.70). A
rule that discards a technique because one of two corpora happens not to contain
it is not a harmonisation rule; it is a lowest-common-denominator rule, and it
would have hidden exactly the cross-corpus disagreement this chapter exists to
measure.

What is deliberately *not* harmonised is as important. There is no per-dataset
feature, no per-dataset threshold, no per-dataset normalisation constant and no
per-dataset model configuration anywhere in the pipeline. Every difference
reported in Section 5.2 is therefore a property of the data, not an artefact of
having processed the two corpora differently.
