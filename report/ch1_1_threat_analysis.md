# Chapter 1.1 — Deep-Dive Threat Analysis

> Scope (WORK_DIVISION.md): Noam writes 1.1 and four mapping rows; Ben
> contributes three rows (`ch1_telemetry_rows_ben.md`) and the detectability
> argument in `ch1_threat_mapping.md`. Numbers cited here are live, from
> `report/ch3_feature_decisions.md` and `results/ch3_feature_audit.json`.

## The technique

MITRE ATT&CK catalogues **T1059.004 — Command and Scripting Interpreter: Unix
Shell** under the Execution tactic (TA0002). It covers adversary use of `sh`,
`bash`, `dash` and their relatives to run commands on a compromised host. It is
not an exotic capability: the shell is the standard administrative interface to
every Unix-family system, which is precisely what makes its abuse difficult to
separate from its use.

The technique is the execution primitive that the rest of an intrusion is built
on. An adversary who has achieved command injection through any initial-access
route — a web application flaw, a stolen SSH credential, an exposed service —
converts that foothold into arbitrary execution through the shell, and then
chains onward: ingress tool transfer (T1105), discovery (T1033, T1083),
credential access (T1552.001), persistence, lateral movement. Detection at the
shell layer is therefore leverage: it sits at the narrow waist that most
subsequent behaviour must pass through.

## Why "living off the land" defeats file-based detection

The defining property of a Living-off-the-Land attack is that **no attacker
binary is introduced**. At the OS layer, execution proceeds through the ordinary
`fork(2)`/`execve(2)` path against a binary that is already on the host:
`/bin/bash`, `/usr/bin/curl`, `/usr/bin/awk`. That binary arrived through the
distribution's package manager, matches its vendor hash, sits at its expected
path with its expected permissions, and — where signature enforcement exists —
is signed. From the kernel's point of view nothing anomalous has occurred.

This dismantles the file-centric detection stack by construction, not by
evasion. Hash blocklists have no novel hash to match. Static scanners and YARA
rules have no dropped file to inspect. Application allow-listing by path or
publisher passes the binary because it genuinely is the legitimate binary.
Integrity monitoring reports no change, because nothing changed. Each of these
controls answers the question *is this program trustworthy?* — and for a LotL
attack the honest answer is yes.

What differs between the attacker's invocation and the administrator's is not
the program but **the instruction given to it**. `curl` fetching a release
tarball and `curl` streaming a dropper into `sh` are the same executable, the
same syscalls, the same file on disk; they differ only in argv. Detection must
therefore move from the binary to the command.

## Why the command string is the right telemetry

The command string is the finest-grained artefact that still carries intent. It
is also routinely available: Linux `auditd` records full argv in `type=EXECVE`,
Sysmon-for-Linux Event ID 1 carries the command line, shell history files
capture interactive sessions, and Cowrie honeypots log attacker input verbatim
as `cowrie.command.input`. No new agent or kernel module is required, and the
representation is uniform across collection methods — which is what allows the
two corpora in this project to be harmonised at all (Chapter 5).

It is also where the signal actually lives. `/dev/tcp/<host>/<port>` is a bash
built-in redirect with essentially no legitimate interactive use, and it behaves
accordingly in our data: an odds ratio of **559.4** on Dataset 1. That kind of
near-categorical evidence exists only at the string level. The binary name alone
carries none of it.

## The provenance-labeling premise, and what it costs

No corpus of shell commands carries per-command intent labels, because intent is
not observable in the artefact — it is a property of the operator. This project,
like the published work it builds on, therefore inherits each label from **where
the command was collected**: offensive references and honeypot capture are
labelled malicious, documentation and user-history corpora benign.

This premise must be stated plainly because it bounds every result that follows.
A classifier can satisfy a provenance-labelled objective by learning corpus
*style* rather than adversarial intent, and we measure three distinct forms of
that failure rather than assume them away:

1. **Unlearnable overlap.** Commands that are byte-identical across classes —
   `whoami`, `id`, `uname -a` — carry no content signal whatever. They can only
   be "detected" by memorising the company they keep.
2. **Source fingerprints.** A feature that saturates one source becomes a proxy
   for that source. `has_ipv4` fires on **100%** of `quasarnix` rows in Dataset 1
   and is flagged `P8-source-fingerprint` for exactly this reason.
3. **Non-transfer.** Style-derived signal does not survive a change of corpus,
   so a model can score well in-distribution and still have learned nothing
   about the technique.

The mitigation is design rather than optimism, and it has to be described
precisely, because the split protects against one failure and not the other. The
in-distribution split is **grouped by command shape**: commands are reduced to a
structural skeleton with literals, blobs and scratch-path filenames blanked, and
a whole shape group is assigned to one side. Verified on the current build, zero
shape groups straddle either split, under either label. That is stronger than
deduplication — not only does no command string appear on both sides (measured
overlap: zero), no structural near-duplicate does either, so per-source recall
cannot be recall on a variant already seen in training.

What the split is *not* grouped by is **source**. All eleven Dataset 1 sources
and all three Dataset 2 sources appear on both sides of their own split, by
design: a same-source test set cannot detect a model that has learned corpus
style rather than adversarial intent, because style is present on both sides of
it. What can is the second corpus. Dataset 1 and Dataset 2 share no source at all, so the
cross-dataset transfer evaluation in Chapter 8.2 is the honest generalisation
test, and in-distribution accuracy is treated as an upper bound rather than a
result. Around that sit a selection gate applied identically to both corpora and
a do-nothing floor of **0.40** (the F1 of predicting "attack" for everything at
25% prevalence) that any candidate feature must beat.

That discipline is measurable. The literal-IPv4 shortcut — the most obvious
available cheat — scores a solo-rule F1 of **0.141** (Dataset 1) and **0.105**
(Dataset 2), *below* the do-nothing floor, at ROC-AUC 0.535 / 0.523. And the
sharpest evidence that provenance labels are being handled honestly is that the
project's own namesake points the wrong way: `has_lotl_bin`, the presence of a
GTFOBins-style trusted binary, is a **negative** predictor on both corpora
(OR 0.62 and 0.50). A pipeline quietly memorising "attack style" would not
surface a result that inconvenient. Section 1.2 maps four adversarial behaviours
onto the features that carry them, and Section 1.3 gives the semantic rationale
for the full 43-feature set.
