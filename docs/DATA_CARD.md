# Data Card — two Linux shell command datasets (malicious vs benign)

**Task.** Binary classification of a single Linux shell command line as
malicious (1) or benign (0). MITRE ATT&CK T1059.004 (Unix Shell),
Living-off-the-Land. Built 2026-08-06 by `build_dataset.py` (seed=42).

## Two datasets, each with attacks and normal commands
No single public dataset has both malicious and benign Linux commands, so we
assemble from public parts (standard practice: SLP 2021, Oliveira & Cafe 2024).
Both datasets are used for training and testing.

The two datasets are **built** provenance-matched: inside a dataset, the attack
side and the normal side are drawn from the same KIND of source (Dataset 1 =
generated and curated on both sides, Dataset 2 = real captured on both sides).
That is a statement about how the datasets were assembled, and it is intended to
stop a model from separating the classes on collection style instead of
maliciousness. **Whether it succeeds is a separate, measured question, and the
answer is currently no** — see "Measured outcomes" below and the P8
source-separability probe in `BASELINE.md`. Treat provenance matching as an
intention, not as a verified property of the finished data.

| | Dataset 1 (generated + curated) | Dataset 2 (real-world) |
|---|---|---|
| attack commands | QuasarNix, SLP, GTFOBins, Atomic Red Team, HackTricks, InternalAllTheThings | SSH honeypot (Cowrie) |
| normal commands | nl2bash, tldr-pages, bash-instruct, LinLM, bash_command_6k | captured `.bash_history`, commandlinefu |
| total | 15,248 | 9,576 |
| train / test | 12,199 / 3,049 | 7,661 / 1,915 |
| attacks / normal | 3,812 / 11,436 | 2,394 / 7,182 |
| distinct command shapes | 14,945 | 9,391 |

Class ratio is 1 attack : 3 normal in both datasets — malicious commands are rare
in real host telemetry, so a 50/50 split would overstate precision. Report
PR-AUC and TPR at a low fixed FPR, not accuracy.

## What the label MEANS
A command is malicious because of **where it came from**, never because of what
it contains.

- **Dataset 1, label 1** = the string is published as an attack payload
  (QuasarNix generator output, SLP, GTFOBins, Atomic Red Team, HackTricks,
  InternalAllTheThings). For the catalogue sources the payload is read from the
  field that carries the attack itself — GTFOBins/HackTricks/IATT code blocks,
  Atomic Red Team's `executor.command` — never from a test harness's
  setup/teardown field (`prereq_command`/`cleanup_command`), so the label stays a
  fact about provenance rather than a function of the text.
- **Dataset 2, label 1** = the string was typed by an attacker during a real
  Cowrie SSH intrusion. Every usable command atom of every attacker session
  carries label 1, including reconnaissance that looks innocuous in isolation
  (`uname -a`, `cd /tmp`). Session-level provenance is the whole rule.

This matters because an earlier build kept a honeypot command only if it matched
a hand-written keyword regex (`RE_MAL_MARKERS`: wget, curl, chmod +x, /dev/tcp,
…). The label was then a restatement of that regex, and run back over its own
output the regex scored **F1 0.9527 at p = 0.250, against a do-nothing floor of
0.400** — a number that measured nothing but its own definition. The keyword rule
no longer selects any row anywhere in the build. It survives only as a
permanently reported probe in `BASELINE.md`, so that if lexical selection is ever
reintroduced, that probe's recall jumps and the regression is visible.

**Known label noise from this rule — measured, and the three routes disagree.**
Provenance labelling means a command that is harmless read in isolation carries
label 1 if an attacker typed it. Three ways of sizing that cost are computed by
this build, and they do not agree; the largest is the one to quote.

| route | what it measures | result |
|---|---|---:|
| upstream `Set_Fingerprint` | honeypot atoms seen **only** in sessions the upstream annotators fingerprinted exactly `['Harmless']`, as a share of atoms reaching that filter | 216 / 407,658 = **0.053%** |
| LogPrecis expert annotations | statements the LogPrecis authors annotated `Harmless`, over all 10,771 annotated statements in their 359 sessions | 237 = **2.20%** |
| direct, on this dataset | Dataset 2 malicious rows that are a single bare read-only command (`cd X`, `ls`, `pwd`, `uname -a`, `cat /proc/cpuinfo`, …) | 98 / 2,394 = **>= 4.09%** |

The first two measure *someone else's session-level or statement-level
annotation*; only the third measures rows of this dataset. The third is a **lower
bound** by construction: it requires the whole command to be one bare read-only
command, so `uname -a & lscpu`, `cat /proc/cpuinfo | grep name | head -n 1` and
`ls -l /bin/dhpcd` are all counted as *not* innocuous. Sample of what it does
catch: `cd .`, `cd ../..`, `cd .ICE-chm`, `cd .ICE-unix/`, `cd .Nasa`, `cd .bash`, `cd .cache`, `cd .d`.

So the honest statement is **at least 4.1% of Dataset 2's malicious rows are
innocuous read in isolation**, not the "~1%, measured two independent ways, both
agree" that earlier versions of this card asserted. That sentence was a hardcoded
literal: nothing computed it, `raw/logprecis.json` was never opened by any code,
and the two routes it named differ from each other by a factor of
42.

Commands seen **only** in sessions fingerprinted exactly `['Harmless']` are
excluded (216 of 407,658); that exclusion comes from someone else's
session labels, never from the command text.

## Files
- `dataset/dataset1_{train,test}.csv` and `dataset/dataset2_{train,test}.csv` — columns `id, command, label, source, split`; the 80/20 group-aware split, one file per side.
- `docs/stats.json` — machine-readable counts for everything below.
- `docs/baseline_metrics.json`, `docs/BASELINE.md` — baseline scores, ablations and regression probes (`scripts/evaluate_baseline.py`).
- `scripts/raw/extracted/*.cm` — vendored one-command-per-line extracts; `scripts/extractors/` holds the script that produced each.

## Sources, provenance, licence
### Dataset 1
| source | class | kind | licence | upstream |
|---|---|---|---|---|
| `atomic_red_team` | malicious | curated | MIT | github.com/redcanaryco/atomic-red-team |
| `gtfobins` | malicious | curated | GPL-3.0 | github.com/GTFOBins/GTFOBins.github.io |
| `hacktricks` | malicious | curated | CC-BY-NC-4.0 | github.com/HackTricks-wiki/hacktricks |
| `payloads` | malicious | curated | MIT | github.com/swisskyrepo/InternalAllTheThings |
| `quasarnix` | malicious | synthetic | Apache-2.0 | hf.co/datasets/dtrizna/QuasarNix |
| `slp` | malicious | curated | MIT | github.com/dtrizna/slp |
| `bash6k` | normal | synthetic | Apache-2.0 | hf.co/datasets/emirkaanozdemr/bash_command_data_6K |
| `bash_instruct` | normal | synthetic | MIT | hf.co/datasets/Frost2o24/bash-instruct-55k |
| `linlm` | normal | synthetic | Apache-2.0 | hf.co/datasets/missvector/linux-commands |
| `nl2bash` | normal | curated | GPL-3.0 | github.com/TellinaTool/nl2bash |
| `tldr` | normal | curated | CC-BY-4.0 | github.com/tldr-pages/tldr |

### Dataset 2
| source | class | kind | licence | upstream |
|---|---|---|---|---|
| `honeypot` | malicious | real | MIT | github.com/ML4Net/SSH-Shell-Attacks |
| `bash_history` | normal | real | MIT | hf.co/datasets/spignelon/bash_history |
| `commandlinefu` | normal | real | site ToS | commandlinefu.com JSON API |

Licences are mixed: one arm is copyleft (GPL-3.0: nl2bash, GTFOBins) and one is
non-commercial (CC-BY-NC-4.0: HackTricks). Ship the build script and the per-row
`source` column rather than redistributing a merged corpus file, and treat the
result as non-commercial while a CC-BY-NC arm is present.

## Processing
1. **Normalise** every command: IPv4 and URL host are replaced by a value
   *derived from a hash of the original*, smart quotes to ASCII, control bytes
   stripped, whitespace collapsed.
2. **Honeypot sessions** (233,035 real Cowrie sessions) are split into command
   atoms on `;`, `&&`, `||` and newline — **quote-aware**, so `awk '{print $4;}'`
   is no longer cut in half. Pipelines are kept intact. Every usable atom is kept
   and labelled by provenance (see "What the label MEANS"); 407,818 distinct atoms
   result.
3. **Well-formedness filter, applied to every source.** Eight rules, each of
   which answers only "is this string a shell command line?" — unterminated
   quote, terminal control bytes / caret notation, spaced assignment
   (`args = options`), JSON member, markup tag, Python block line, no word
   character at all, bare prompt phrase (`Enter new UNIX password:`).
   **11,517 rows** removed in total; per-rule, per-source counts are in the
   table below and in `stats.json > well_formed_dropped`. No rule may reference
   maliciousness or a command vocabulary — a filter that removes attacker-dropped
   binary names while leaving benign rows untouched would be the same
   circularity as the old keyword selection, so a command-name allowlist was
   considered and rejected.
4. **Uniform per-shape cap.** Every source is reduced to at most
   2 commands per distinct command shape, dealt round-robin over shapes so
   every structure is represented before any structure repeats. This used to
   apply to QuasarNix alone (and the honeypot used a different, weaker dedup),
   which let the two generator-scale sources contribute tens of thousands of
   near-copies while the curated sources contributed a few hundred distinct ones.
   Per-source figures below and in `stats.json > shape_cap`.
5. **Label hygiene.** 363 distinct strings appeared verbatim in both a malicious
   and a benign source (`vim`, `curl`, `ping`, `apt-get update`, …) and were
   dropped from both. A further 337 distinct strings were dropped because their
   *shape* appeared under both labels. (Both figures count **strings**, not rows;
   the per-dataset `shape_conflict_malicious_rows` in `stats.json` count rows and
   will not reconcile with them.) Dataset 1 5.90% of its malicious pool
   (fired), Dataset 2 8.96% (fired); the branch fires above
   5%. 95 further rows inside benign sources carried an
   unambiguous download-and-run attack pattern and were dropped as label noise.
6. **Dedup** by exact normalized string, keep-first, across everything.
7. **Per-source share cap on the normal class.** No single source may supply more
   than 70% of a dataset's normal commands; the remainder is re-apportioned
   across the other sources by largest-remainder apportionment, and the cap is
   exceeded only if every other source is exhausted (reported as `cap_breached`,
   currently `False` for Dataset 2). Within a source the draw is again
   round-robin over shapes, so the surviving rows are the structurally most
   diverse ones rather than a uniform sample.
8. **Split** each dataset 80/20 train/test, **grouped by command shape** so an
   identical structure never straddles the split.

### Per-source effect of the shape cap
| source | dataset | class | pool rows | distinct shapes | rows/shape | kept |
|---|---|---|---:|---:|---:|---:|
| `honeypot` | 2 | malicious | 407,442 | 2,455 | 165.96 | 2,655 |
| `quasarnix` | 1 | malicious | 239,638 | 102 | 2,349.39 | 204 |
| `bash_history` | 2 | normal | 50,978 | 45,384 | 1.12 | 46,784 |
| `bash_instruct` | 1 | normal | 33,869 | 22,876 | 1.48 | 24,759 |
| `tldr` | 1 | normal | 29,552 | 29,349 | 1.01 | 29,474 |
| `nl2bash` | 1 | normal | 10,548 | 9,561 | 1.1 | 10,055 |
| `commandlinefu` | 2 | normal | 7,025 | 6,706 | 1.05 | 6,841 |
| `linlm` | 1 | normal | 5,429 | 5,323 | 1.02 | 5,388 |
| `bash6k` | 1 | normal | 4,077 | 3,727 | 1.09 | 3,908 |
| `hacktricks` | 1 | malicious | 2,054 | 1,858 | 1.11 | 1,950 |
| `gtfobins` | 1 | malicious | 1,115 | 991 | 1.13 | 1,039 |
| `atomic_red_team` | 1 | malicious | 863 | 710 | 1.22 | 763 |
| `slp` | 1 | malicious | 123 | 101 | 1.22 | 111 |
| `payloads` | 1 | malicious | 69 | 61 | 1.13 | 64 |

### Per-source effect of the well-formedness filter
| source | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `atomic_red_team` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `bash6k` | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 13 |
| `bash_history` | 385 | 7 | 36 | 9 | 5 | 1 | 0 | 45 | 488 |
| `bash_instruct` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `commandlinefu` | 56 | 8 | 1 | 0 | 21 | 0 | 0 | 0 | 86 |
| `gtfobins` | 30 | 6 | 2 | 0 | 0 | 0 | 4 | 0 | 42 |
| `hacktricks` | 0 | 0 | 0 | 8 | 0 | 0 | 2 | 2 | 12 |
| `honeypot` | 16 | 62 | 0 | 62 | 14 | 0 | 5 | 1 | 160 |
| `linlm` | 9 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 11 |
| `nl2bash` | 35 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 37 |
| `payloads` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `quasarnix` | 10,565 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10,565 |
| `slp` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `tldr` | 5 | 0 | 0 | 0 | 85 | 0 | 11 | 2 | 103 |

### Source concentration in the finished datasets
| dataset | class | shares |
|---|---|---|
| dataset1 | malicious | `hacktricks` 47.3%, `gtfobins` 25.1%, `atomic_red_team` 18.0%, `quasarnix` 5.3%, `slp` 2.6%, `payloads` 1.6% |
| dataset1 | normal | `tldr` 40.0%, `bash_instruct` 34.4%, `nl2bash` 13.7%, `linlm` 6.6%, `bash6k` 5.3% |
| dataset2 | malicious | `honeypot` 100.0% |
| dataset2 | normal | `bash_history` 70.0%, `commandlinefu` 30.0% |

## Measured outcomes from `BASELINE.md`
<!-- BEGIN measured-outcomes -->
_Measured by `evaluate_baseline.py` (seed 42) against the current `dataset/`. Every score is shown with the prevalence it was measured at and the do-nothing floor 2p/(1+p) that follows from it._

| setting | n | prevalence p | do-nothing floor | F1 | fraction of headroom |
|---|---:|---:|---:|---:|---:|
| `dataset1` in-distribution test | 3,049 | 0.250 | 0.3999 | 0.8975 | 0.8293 |
| `dataset2` in-distribution test | 1,915 | 0.250 | 0.4002 | 0.8824 | 0.8040 |
| transfer `dataset1` -> `dataset2` | 9,576 | 0.250 | 0.4000 | 0.5844 | 0.3073 |
| transfer `dataset2` -> `dataset1` | 15,248 | 0.250 | 0.4000 | 0.2740 | -0.2101 |

**Transfer is not symmetric, and neither direction is a pass.** `dataset1 -> dataset2` reaches F1 0.5844 against a floor of 0.4000 - above the floor, but only 30.7% of the available headroom, against 80.4% for a model trained on Dataset 2 itself. `dataset2 -> dataset1` reaches 0.2740 against a floor of 0.4000 (-21.0% of headroom). The earlier wording "both directions sit near or below the do-nothing floor" was wrong about the first direction; the accurate statement is that one direction is clearly above its floor while capturing a small fraction of the headroom, and the other is not.

**P8 source separability, `dataset1`: FAILED.** Benign-source macro-F1 0.7965 over k = 5 classes on n = 2,287 rows, against a do-nothing floor of 0.1161 (77.0% of headroom). Mean pairwise benign-vs-benign macro-F1 0.9085 raw / 0.8393 normalised over 10 pair(s), against the 0.90 raw / 0.85 normalised lines. Bootstrap over pairs: [0.8713, 0.9452] - the 0.90 line is inside it, so this verdict is BORDERLINE and rests on a margin smaller than the spread between pairs. Style gap (mal-vs-ben minus ben-vs-ben) +0.0488 raw, +0.0864 normalised; the normalised value is the comparable one because the two families have different floors.

**P8 source separability, `dataset2`: passed.** Benign-source macro-F1 0.8990 over k = 2 classes on n = 1,436 rows, against a do-nothing floor of 0.4167 (82.7% of headroom). Mean pairwise benign-vs-benign macro-F1 0.8990 raw / 0.8269 normalised over 1 pair(s), against the 0.90 raw / 0.85 normalised lines. With only two benign sources these two statistics are the same fit reported twice, not independent evidence. Style gap (mal-vs-ben minus ben-vs-ben) +0.0280 raw, +0.0550 normalised; the normalised value is the comparable one because the two families have different floors.

**Leave-one-source-out.** Retraining with a malicious source deleted from the training set and rescoring that source's test rows: `atomic_red_team` 0.902 -> 0.624; `gtfobins` 0.905 -> 0.402; `hacktricks` 0.890 -> 0.538; `payloads` 1.000 -> 0.867; `quasarnix` 1.000 -> 0.983; `slp` 0.957 -> 0.957. Sources that keep their recall are reachable from the rest of the corpus; sources that collapse were being recognised rather than detected. Collapsing: `gtfobins`. Holding above 0.90: `quasarnix`, `slp`.

**Near-duplicate leakage** (measured without `shape()`, so it catches what a shape-group straddle count structurally cannot): every test row is compared to the most similar TRAIN row of its own source as character 4-gram sets. The worst source is `slp` in `dataset1`, with 17.4% of its 23 test rows above the loose 0.80 line and 4.3% above the strict 0.90 line (median similarity 0.565). The assertion is on the strict line at 10%; per-source recall for a source above the loose line is partly recall on variants of commands already seen in training. On difflib's ratio - the metric on which `quasarnix` measured 26.2% before the `shape()` repair, and 2.5% after it - the sources above 10% are: `slp` (dataset1) 39.1%; `honeypot` (dataset2) 24.0%; `bash_instruct` (dataset1) 23.7%; `atomic_red_team` (dataset1) 19.5%; `gtfobins` (dataset1) 19.0%; `hacktricks` (dataset1) 12.5%. Those are curated corpora of short commands that share payload templates, so the number is an upper bound on leakage, not a measurement of it - but their per-source recall may not be quoted as recall on unseen technique.

<!-- END measured-outcomes -->

## Known limitations / confound caveats (read before trusting a score)
The **counts** below come from this build's `stats.json`. Every **score**
mentioned is produced by `evaluate_baseline.py` into `docs/BASELINE.md` and
`docs/baseline_metrics.json`; read the current values there rather than trusting
a number copied into prose.

- **F1 has no absolute scale here.** At 1:3 the prevalence is
  0.250/0.250, so a model that shouts MALICIOUS at everything already
  scores 2p/(1+p). Every row of every table in `BASELINE.md` therefore carries
  n, prevalence, that do-nothing floor, and F1 normalised by the remaining
  headroom. Never quote an F1 from this project without its floor.
- **Address shortcut (mitigated at the token level, still present as a
  correlation).** Every QuasarNix reverse shell carries a network address; benign
  commands rarely do. An earlier build mapped all IPv4 to the constant `1.1.1.1`,
  so that one token appeared in 100.0% of malicious and ~1% of benign commands
  and was by itself a near-perfect classifier. Addresses are now hashed per
  value, which removes the constant token — but "contains any IPv4" remains a
  meaningful single-feature rule on Dataset 1. `BASELINE.md` reports it as a
  probe and repeats every score with all addresses stripped from both classes.
- **Length shortcut.** Malicious commands in Dataset 1 are far longer than benign
  ones, so command length alone is a usable feature. The length ablation pairs
  each attack with an *unused* benign command of the same length (within
  max(5 chars, 10%)) and **drops attacks it cannot pair**, making the subset
  exactly 1:1. An earlier version kept the unmatched attacks, which produced a
  "length-matched" Dataset 1 subset that was 83% malicious — its F1 was being
  read against a 0.908 floor while presented next to 0.400-floor numbers.
  `BASELINE.md` now reports the **coverage** of the match; where coverage is low
  the ablation speaks only for the short end of the malicious class.
- **Source concentration.** See the table above. Where one source supplies more
  than 50% of a class the build prints a warning; the rows are kept
  (concentration is a fact about what is publicly available) but per-source
  recall must be reported, never the aggregate alone. `BASELINE.md` gives
  per-source rates as k/n with Wilson 95% intervals and flags every pair of
  sources whose intervals overlap, because "source A scores better than source B"
  is usually not supported at these sample sizes.
- **Cross-dataset transfer is poor, and that is the interesting result.** A
  detector trained on synthetic reverse shells does not recognise real honeypot
  activity, and vice versa. The two directions are **not** symmetric and must be
  quoted separately with their headroom fractions — see "Measured outcomes"
  above, which carries the current numbers. This is the finding the two-dataset
  design exists to produce; do not treat it as a bug to be tuned away.
- **Collection-style separability — measured, and it FAILED.** `BASELINE.md`'s P8
  probe asks a classifier which *pile* a command came from, ignoring the
  malicious/benign label. The current verdicts are in "Measured outcomes" above.
  Because the probe fails, the consequences it names are live, not hypothetical:
  the headline F1 is partly corpus identification and **must** be presented as an
  upper bound, it may not be quoted without the transfer result beside it, and
  the ablations are load-bearing rather than confirmatory.
- **QuasarNix is still lexically distinct from every benign Dataset 1 source.**
  The shape fix removed QuasarNix's numerical dominance and its near-copy
  leakage; it did not remove the fact that every generated reverse shell carries
  a network address while ordinary commands do not. In this build: `quasarnix` 204/204 = 100.0%, against 0.17%-1.06% for every benign Dataset 1 source.
  A per-source recall of 1.000 on `quasarnix` in `BASELINE.md` is therefore not
  evidence of detection capability — see the pairwise macro-F1 rows for that
  source in P8 (b).
- **Residual junk in the malicious pool.** Roughly 3-5% of Dataset 2's malicious
  rows are still not command lines: single-token password guesses typed at a
  login prompt (`admi`, `adminpasswd`, `!@#$1234`), terminal residue that is not
  at a string boundary, and loop-body fragments (`do echo $i`, `done < .s`).
  Removing them would require exactly the command-vocabulary judgement rejected
  in processing step 3, so they stay and are declared here instead.
- **Accepted well-formedness false positives.** W8 (prompt phrase) removes
  tldr's `incus image list images:` and `... local:` — an `incus` remote name
  legitimately ends in `:`. W1's quote scanner does not honour backslash escapes,
  so a few heavily escaped commandlinefu recipes are lost (~0.8% of that source).
- **Placeholder style.** GTFOBins and tldr both use `path/to/…` placeholders on
  opposite labels, so the placeholder itself carries a little label signal in
  Dataset 1.
- **Synthetic share, and which dataset to trust.** Dataset 1's normal side is
  partly LLM/template-generated (bash-instruct, LinLM, bash_command_6k);
  Dataset 2's is fully organic on both sides. That is one point in Dataset 2's
  favour, and it does **not** settle the question: Dataset 2 is also the dataset
  whose P8 source-separability probe scores worse and whose style gap is smaller,
  i.e. less of its headline score is attributable to maliciousness rather than to
  collection style (see "Measured outcomes" above), and its labels carry the
  provenance noise measured in "What the label MEANS". Neither dataset dominates
  the other; quote both. (On size: Dataset 1 has 15,248 rows and Dataset 2
  has 9,576, so **Dataset 1
  is the larger of the two**. That comparison is computed from this build rather
  than asserted: the sentence used to hardcode the opposite conclusion and stayed
  in the card unchanged after the row counts moved, so it stated the reverse of
  the two numbers printed immediately before it.)
- **`shape()` is lossy and is not a security control.** It blanks quoted strings,
  base64/hex blobs, numbers, variable names, random-looking alphanumeric runs and
  the arbitrary file name directly below a scratch or home directory (`/tmp/…`,
  `/var/tmp/…`, `/var/www/…`, `/dev/shm/…`, `/root/…`, `/home/<user>/…`, `~/…`),
  and it collapses whitespace. Two genuinely different commands can share a
  shape; that costs recall in the split, never correctness of a label. Measured
  over-collapse of the scratch-name rule on the benign pools: tldr 0 shapes,
  bash_history -0.13%, nl2bash -0.06%, commandlinefu -0.03%.
- **`shape()`'s randomness test is blind to all-lowercase random words.**
  `_randomish()` is character-level: it catches `PIALH`, `j6rslnsu`, `Ab3cDe`,
  but not `zanjaffk` or `orverpzt`, which have the length and vowel ratio of
  ordinary words. Adding a rule for those was measured and rejected — it
  collapsed nothing further (the scratch-name rule already covers the case that
  mattered) and merged another 1.1% of `bash_history` and 1.5% of `linlm` shapes.
  If a future source puts random lowercase words somewhere other than a scratch
  path, this blindness will let near-copies through, and the near-duplicate
  metric in `BASELINE.md`'s P2/P7 section is what will show it.
- **Shape groups are formed per label,** so a shape appearing on both labels can
  be train-side for one and test-side for the other. This works against the
  model, not for it: it sees a structure labelled benign in training and must
  call it malicious at test. `BASELINE.md` counts these.
