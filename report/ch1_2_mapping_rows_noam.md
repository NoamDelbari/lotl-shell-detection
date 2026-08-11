# Chapter 1.2 — Telemetry & Feature Mapping (Noam's 4 rows)

> Work split (WORK_DIVISION.md): Noam contributes rows N1–N4; Ben contributes
> B1–B3 (`ch1_telemetry_rows_ben.md`). Each row uses the assignment's mandated
> five-field structure. Every feature named below exists in `FEATURE_NAMES`
> (`src/features.py`); every effect size is quoted live from
> `report/ch3_feature_decisions.md` (train splits only). Every ATT&CK ID was
> confirmed against the live technique page, including its platform list.

### Row N1 — Command obfuscation (encoded and spliced payloads)

| Field | Content |
|---|---|
| **Adversarial behavioural characteristic** | Attacker preserves command functionality while destroying its lexical signature — base64- or hex-encoding the payload and piping it to a decoder, splicing keywords with quotes (`c"u"rl`), or rebuilding argument separators through `$IFS` — specifically to defeat string- and signature-matching detection (T1027.010 Command Obfuscation, sub-technique of T1027; platforms Linux, Windows, macOS). |
| **Required telemetry source** | Shell command log: Linux `auditd` `type=EXECVE` argv, Sysmon-for-Linux Event ID 1, or Cowrie `cowrie.command.input` for honeypot capture. |
| **Specific log attributes / raw fields** | The raw `command` string. Concretely: long unbroken `[A-Za-z0-9+/=]` runs; `\x41`-style escapes; `base64 -d`/`openssl enc`/`xxd -r` adjacent to a `\|` and an interpreter; `${IFS}` in argument position; quote characters interrupting a binary name. |
| **Derived / engineered feature(s)** | `has_base64_blob`, `b64_run_len`, `has_hex_escape`, `has_decode_exec`, `has_quote_splice`, `has_ifs_expansion`, supported by the two density ratios `special_ratio` and `digit_ratio`. |
| **Detailed explanation** | Obfuscation is the one adversarial behaviour that *adds* rather than removes signal, because the evasion itself is anomalous: benign administration has no reason to splice a binary name or route arguments through `$IFS`. The micro-structural features are accordingly sharp but rare — `has_decode_exec` at OR 45.1 and `has_quote_splice` at OR 27.0 on Dataset 1, each firing on well under 1% of rows. Rarity is the point: they contribute nothing to aggregate accuracy and everything to the cases that matter, which is why they are kept despite near-zero solo F1. The two ratio features are the dense counterpart, capturing the same phenomenon continuously — `special_ratio` is the second-strongest feature in the whole set by effect size on Dataset 1 (d +0.32, AUC 0.66). The honest caveat is that this family is Dataset-1-heavy: `has_decode_exec` inverts to OR 0.60 on the honeypot corpus, where attackers type unencoded droppers because they are not evading anything. |

### Row N2 — Privilege escalation via sudo

| Field | Content |
|---|---|
| **Adversarial behavioural characteristic** | Attacker elevates from an unprivileged foothold to root using the host's own elevation mechanism, invoking `sudo`/`su` directly or exploiting cached credentials and permissive `sudoers` entries (T1548.003 Sudo and Sudo Caching; platforms Linux, macOS). |
| **Required telemetry source** | Shell command log as above; `auditd` EXECVE is the authoritative source because it records the escalation attempt whether or not it succeeded. |
| **Specific log attributes / raw fields** | The `command` string, and specifically its **first token** after assignment-prefix stripping — `sudo`, `su`, `doas`, `pkexec` in head position, as distinct from the same tokens appearing anywhere in the line. |
| **Derived / engineered feature(s)** | `head_is_privesc` — and nothing else. |
| **Detailed explanation** | This row is deliberately the thinnest, because the evidence forced it. The obvious feature, a presence flag `has_privesc_bin`, was built, measured and **killed**: at OR 0.99 (Dataset 1) and 1.01 (Dataset 2) it is almost perfectly class-neutral. `sudo` and `chmod` are simply everywhere, in attack corpora and administrator history alike, so presence carries no information. What survives is *position*: a command whose head is the elevation binary is an escalation attempt, whereas one that merely mentions it is usually documentation or a compound administrative line. Even then the feature is corpus-dependent and inverts — OR 0.77 on Dataset 1 versus 3.70 on Dataset 2 — because the curated Dataset 1 benign sources are full of `sudo`-prefixed tutorial commands while the honeypot's benign side is real user history. Reported as-is rather than smoothed over: it is a case where the technique is real, security-critical, and only weakly separable from ordinary administration by content alone. |

### Row N3 — Credential harvesting from files

| Field | Content |
|---|---|
| **Adversarial behavioural characteristic** | Attacker reads credential material straight off the filesystem — `/etc/shadow`, SSH private keys, cloud and application config — using ordinary file-reading utilities, requiring no tooling and leaving no dropped binary (T1552.001 Credentials In Files; platforms Containers, IaaS, Linux, Windows, macOS). |
| **Required telemetry source** | Shell command log; `auditd` EXECVE argv captures the target path as an argument token. |
| **Specific log attributes / raw fields** | The `command` string: absolute paths under `/etc`, `/proc`, `/var/log`, `/root`; dot-prefixed path components (`~/.ssh/id_rsa`, `.aws/credentials`, `.bash_history`); and the path count itself. |
| **Derived / engineered feature(s)** | `n_sensitive_paths`, `n_abs_paths`, `has_hidden_path`, `has_home_ref`. |
| **Detailed explanation** | The behaviour is expressed almost entirely through *what is named*, not what is run, which makes the path features the natural encoding. `n_abs_paths` is the single strongest feature in the project on Dataset 1 — d +0.45, AUC 0.73, solo-rule F1 0.595 against a 0.40 do-nothing floor, and the top Random Forest Gini importance at 0.124 — because reaching for absolute paths is characteristic of an operator working somewhere unfamiliar rather than in their own working directory. `n_sensitive_paths` is deliberately a **lumped count**: the finer-grained `n_cred_paths`, `n_proc_paths` and `n_log_paths` were each built and killed for failing the selection gate individually, and pooling them recovers a feature that passes on both corpora (d +0.18 / +0.06). `has_hidden_path` is the most transferable member of the group, holding at OR 4.36 and 3.99 across two corpora that agree on very little. `has_home_ref` is the counter-example and is reported as such — OR 2.02 on Dataset 1 but 0.38 on Dataset 2, where `~` references are the ordinary vocabulary of a real user's shell history. |

### Row N4 — Local staging before exfiltration

| Field | Content |
|---|---|
| **Adversarial behavioural characteristic** | Attacker collects, archives and parks data in a world-writable scratch directory prior to exfiltration, or uses the same directories to land and execute a second-stage payload (T1074.001 Local Data Staging; platforms ESXi, Linux, Windows, macOS). |
| **Required telemetry source** | Shell command log; Cowrie `cowrie.command.input` is the richest source here, since dropper chains are logged whole as a single attacker input line. |
| **Specific log attributes / raw fields** | The `command` string: `/tmp`, `/var/tmp`, `/dev/shm` as path prefixes, typically alongside `cd`, `tar`/`zip`, `chmod +x`, and a subsequent relative execution (`./x`). |
| **Derived / engineered feature(s)** | `has_staging_dir`, with `n_abs_paths` and `has_hidden_path` as supporting context. |
| **Detailed explanation** | `/tmp` and `/dev/shm` are chosen by attackers for a structural reason rather than a stylistic one: they are the directories guaranteed to be writable by an unprivileged account, and `/dev/shm` is memory-backed, so staging there avoids a disk write entirely. That structural necessity is why the feature transfers — `has_staging_dir` holds at OR 14.3 on Dataset 1 and 4.75 on Dataset 2, one of the few strong signals that keeps both its sign and its magnitude across corpora. It is also the clearest illustration of why single features are insufficient: developers legitimately use `/tmp` constantly, so the feature earns its weight only in conjunction with a fetch binary, a `chmod`, or an execution — which is precisely the conjunction a tree ensemble can represent and a keyword rule cannot. |

---

**Closing observation — the namesake signal points the wrong way.** Across these
four rows and Ben's three, the features that behave most consistently are
structural (`has_staging_dir`, `has_hidden_path`, `has_dev_tcp`), while the
features naming *what program ran* behave worst. The extreme case is the family
the project is named after: `has_lotl_bin` carries OR **0.62** on Dataset 1 and
**0.50** on Dataset 2, and the positional `head_is_lotl` reaches OR **0.09** on
Dataset 2 — meaning a command that *starts* with a GTFOBins-catalogued binary is
roughly eleven times more likely to be labelled benign than malicious. This is
not a modelling failure; it is the correct empirical answer to a provenance-
labelled question. `awk`, `find`, `tar` and `env` are overwhelmingly used for
their intended purpose, so under labels inherited from collection context their
presence is evidence of ordinary administration. It sharpens Ben's T1033
conclusion: some behaviours have no content signature, and some have one that
points in the wrong direction. Detection of LotL abuse therefore cannot rest on
recognising the binary, only on the argument structure wrapped around it — which
is the design premise of the feature set set out in Section 1.3.
