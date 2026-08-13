# Chapter 1 — Threat Characterization

## 1.1 The technique, the telemetry, and the labels

**The technique.** ATT&CK catalogues **T1059.004 — Command and Scripting
Interpreter: Unix Shell** under the Execution tactic (TA0002): adversary use of
`sh`, `bash`, `dash` and their relatives on a compromised host. The shell is the
standard administrative interface to every Unix system, which is exactly what
makes its abuse hard to separate from its use. It is also the narrow waist of an
intrusion — a foothold obtained through any initial-access route becomes
arbitrary execution here, then chains onward to ingress tool transfer (T1105),
discovery (T1033), credential access (T1552.001) and lateral movement — so
detection at this layer is leverage.

**Living off the land defeats file-based detection by construction, not by
evasion.** No attacker binary is introduced: execution follows the ordinary
`fork(2)`/`execve(2)` path against a binary already present — `/bin/bash`,
`/usr/bin/curl`, `/usr/bin/awk` — which arrived through the package manager,
matches its vendor hash, sits at its expected path and, where enforced, is
signed. Hash blocklists have no novel hash; YARA rules have no dropped file;
allow-listing passes the binary because it *is* the legitimate binary; integrity
monitoring reports no change, because nothing changed. Each control answers *is
this program trustworthy?*, and the honest answer is yes. What differs is **the
instruction given to it**: `curl` fetching a release tarball and `curl` streaming
a dropper into `sh` are the same executable, the same syscalls and the same file
on disk, differing only in argv. Detection must move from the binary to the
command.

**The command string is therefore the right telemetry.** It is the
finest-grained artefact that still carries intent, and it needs no new agent:
`auditd` records full argv in `type=EXECVE`, Sysmon-for-Linux Event ID 1 carries
the command line, history files capture interactive sessions, and Cowrie logs
attacker input verbatim as `cowrie.command.input`. That the representation is
uniform across all four is what allows this project's two corpora to be
harmonised at all (Chapter 5), and it is where the signal lives:
`/dev/tcp/<host>/<port>` is a bash built-in redirect with essentially no
legitimate interactive use, at an odds ratio of **559** on Dataset 1. The binary
name alone carries none of that.

**The provenance-labeling premise, and what it costs.** No corpus carries
per-command intent labels, because intent is a property of the operator rather
than of the artefact, so each label is inherited from *where the command was
collected*: offensive references and honeypot capture malicious, documentation
and user history benign. Dataset 2's entire attack class is one Cowrie capture,
so "the honeypot corpus" below means Dataset 2. The premise bounds every result
that follows, because a classifier can satisfy a provenance-labelled objective by
learning corpus **style** instead of adversarial intent — and three forms of that
failure are measured here rather than assumed away: *unlearnable overlap*, where
commands are byte-identical across classes (`whoami`, `id`); *source
fingerprints*, where a feature saturates one source and proxies for it (`has_ipv4`
fires on 100% of `quasarnix` rows); and *non-transfer*. The mitigation is design,
and it is precise about what it does not cover. The in-distribution split is
**grouped by command shape** — literals, blobs and scratch filenames blanked to a
skeleton, whole groups assigned to one side, zero groups straddling either split
— which is stronger than deduplication, since not even a structural near-duplicate
is shared. It is deliberately **not** grouped by source: every Dataset 1 and
Dataset 2 source appears on both of its own sides, because a same-source test set
cannot expose a model that learned corpus style. Only the second corpus can, and
the two share no source at all, so §8.2's transfer result is the honest
generalisation test and in-distribution accuracy is treated as an upper bound.
That the discipline holds is measurable: the literal-IPv4 shortcut, the most
obvious available cheat, scores a solo-rule F1 of **0.141** (D1) and **0.105**
(D2), below the 0.40 do-nothing floor.

## 1.2 Behaviour → telemetry → feature mapping

Seven adversarial behaviours observed in the corpora are mapped below, chosen to
span the detectability spectrum rather than the threat rankings. Effect sizes
come from `report/ch3_feature_decisions.md`, train splits only: odds ratio *OR*
for binary features, Cliff's delta *d* for continuous ones, Dataset 1 then
Dataset 2.

**Table 1.1 — Adversarial behaviour mapped to telemetry source, raw log fields,
engineered features and detection reasoning.** The bold verdict opening each
explanation states whether a provenance-labelled classifier can detect that
behaviour reliably; every feature named is in `FEATURE_NAMES` (`src/features.py`).

<!-- cols: 1.30 0.80 1.20 1.15 2.05 -->

| Adversarial Behavioral Characteristic | Required Telemetry Source | Specific Log Attributes / Raw Fields | Derived / Engineered Feature | Detailed Explanation |
|---|---|---|---|---|
| **Reverse / bind shell** (T1059.004; C2 via T1071) — an interactive shell wired to a remote socket as the primary post-exploitation foothold. | `auditd` `type=EXECVE` argv; Sysmon-for-Linux Event ID 1 for parent-image context. | `/dev/tcp/<ip>/<port>` and `/dev/udp` redirects; interactive `-i`; exec flags `-e`/`-c`; stacked stream duplication (`>&`, `0<&1`, `2>&1`). | `has_dev_tcp`, `has_shell_flag_i`, `has_exec_flag`, `n_redirect_out`, `has_stderr_merge`, `has_shell_bin` | **Reliably detectable.** `/dev/tcp` is a bash-only redirect with essentially no legitimate interactive use — OR 559, the purest signal in the set; `has_stderr_merge` follows at 28.7. `n_redirect_out` is a count, not a flag, because reverse shells stack redirections to a depth ordinary commands never reach. Forensics agree: **0 of 58 `quasarnix` and 0 of 15 `payloads` false negatives** (§8.1). Reliability rides on those sources' clean style; a `socat` variant could still pass. |
| **Download-and-execute** (T1105 + T1059.004) — a next-stage payload pulled from attacker infrastructure and piped straight into an interpreter, so nothing touches disk. | `auditd` EXECVE; Cowrie `cowrie.command.input`, which logs the dropper chain as one input line. | A fetch binary (`curl`, `wget`, `tftp`); a URL or raw IPv4 in argv; the `\|` joining it to `sh`; `chmod +x` and a `/tmp` landing path. | `has_fetch_bin`, `has_url`, `has_ipv4`, `n_pipes`, `has_pipe_to_shell`, `has_fetch_exec_chain` | **Detectable in-domain, but confounded.** `curl` is ubiquitous, and benign use overwhelmingly *saves* a file (`-o file`) where the malicious idiom *streams into an interpreter* — so the extractor computes that conjunction explicitly rather than leaving the model to find it: `has_fetch_exec_chain` OR 45.1 / 9.03, `has_pipe_to_shell` 8.65 / 8.68. The confound is the endpoint: an IPv4-presence-only rule already reaches ROC-AUC 0.535 / 0.523 — weak but real, and register-specific enough to drive the D2→D1 collapse (§8.2). |
| **Trusted-binary abuse and host discovery** (T1059.004 via GTFOBins; T1033) — an allow-listed binary made to spawn a shell or read protected files, plus argument-free host fingerprinting. | `auditd` EXECVE; the abnormal-parent signal needs the Sysmon parent-image field. | Escape arguments on an ordinary tool — `awk 'BEGIN{system("/bin/sh")}'`, `find … -exec /bin/sh \;`, `vim -c ':!sh'`; bare `whoami`, `id`, `uname -a`. | `has_lotl_bin`, `head_is_lotl`, `has_enum_bin`, `n_quotes`, `special_ratio`, `max_token_len` | **Not detectable from the binary — the signal inverts.** Under provenance labels `has_lotl_bin` is a *benign* indicator on both corpora (OR 0.62 / 0.50) and `head_is_lotl` reaches 0.09 on Dataset 2: a command that *starts* with a GTFOBins binary is roughly eleven times more likely to be labelled benign, because `awk`, `find` and `tar` are overwhelmingly used as intended. `has_enum_bin` inverts too (2.50 / 0.67), and `whoami`/`id` are byte-identical across classes. Only argument structure remains — the quoted payload lifts `n_quotes`, `special_ratio` and `max_token_len`, and `head_is_lotl` is still top-four by gain on both corpora (0.045 / 0.066) because it reads *position*, not identity. |
| **Command obfuscation** (T1027.010) — functionality preserved while the lexical signature is destroyed, by encoding a payload into a decoder, splicing keywords (`c"u"rl`) or rebuilding separators through `$IFS`. | Shell command log: `auditd` EXECVE argv, Sysmon Event ID 1, or Cowrie `cowrie.command.input`. | Long unbroken `[A-Za-z0-9+/=]` runs; `\x41`-style escapes; `base64 -d` or `xxd -r` next to a pipe and an interpreter; `${IFS}` in argument position. | `has_base64_blob`, `b64_run_len`, `has_hex_escape`, `has_decode_exec`, `has_quote_splice`, `has_ifs_expansion` | **Sharp, rare and corpus-dependent.** Obfuscation is the one adversarial behaviour that *adds* signal, because the evasion is itself anomalous: no benign workflow splices a binary name or routes arguments through `$IFS`. Hence `has_decode_exec` at OR 45.1 and `has_quote_splice` at 27.0, each firing on well under 1% of rows — nothing for aggregate accuracy, everything for the cases that matter. Caveat: `has_decode_exec` inverts to OR 0.60 on the honeypot, where attackers type unencoded droppers because they are not evading anything. |
| **Local data staging** (T1074.001) — data archived and parked in a world-writable scratch directory before exfiltration, or a second stage landed and run from the same place. | Shell command log; Cowrie `cowrie.command.input` captures the staging chain whole. | `/tmp`, `/var/tmp` and `/dev/shm` as path prefixes, typically with `cd`, `tar`, `chmod +x` and a relative execution (`./x`). | `has_staging_dir`, with `n_abs_paths` and `has_hidden_path` as context | **Transfers, because the reason is structural rather than stylistic.** These are the directories guaranteed writable by an unprivileged account, and `/dev/shm` is memory-backed, so staging there avoids a disk write entirely. That necessity is why `has_staging_dir` keeps both sign and magnitude across corpora (OR 14.3 / 4.75) where style-derived features do not. It also shows why single features are insufficient: developers use `/tmp` constantly, so it earns weight only alongside a fetch binary, a `chmod` or an execution — the conjunction a tree ensemble represents and a keyword rule cannot. |
| **Credentials in files** (T1552.001) — credential material read straight off the filesystem with ordinary utilities, requiring no tooling and dropping no binary. | Shell command log; `auditd` EXECVE argv captures the target path as an argument token. | Absolute paths under `/etc`, `/proc`, `/var/log`, `/root`; dot-prefixed components (`~/.ssh/id_rsa`, `.aws/credentials`); the path count itself. | `n_abs_paths`, `n_sensitive_paths`, `has_hidden_path`, `has_home_ref` | **The strongest row by effect size.** The behaviour is expressed through what is *named*, not what is run. `n_abs_paths` is the strongest single feature in the project — d +0.45, AUC 0.73, solo-rule F1 0.595 against the 0.40 floor, top Random Forest Gini 0.124 — because reaching for absolute paths is characteristic of an operator working somewhere unfamiliar. `n_sensitive_paths` is a deliberate lumped count: `n_cred_paths`, `n_proc_paths` and `n_log_paths` each failed the gate individually. `has_home_ref` is the documented counter-example, inverting from 2.02 to 0.38 where `~` is a real user's ordinary vocabulary. |
| **Privilege escalation via sudo** (T1548.003) — elevation to root through the host's own mechanism, including cached credentials and permissive `sudoers` entries. | Shell command log; `auditd` EXECVE records the attempt whether or not it succeeded. | The **first token** after assignment-prefix stripping — `sudo`, `su`, `doas`, `pkexec` in head position, as distinct from anywhere in the line. | `head_is_privesc` — and nothing else | **Deliberately the thinnest row; the evidence forced it.** The obvious feature, a presence flag `has_privesc_bin`, was built, measured and **killed** at OR 0.99 / 1.01 — almost perfectly class-neutral, because `sudo` is simply everywhere, in offensive references and administrator history alike. Only *position* survives: a command whose head is the elevation binary is an escalation attempt, whereas one that merely mentions it is usually documentation. Even that inverts across corpora (OR 0.77 / 3.70), Dataset 1's benign sources being full of `sudo`-prefixed tutorial commands. |

**Takeaway — detectability tracks lexical distinguishability, not danger.**
Reverse shells carry unforgeable syntax and are caught perfectly; download
cradles hide a real signal behind a URL/IP artefact that is genuine in-domain and
non-transferable; discovery and trusted-binary abuse have no content signature at
all, and the family the project is named after carries one that points the *wrong
way*. That last result is the sharpest evidence these labels are handled
honestly — a pipeline quietly memorising "attack style" would not surface a
finding so inconvenient. Across all seven rows the features that behave most
consistently are structural (`has_pipe_to_shell`, `has_staging_dir`,
`has_dev_tcp`), while those naming *what program ran* behave worst. A detector
reporting high aggregate accuracy is therefore strong on the first class, brittle
on the second and effectively blind on the third — a distinction aggregate F1
hides and per-technique mapping makes explicit.

## 1.3 Theoretical feature rationale — 43 features in eight families

The set answers one question: **what, in a command string, distinguishes
adversarial intent from ordinary administration when the program being run is
legitimate in both cases?** Sixty-eight candidates were proposed from the threat
model above, then reduced to 43 by a selection gate applied identically to both
corpora (Table B.3). Two commitments run through every family. First, **no single
feature is expected to separate the classes**: on Dataset 1 only three of the 43
clear the 0.40 do-nothing floor as a solo rule (`n_abs_paths` 0.595,
`digit_ratio` 0.434, `special_ratio` 0.411), and on Dataset 2 **not one does** —
the most compact statement available of how much harder the honeypot corpus is.
The set is built for conjunctions, which a tree ensemble or a CNN can represent
and a keyword rule cannot. Second, **the `source` column is never a model
input**, so no feature may proxy for collection provenance; where one turned out
to, it is flagged rather than quietly dropped.

**Table 1.2 — The eight feature families, the security premise each was designed
from, and what measurement returned.** Premises were fixed from the threat model
before the evidence was gathered, so a family whose premise failed is reported as
a finding; per-feature evidence for all 68 candidates ships as
`report/ch3_feature_decisions.md`.

<!-- cols: 1.55 4.95 -->

| Family and features | Design premise → what the measurement returned |
|---|---|
| **Shape and size (4)** — `len_chars`, `len_tokens`, `mean_token_len`, `max_token_len` | Attack one-liners are compressed, because the operator has one shot through an injection primitive and must chain fetch, permission change and execution into a single line; long individual tokens are a second signal (URLs, blobs, paths). **The premise holds on the curated corpus (`len_chars` d +0.25) and inverts on the honeypot (−0.17)**, where attacker input at a Cowrie prompt is terse recon while real user history is verbose. All four sit at the 0.40 floor on solo F1 and only `mean_token_len` keeps its sign on both. Retained as cheap split variables, and the primary exhibit for §5.2's distribution shift. |
| **Structure and chaining (4)** — `n_pipes`, `n_redirect_out`, `has_stderr_merge`, `n_quotes` | Composition depth tracks payload complexity: a reverse shell stacks redirections at a level ordinary commands rarely reach, and `2>&1` merging is characteristic of a shell attached to a socket rather than a terminal. `has_stderr_merge` bears that out at OR 28.7, and is why `n_redirect_out` alone is insufficient — the extractor strips `>&` and `2>&1` before counting, so the two are complementary. The instructive failure is **`n_pipes`, which leans benign on both corpora (d −0.17 / −0.11)**: piping is the core idiom of Unix administration, and being reliably wrong in a known direction is still useful to a model. |
| **Network and delivery (4)** — `has_ipv4`, `has_private_ip`, `has_url`, `has_dev_tcp` | A LotL attack must eventually name somewhere to fetch from or call back to, and that endpoint has to appear literally in the string. `has_dev_tcp` is the purest signal in the set (OR 559); the others are progressively more dual-use, `has_url` (2.70 / 6.50) genuinely ambiguous because documentation corpora are full of URLs. `has_ipv4` is the designated shortcut hazard and was **kept deliberately rather than removed**: its Dataset 2 odds ratio of 5.00 is earned on a corpus containing no `quasarnix` at all, so the signal is real even where the Dataset 1 measurement is contaminated. Hiding the feature would have hidden the problem. |
| **Binary families (6)** — `has_fetch_bin`, `has_shell_bin`, `has_interp_bin`, `has_lotl_bin`, `has_enum_bin`, `has_evasion_tok` | Fixed, threat-mapped lists chosen before seeing data, so they cannot memorise corpus vocabulary the way a learned bag-of-words does; each answers *which class of program* is involved. `has_fetch_bin` is the strongest and most transferable member (OR 5.56 / 7.96). The family also carries the project's central negative result: **`has_lotl_bin` is a benign indicator on both corpora (0.62 / 0.50) and `has_enum_bin` inverts outright (2.50 / 0.67)**. Naming a program is weak evidence about intent — precisely what justifies the two families below. |
| **Head and arguments (6)** — `head_is_shell`, `head_is_interp`, `head_is_lotl`, `head_is_privesc`, `n_flags`, `has_long_flag` | If presence is weak, *position* should be stronger: a command whose first token is a shell is being invoked as one, whereas a command that merely mentions `bash` may be documentation. Heads are read after stripping variable-assignment prefixes, so `FOO=1 bash -i` parses correctly. The gain is real — **`head_is_shell` reaches OR 47.9 / 13.6 against `has_shell_bin`'s 32.8 / 5.99 on the same rows** — and it is what rescued the sudo row in §1.2. The flag features capture invocation style: administrators write readable long options, scripted payloads do not, so `has_long_flag` drops to OR 0.08 on the honeypot. |
| **Execution micro-structure (8)** — `has_pipe_to_shell`, `has_fetch_exec_chain`, `has_decode_exec`, `has_ifs_expansion`, `has_heredoc`, `has_dev_null`, `has_shell_flag_i`, `has_exec_flag` | The family that most directly encodes the conjunction argument: rather than leave the model to discover that *fetch tool* ∧ *pipe* ∧ *interpreter* is the download-cradle signature, the extractor computes it as `has_fetch_exec_chain` (OR 45.1 / 9.03), and `has_pipe_to_shell` for any pipe terminating in an interpreter. These are deliberately rare — most fire on well under 1% of rows and add nothing to aggregate accuracy — and kept for exactly that reason, being near-conclusive when they do fire. **`has_pipe_to_shell` is the most transferable feature in the project (OR 8.65 / 8.68)**, strong evidence that behaviour rather than a corpus artefact is being measured. |
| **Paths and filesystem (5)** — `n_abs_paths`, `has_hidden_path`, `has_staging_dir`, `has_home_ref`, `n_sensitive_paths` | What a command *names* proves more informative than what it runs. **`n_abs_paths` is the strongest single feature in the set** (d +0.45, AUC 0.73, top Random Forest Gini 0.124), on the reasoning that absolute paths indicate an operator working without a familiar working directory or shell history. `has_staging_dir` encodes the structural necessity behind `/tmp` and `/dev/shm` and keeps sign and magnitude across corpora (14.3 / 4.75); `n_sensitive_paths` is a lumped count recovering three counters that each failed the gate alone; `has_home_ref` is retained as a documented counter-example, inverting from 2.02 to 0.38. |
| **Obfuscation (6)** — `has_base64_blob`, `b64_run_len`, `has_hex_escape`, `has_quote_splice`, `digit_ratio`, `special_ratio` | Obfuscation is the only adversarial behaviour that *adds* signal, so the family pairs sparse near-categorical flags with dense continuous ratios to cover both blatant and subtle cases: `has_quote_splice` at OR 27.0 is rare and sharp, while `special_ratio` (d +0.32, the second-largest effect on Dataset 1) fires on every row. **Encoding artefacts, unlike vocabulary, survive a change of corpus** — `digit_ratio` is the most stable continuous feature in the project (+0.24 / +0.23) and `has_hex_escape` the most stable binary one (22.3 / 11.7). `b64_run_len` supplements the flag with magnitude, a long unbroken run being far more indicative than an incidental base64-shaped token. |

**What the rejections contribute.** The 25 killed candidates are part of the
argument, not noise, and three patterns recur: features that were *redundant*
(`char_entropy` and `token_entropy`, dropped for `len_chars` and `len_tokens`);
features that were *class-neutral despite strong intuition* (`has_privesc_bin`,
`nonprintable_ratio`); and features that were *too sparse individually but
recoverable when pooled* — the three themed path counters, which refute the
assumption that a split covers its lump. Reporting them makes the 43-feature set
a result rather than a starting assumption, and lets Chapter 4's ranking be read
as evidence rather than as confirmation of the choices made here. The full funnel
is Table B.3.
