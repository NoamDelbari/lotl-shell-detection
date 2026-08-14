# Chapter 4 — Feature Ranking Findings

XGBoost gain-based importance quantifies how much each engineered feature reduces training loss across the splits it participates in — a direct measure of the discriminative signal the model leans on, not merely how often a feature appears. `report/figures/ch4_feature_importance_dataset1.png` ranks the top-20 engineered features for Dataset 1; the leaders and their MITRE ATT&CK mappings are summarised below (full RF-MDI, XGBoost-gain and permutation scores in `report/ch4_feature_ranking.csv`).

## Top 5 Dataset 1 features

| Rank | Feature | XGB gain | What it measures | MITRE ATT&CK tactic → technique |
|------|---------|----------|------------------|---------------------------------|
| 1 | `n_abs_paths` | 0.181 | Count of absolute-path tokens (`/etc`, `/proc`, `/tmp`, …) | Discovery / Collection → filesystem targeting |
| 2 | `has_dev_null` | 0.111 | Output suppression via `>/dev/null` | Defense Evasion → output/indicator suppression |
| 3 | `has_shell_bin` | 0.097 | A shell interpreter is named (`bash`, `sh`, `zsh`, `dash`) | Execution → Unix Shell (T1059.004) |
| 4 | `head_is_lotl` | 0.045 | The command head *is* a GTFOBins/LotL binary | Execution / Defense Evasion → LotL abuse |
| 5 | `has_interp_bin` | 0.041 | An interpreter is named (`python`, `perl`, `ruby`) | Execution → Command & Scripting Interpreter |

The gain is steeply front-loaded: `n_abs_paths` alone (0.181) outweighs the next two features combined, and the top three carry the bulk of the ranked importance before the curve flattens into a long tail of near-equal features. The model is not spreading confidence evenly; it bets heavily on a few dominant cues — where a command reaches in the filesystem, whether it suppresses its own output, and whether it invokes an explicit interpreter.

## Surprises versus intuition

The intuitive expectation for a T1059.004 classifier is that it keys on *semantically malicious* content — reverse-shell primitives (`has_dev_tcp`), download cradles (`has_fetch_bin`), or privilege escalation. Instead the top of the ranking is dominated by **structural and filesystem-reach** features: how many absolute paths the command names, whether it redirects to `/dev/null`, whether *a* shell binary is present. These describe the *shape and reach* of a command more than its intent. The single sharpest intent primitive, `has_dev_tcp`, sits far down the gain curve — reverse shells are caught by their whole token signature, not by any one feature the tree isolates. This is the **style-shortcut risk** the project set out to probe: because labels are provenance-derived, the model can separate the classes by learning the stylistic fingerprint of the attack corpus rather than the underlying behaviour.

## Cross-dataset divergence foreshadows transfer collapse

Comparing the two ranking figures is the most consequential observation. Dataset 1's leading XGBoost-gain cue is `n_abs_paths`, with shell/interpreter presence close behind; Dataset 2 (`ch4_feature_importance_dataset2.png`) instead leads with `has_fetch_bin` (0.093) and the positional `head_is_shell` / `head_is_lotl`, with `has_shell_bin` demoted. The corpora do not merely weight a shared signal differently — they disagree about *which* family of cues is most discriminative. Each model has latched onto the provenance-specific style of its own training corpus (curated exploit text vs. live honeypot droppers). Because those styles diverge at the very top of the gain ranking, a boundary tuned to Dataset 1's path/shell cues has little reason to fire on Dataset 2's fetch cues — the early warning sign for the cross-dataset **transfer collapse** examined in Chapter 8.
