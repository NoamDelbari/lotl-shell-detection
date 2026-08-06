# Known issues in the dataset build and evaluation

**Status:** mostly resolved. Written 2026-08-03 after auditing the 2026-08-02
rebuild; P1–P4 fixed 2026-08-04, D1 expanded 2026-08-05 (a benign FPR audit
capability added the same day was removed in the 2026-08-06 handoff cleanup as
out of scope). Current build: Dataset 1 = 15,248 rows, Dataset 2 = 9,576 rows.
Per-problem resolution is in the **Resolution status** table below; the diagnostic
sections that follow are kept verbatim as the record of what was wrong and why.

**What this document is.** Every problem known in `build_dataset.py` and
`evaluate_baseline.py`, explained from scratch, with the evidence, the cause, and
the fix. Written to be handed to someone (or something) that has to fix them
without having been part of the original work. The problem sections (P1–P8) below
are the original 2026-08-03 diagnosis, left unedited as the record of what was
wrong; their current disposition is in the **Resolution status** table above.

**Read this first if you are about to quote a number from `BASELINE.md`.** The P3
prevalence trap is fixed — every row now carries its prevalence and the do-nothing
floor `2p/(1+p)`, so an F1 can no longer be read on the wrong ruler. But P8 still
**FAILs on Dataset 1** (a real shortcut, see below); the top of `BASELINE.md`
says so and tells you not to quote a score until the failure is explained.

> **Blocking (partially cleared):** `final_project/preliminary_proposal.md` §6.1,
> the generated `preliminary_proposal.pdf`, and
> `final_project/email_to_advisor.txt` still state the old "~0.98 F1 after
> stripping addresses and matching lengths" claim, which P3 showed was measured on
> the wrong ruler. P3 is fixed and the numbers are regenerated (see the deltas
> below), so the claim can now be **corrected** — but the proposal/PDF/email have
> not yet been rewritten. **Do not send the email or circulate the PDF until those
> three documents are updated to the regenerated numbers.**

---

## Background: two ideas you need before the rest makes sense

### Idea 1 — a score is only meaningful relative to what a stupid model would get

F1 is not on an absolute scale. It depends on **prevalence**: the fraction of the
test set that is actually malicious.

Consider a "model" that ignores its input and shouts MALICIOUS at everything. Its
recall is 1.0 and its precision is just the prevalence, so:

```
F1(always-malicious) = 2p / (1 + p)      where p = fraction malicious
```

| prevalence | F1 of the do-nothing model |
|---:|---:|
| 25% | 0.400 |
| 51% | 0.678 |
| 83% | **0.908** |

So **F1 = 0.95 on an 83%-malicious test set is worse than F1 = 0.85 on a
25%-malicious test set.** The first beats do-nothing by 0.04; the second beats it
by 0.45. Any time you change the test set, you must recompute the floor, or you
are comparing scores measured on different rulers.

### Idea 2 — a shortcut is a feature that separates the classes for the wrong reason

We want the model to learn *"this command does something malicious"*. The risk is
it instead learns *"this command came from the malicious pile"* by latching onto
some artefact of how we collected the data — a token, a length, a formatting
habit. It then scores brilliantly on our test set and fails completely in
production, because production data has no such artefact.

There are two distinct diseases here, and it matters which one you have:

- **Shortcut** — a feature that *happens* to correlate with the label because of
  how the sources were collected. Example: our attack source generates long
  commands with IP addresses; our benign sources are short tutorial one-liners.
- **Circularity** — the label was *defined* by the feature. The model recovers
  our own selection rule and scores near-perfectly by construction. This is
  worse, because no amount of model improvement can fix it.

Dataset 1 has a shortcut problem. Dataset 2 has a circularity problem.

---

## Summary

| id | problem | severity | what it invalidates |
|---|---|---|---|
| **P1** | Dataset 2's malicious labels were defined by a keyword regex, and the model just relearns that regex | **critical** | Dataset 2's entire headline score |
| **P2** | `shape()` fails to normalise QuasarNix's random variable names, so the anti-leakage grouping does nothing | **critical** | Dataset 1's QuasarNix recall; the "shape-stratified sampling" claim |
| **P3** | `length_match()` changes class prevalence, so the length ablation compares scores on different scales | **high** | the length-ablation rows of `BASELINE.md`, §6.1 of the proposal, the advisor email |
| **P4** | Per-source recall reported to 4 significant figures on as few as 27 samples | medium | the "0.815 vs 0.819 vs 0.821" comparison |
| **P5** | 89.8% of Dataset 1's malicious class is one generator (QuasarNix) | medium (design) | how much the aggregate D1 number means |
| **P6** | 88% of Dataset 2's benign class is one source (`bash_history`) | low | breadth of D2's benign side |
| **P7** | Shape groups are built per label, so 8 shapes straddle the split | low | nothing (works against the model) |
| **P8** | Untested: are the sources themselves trivially distinguishable? | unknown | possibly everything; needs measuring |

---

## Resolution status (as of 2026-08-05)

| id | status | how, and where it is now enforced |
|---|---|---|
| **P1** | **fixed** (2026-08-04) | Labels are now **provenance**-based, never lexical. A row is malicious because of *where it came from* (typed inside a real attacker session, for D2; drawn from an attack-tradecraft catalogue, for D1), never because it matches a keyword. `RE_MAL_MARKERS` is demoted to a **probe-only** signal and decides no label. The P1 selection-regex probe (regex-as-classifier) **PASSes** on both datasets. |
| **P2** | **fixed** (2026-08-04) | `shape()` now collapses QuasarNix's random variable names (and base64/hex/numbers/scratch-dirs). The P2/P7 rows-per-shape probe **PASSes** on both datasets; QuasarNix collapses 239k raw lines → 102 shapes, so it can no longer leak identical templates across the split. |
| **P3** | **fixed** (2026-08-04) | `length_match()` returns an exactly 1:1 subset, drops unmatched attacks, and reports coverage; every reported row carries prevalence and the do-nothing floor `2p/(1+p)`, plus a headroom-normalised column. Was pinned by a test suite (removed in the 2026-08-06 handoff cleanup). The length ablation can no longer be quoted at a prevalence it was not measured at. |
| **P4** | **fixed** (2026-08-04) | Every per-source rate carries a **Wilson** 95% interval; `SMALL_N=30` flags point estimates too small to quote; pairwise source comparisons print `OVERLAP`/`SEPARATED` so no "0.815 vs 0.819" claim can be made across overlapping intervals. |
| **P5** | **substantially resolved** (2026-08-05) | The D1 expansion cut QuasarNix from **89.8% → 5.4%** of the D1 attack side. The largest source is now `hacktricks` at 47.4%, but it is **shape-diverse tradecraft, not a generator** (1.11 rows/shape, 1,795 new shapes) — the opposite of the P5 failure mode. `MAX_SOURCE_SHARE=0.70` still guards against any single source dominating. |
| **P6** | **improved, still low** | bash_history fell from 88% → **70.0%** of the D2 benign side. D2 is bounded by provenance (see the size section) and was not expanded, so this is as far as it moves without a new *real* benign source. Severity stays low. |
| **P7** | **fixed / harmless** | Shape grouping is consistent across the split; the P2/P7 probe covers it. It only ever worked against the model. |
| **P8** | **probe added (2026-08-05); D1 still FAILs** | The source-separability probe now exists and runs every build. **D1 FAILs**: five malicious-vs-benign pairs are *exactly* 1.0000 separable — QuasarNix carries an IPv4 literal in 100% of its rows vs ≤1.94% of each benign source, and SLP has similar giveaway tokens. This is a **real shortcut**, reported and quarantined (the report refuses to certify D1's scores), not silently passed. **D2 "PASSes" but only just** — benign-vs-benign macro-F1 is 0.899, a hair under the `SEP_FAIL=0.90` line (it was 0.910 in the 2026-08-04 build; the ~0.011 move is D2 resampling noise from cross-dataset dedup, **not** a fix, and **not** attributable to the D1 expansion, which never touched D2). Treat D2's P8 as borderline, not clean. |

### Regenerated numbers — before (2026-08-04 build) → after (2026-08-05)

Baseline model is unchanged (char_wb 3–5 gram TF-IDF + logistic regression, threshold 0.5, seed 42); only the data changed.

| metric | before | after | note |
|---|---|---:|---|
| Dataset 1 rows | 7,628 | **15,248** | +100%; attack side 1,907 → 3,812 |
| Dataset 2 rows | 9,588 | 9,576 | −12 (cross-dataset dedup against new D1 commands; D2 not expanded) |
| D1 F1 (full test, in-distribution) | 0.8904 | 0.8975 | p≈0.25 both, floor 0.400 |
| D2 F1 (full test, in-distribution) | 0.8882 | 0.8824 | within resampling noise |
| **D1 → D2 transfer** F1 (norm) | 0.4788 (0.131) | **0.5844 (0.307)** | **the headline win**: broader, more realistic D1 attacks generalise better to real honeypot attacks |
| D2 → D1 transfer F1 (norm) | 0.3037 (−0.161) | 0.2740 (−0.210) | got *worse*, as expected: D1 is now broader than the narrow honeypot, so a honeypot-trained model recognises even less of it |

### Leave-one-source-out recall (in-train → source removed from train)

The clearest evidence the expansion added *generalizable* tradecraft rather than more memorizable templates: with the other curated corpora present, each source's attacks are far more reachable when the source itself is deleted from training.

| source | before | after |
|---|---|---|
| atomic_red_team | 0.871 → 0.105 | 0.902 → **0.624** |
| gtfobins | 0.826 → 0.164 | 0.905 → **0.402** |
| slp | 0.909 → 0.500 | 0.957 → **0.957** |
| quasarnix | 1.000 → 0.975 | 1.000 → 0.983 |
| hacktricks (new) | — | 0.890 → 0.538 |
| payloads (new) | — | 1.000 → 0.867 (n=15) |

### Benign false-positive audit (added 2026-08-05, removed 2026-08-06)

A scoring-only held-out benign pool (the commands the sampler did not draw) once
shipped alongside each dataset so TPR at a fixed low FPR could be measured below
the test split's 1/n_test resolution. It was not required by the project
instructions and was removed in the handoff cleanup — files, build/evaluation
code, and report sections together. If the final detector needs low-FPR
operating points, the capability can be recovered from this file's history: the
selection rule was "benign rows the sampler did not draw, dropping any that
share an exact command or a `shape()` with a built row".

### Cross-dataset independence — now asserted at build time (2026-08-05)

The proposal's "0 cross-dataset overlap" claim was true but only checked post-hoc (tracked as
Issue D in the since-removed session notes). `build_dataset.py` now **asserts command-level D1/D2 disjointness** before any
file is written, and records the measurement in `stats.json["cross_dataset"]` (the key lands in
`stats.json` on the next full build; the values it will record — 0 / 19 / 6 — were verified
directly on the built CSVs on 2026-08-05). Shape-level overlap
is **recorded, not asserted**: 19 generic shapes appear in both datasets, 6 with opposite labels —
e.g. `chmod +x Q`, malicious in D1's catalogues, benign in D2's user history. We deliberately do
**not** force shape overlap to zero: generic one-liner structures legitimately occur in both an
attack catalogue and real shell history, and deleting them would distort both datasets and
manufacture a provenance artifact where none exists. At 19 shapes against **14,945 + 9,391**
distinct shapes the overlap is negligible — but worth remembering when reading the transfer
numbers: the two datasets are structurally almost, not perfectly, disjoint.

---

## Dataset size and what bounds it

Fixing P1 (removing the keyword-regex label gate) **shrank** both datasets, which
runs against the advisor's guidance to make them bigger. This section is the
honest account of what was done about size and — more importantly — what
*fundamentally* bounds each dataset, so the size is not mistaken for a knob that
can simply be turned up.

### Dataset 1 (curated attack tradecraft) — expanded 2026-08-05

D1's attack side is drawn from published attack-tradecraft catalogues, so it can
grow by adding more catalogues **as long as the selection stays label-independent**
(a corpus is admitted by *what it is* — a reverse-shell cheatsheet, a privesc
wiki — never by whether individual lines look malicious). Added this round:

- **`hacktricks`** — the `linux-hardening/` subtree of the HackTricks book,
  extracted by `extractors/10_extract.py`. **1,795 new shapes at 1.11 rows/shape**
  (genuine privesc/enum/LotL tradecraft, not a generator). Two deliberate
  exclusions, both by *path* so the label stays independent of the text:
  - the whole-book walk was cut to `linux-hardening/` only, dropping the
    off-topic surplus (macOS, `binary-exploitation` gdb scripts, forensics
    `file(1)` output);
  - the `generic-hacking/reverse-shells/` subtree was dropped even though it is
    on-topic, because its dense one-liners trip **Windows Defender**, which
    quarantines the `.cm` mid-build (Defender ate the file, `revshells.cm`, and a
    honeypot pickle during development). The reverse/bind column is already
    carried by `payloads` + `quasarnix` + `slp`. The `.cm` is regenerable at any
    time by re-running the extractor, so a quarantine costs ~1 minute, not data.
- **`payloads`** — bash-fence one-liners from `swisskyrepo/InternalAllTheThings`
  (MIT), selected by file + fence language.
- **`gtfobins`** — re-extracted fuller (still all GTFOBins, all by-design attack).

**Atomic Red Team was deliberately NOT expanded.** `extractors/8_extract.py:80`
reads `executor.command` only. The tempting "+592 new shapes" from also reading
`cleanup_command` / `prereq_command` / `get_prereq_command` are the test
**harness** (setup/teardown), not the attack — a row drawn from them would carry a
provenance label ("this is an attack payload") the field does not support. Adding
them would also have made ART 64.7% of the D1 attack side. Same provenance rule
that killed the P1 keyword gate; same rule that rejected the Sigma/Elastic
detection-rule strings (those are *defender*-authored — a base64 blob Elastic
allowlisted decodes to a benign oVirt health check that merely *looks* malicious).

Result: **D1 7,628 → 15,248** (attack side 1,907 → 3,812). The benign side scales
automatically to hold `BENIGN_PER_ATTACK = 3`, so D1_total = attacks × 4.

### Dataset 2 (real honeypot sessions) — cannot grow from catalogues, and the well is nearly dry

D2's malicious label means "typed inside a real attacker session". A curated
catalogue has no session behind it, so **no catalogue can ever add a D2 malicious
row** — that is the provenance rule, not a limitation of the current corpora. The
only way to grow D2 is more *real capture*, and the honeypot we have is
effectively exhausted:

| distinct exact commands | usable shapes | top-4 shapes | top-10 shapes | shapes seen once |
|---:|---:|---:|---:|---:|
| 407,442 | 2,455 | 93.3% | 98.4% | 2,255 of 2,455 |

407,442 distinct strings collapse to **2,455 shapes**; four templates are 93% of
the traffic. Because 2,255 shapes occur exactly once, `MAX_PER_SHAPE` barely
bites, and raising it buys almost nothing:

| `MAX_PER_SHAPE` | 1 | 2 (current) | 3 | 5 | 10 | ∞ |
|---|---:|---:|---:|---:|---:|---:|
| honeypot rows | 2,455 | 2,655 | 2,785 | 2,958 | 3,314 | 407,442 |

(The ∞ column is why row-count-as-size is a vanity metric: 407k "rows" of 2,455
repeated shapes is not a bigger dataset.) A genuinely disjoint 2025 capture
(**COW160x4**, Zenodo DOI 10.5281/zenodo.21260400 — operator- and era-disjoint
from D2's 2019–2020 window) could add an honest **~800–1,200 new structures**
(the raw ~2,500–3,500 is inflated by Cowrie passwd-prompt prose and one
`useradd … openssl passwd` template `shape()` fails to fold). That would take D2 to
~13,400–14,200. It needs two pre-processing fixes, has no `Set_Fingerprint`
field, and contains a racial slur in attacker-chosen filenames — so it is left as
a **decision for later**, not silently pulled in.

### Are the two datasets even describing the same phenomenon? (why transfer is asymmetric)

Mapping every corpus onto the seven behaviours the proposal §3.1 declares, on the
**as-built** data (multi-label; "real" = the honeypot):

| behaviour (proposal §3.1) | D1 before | D1 after | real (honeypot) |
|---|---:|---:|---:|
| 1 reverse/bind shell | 10.0% | 6.4% | **0.0%** |
| 2 download-and-exec | 3.0% | 3.1% | **17.8%** |
| 3 LotL binary abuse | 1.9% | 1.4% | 0.0% |
| 4 encoded/inline exec | 4.4% | 2.9% | 3.7% |
| 5 host/account enum | 7.2% | 9.4% | 4.7% |
| 6 privesc/persist | 11.3% | 12.1% | 6.2% |
| 7 defense evasion | 2.6% | 2.0% | 1.6% |
| (none of the seven) | 62.8% | 66.1% | 68.1% |

Two misalignments survive the expansion and are **structural**, not fixable by
adding more catalogues:

1. **reverse/bind shells: D1 6.4% vs real 0.0%.** The proposal §2 calls these "the
   primary foothold", but real captured intrusions never *type* an interactive
   reverse shell — they fetch and run a payload instead. D1's 6.4% is mostly
   leftover QuasarNix and `payloads`.
2. **download-and-execute: D1 3.1% vs real 17.8%.** This is the head of the real
   distribution and D1 barely covers it. Catalogues teach technique *syntax*; they
   do not reproduce the `wget … | sh` muscle memory of a botnet. This gap is the
   main reason cross-dataset transfer is weak in both directions and why D2 → D1
   sits below the do-nothing floor.

The expansion moved D1 toward the enum/privesc mass where the two datasets *do*
overlap (that is what lifted D1 → D2 from 0.48 to 0.58 F1), and D1's "none of the
seven" share (66.1%) now closely tracks reality's (68.1%). But it did not — and a
curated corpus cannot — close the download-and-exec gap. That is a note for §6 of
the proposal, not a bug in the build.

---

## P1 — Dataset 2's labels are circular *(critical)*

### The claim that is wrong

> "Dataset 2 is clean. It holds F1 0.985 with addresses stripped and lengths
> matched. That's the strongest evidence that the task is learnable beyond
> shortcuts."

### What is actually happening

Dataset 2's attack commands were **selected** with a keyword filter. In
`build_dataset.py`, `load_honeypot()` walks 233,035 honeypot sessions, splits
them into individual commands, and keeps a command **only if it matches
`RE_MAL_MARKERS`** — that is, only if it contains one of:

```
wget · curl · tftp · ftpget · scp · | sh · | bash · chmod +x · chmod 777
/dev/tcp/ · /dev/udp/ · nc -e · bash -i · authorized_keys · echo ssh-rsa
crontab · chpasswd · history -c · > /var/log · rm -rf /
```

So **100% of Dataset 2's malicious rows contain one of those keywords.** That is
not an observation about attacks; it is the definition of how they got in.

Now we train a classifier and ask it to separate malicious from benign. It can
score almost perfectly by learning nothing more than "does this contain `wget`,
`curl`, `chmod +x`, or `/dev/tcp`?" — because that is literally the rule that
built the labels.

**Analogy.** Suppose you build a dataset of "tall people" by measuring everyone
and keeping those over 180 cm. You then train a model to recognise tall people.
It discovers the rule "height > 180 cm" and scores 100%. You have learned nothing
about tallness. You have recovered your own filter.

### The evidence

I ran `RE_MAL_MARKERS` itself as if it were a classifier:

| dataset | recall | F1 | false positives |
|---|---:|---:|---:|
| **Dataset 2** | **1.0000** | **0.9527** | fired on 381 benign rows |
| Dataset 1 | 0.3634 | 0.5000 | fired on 1,768 benign rows |

The recall of 1.0000 on Dataset 2 is not a result — it is arithmetic. Every
malicious row contains a marker because that is why it is there.

The trained model scores **F1 0.9715**. The regex that created the labels scores
**0.9527**. The model's entire contribution over "re-derive Noam's filter" is
**about 0.02 F1**.

Contrast Dataset 1, where the same regex only manages 0.5000, because D1's labels
come from *which source the command came from*, not from a keyword test. D1 does
not have this problem.

### Why the benign scrub makes it worse

Step 3 of `main()` also deletes benign rows matching `RE_BENIGN_SCRUB` (a
stricter attack-pattern regex). That sharpens the same boundary from the other
side: we remove the benign counter-examples that would have taught the model
*"`curl` is not automatically malicious"*.

### Impact

Dataset 2's headline number is close to meaningless as evidence of detection
ability. It cannot support the sentence "the task is learnable beyond shortcuts",
which is exactly what I used it for.

Note carefully what is **not** wrong: the *commands are real*. Dataset 2 is still
genuine captured attacker activity, correctly labelled. The data is fine. It is
the **evaluation claim** that is broken.

### Fix — this one needs a decision, not just a patch

Three defensible directions:

- **(a) Held-out markers.** Split the marker list in two. Build the training set
  using markers group A (`wget`, `curl`, `chmod +x`, …) and the *test* set using
  only markers group B (`crontab`, `chpasswd`, `history -c`, `authorized_keys`,
  …), with no overlap. Now the test asks a real question: *does a model trained on
  download-and-run attacks recognise persistence and anti-forensics attacks it has
  never seen?* This is the strongest option scientifically and reuses work already
  planned for E3.
- **(b) Declare the regex as the baseline.** Keep the build as-is, but report the
  marker regex as the mandatory baseline row in every table, and state every
  result as "beats the keyword rule by X". Honest, cheap, but concedes that D2
  cannot demonstrate much.
- **(c) Re-label by a non-lexical signal.** Select attacks by something other than
  the command text — e.g. session outcome, downloaded-payload hash, or manual
  review of a sample. Most rigorous, most work, and may not be feasible with the
  fields available in `ssh_attacks.parquet`.

**Recommendation: (a),** with (b)'s baseline row kept permanently as a sanity
check. Option (a) converts the flaw into the project's most interesting
experiment.

### Acceptance criterion

`RE_MAL_MARKERS`-as-classifier must score **near chance on the test split**. If a
keyword rule still gets F1 > 0.8 on the test set, the fix did not work.

---

## P2 — `shape()` is broken, so the anti-leakage split does nothing *(critical)*

### The claim that is wrong

> "QuasarNix is sampled shape-stratified (round-robin over distinct shapes, at
> most two per shape)… split 80/20 grouped by command shape so an identical
> structure can never straddle train and test."

Both halves of that sentence are, in practice, false for QuasarNix.

### What `shape()` is supposed to do

If the model sees a command in training and something nearly identical in
testing, it can "recognise" the test item from memory. That is memorisation, not
detection, and it inflates the score.

The defence: reduce every command to a **shape** by blanking out the parts that
vary, then make sure all commands sharing a shape go to train *or* to test, never
split across both. `shape()` blanks quoted strings (`Q`), numbers (`N`), hex and
base64 blobs, and tokens that look randomly generated (`R`).

### Why it fails

QuasarNix also randomises its **shell variable names**, and `shape()` does not
touch those. Two commands from the identical template:

```
export 3nu1_1="40.58.24.116";export 3nu1_2=60005;python -c '...'
export g4b5_1="13.166.181.83";export g4b5_2=8000;python -c '...'
```

become these shapes:

```
export 3nu1_1=Q;export 3nu1_2=N;python -c Q
export g4b5_1=Q;export g4b5_2=N;python -c Q      <- treated as a DIFFERENT shape
```

The IP became `Q`, the port became `N`, but `3nu1_1` and `g4b5_1` survived. Same
for the loop-variable form:

```
exec N<>/dev/tcp/N.N.N.N/N;cat <&N | while read ih2v; do $ih2v N>&N >&N; done
exec N<>/dev/tcp/N.N.N.N/N;cat <&N | while read 7mfr; do $7mfr N>&N >&N; done
```

The `_randomish()` helper was meant to catch these, but it rejects any token that
is not `isalnum()` after stripping `./_-` from the ends only — so `3nu1_1` fails
on the interior underscore — and it accepts anything containing a vowel, so
`ih2v` slips through too.

### The evidence

```
quasarnix: 17,580 rows -> 17,321 distinct shapes  (1.01 rows per shape)
```

Essentially every command is its own group. Two consequences, both silent:

1. **Shape-stratified sampling never did anything.** `MAX_PER_SHAPE = 2` never
   bound, because almost no shape had two members. The "maximally diverse sample"
   claim is unsupported — it was an ordinary sample.
2. **The group split protects nothing.** Sibling commands from the same template
   were free to land on opposite sides of the 80/20 line.

This is the direct explanation for QuasarNix test recall of **0.9997** (3,489 of
3,490) while the other three attack sources sit near 0.82.

Underneath, QuasarNix has only **20 distinct first tokens**, and two of them cover
89% of it:

```
export 10,474 · exec 5,291 · echo 1,549 · nc 108 · rcat 36 · ... (20 total)
```

So Dataset 1's headline number is largely "can you recognise an `export`/`exec`
reverse-shell one-liner", scored against near-copies of things it trained on.

### Fix

1. In `shape()`, normalise shell variable names before blanking anything else:
   - assignment targets: `\b[A-Za-z_][A-Za-z0-9_]*=` → `V=`
   - expansions: `\$[A-Za-z_][A-Za-z0-9_]*` and `\$\{...\}` → `$V`
   - `while read <name>` / `for <name> in` binders → `V`
2. Fix `_randomish()` to strip `_` and digits anywhere in the token, not just at
   the ends, before its vowel test.
3. Rebuild, then re-measure rows-per-shape for QuasarNix. It should be **well
   above 1.0** — the two examples above must collapse to one shape.
4. Re-run `evaluate_baseline.py` and expect QuasarNix recall to **fall**. That
   drop is the point: the previous number was inflated.

### Acceptance criterion

`shape()` maps the two `export …` examples above to the identical string, and
QuasarNix's rows-per-shape is > 1.5. Report the new QuasarNix recall next to the
old 0.9997 so the size of the correction is visible.

---

## P3 — the length ablation compares scores on different rulers *(high)*

### The claim that is wrong

> "Ablation: length-matched test → F1 0.9894 (Dataset 1), 0.9811 (Dataset 2). The
> score survives, so it isn't driven by length."

### What length matching is for

Dataset 1's attacks are long (median 221 characters) and its benign commands are
short (median 30). A model could separate the classes on length alone — measured,
that gets **F1 0.858**, which is a lot for a single number that knows nothing
about shells.

To test whether the model is leaning on that, build a test set where length
*cannot* help: pair every malicious command with a benign command of nearly the
same length. If the score holds on that subset, length was not the crutch.

### Why it fails

`length_match()` in `evaluate_baseline.py` keeps **every** malicious row, and adds
a benign partner **only when it can find one** of similar length within a ±40-row
window of the sorted benign lengths. Dataset 1's benign pool has very few long
commands, so most long attacks found no partner — but stayed in the test set
anyway.

| test set | rows | malicious | benign | % malicious | do-nothing F1 | reported F1 |
|---|---:|---:|---:|---:|---:|---:|
| D1 full test | 15,668 | 3,917 | 11,751 | 25.0% | 0.400 | 0.9855 |
| D1 "length-matched" | 4,713 | 3,917 | **796** | **83.1%** | **0.908** | 0.9894 |
| D2 full test | 3,069 | 767 | 2,302 | 25.0% | 0.400 | 0.9715 |
| D2 "length-matched" | 1,495 | 767 | 728 | 51.3% | 0.678 | 0.9811 |

**3,121 of Dataset 1's 3,917 malicious rows have no partner.** The subset is 83%
malicious. Against a do-nothing floor of 0.908, an F1 of 0.9894 is unremarkable —
whereas 0.9855 against a floor of 0.400 on the full set is genuinely strong.

I reported the ablation number as higher and called it "survived". It is measured
on an easier scale. And the lengths did not even end up matched: medians stayed
**222 vs 75**.

So: **Dataset 1's length shortcut remains untested.** We do not know whether the
score depends on it.

Dataset 2 comes out better. Its matched subset is 51.3% malicious and its lengths
genuinely matched (39 vs 38), so length really is not doing the work there. But
the floor still moved from 0.400 to 0.678, so `0.9715 → 0.9811` is not the
like-for-like "it went up slightly" that the table implies.

### Fix

1. In `length_match()`, **drop malicious rows that find no partner**, so the
   result is exactly 1:1, then optionally down-weight or resample to restore the
   original 25% prevalence.
2. Print the do-nothing floor (`2p/(1+p)`) beside every score in `BASELINE.md`,
   and report **F1 above floor** as well as raw F1.
3. If Dataset 1 simply lacks long benign commands to match against — likely — say
   so explicitly and report the matched subset's coverage ("only 796 of 3,917
   attacks could be length-matched") instead of presenting a full-coverage number.
4. Regenerate `BASELINE.md`, fix proposal §6.1, rebuild the PDF, and correct
   `email_to_advisor.txt`.

### Acceptance criterion

Every row of the scores table in `BASELINE.md` reports its prevalence and its
do-nothing floor, and no two rows with different prevalence are compared in prose
without mentioning it.

---

## P4 — false precision in the per-source numbers *(medium)*

### The claim that is wrong

> "recall 0.9997 on QuasarNix but 0.821 on GTFOBins, 0.819 on Atomic Red Team and
> 0.815 on SLP."

The QuasarNix-versus-the-rest gap is real. The ordering *among the other three* is
not — those three numbers are indistinguishable from each other.

| source | correct | recall | 95% confidence interval |
|---|---:|---:|---|
| slp | 22 / 27 | 0.815 | **[0.668, 0.961]** |
| atomic_red_team | 136 / 166 | 0.819 | [0.761, 0.878] |
| gtfobins | 192 / 234 | 0.821 | [0.771, 0.870] |
| quasarnix | 3489 / 3490 | 1.000 | [0.999, 1.000] |

With 27 test samples, SLP's true recall is somewhere between about 67% and 96%.
Writing "0.815" implies a precision of ±0.001 that 27 samples cannot support. The
three intervals overlap almost entirely, so "GTFOBins is better than SLP" is not a
finding — it is noise.

### Fix

Report `k/n` and a 95% interval (Wilson, not normal-approximation, at these
sample sizes) for every per-source row. Do not make comparative claims between
sources with overlapping intervals. Do not draw any conclusion from SLP alone at
n = 27; either pool it with the other curated sources or report it as indicative
only.

---

## P5 — Dataset 1's malicious class is 90% one generator *(medium, design)*

19,585 attacks: QuasarNix 17,580 (**89.8%**), GTFOBins 1,071, Atomic Red Team 812,
SLP 122. Combined with P2, the aggregate Dataset 1 score is close to a QuasarNix
score wearing a disguise.

This is not a bug — it reflects what is publicly available, and QuasarNix is the
only source with real scale. But it means:

- the aggregate F1 for Dataset 1 should **never** be quoted without the per-source
  breakdown beside it;
- weighting the loss, or capping QuasarNix lower, is worth an experiment;
- after P2 is fixed, re-check this ratio — QuasarNix's contribution may shrink
  once its variants collapse properly into shapes.

---

## P6 — Dataset 2's benign class is 88% one source *(low)*

11,511 benign rows: `bash_history` 10,134 (88.0%), `commandlinefu` 1,377 (12.0%).
The proportional sampler allocates by pool size, and `bash_history` has 51,462
available against commandlinefu's 7,111.

Not wrong, but the "real user commands" side is effectively one person's shell
history. Consider capping any single source's share (e.g. at 70%) so
`commandlinefu`'s different style is better represented.

---

## P7 — shape groups are built per label *(low, harmless)*

`group_split()` groups by shape **within each label separately**, so a shape that
appears on both labels can be train-side for one label and test-side for the
other. This affects 7 shapes in Dataset 1 and 1 in Dataset 2.

This makes the task *harder*, not easier — the model sees the structure labelled
benign in training and must call it malicious at test. Already documented in the
data card. Listed here only so nobody "discovers" it later and assumes the worst.

---

## P8 — untested: are the sources themselves trivially separable? *(unknown)*

The whole provenance-matching design rests on an assumption nobody has yet
measured: that within a dataset, the attack side and the benign side are not
distinguishable by collection style.

That assumption is shaky for Dataset 2. Its benign side is a Linux hobbyist's
history (`git`, `sudo nano`, `apt`) and its malicious side is botnet traffic
(`busybox`, `tftp`, `chmod +x`). A model could separate those on vocabulary alone
while learning nothing transferable about malice.

**The test to run:** ignore the real labels and train a classifier to predict the
**source** of each command among the benign sources only. If sources are trivially
separable (say F1 > 0.9), then "which pile did this come from" is an easy learnable
signal, and the provenance-matching defence is weaker than claimed. Run the same
probe malicious-source-vs-benign-source within each dataset.

Until this is measured, treat the provenance-matching argument as a design intent,
not a verified property.

---

## What is *not* broken

Listed so nobody re-litigates settled ground:

- **Integrity.** 0 cross-dataset command overlap, 0 train/test string overlap,
  exact 80/20 splits, unique ids. Verified on the built files.
- **The address ablation is valid.** It runs on the *same* test set with the
  *same* prevalence, so `0.9855 → 0.9865` (D1) and `0.9715 → 0.9728` (D2) is a
  fair comparison. Conclusion holds: the model is not relying on addresses.
- **The address normalisation fix is real.** Mapping every IPv4 to the constant
  `1.1.1.1` genuinely was a fatal confound (100.0% of malicious vs ~1% of benign);
  hash-derived addresses genuinely fix that specific token. The residual
  correlation — an "any IPv4" rule still scores F1 0.938 on D1 — is a *shortcut*
  (P-class), not a bug in the fix.
- **The dataset sizes are real.** 78,340 and 15,348 rows, deduplicated, from
  licence-checked public sources. Growth is not inflated by duplicates.
- **Rejecting session-level honeypot labelling was correct.** It reaches ~27k rows
  but the additions are `/bin/busybox <RANDOM>` and leaked passwords. Do not
  reverse this to make Dataset 2 bigger.
- **The poor cross-dataset transfer (D1→D2 F1 0.365, D2→D1 F1 0.007) is a
  result, not a defect** — though note it must be re-measured after P1 and P2,
  since both inflate the source side.

---

## Suggested order of work

1. **P2** (`shape()`) — mechanical, self-contained, and everything downstream
   changes once it lands. Do this first so later numbers are measured on a sound
   split.
2. **P3** (`length_match()` + floors in `BASELINE.md`) — mechanical, and it
   unblocks the proposal and the advisor email.
3. **P4** (confidence intervals) — small, do it while touching the reporting code.
4. **P8** (source-separability probe) — cheap to run, and its answer may change
   how P1 should be handled.
5. **P1** (Dataset 2 circularity) — needs the option (a)/(b)/(c) decision first;
   biggest change to what the project claims.
6. **P5 / P6** — revisit after P2 lands, since the ratios may shift.

After 1–3, regenerate `BASELINE.md` and `DATA_CARD.md`, correct proposal §6.1,
rebuild the PDF, and rewrite the advisor email with the corrected figures.

## How to reproduce the evidence

```
cd final_project/dataset
python build_dataset.py        # rebuild both datasets (uses cached downloads)
python evaluate_baseline.py    # regenerates BASELINE.md
```

The specific audit scripts behind P1–P4 were run ad hoc; the checks worth keeping
permanently are the do-nothing floor (P3), the selection-regex-as-classifier probe
(P1), the rows-per-shape statistic (P2), and per-source confidence intervals (P4).
All four belong in `evaluate_baseline.py` so they cannot silently regress.
