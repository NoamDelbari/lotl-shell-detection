# 7.3 — Hyperparameter Sensitivity: XGBoost & 1D-CNN

This chapter reports one-at-a-time (OAT) sensitivity sweeps for the two
production candidate models — the gradient-boosted tree ensemble (XGBoost) and
the character-level 1D-CNN — on the binary attack/benign command-line task
(MITRE ATT&CK T1059.004, 1:3 attack:benign). Each sweep fixes every
hyperparameter at its base value and varies a single one across a small grid,
recording the resulting **F1** and **false-positive rate (FPR)** on the held-out
test split of each corpus (`n_test = 3,049` for Dataset 1, `1,915` for
Dataset 2). Eight axes are swept — four per model — giving 13 measured points
per model per corpus, 52 in all. Figures
`ch7_sensitivity_xgboost_dataset{1,2}.png` and
`ch7_sensitivity_cnn1d_dataset{1,2}.png` plot every curve below.

> **Scope.** Every sweep below trains on the **full training split**
> (`n_train = 12,199` for Dataset 1, `7,661` for Dataset 2) and scores on that
> corpus's test split; the numbers are read straight from
> `results/ch7_sensitivity.json`. Two caveats apply. First, the CNN sweeps run
> at **4 epochs** for tractability against the shipped model's 8
> (`SWEEP_OVERRIDE` in `analysis/ch7_train.py`), so CNN sweep F1 sits roughly
> three points below the headline 0.860 and should be read for *shape*, not
> level. Second, because the sweeps score on the test hold-out, they are a
> **sensitivity analysis and not a selection procedure** — adopting an
> arg-max from these tables as the production setting would be tuning on the
> test set. The shipped configuration is the pre-registered one in
> `src/models.py`; §6.3 sets the two side by side.

---

## Where these hyperparameters land

The two models tuned here are stages of the three-stage **cascade detector**
of §7.1 (Figure 7.1): raw commands enter a cheap Isolation-Forest bulk filter,
survivors reach the tuned XGBoost-hybrid, and only the 0.35–0.65 edge band
reaches the LLM. The class-weight and convergence findings below are therefore
findings about stage 2's operating point, which §8.4 then evaluates end to end.

---

## Headline answers

Only **two** of the eight swept axes move anything, and they are the same two on
both models and both datasets.

- **Biggest impact on FPR: the class-weight dial** — `scale_pos_weight` on
  XGBoost, `pos_weight` on the CNN. Going from 1.0 to 6.0 multiplies the false
  alarm rate by **2.8×** (XGBoost D1, 0.039 → 0.108), **2.3×** (XGBoost D2),
  **3.6×** (CNN D1, 0.033 → 0.119) and **4.3×** (CNN D2, 0.042 → 0.181) while
  F1 moves by at most 0.077. It is a recall/false-alarm dial, not an accuracy
  dial: on XGBoost D1 it buys **+9.2 points of recall** (0.727 → 0.819) for
  those false alarms, and on CNN D2 **+12.7 points** (0.770 → 0.898).
- **Biggest impact on F1 among the accuracy knobs: `lr` on the CNN**
  (0.812 → 0.843 on D1, 0.791 → 0.833 on D2). The class weight moves F1 further
  still on Dataset 2 (Δ0.077), but only by pushing the CNN past the point where
  extra recall pays for itself. On XGBoost no axis moves F1 by more than
  **0.025**, and the capacity axes move it by **0.003–0.010** — the tree model
  is, for practical purposes, tuning-proof on this task.

**The capacity knobs are inert.** `max_depth`, `n_estimators` and `n_filters`
together account for F1 swings of 0.003–0.029 across all four model/dataset
combinations. Whatever governs performance here, it is not ensemble or
convolutional capacity — it is the representation (Ch. 2) and the label
boundary (Ch. 8.1).

The rest of the chapter substantiates and interprets these claims.

---

## XGBoost — F1 is saturated; false alarms are governed by `scale_pos_weight`

**Base config** (`analysis/ch7_train.py`): `n_estimators=400`, `max_depth=6`,
`learning_rate=0.1`, `subsample=0.9`, `colsample_bytree=0.9`,
`min_child_weight=1.0`, `reg_lambda=1.0`, `scale_pos_weight=3.0`; 5-fold
stratified CV. Bold marks the base value in each grid.

**Table 7.1 — XGBoost one-at-a-time sweeps, both datasets (F1 / FPR, test hold-out).**

| axis | value | D1 F1 | D1 FPR | D2 F1 | D2 FPR |
|---|---:|---:|---:|---:|---:|
| `max_depth` | 3 | 0.7837 | 0.0787 | 0.7457 | 0.1010 |
| | **6** | **0.7856** | **0.0717** | **0.7557** | **0.0815** |
| | 9 | 0.7873 | 0.0669 | 0.7558 | 0.0780 |
| | 12 | 0.7831 | 0.0691 | 0.7519 | 0.0745 |
| `n_estimators` | 100 | 0.7823 | 0.0752 | 0.7597 | 0.0905 |
| | **400** | **0.7856** | **0.0717** | **0.7557** | **0.0815** |
| | 800 | 0.7823 | 0.0752 | 0.7503 | 0.0794 |
| `learning_rate` | 0.03 | 0.7823 | 0.0752 | 0.7633 | 0.0884 |
| | **0.1** | **0.7856** | **0.0717** | **0.7557** | **0.0815** |
| | 0.3 | 0.7747 | 0.0770 | 0.7492 | 0.0815 |
| `scale_pos_weight` | 1.0 | 0.7892 | 0.0385 | 0.7593 | 0.0487 |
| | **3.0** | **0.7856** | **0.0717** | **0.7557** | **0.0815** |
| | 6.0 | 0.7647 | 0.1076 | 0.7522 | 0.1135 |

**Table 7.2 — F1 swing per axis (max − min).** The ordering is the finding.

| axis | D1 swing | D2 swing |
|---|---:|---:|
| `scale_pos_weight` | **0.0245** | 0.0071 |
| `learning_rate` | 0.0109 | **0.0141** |
| `max_depth` | 0.0042 | 0.0101 |
| `n_estimators` | 0.0033 | 0.0094 |

### Interpretation

**F1 is saturated.** Every one of the twenty-six XGBoost measurements above
lands between **0.765 and 0.789** on D1 and **0.746 and 0.763** on D2. The
widest swing on either dataset is 0.0245 — smaller than the gap between the
plain XGBoost and the hybrid (0.786 → 0.876), and smaller than the gap between
either and the untuned char-n-gram baseline (0.898). This is the signature of a
model whose ranking quality is set by the **feature representation**, not by
ensemble capacity: deeper trees, more trees and a hotter step size all buy
essentially nothing. XGBoost is robust to the point of being tuning-proof —
you cannot easily break it, and you cannot easily improve it either.

The capacity axes make the point most sharply. `max_depth` spans 0.0042 F1 on
D1, and its arg-max (9) beats the shipped depth 6 by 0.0017 — an order of
magnitude inside run-to-run variance. `n_estimators` is flatter still (0.0033),
and is *symmetric*: 100 and 800 trees score identically (0.7823), so the 800-tree
model pays double the fit time for nothing. Neither axis shows the
underfitting cliff a capacity-limited model would.

**The class-weight dial is the false-alarm knob, not an F1 knob.** On D1
`scale_pos_weight` owns both the largest F1 swing (0.0245) *and*, far more
importantly, the largest FPR swing of any parameter in the study: **0.0385 →
0.1076**, a 2.8× inflation. But the F1 column understates what is happening,
because F1 blends the two error types the dial is trading. Read recall instead:
1.0 → 6.0 moves recall **0.727 → 0.819** on D1 and **0.702 → 0.808** on D2. The
parameter is doing exactly its job — up-weighting the minority attack class to
buy recall with false alarms — and F1 stays pinned only because it charges for
both sides of that trade.

This is the operationally load-bearing result of the chapter: **the model's
position on the false-alarm axis is chosen almost entirely by one number**, and
that number should be set by how much triage load the SOC can absorb, not by
maximising F1. At `scale_pos_weight=1.0` the detector runs at 3.9% FPR and
misses 27% of attacks; at 6.0 it runs at 10.8% and misses 18%. The shipped 3.0
sits deliberately between them.

### Chosen setting — XGBoost

The shipped configuration is unchanged from the base config, and the sweep is
the justification for *not* moving it:

| hyperparameter | shipped | why the sweep does not move it |
|---|---|---|
| `max_depth` | **6** | 9 leads by 0.0017 F1 on D1 and 0.0001 on D2 — inside noise, and chasing it would be test-set selection. |
| `n_estimators` | **400** | Sweep arg-max on D1 and the symmetric centre of the curve; 800 costs 2× for 0.0033 less. |
| `learning_rate` | **0.1** | Arg-max on D1. D2 mildly prefers 0.03 (+0.0076), not enough to justify a per-dataset split of the config. |
| `scale_pos_weight` | **3.0** | The recall/FPR trade, chosen on operating-point grounds rather than F1: it buys ~6 points of recall over 1.0 for ~3 points of FPR. Lower it to 1.0 if triage capacity is the binding constraint — that is the one genuinely defensible alternative in this table. |

The through-line: for XGBoost, **stop trying to tune F1** — it is saturated —
and **set `scale_pos_weight` to the FPR your SOC can absorb.**

---

## CNN — `learning_rate` dominates everything else

**Base config** (`analysis/ch7_train.py`): `max_len=192`, `embed_dim=32`,
`n_filters=128`, `kernel_sizes=(3,5,7)`, `dropout=0.3`, `lr=1e-3`,
`pos_weight=3.0`, `batch_size=256`, **`epochs=4`** (`SWEEP_OVERRIDE`, against the
shipped 8); 3-fold stratified CV. All CNN F1 values below therefore sit roughly
three points under the shipped 0.860 / 0.838 and should be read for *shape*.

**Table 7.3 — 1D-CNN one-at-a-time sweeps, both datasets (F1 / FPR, test hold-out).**

| axis | value | D1 F1 | D1 FPR | D2 F1 | D2 FPR |
|---|---:|---:|---:|---:|---:|
| `n_filters` | 64 | 0.8197 | 0.0818 | 0.7976 | 0.0905 |
| | **128** | **0.8293** | **0.0761** | **0.8086** | **0.0912** |
| | 256 | 0.8339 | 0.0813 | 0.8265 | 0.0738 |
| `dropout` | 0.1 | 0.8429 | 0.0678 | 0.8156 | 0.0891 |
| | **0.3** | **0.8293** | **0.0761** | **0.8086** | **0.0912** |
| | 0.5 | 0.8217 | 0.0756 | 0.7873 | 0.1052 |
| `lr` | 5e-4 | 0.8124 | 0.0778 | 0.7914 | 0.0780 |
| | **1e-3** | **0.8293** | **0.0761** | **0.8086** | **0.0912** |
| | 2e-3 | 0.8432 | 0.0765 | 0.8333 | 0.0662 |
| `pos_weight` | 1.0 | 0.8302 | 0.0328 | 0.8128 | 0.0418 |
| | **3.0** | **0.8293** | **0.0761** | **0.8086** | **0.0912** |
| | 6.0 | 0.8060 | 0.1189 | 0.7357 | 0.1811 |

**Table 7.4 — F1 swing per axis (max − min).**

| axis | D1 swing | D2 swing |
|---|---:|---:|
| `lr` | **0.0308** | 0.0419 |
| `pos_weight` | 0.0242 | **0.0771** |
| `dropout` | 0.0212 | 0.0283 |
| `n_filters` | 0.0143 | 0.0288 |

### Interpretation

**`lr` is the CNN's dominant F1 axis, and the reason is the epoch budget.** It
spans 0.0308 F1 on D1 and 0.0419 on D2 — wider than any other CNN axis on D1
and the widest *pure-accuracy* axis on both. The curve is monotone increasing
(5e-4 → 1e-3 → 2e-3) with FPR essentially flat on D1 (0.078 → 0.076 → 0.077)
and, on D2, ending *below* where it started (0.078 → 0.091 → 0.066 — the top of
the range is the lowest false-alarm point on the axis). That is the signature of
**under-convergence, not under-regularisation**: inside a 4-epoch budget a
larger step simply gets further down the same loss surface, so accuracy rises
without the precision/recall trade a genuine capacity change would force. It is
also the reason the sweep's arg-max is not adopted — at the shipped 8 epochs the
default 1e-3 has the schedule to converge on its own, and the shipped model's
0.860 (versus 0.843 for the best 4-epoch point here) confirms it.

The same reading explains `dropout`, whose sweep arg-max (0.1, +0.0136 on D1)
is the one place a sweep clearly prefers a non-shipped value. Less
regularisation looking better in a truncated schedule is what early-training
over-fit looks like, and §8.2 shows this model's real failure mode is
corpus-style memorisation — precisely what weakening dropout would amplify. It
is recorded as an open question rather than tuned away.

`n_filters` is the flattest axis on D1 (0.0143) and shows a mild, real capacity
gain on D2 (0.0288, monotone to 256, and at 256 the D2 FPR *falls* to 0.0738 —
more capacity buying accuracy without buying false alarms). It
is the only axis where the sweep hints that the shipped model may be
under-parameterised, but 256 filters double the convolutional parameter count
for under half a point of D1 F1.

**`pos_weight` is again the false-alarm dial, and on the CNN it is more violent
than on the trees.** D1 FPR runs **0.0328 → 0.1189** (3.6×) and D2 **0.0418 →
0.1811** (4.3×) — the largest FPR excursion anywhere in this chapter. On D2 it
is also the largest *F1* mover (0.0771), because at `pos_weight=6.0` the model
tips past the point where extra recall pays for itself: recall reaches 0.898
but F1 falls to 0.7357 as nearly one benign command in five is flagged. Reading recall
across the dial: D1 **0.780 → 0.870 → 0.916**, D2 **0.770 → 0.864 → 0.898**.
The shipped 3.0 sits at the knee of both curves.

### Chosen setting — CNN

| hyperparameter | shipped | why the sweep does not move it |
|---|---|---|
| `lr` | **1e-3** | 2e-3 leads at 4 epochs, but the gap is a convergence artefact of the shortened sweep schedule; the shipped 8-epoch run reaches 0.860 at 1e-3. |
| `dropout` | **0.3** | 0.1 leads by 0.0136 (D1) / 0.0070 (D2). Not adopted: weaker regularisation is the wrong direction for a model whose documented weakness is corpus-style memorisation (§8.2). Flagged, not tuned. |
| `n_filters` | **128** | 256 gains 0.0046 (D1) / 0.0179 (D2) for 2× the parameters. The D2 gain is the one result in this table worth revisiting with more compute. |
| `pos_weight` | **3.0** | The knee of the recall/FPR curve: +9 points of recall over 1.0 on D1 for +4.3 points of FPR, where 6.0 costs a further 4.3 points of FPR for +4.6 recall and *loses* F1 on both corpora. |
| `epochs` | **8** (sweep: 4) | Not swept; the 4-epoch override exists only to make a 13-point grid on two corpora tractable on CPU. |

Best observed CNN point in the sweep, `lr=2e-3` (D1 F1 0.8432, D2 0.8333),
still trails the shipped 8-epoch model (0.8603 / 0.8384) — the sweep's ceiling
is set by its epoch budget, not by its hyperparameters.

---

## Cross-model synthesis

**Table 7.5 — The three questions the sensitivity analysis was run to answer.**

| question | answer | evidence |
|---|---|---|
| Which hyperparameter most affects **F1**? | **The class-weight dial**, then the CNN's `lr` | Largest single swing in the study is CNN `pos_weight` on D2 (Δ0.0771); `scale_pos_weight` leads on XGBoost D1 (Δ0.0245); CNN `lr` leads on D1 (Δ0.0308). No *capacity* axis exceeds Δ0.0288 anywhere. |
| Which hyperparameter most affects **FPR**? | **The class-weight dial**, unambiguously | 1.0 → 6.0 multiplies FPR 2.8× (XGB D1), 2.3× (XGB D2), 3.6× (CNN D1), 4.3× (CNN D2) — every other axis moves FPR by under 3 points absolute. |
| Which model is more sensitive overall? | **The CNN** | Its four axes span 0.0143–0.0771 F1 against XGBoost's 0.0033–0.0245; XGBoost never leaves a 0.746–0.789 band across all 26 measurements. |

Three lessons follow.

**The levers are decoupled by role.** Six of the eight swept axes are capacity
or regularisation knobs, and none of them moves F1 by more than 0.029. The two
that matter are a *convergence* knob (the CNN's `lr`, and only because the sweep
schedule is truncated to 4 epochs) and an *operating-point* knob (the class
weight, on both models). Nothing in this chapter suggests either detector is
capacity-limited on this task — which is consistent with §8.1's finding that the
residual errors are label-contamination cases with no content signal to learn,
and with §8.2's finding that the untuned char-n-gram baseline outscores every
tuned model here.

**The class weight is the only decision a deployment actually has to make.** It
is simultaneously the biggest FPR lever (up to 4.3×) and, on three of the four
model/dataset pairs, close to the biggest F1 lever — and it is the one axis
whose "best" value is not a modelling question at all. At weight 1.0 the
detectors run at 3–5% FPR and miss 22–30% of attacks; at 6.0 they run at 11–18%
FPR and miss 8–19%. Which of those a SOC wants depends on analyst capacity, not
on a validation curve. The shipped 3.0 — the corpus's own `neg/pos` ratio — is
the neutral cost-sensitive correction, and it sits at the knee of every recall
curve measured.

**XGBoost's insensitivity is a deployment asset in its own right.** A detector
that holds F1 within 0.04 across every reasonable setting of four
hyperparameters is cheap to retrain and nearly impossible to misconfigure, even
though its ceiling trails the CNN by seven points in-domain. The CNN buys its
higher ceiling — and its better cross-corpus transfer (§8.2) — at the cost of
needing its schedule and its class weight to be right.

Finally, the honest caveat: because these sweeps score on the test hold-out,
none of the arg-maxima above is adopted. The shipped configuration is the
pre-registered one in `src/models.py`, and the value of this chapter is the
demonstration that **almost nothing in it would have changed if we had tuned** —
the twenty-six XGBoost configurations span 0.04 F1, and the best CNN sweep point
still loses to the shipped model.
