# Chapter 1 — Threat Characterization

## 1.1 The technique, the telemetry, and the labels

**The technique.** ATT&CK catalogues **T1059.004 — Command and Scripting
Interpreter: Unix Shell** under Execution (TA0002): adversary use of `sh`,
`bash` and relatives. The shell is also the standard administrative interface,
so abuse is hard to separate from use.

**Living off the land defeats file-based detection by construction, not by
evasion.** The binary is vendor-packaged and already present, so hash
blocklists, YARA, allow-listing and integrity monitoring all ask *is this
program trustworthy?*; yes. What differs is **the instruction**: `curl` fetching
a tarball and `curl` streaming a dropper into `sh` are the same file on disk,
differing only in argv.

**The command string is therefore the right telemetry.** It carries intent at
the finest grain and needs no new agent: `auditd`, Sysmon-for-Linux and Cowrie
already record it (Table 1.1). Its uniformity lets the corpora be harmonised
(Chapter 5).

**The provenance-labeling premise, and what it costs.** No corpus carries
per-command intent labels; each is inherited from *where it was collected*:
offensive references and honeypot malicious, documentation and user history
benign. A classifier can satisfy it by learning corpus **style**, not intent —
three failure modes, measured not assumed: *unlearnable overlap* (`whoami`,
`id` identical across classes); *source fingerprints* (`has_ipv4` on 100% of
`quasarnix` rows); and *non-transfer*. The split is **grouped by command shape**
but deliberately **not** by source, since only the second corpus exposes learned
style: §8.2's transfer is the honest generalisation test, in-distribution
accuracy an upper bound. The most obvious cheat, a literal-IPv4 rule, scores
solo-rule F1 **0.141** (D1) and **0.105** (D2), below the 0.40 floor.

## 1.2 Behaviour → telemetry → feature mapping

Seven behaviours span the detectability spectrum, not the threat rankings.
Effect sizes come from `report/ch3_feature_decisions.md`, train splits only:
odds ratio *OR* for binary, Cliff's delta *d* for continuous, D1 then D2.

**Table 1.1 — Adversarial behaviour mapped to telemetry, log fields, engineered
features and detection reasoning.** The bold verdict states whether a
provenance-labelled classifier detects it; every feature is in `FEATURE_NAMES`
(`src/features.py`).

<!-- cols: 1.10 0.80 1.05 1.30 2.25 -->

| Adversarial Behavioral Characteristic | Required Telemetry Source | Specific Log Attributes / Raw Fields | Derived / Engineered Feature | Detailed Explanation |
|---|---|---|---|---|
| **Reverse/bind shell** (T1059.004; C2 via T1071). | `auditd` EXECVE argv; Sysmon Event ID 1. | `/dev/tcp/<ip>/<port>` redirects; `-i`; `-e`/`-c`; `2>&1`. | `has_dev_tcp`, `has_shell_flag_i`, `has_exec_flag`, `n_redirect_out`, `has_stderr_merge`, `has_shell_bin` | **Reliably detectable.** `/dev/tcp` is bash-only, with no legitimate use (OR 559); §8.1 records **0 of 58 `quasarnix` and 0 of 15 `payloads` false negatives** — though `socat` variants pass. |
| **Download-and-execute** (T1105 + T1059.004). | `auditd` EXECVE; Cowrie `cowrie.command.input`. | Fetch binary (`curl`, `wget`); URL or IPv4; pipe into `sh`. | `has_fetch_bin`, `has_url`, `has_ipv4`, `n_pipes`, `has_pipe_to_shell`, `has_fetch_exec_chain` | **Detectable in-domain, but confounded.** The extractor computes fetch-pipe-shell as `has_fetch_exec_chain` (OR 45.1 / 9.03), but an IPv4-only rule reaches ROC-AUC 0.535 / 0.523 — enough to drive the D2→D1 collapse (§8.2). |
| **Trusted-binary abuse and discovery** (T1059.004 via GTFOBins; T1033). | `auditd` EXECVE; Sysmon's parent-image field. | `awk 'BEGIN{system("/bin/sh")}'`, `find … -exec /bin/sh \;`; bare `whoami`, `id`. | `has_lotl_bin`, `head_is_lotl`, `has_enum_bin`, `n_quotes`, `special_ratio`, `max_token_len` | **Not detectable from the binary — the signal inverts.** `has_lotl_bin` is *benign* on both corpora (OR 0.62 / 0.50), `has_enum_bin` too (2.50 / 0.67); only argument structure remains, read positionally by `head_is_lotl`. |
| **Command obfuscation** (T1027.010) — encoding, splicing (`c"u"rl`) or `$IFS`. | `auditd` EXECVE argv or Cowrie `cowrie.command.input`. | Long `[A-Za-z0-9+/=]` runs; `\x41` escapes; `base64 -d` beside a pipe; `${IFS}`. | `has_base64_blob`, `b64_run_len`, `has_hex_escape`, `has_decode_exec`, `has_quote_splice`, `has_ifs_expansion` | **Sharp, rare and corpus-dependent.** `has_decode_exec` reaches OR 45.1 and `has_quote_splice` 27.0, each on under 1% of rows. Caveat: `has_decode_exec` inverts to 0.60 on the honeypot, where attackers type unencoded droppers. |
| **Local data staging** (T1074.001) — archived in a world-writable directory. | Shell command log; Cowrie `cowrie.command.input`. | `/tmp`, `/var/tmp`, `/dev/shm` with `cd`, `tar`, `chmod +x`. | `has_staging_dir`, `n_abs_paths`, `has_hidden_path` | **Transfers: the reason is structural, not stylistic.** Any unprivileged account can write there, so `has_staging_dir` keeps sign and magnitude (OR 14.3 / 4.75). Developers use `/tmp` constantly, so it earns weight only in conjunction. |
| **Credentials in files** (T1552.001) — read with ordinary utilities. | Shell command log; `auditd` EXECVE argv. | Absolute paths under `/etc`, `/proc`, `/var/log`, `/root`; dot-prefixed (`~/.ssh/id_rsa`). | `n_abs_paths`, `n_sensitive_paths`, `has_hidden_path`, `has_home_ref` | **The strongest row by effect size**: the behaviour is in what is *named*, not run. `n_abs_paths` scores d +0.45, AUC 0.73, solo-rule F1 0.595 and top Random Forest Gini 0.124. `has_home_ref` is the counter-example, inverting from 2.02 to 0.38. |
| **Privilege escalation via sudo** (T1548.003) — via the host's own mechanism. | Shell command log; `auditd` EXECVE. | The **first token** after assignment-prefix stripping — `sudo`, `su`, `doas`, `pkexec`. | `head_is_privesc` — and nothing else | **Deliberately the thinnest row; the evidence forced it.** `has_privesc_bin` was built, measured and **killed** at OR 0.99 / 1.01: `sudo` is everywhere. Only *position* survives, and it inverts (OR 0.77 / 3.70). |

**Takeaway — detectability tracks lexical distinguishability, not danger.**
Reverse shells carry unforgeable syntax; download cradles hide a signal behind a
non-transferable URL/IP artefact; trusted-binary abuse has no content signature
and points the *wrong way* — the sharpest evidence these labels are handled
honestly.

## 1.3 Theoretical feature rationale — 43 features in eight families

**What distinguishes adversarial intent from ordinary administration when the
program is legitimate in both cases?** Sixty-eight candidates were reduced to 43
by a gate applied identically to both corpora (Table B.3). First, **no single
feature separates the classes**: on D1 only three clear the 0.40 do-nothing
floor as solo rules (`n_abs_paths` 0.595, `digit_ratio` 0.434, `special_ratio`
0.411); on D2 **not one does**. The set is built for conjunctions, which a tree
ensemble or CNN represents and a keyword rule cannot. Second, **the `source`
column is never a model input**; features that proxied for provenance anyway are
flagged, not quietly dropped.

**Table 1.2 — The eight feature families, each family's design premise, and what
measurement returned.** Premises were fixed before the evidence, so a failed one
is a finding.

<!-- cols: 2.10 4.40 -->

| Family and features | Design premise → what the measurement returned |
|---|---|
| **Shape and size (4)** — `len_chars`, `len_tokens`, `mean_token_len`, `max_token_len` | Attack one-liners are compressed. **The premise holds on D1 (`len_chars` d +0.25) and inverts on the honeypot (−0.17)**; all four sit at the 0.40 solo-F1 floor (§5.2). |
| **Structure and chaining (4)** — `n_pipes`, `n_redirect_out`, `has_stderr_merge`, `n_quotes` | Composition depth tracks complexity; `2>&1` suits a socket-attached shell (OR 28.7). But **`n_pipes` leans benign on both corpora (d −0.17 / −0.11)** — piping is Unix's core idiom. |
| **Network and delivery (4)** — `has_ipv4`, `has_private_ip`, `has_url`, `has_dev_tcp` | Attacks must name an endpoint literally; `has_dev_tcp` is the purest signal (OR 559). `has_ipv4`, the designated shortcut hazard, was **kept deliberately**: its D2 OR of 5.00 is earned on a corpus with no `quasarnix`. |
| **Binary families (6)** — `has_fetch_bin`, `has_shell_bin`, `has_interp_bin`, `has_lotl_bin`, `has_enum_bin`, `has_evasion_tok` | Threat-mapped lists fixed before seeing data; `has_fetch_bin` transfers best (OR 5.56 / 7.96). The central negative result: **`has_lotl_bin` is benign on both corpora (0.62 / 0.50), `has_enum_bin` inverts outright (2.50 / 0.67)**. |
| **Head and arguments (6)** — `head_is_shell`, `head_is_interp`, `head_is_lotl`, `head_is_privesc`, `n_flags`, `has_long_flag` | If presence is weak, *position* should be stronger — **`head_is_shell` reaches OR 47.9 / 13.6 against `has_shell_bin`'s 32.8 / 5.99** — invocation style separates too (`has_long_flag` OR 0.08 on the honeypot). |
| **Execution micro-structure (8)** — `has_pipe_to_shell`, `has_fetch_exec_chain`, `has_decode_exec`, `has_ifs_expansion`, `has_heredoc`, `has_dev_null`, `has_shell_flag_i`, `has_exec_flag` | The extractor computes *fetch* ∧ *pipe* ∧ *interpreter* as `has_fetch_exec_chain` (OR 45.1 / 9.03), not the model. **`has_pipe_to_shell` is the most transferable feature (OR 8.65 / 8.68)**. |
| **Paths and filesystem (5)** — `n_abs_paths`, `has_hidden_path`, `has_staging_dir`, `has_home_ref`, `n_sensitive_paths` | What a command *names* beats what it runs: **`n_abs_paths` is the strongest single feature** (d +0.45, AUC 0.73, top Random Forest Gini 0.124), while `has_home_ref` inverts from 2.02 to 0.38. |
| **Obfuscation (6)** — `has_base64_blob`, `b64_run_len`, `has_hex_escape`, `has_quote_splice`, `digit_ratio`, `special_ratio` | The only adversarial behaviour that *adds* signal: `special_ratio` (d +0.32) fires on every row, `has_quote_splice` (OR 27.0) rarely. **Encoding artefacts, unlike vocabulary, survive a corpus change** — `digit_ratio` +0.24 / +0.23, `has_hex_escape` 22.3 / 11.7. |

**What the rejections contribute.** Three patterns recur among the 25 killed
candidates: *redundancy* (`char_entropy`, `token_entropy`, dropped for
`len_chars`/`len_tokens`); *class-neutrality* (`has_privesc_bin`,
`nonprintable_ratio`); and *sparsity that pooling recovers* — the three themed
path counters. This makes the 43-feature set a result, not an assumption. Full
funnel: Table B.3.
