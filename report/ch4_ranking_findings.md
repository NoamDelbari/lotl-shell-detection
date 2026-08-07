# Chapter 4 — Feature Ranking Findings

XGBoost gain-based importance quantifies how much each engineered feature
reduces training loss across every split it participates in — a direct measure
of the discriminative signal the model actually leans on, not merely how often a
feature appears. Figure `ch4_feature_importance_dataset1.png` ranks the top 20
engineered features for Dataset 1; the leaders and their MITRE ATT&CK mappings
are summarized below.

## Top 5 Dataset 1 features

| Rank | Feature | Gain | What it measures | MITRE ATT&CK tactic → technique |
|------|---------|------|------------------|---------------------------------|
| 1 | `shell_bins` | 0.194 | Presence of a shell interpreter (`bash`, `sh`, `zsh`, `dash`) | Execution → Command and Scripting Interpreter: Unix Shell (T1059.004) |
| 2 | `redirect_count` | 0.130 | Count of `>` / `>>` output redirects | Execution → Unix Shell (T1059.004) |
| 3 | `pipe_count` | 0.076 | Count of single-`\|` pipe stages | Execution → Unix Shell (T1059.004) |
| 4 | `path_proc` | 0.040 | References to `/proc/` | Discovery → Process/System Discovery (T1057) |
| 5 | `lotl_bins` | 0.030 | Presence of dual-use LotL binaries (`awk`, `find`, `vim`, `dd`, `xxd`, `tar`, `zip`) | Execution / Defense Evasion / Collection → e.g. Archive Collected Data (T1560) |

The gain is steeply front-loaded: `shell_bins` alone (0.194) carries more weight
than the next two features combined, and the top three — all Execution/Unix-Shell
signals — account for the bulk of the ranked importance before the curve flattens
into a long tail of near-equal features (`path_proc` at 0.040 down to `lotl_bins`
at 0.030 and below). The model is not spreading its confidence evenly; it is
betting heavily on a handful of dominant cues.

## Surprises versus intuition

The intuitive expectation for a T1059.004 classifier is that it would key on
*semantically malicious* content — credential-store paths (`/etc/shadow`,
`~/.ssh`), reverse-shell primitives (`/dev/tcp`), download cradles, or privilege
escalation binaries. Instead, four of the top five features are **structural**
rather than semantic: whether *a* shell binary is present at all, and how many
redirects and pipes stitch the one-liner together. These describe the *shape* of
a command — its composition grammar — not its intent. Only `path_proc` (Discovery)
and, weakly, `lotl_bins` gesture at what the command is actually trying to *do*,
and both sit far down the gain curve. The genuinely intent-bearing features from
the wider feature set (`path_etc_passwd`, `privesc_bins`, `dev_tcp_present`,
`evalexec_present`) either appear only in the mid-pack of
`ch4_feature_importance_dataset1.png` or drop out of the top 20 entirely.

This is exactly the **style-shortcut risk** the project set out to probe. Because
the labels are provenance-derived (attack samples drawn from one class of
sources, benign from another), the model can achieve strong training separation
by learning the *stylistic fingerprint* of the attack corpus — its authors' habit
of invoking an explicit interpreter and chaining stages with pipes and redirects —
rather than the underlying malicious behavior. Redirects and pipes are the
connective tissue of shell tradecraft, but they are equally the connective tissue
of ordinary admin and CI scripting; leaning on their *counts* is a proxy for
"looks like a dense one-liner," not "is an attack." A structural feature that
correlates with the label in this dataset is a shortcut that may not survive a
change of provenance.

## Cross-dataset divergence foreshadows transfer collapse

The most consequential observation comes from comparing the two ranking figures.
In Dataset 1 the headline feature is `shell_bins` (gain 0.194), with `lotl_bins`
trailing far behind at 0.030. In Dataset 2
(`ch4_feature_importance_dataset2.png`) the ordering is nearly inverted:
`lotl_bins` dominates at 0.177 while `shell_bins` falls to 0.052. The two corpora
do not merely weight a shared signal differently — they disagree about *which*
family of cues is most discriminative in the first place. Each model has latched
onto the provenance-specific style of its own training corpus. Because those
styles diverge, a decision boundary tuned to Dataset 1's shell-interpreter cue
has little reason to fire on Dataset 2's LotL-binary cue, and vice versa. This
divergence at the very top of the gain ranking is the early warning sign for the
cross-dataset **transfer collapse** examined later: features that look powerful
in-distribution are, in large part, learned stylistic shortcuts that do not
generalize across provenance boundaries.
