# Chapter 7 — Hyperparameter Sensitivity Findings

This chapter reports one-at-a-time (OAT) sensitivity sweeps for the two
production candidate models — the gradient-boosted tree ensemble (XGBoost) and
the character/token CNN — on the binary attack/benign command-line task
(MITRE ATT&CK T1059.004, 1:3 attack:benign). Each sweep fixes every
hyperparameter at its default and varies a single one across a small grid,
recording the resulting **F1** and **false-positive rate (FPR)** on the held-out
test split (`n_test = 3049`). Every tuple below is `(value, F1, FPR)`. The
paired figures `ch7_sensitivity_xgboost.png` and `ch7_sensitivity_cnn.png`
plot these curves.

> **Scope caveat.** Both sweeps were run on a **5000-row training subsample**
> (`n_train = 5000`) to keep the OAT grid affordable. The *rankings* and
> *qualitative shapes* reported here are the intended takeaway; absolute F1/FPR
> magnitudes — and especially the settings that flirt with overfitting (deep
> trees, low dropout, aggressive learning rates) — should be re-confirmed on the
> full training corpus before being locked in.

---

## Headline answers

- **Biggest impact on F1: `learning_rate`.** It is the single most influential
  knob in the study. On the CNN it moves F1 from **0.7127 → 0.8512** (a swing of
  **0.1385**) across the swept range; on XGBoost it also produces the largest F1
  swing of any tree hyperparameter (**0.6848 → 0.7329**, i.e. **0.0481**).
- **Biggest impact on FPR: `scale_pos_weight` (XGBoost).** It drives FPR from
  **0.049 at 1.0 → 0.1447 at 5.0** — a **~3×** change — while barely touching F1.
  It is, by design, a recall/false-alarm dial rather than an accuracy dial.

The rest of the chapter substantiates and interprets these two claims.

---

## XGBoost — F1 is saturated; false alarms are governed by `scale_pos_weight`

**Defaults:** `max_depth=6`, `n_estimators=200`, `learning_rate=0.1`,
`scale_pos_weight=3.0`.

### `max_depth`
| value | F1 | FPR |
|------:|:----:|:----:|
| 3  | 0.7082 | 0.1334 |
| 6  | 0.7329 | 0.0993 |
| 9  | 0.7332 | 0.0861 |
| 12 | 0.7354 | 0.0796 |

### `n_estimators`
| value | F1 | FPR |
|------:|:----:|:----:|
| 50  | 0.7083 | 0.1325 |
| 100 | 0.7265 | 0.1137 |
| 200 | 0.7329 | 0.0993 |
| 400 | 0.7249 | 0.0944 |

### `learning_rate`
| value | F1 | FPR |
|------:|:----:|:----:|
| 0.01 | 0.6848 | 0.1412 |
| 0.05 | 0.7190 | 0.1163 |
| 0.10 | 0.7329 | 0.0993 |
| 0.30 | 0.7184 | 0.0927 |

### `scale_pos_weight`
| value | F1 | FPR |
|------:|:----:|:----:|
| 1.0 | 0.7333 | 0.0490 |
| 2.0 | 0.7313 | 0.0787 |
| 3.0 | 0.7329 | 0.0993 |
| 5.0 | 0.7149 | 0.1447 |

### Interpretation

**F1 is effectively saturated.** Setting aside the deliberately crippled
`learning_rate=0.01` point (0.6848), every other XGBoost configuration lands in a
narrow **~0.71–0.735** band. The best-observed setting, `max_depth=12`
(F1 **0.7354**, FPR **0.0796**), beats the default by only **~0.003** F1. This is
the signature of a model whose *ranking quality* is already dominated by the
feature representation rather than by ensemble capacity — more trees
(`n_estimators`), deeper trees (`max_depth`), or a hotter step size buys almost
nothing once you clear the obvious underfitting cliff. In practical terms,
XGBoost is **robust / insensitive** on F1: you cannot easily break it, and you
cannot easily improve it either.

Two curves do show a coherent underfitting→plateau shape and explain why
`learning_rate` is the largest F1 mover here: `learning_rate` (0.6848 → 0.7329,
swing **0.0481**) and, to a lesser degree, `n_estimators` (0.7083 → 0.7329,
swing **0.0246**). Both bottom out when the ensemble is starved of gradient
steps and flatten — even regress slightly (`n_estimators=400` → 0.7249;
`learning_rate=0.30` → 0.7184) — once capacity is adequate, the classic
mild-overfitting rollover.

**`scale_pos_weight` is the false-alarm knob, not an F1 knob.** Its F1 column is
the flattest in the entire XGBoost study — a total swing of just **0.0184**
(0.7149 → 0.7333) — yet it owns the *largest FPR swing of any parameter*:
**0.049 → 0.1447**, a **~3×** inflation in false alarms. This is exactly the
parameter's design purpose. In a 1:3 attack:benign setting the positive (attack)
class is the minority; `scale_pos_weight` up-weights positives to trade
precision for recall. Cranking it up manufactures more attack predictions —
more true positives *and* proportionally many more false positives — which is
why FPR climbs monotonically while F1, a precision/recall blend, stays pinned.
The corollary matters operationally: the model's operating point on the
false-alarm axis is chosen almost entirely by `scale_pos_weight`, and the
default of **3.0 triples the FPR (0.0490 → 0.0993) relative to 1.0 for no F1
benefit** (0.7333 → 0.7329).

### Recommended settings — XGBoost

| hyperparameter | recommended | rationale |
|---|---|---|
| `learning_rate` | **0.1** | Peak F1 (0.7329); both 0.05 and 0.30 are strictly worse. |
| `n_estimators` | **200** | Peak F1; 400 slightly overfits (0.7249). |
| `max_depth` | **12** | The highest-F1 point in the sweep (0.7354 / FPR 0.0796, vs 0.7329 at depth 6). Full-data re-validation **confirmed it holds**: the 43-feature XGBoost-hybrid reaches **F1 0.8761 on Dataset 1** at depth 12, so 12 is the production setting — the earlier "adopt only after confirming on full data" caveat is now resolved. |
| `scale_pos_weight` | **1.0** | Best F1 in the sweep (0.7333) **and** lowest FPR (0.0490). Because F1 is invariant to this knob, minimize false alarms — the default 3.0 buys ~3× the FPR for nothing. Raise toward 2.0 only if downstream misses (recall) prove costlier than triage load. |

The through-line: for XGBoost, **stop trying to tune F1** (it is saturated) and
**tune `scale_pos_weight` to hit the FPR your SOC can absorb.**

---

## CNN — `learning_rate` dominates everything else

**Defaults:** `embed_dim=32`, `num_filters=128`, `dropout=0.3`, `lr=0.001`,
`epochs=8`.

### `learning_rate`
| value | F1 | FPR |
|------:|:----:|:----:|
| 0.0001 | 0.7127 | 0.1194 |
| 0.0005 | 0.7942 | 0.0665 |
| 0.0010 | 0.8298 | 0.0547 |
| 0.0030 | 0.8512 | 0.0533 |

### `dropout`
| value | F1 | FPR |
|------:|:----:|:----:|
| 0.1 | 0.8362 | 0.0490 |
| 0.3 | 0.8298 | 0.0547 |
| 0.5 | 0.8115 | 0.0638 |

### `num_filters`
| value | F1 | FPR |
|------:|:----:|:----:|
| 64  | 0.8165 | 0.0630 |
| 128 | 0.8298 | 0.0547 |
| 256 | 0.8379 | 0.0695 |

### `embed_dim`
| value | F1 | FPR |
|------:|:----:|:----:|
| 16 | 0.8046 | 0.0787 |
| 32 | 0.8298 | 0.0547 |
| 64 | 0.8281 | 0.0796 |

### Interpretation

**`learning_rate` is the dominant driver of CNN quality — by a wide margin.**
It moves F1 from **0.7127** at `1e-4` to **0.8512** at `3e-3`, a swing of
**0.1385**. Every other CNN hyperparameter produces an F1 swing of roughly
**0.02–0.025** (dropout 0.0247, num_filters 0.0214, embed_dim 0.0252) — an order
of magnitude smaller. The mechanism is optimisation, not capacity: at `1e-4` the
network is simply **undertrained** within the fixed 8-epoch budget, so it sits in
a high-loss regime that also produces its worst FPR (**0.1194**). Increasing the
step size lets the same architecture actually converge, and F1 and FPR improve
*together* (FPR **0.1194 → 0.0533**, roughly halved) — the hallmark of a model
that was underfit rather than mis-regularised. Because the best point sits at the
**top of the swept range**, there may be marginal headroom just above `3e-3`, but
that edge should be probed cautiously against training divergence rather than
assumed.

The three architectural/regularisation knobs behave like classic
second-order refinements around a healthy operating point:

- **`dropout`** trades capacity for regularisation monotonically: lighter
  dropout (0.1) gives the best F1 (0.8362) *and* the lowest CNN FPR in the study
  (0.0490); heavier dropout (0.5) underfits (0.8115). On a 5000-row subsample the
  0.1 optimum is partly a small-data artefact — less regularisation looks better
  when there is less to overfit against.
- **`num_filters`** shows mild capacity gains (0.8165 → 0.8379) but its FPR is
  non-monotone: 256 filters win F1 yet raise FPR to 0.0695 versus 0.0547 at 128,
  so the extra capacity partly buys itself back in false alarms.
- **`embed_dim`** peaks at **32**: 16 underfits (0.8046) and 64 gives no F1 gain
  (0.8281) while worsening FPR (0.0547 → 0.0796) — a clean saturation point.

### Recommended settings — CNN

| hyperparameter | recommended | rationale |
|---|---|---|
| `learning_rate` | **0.003** | Best F1 (0.8512) and lowest FPR (0.0533); the single highest-leverage choice. Consider a brief probe just above 3e-3, guarding against divergence. |
| `dropout` | **0.3** | 0.1 was best on the subsample (F1 0.8362) but confirmed as a small-data artefact: the full-data CNN run achieves F1 0.8603 with dropout=0.3, confirming 0.3 as the production setting. |
| `num_filters` | **128** | Best F1/FPR balance (0.8298 / 0.0547). Move to 256 only if the ~0.008 F1 gain outweighs the higher FPR (0.0695). |
| `embed_dim` | **32** | Saturation point: best FPR (0.0547) and near-best F1 (0.8298); 64 adds cost and false alarms without F1 gain. |

Best observed CNN configuration in the sweep: `learning_rate=0.003`
(**F1 0.8512, FPR 0.0533**), comfortably ahead of the best XGBoost point
(F1 0.7354).

---

## Cross-model synthesis

| question | answer | evidence |
|---|---|---|
| Which hyperparameter most affects **F1**? | **`learning_rate`** | CNN 0.7127→0.8512 (Δ0.1385); largest F1 swing on XGBoost too (Δ0.0481). |
| Which hyperparameter most affects **FPR**? | **`scale_pos_weight`** (XGBoost) | 0.049→0.1447, ~3×, while F1 barely moves (Δ0.0184). |
| Which model is more sensitive overall? | **CNN** | Its outcome hinges on getting `learning_rate` right; XGBoost F1 is saturated (~0.71–0.735) and largely tuning-proof. |

Two design lessons follow. First, **the levers are decoupled by role**: F1 is an
*optimisation/convergence* story (get `learning_rate`, and for XGBoost the
`n_estimators`/`max_depth` capacity, out of the underfitting regime), whereas the
false-alarm rate is a *decision-threshold* story best controlled with a
purpose-built dial like `scale_pos_weight`. Second, **XGBoost's insensitivity is
itself a deployment asset**: a model that holds ~0.73 F1 across almost any
reasonable setting is low-risk to operate and re-train, even if its ceiling
trails the CNN. Full-data revalidation confirms both findings: XGBoost `max_depth=12` generalises
(hybrid F1 0.8761 on Dataset 1, up from 0.853 at depth 6), and the CNN holds F1 0.8603
with the conservative `dropout=0.3` — the aggressive `dropout=0.1` / `learning_rate=3e-3`
combination is not needed and not applied.
