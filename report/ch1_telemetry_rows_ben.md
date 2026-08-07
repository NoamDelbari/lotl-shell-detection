# Chapter 1.2 — Telemetry & Feature Mapping (Ben's 3 rows)

> Work split (WORK_DIVISION.md): Noam writes 1.1 deep-dive + 4 mapping rows;
> Ben contributes these 3 rows. Each row follows the assignment's mandated
> 5-field structure and maps to concrete features implemented in
> `src/features.py`, so Ch3's empirical justification and Ch4's ranking can be
> traced straight back to a behaviour here.

### Row B1 — Download-and-execute (fileless staging)

| Field | Content |
|---|---|
| **Adversarial behavioural characteristic** | Attacker pulls a next-stage payload from attacker-controlled infrastructure and pipes it straight into an interpreter, so nothing touches disk for a file scanner to catch (MITRE T1105 Ingress Tool Transfer + T1059.004). |
| **Required telemetry source** | Linux auditd `type=EXECVE` (full argv); equivalently Sysmon-for-Linux Event ID 1. |
| **Specific log attributes / raw fields** | `a0..aN` argv tokens of the EXECVE record: the fetch binary (`curl`,`wget`,`nc`,`tftp`), the attacker URL/host or raw IPv4 in argv, and the `\|` byte joining it to `sh`/`bash`. |
| **Derived / engineered feature(s)** | `has_fetch_bin`, `has_url`, `has_ipv4`/`n_ipv4`, `n_pipes`, `has_shell_bin` (co-occurrence of a fetch tool + a pipe + a shell is the signature). |
| **Explanation** | Benign use of `curl`/`wget` overwhelmingly *saves* a file (`-o file`) or prints it; the malicious idiom instead *streams to an interpreter*. No single token is malicious — `curl` is ubiquitous — so the feature that matters is the **conjunction** fetch-tool ∧ pipe ∧ shell, plus the presence of a raw network endpoint in argv. This is why we encode each as a separate boolean the tree/CNN can AND together rather than a single keyword. |

### Row B2 — Reverse / bind shell (interactive foothold)

| Field | Content |
|---|---|
| **Adversarial behavioural characteristic** | Attacker spawns an interactive shell that either beacons out to C2 (reverse) or listens for inbound (bind), the primary post-exploitation foothold (T1059.004, relates to C2 T1071). |
| **Required telemetry source** | auditd `EXECVE` (+ `SYSCALL` for the parent process); Sysmon-for-Linux Event ID 1 for parent-image context. |
| **Specific log attributes / raw fields** | argv containing the bash `/dev/tcp/<ip>/<port>` or `/dev/udp` redirect, the interactive flag `-i`, exec flags `-e`/`-c` (`nc -e /bin/sh`, `bash -c`), and stream-duplication redirects (`>&`, `0<&1`). |
| **Derived / engineered feature(s)** | `has_dev_tcp`, `has_shell_flag_i`, `has_exec_flag`, `n_redirects`, `n_ports`, `has_shell_bin`/`has_interp_bin`. |
| **Explanation** | `/dev/tcp` has essentially no legitimate interactive use — its appearance is a near-categorical malicious signal, captured by `has_dev_tcp`. The interactive/exec flags and the redirect count separate a *shell being wired to a socket* from ordinary shell invocation. `n_redirects` is deliberately a count, not a boolean, because reverse shells stack several fd redirections (`0<&196;exec 196<>/dev/tcp/..;sh <&196 >&196`) — a level ordinary commands rarely reach, which the Ch3 effect size confirms (r ≈ +0.25). |

### Row B3 — LotL binary abuse / GTFOBins shell escape

| Field | Content |
|---|---|
| **Adversarial behavioural characteristic** | Attacker uses a trusted, allow-listed binary (`awk`,`find`,`vim`,`perl`,`tar`,`env`…) to spawn a shell, read protected files, or escalate — hiding the action behind a legitimate program (T1059.004 + defense-evasion via trusted binaries; catalogued by GTFOBins). |
| **Required telemetry source** | auditd `EXECVE`; the abnormal-parent signal (a service spawning a shell) additionally needs the `SYSCALL`/Sysmon parent-image field. |
| **Specific log attributes / raw fields** | argv of the trusted binary carrying its tell-tale escape argument: `awk 'BEGIN{system("/bin/sh")}'`, `find … -exec /bin/sh \;`, `vim -c ':!sh'`, and inline `$( )`/backtick subshells; reads of `/etc/passwd`, `/etc/shadow`, `~/.ssh`. |
| **Derived / engineered feature(s)** | `has_lotl_bin`, `n_backticks_subshell`, `n_sensitive_paths`, `special_ratio`, `char_entropy`. |
| **Explanation** | The binary itself is benign, so a name-only rule fails; maliciousness lives in the *argument structure* — a normal tool invoked with a shell-spawning payload. `has_lotl_bin` flags the trusted binary; `n_backticks_subshell` and the raised `special_ratio`/`char_entropy` capture the embedded shell/`system()` payload; `n_sensitive_paths` captures the protected targets these escapes typically read. Ch4's ranking places `has_lotl_bin` and `n_sensitive_paths` in the top consensus features on both datasets, confirming this behaviour carries real weight, not just intuition. |
