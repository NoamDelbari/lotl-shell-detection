# Chapter 3 — Exploratory Data Analysis Findings (Dataset 1)

The command-length histogram (`ch3_length_hist_dataset1.png`, density-normalized and clipped at the 99th percentile) confirms that attack one-liners are, on average, longer than benign ones: benign commands center at a mean of 37.8 characters (median 29), while attack commands run to a mean of 52.4 (median 41). The right tail is decisively heavier for attacks — the 99th percentile stretches to 227 characters versus 147 for benign — which is what a payload-carrying reverse shell, download cradle, or base64 blob looks like next to a bare `ls` or `git commit`. The honest caveat is that this is a difference of *distributions*, not of *classes*: both labels pile up in the same 20–50 character body, and the benign curve fully envelops the attack curve there. A probe trained on length alone scores only **AUC 0.611** on the held-out test split (0.624 in-train), barely above the 0.5 no-skill line. Length is a real signal that is nearly useless as a standalone rule, because the overlap in the common range swamps the separation in the tail.

The per-feature variance-by-label plot (`ch3_variance_by_label_dataset1.png`) makes the same point structurally and explains *why* length looks strong in aggregate yet fails as a discriminator. The features with the largest benign-vs-attack variance gap are dominated by raw-magnitude "shape" features: `len_chars` alone accounts for a gap of ~1233 (attack variance 2055 is 2.5× the benign 822), followed by `max_token_len` and, further down, `len_tokens` and `mean_token_len`. Crucially, the gap is driven by attack commands being far more *dispersed*, not uniformly shifted — attackers produce both terse `id`-style probes and enormous encoded payloads, inflating variance without cleanly moving the mean. Below the size features, the gap ranking turns behavioral: `b64_run_len` (the longest base64 run) carries 4.3× the attack-side variance, and `n_abs_paths`, `n_sensitive_paths`, `n_redirect_out`, and `has_shell_bin` (gap 0.15, rank 11) all spike. Taken together this describes the attack profile precisely — longer commands, longer individual tokens (encoded blobs, long URLs and paths), more base64, deeper reach into the filesystem (absolute paths, then `/etc`- and `/proc`-class targets), redirection into files or `/dev/tcp`, and an explicit `bash`/`sh` invocation.

| Feature | Benign var | Attack var | Variance gap |
|---|---:|---:|---:|
| `len_chars` | 821.80 | 2055.09 | 1233.28 |
| `max_token_len` | 34.75 | 112.82 | 78.08 |
| `b64_run_len` | 19.17 | 82.09 | 62.92 |
| `len_tokens` | 16.63 | 36.27 | 19.64 |
| `mean_token_len` | 7.06 | 13.04 | 5.98 |
| `n_quotes` | 2.56 | 4.89 | 2.33 |
| `n_flags` | 1.76 | 2.63 | 0.87 |
| `n_abs_paths` | 0.12 | 0.86 | 0.74 |
| `n_sensitive_paths` | 0.03 | 0.37 | 0.34 |
| `n_redirect_out` | 0.07 | 0.34 | 0.27 |

Variance gap is a measure of *spread*, not of separation, and the rank-biserial
effect sizes (`report/ch3_d1_feature_stats.csv`, and the same statistics in
`report/ch3_feature_justification.csv`) reorder the table decisively. On
Dataset 1, 41 of the 43 features separate the classes at p < 0.05, but only six
reach |r| ≥ 0.2: `n_abs_paths` (+0.452), `special_ratio` (+0.318),
`max_token_len` (+0.303), `len_chars` (+0.247), `digit_ratio` (+0.238), and
`n_redirect_out` (+0.229). The two that fail the significance test are
`has_long_flag` (p = 0.081) and `has_private_ip`, which is essentially inert
here (r ≈ 0, prevalence 0.0007 in both classes) and earns its place in the
feature set on Dataset 2 rather than this one. Note the crossings: `n_abs_paths`
ranks eighth by variance gap and *first* by effect, while `len_chars` leads the
gap table and places only fourth by effect — spread and signal are not the same
quantity, which is the theme of the takeaways below.

Three takeaways shape the downstream model design. First, the top of the gap ranking is an artifact of *scale*, not necessarily of *information*: `len_chars`, `max_token_len`, and `mean_token_len` win the variance contest largely because they are measured in raw character units. The cleanest counter-example is `special_ratio`, which ranks 41st of 43 by variance gap and second by effect size — its entire signal lives inside a [0,1] band that the variance chart cannot show. Any distance-, linear-, or neural-based learner will be dominated by `len_chars`'s magnitude unless these features are standardized or log-transformed, whereas the bounded ratio features (`special_ratio`, `digit_ratio`) already encode obfuscation without the scale baggage; that is the argument for the in-pipeline standardization described in Chapter 5.3, and it is why the feature audit dropped the entropy features as redundant with `len_chars` rather than keeping a third scale-free proxy. Second, expect heavy dual-use overlap: pipes, redirects, and privilege escalation are the daily vocabulary of legitimate administration, so no single feature cleanly partitions the classes. The sharpest evidence is directional — `n_pipes` leans **benign** even on this curated corpus (attack mean 0.311 vs benign 0.557, r = −0.166), as do `has_lotl_bin` and `head_is_lotl`; the mere presence of LotL vocabulary is an anti-signal on both datasets, and Chapter 3's Dataset 2 analysis shows the same signs more strongly still. This is exactly why the length probe collapses to 0.611, and the correlation heatmap (`ch3_corr_heatmap_dataset1.png`) shows why redundancy compounds it: `len_chars` and `len_tokens` are collinear at 0.897 because they largely re-measure "how big is this command", and a second, non-size duplication runs through the presence-versus-head pairs (`has_lotl_bin` ~ `head_is_lotl` at 0.871, `has_interp_bin` ~ `head_is_interp` at 0.685). The model must earn its lift from *conjunctions* — a long token **and** a base64 run **and** a `/dev/tcp` redirect — not from any feature in isolation. Third, character count is real-but-insufficient by design: keep it as a cheap weak learner and a useful split variable for tree ensembles, but do not mistake its large variance gap for separating power. The distributional overlap in the 20–50 character body is the ceiling on what size alone can deliver, and closing that gap is the job of the path, network, and obfuscation features — `n_abs_paths` and `n_sensitive_paths` above all — rather than the shape features.
