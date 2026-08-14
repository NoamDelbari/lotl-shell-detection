# Chapter 1.3 — Theoretical Feature Rationale (43 features, 8 families)

> Every feature below is in `FEATURE_NAMES` (`src/features.py`). Effect sizes are
> quoted from `report/ch3_feature_decisions.md` (train splits only): Cliff's
> delta *d* for continuous features, odds ratio *OR* for binary ones, on
> Dataset 1 and Dataset 2 respectively. The per-feature evidence table ships as
> an appendix; this section gives the security reasoning that motivated each
> family *before* the evidence was gathered.

The feature set was designed to answer one question: **what, in a command
string, distinguishes adversarial intent from ordinary administration when the
program being run is legitimate in both cases?** Sixty-eight candidates were
proposed from the threat model in Section 1.2, then reduced to 43 by a
pre-registered selection gate applied identically to both corpora. The 25
rejections are retained with their evidence, because a feature that was built,
measured and discarded is part of the argument.

Two design commitments run through every family. First, **no single feature is
expected to separate the classes.** The do-nothing floor — the F1 obtained by
labelling every command an attack at 25% prevalence — is 0.40. On Dataset 1 only
three of the 43 clear it as a solo rule (`n_abs_paths` 0.595, `digit_ratio`
0.434, `special_ratio` 0.411); on Dataset 2 **not one feature does**, which is
the most compact statement available of how much harder the honeypot corpus is.
The set is built for *conjunctions*, which is what a tree ensemble or a CNN can
represent and a keyword rule cannot. Second, **the `source` column is never a
model input**, so no feature may be a proxy for collection provenance; where one
turned out to be (`has_ipv4` saturating `quasarnix`), it is flagged rather than
quietly dropped.

**Shape and size (4) — `len_chars`, `len_tokens`, `mean_token_len`,
`max_token_len`.** The premise is that attack one-liners are compressed: a
dropper chains fetch, permission change and execution into a single line because
the operator has one shot through a command-injection primitive, whereas an
administrator works interactively across several short commands. Long individual
tokens are a second, distinct signal — URLs, encoded blobs and absolute paths all
produce them, so `max_token_len` fires where `len_chars` may not. The measured
result is the sharpest warning in the chapter: the premise holds on the curated
corpus (`len_chars` d +0.25) and **inverts** on the honeypot (d −0.17), because
real attacker input at a Cowrie prompt is terse recon while real user history is
verbose. All four sit exactly at the 0.40 floor on solo F1. They are retained as
cheap split variables and context for other features, not as evidence in their
own right, and they are the primary exhibit for the distribution shift analysed
in Chapter 5.2. Only `mean_token_len` keeps its sign on both corpora (+0.16 /
+0.20).

**Structure and chaining (4) — `n_pipes`, `n_redirect_out`, `has_stderr_merge`,
`n_quotes`.** These encode how a command wires processes and file descriptors
together. The security reasoning is that composition depth tracks payload
complexity: a reverse shell stacks redirections (`>& /dev/tcp/… 0>&1`) at a level
ordinary commands rarely reach, and `2>&1` stream-merging is characteristic of a
shell being attached to a socket rather than a terminal. `has_stderr_merge` bears
this out on Dataset 1 (OR 28.7) and is the reason `n_redirect_out` alone is
insufficient — the extractor strips `>&` and `2>&1` forms before counting, so the
two features are complementary rather than redundant. The instructive failure is
`n_pipes`, which leans **benign on both corpora** (d −0.17 / −0.11): piping is the
core idiom of Unix administration, and attackers use it less than administrators
do. The intuition that "piping looks suspicious" is simply wrong, and the feature
is kept because being reliably wrong in a known direction is useful to a model.

**Network and delivery (4) — `has_ipv4`, `has_private_ip`, `has_url`,
`has_dev_tcp`.** A LotL attack must eventually name somewhere to fetch from or
call back to, and that endpoint has to appear literally in the command string.
`has_dev_tcp` is the purest signal in the entire feature set — a bash-only
redirect with essentially no legitimate interactive use, at OR 559 on Dataset 1.
The others are progressively more dual-use: `has_url` (OR 2.70 / 6.50) is
genuinely ambiguous because documentation corpora are full of URLs, and
`has_ipv4` is the project's designated shortcut hazard, firing on 100% of
`quasarnix` rows in Dataset 1. It was kept deliberately rather than removed: its
Dataset 2 odds ratio of 5.00 is earned on a corpus containing no `quasarnix` at
all, so the signal is real even though the Dataset 1 measurement is contaminated.
Hiding the feature would have hidden the problem; it is instead surfaced as a
Chapter 4 source-ablation exhibit. `has_private_ip` separates lateral movement
(RFC1918 targets) from external C2, and is near-inert on Dataset 1 by design.

**Binary families (6) — `has_fetch_bin`, `has_shell_bin`, `has_interp_bin`,
`has_lotl_bin`, `has_enum_bin`, `has_evasion_tok`.** These are fixed,
threat-mapped lists — chosen from the threat model before seeing data, so they
cannot memorise corpus vocabulary the way a learned bag-of-words does. Each
answers "which *class* of program is involved": something that downloads,
something that is a shell, something that interprets code, something catalogued
by GTFOBins, something that enumerates, something that evades. `has_fetch_bin` is
the family's strongest and most transferable member (OR 5.56 / 7.96). The family
also contains the project's central negative result: `has_lotl_bin` is a
**benign** indicator on both corpora (OR 0.62 / 0.50), and `has_enum_bin` inverts
outright (2.50 / 0.67). Naming a program turns out to be weak evidence about
intent, which is precisely the finding that justifies the next two families.

**Head and arguments (6) — `head_is_shell`, `head_is_interp`, `head_is_lotl`,
`head_is_privesc`, `n_flags`, `has_long_flag`.** If presence is weak, *position*
should be stronger: a command whose first token is a shell is being invoked as a
shell, whereas one that merely mentions `bash` may be documentation. The head
tokens are extracted after stripping variable-assignment prefixes, so
`FOO=1 bash -i` is read correctly. The gain is real — `head_is_shell` reaches OR
47.9 / 13.6, far above `has_shell_bin`'s 32.8 / 5.99 on the same corpora — and it
is what rescued the sudo row in Section 1.2 after the presence-based
`has_privesc_bin` was killed as class-neutral (OR 0.99 / 1.01). The flag features
capture invocation *style*: administrators use readable long options (`--verbose`),
scripted payloads use terse ones, which is why `has_long_flag` drops to OR 0.08 on
the honeypot corpus.

**Execution micro-structure (8) — `has_pipe_to_shell`, `has_fetch_exec_chain`,
`has_decode_exec`, `has_ifs_expansion`, `has_heredoc`, `has_dev_null`,
`has_shell_flag_i`, `has_exec_flag`.** This is the family that most directly
encodes the conjunction argument. Rather than leaving the model to discover that
*fetch tool* ∧ *pipe* ∧ *interpreter* is the download-cradle signature, the
extractor computes that conjunction explicitly as `has_fetch_exec_chain` (OR 45.1
/ 9.03), and likewise `has_pipe_to_shell` for any pipe terminating in an
interpreter. These are deliberately rare — most fire on well under 1% of rows and
contribute nothing to aggregate accuracy — and they are kept for exactly that
reason: they are near-conclusive when they do fire. `has_pipe_to_shell` is the
single most transferable feature in the project (OR 8.65 on Dataset 1, 8.68 on
Dataset 2), which is strong evidence that the underlying behaviour, not a corpus
artefact, is being measured. `has_shell_flag_i` and `has_exec_flag` capture the
interactive and inline-command invocations characteristic of reverse shells;
`has_dev_null` and `has_heredoc` capture output suppression and inline payload
delivery.

**Paths and filesystem (5) — `n_abs_paths`, `has_hidden_path`, `has_staging_dir`,
`has_home_ref`, `n_sensitive_paths`.** What a command *names* proves to be more
informative than what it runs. `n_abs_paths` is the strongest single feature in
the set (d +0.45, AUC 0.73, top Random Forest Gini importance at 0.124 on
Dataset 1) on the reasoning that absolute paths indicate an operator working
somewhere unfamiliar, without the benefit of a working directory or shell
history. `has_staging_dir` encodes the structural necessity behind `/tmp` and
`/dev/shm` — guaranteed-writable, and memory-backed in the latter case — and is
one of the few features to keep both sign and magnitude across corpora (OR 14.3 /
4.75). `n_sensitive_paths` is intentionally a lumped count: `n_cred_paths`,
`n_proc_paths` and `n_log_paths` each failed the gate individually and pool into
a feature that passes on both. `has_home_ref` is retained as a documented
counter-example, inverting from OR 2.02 to 0.38.

**Obfuscation (6) — `has_base64_blob`, `b64_run_len`, `has_hex_escape`,
`digit_ratio`, `special_ratio`, `has_quote_splice`.** Obfuscation is the only
adversarial behaviour that *adds* signal, because the evasion is itself
anomalous: no benign workflow splices quotes through a binary name. The family
pairs sparse near-categorical flags with dense continuous ratios so that both
blatant and subtle cases are covered — `has_quote_splice` at OR 27.0 is rare and
sharp, while `special_ratio` (d +0.32, the second-largest effect in the set on
Dataset 1) and `digit_ratio` fire on every row. `digit_ratio` is the most stable
continuous feature in the whole project (+0.24 / +0.23), and `has_hex_escape` the
most stable binary one (OR 22.3 / 11.7); encoding artefacts, unlike vocabulary,
survive a change of corpus. `b64_run_len` supplements the base64 flag with
magnitude, since a long unbroken encoded run is far more indicative than an
incidental base64-shaped token.

**What the rejections contribute.** The 25 killed candidates are not noise. Three
patterns recur and each is an argument in its own right: features that were
*redundant* (`char_entropy` and `token_entropy` dropped in favour of `len_chars`
and `len_tokens`, `head_is_fetch` in favour of `has_fetch_bin`); features that
were *class-neutral* despite strong intuition (`has_privesc_bin`,
`nonprintable_ratio`); and features that were *too sparse individually* but
recoverable when pooled (the three path counters). Reporting them makes the
43-feature set a result rather than a starting assumption, and it is what allows
Chapter 4's ranking to be read as evidence rather than as confirmation of the
choices made here.
