"""
features.py -- engineered feature extractor over raw command text.

OWNERSHIP NOTE (docs/WORK_DIVISION.md): `featurize()` is Noam's deliverable
(Ch3, due Aug 8) and is the shared contract every downstream module depends on.
This file ships a *provisional* implementation so Ben's skeleton, EDA, feature
ranking, and models can run end-to-end before Aug 8. When Noam's version lands,
it must keep the same signature and the same "one row in -> fixed-width numeric
vector out" contract; nothing else in the pipeline should need to change.

Design rules (kept stable so the contract holds):
  * Input is the raw command string only. No dataset identity, no source tag.
  * Output is a fixed, ordered, purely numeric vector -- same columns for every
    command, every dataset. FEATURE_NAMES is the authoritative order.
  * Every feature maps to a behavioural characteristic in the proposal's
    threat->telemetry table (reverse shell, download-exec, LotL-binary abuse,
    encoded execution, enumeration, privesc/persistence, defense evasion). This
    is what lets Ch3/Ch4 argue "domain intuition" against the tree ranking.
  * NO lexical label leakage: features describe structure and behaviour, not a
    keyword whose presence *defines* the label (see DATA_CARD -- the label is
    provenance-based; a feature that re-derives a selection keyword would be a
    shortcut, not a detector).

`featurize(commands)` accepts an iterable of strings and returns a pandas
DataFrame with columns == FEATURE_NAMES, index aligned to the input order.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np
import pandas as pd

# --- token vocabularies grounded in the threat model (proposal section 3) -----
# These are behavioural markers, not the (retired) selection regex. They are
# intentionally broad tradecraft categories; the model decides their weight.
_FETCH_BINS = ("curl", "wget", "fetch", "tftp", "scp", "ftpget", "nc", "ncat",
               "socat")
_SHELL_BINS = ("bash", "sh", "zsh", "dash", "ksh", "ash")
_INTERP_BINS = ("python", "python2", "python3", "perl", "ruby", "php", "lua",
                "node")
# GTFOBins-style trusted binaries abused for shell escapes / file reads
_LOTL_BINS = ("awk", "gawk", "find", "vim", "vi", "nmap", "tar", "zip", "tee",
              "sed", "ed", "expect", "env", "xargs", "man", "less", "more",
              "busybox", "gdb", "make", "lua", "base32")
_ENUM_BINS = ("whoami", "id", "uname", "hostname", "ifconfig", "ip", "ss",
              "netstat", "ps", "who", "w", "last", "lscpu", "lsb_release",
              "arch", "groups")
_PRIVESC_BINS = ("sudo", "su", "chmod", "chown", "chattr", "setcap", "crontab",
                 "systemctl", "service", "usermod", "useradd", "passwd",
                 "visudo", "doas")
_EVASION_TOK = ("history", "histfile", "unset", "shred", "wipe", "truncate",
                "chattr", "> /var/log", ">/var/log", "rm -rf", "kill -9")
_SENSITIVE_PATHS = ("/etc/passwd", "/etc/shadow", "/etc/sudoers", "/root/",
                    "/.ssh", "authorized_keys", "id_rsa", "/proc/", "/dev/tcp",
                    "/dev/udp", "/tmp/", "/var/log", "crontab", "/etc/cron")

_WORD_RE = re.compile(r"[A-Za-z0-9_./-]+")
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_URL_RE = re.compile(r"https?://|ftp://|www\.")
_B64_RE = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
_HEX_RE = re.compile(r"\\x[0-9a-fA-F]{2}|0x[0-9a-fA-F]{6,}")


def _shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _count_any(low: str, needles) -> int:
    return sum(low.count(n) for n in needles)


def _has_any_token(tokens: set, names) -> int:
    return int(any(n in tokens for n in names))


# Authoritative column order. Keep in sync with _features_for_one().
FEATURE_NAMES = [
    # --- shape / size ---
    "len_chars",
    "len_tokens",
    "token_entropy",          # entropy over whitespace tokens
    "char_entropy",           # entropy over characters (encoded blobs raise it)
    "mean_token_len",
    "max_token_len",
    # --- structure / chaining ---
    "n_pipes",                # | -- fetch|shell staging
    "n_redirects",            # > < >> -- log truncation, /dev/tcp
    "n_semicolons",           # ; -- command chaining / enumeration bursts
    "n_and_or",               # && ||
    "n_backticks_subshell",   # ` and $( ) -- inline execution
    "n_quotes",
    "n_parens",
    "n_braces",
    # --- network / delivery ---
    "has_ipv4",
    "n_ipv4",
    "has_url",
    "has_dev_tcp",            # /dev/tcp|/dev/udp -- bash reverse shell
    "n_ports",                # :<port> style
    # --- behavioural binary families (proposal section 3 table) ---
    "has_fetch_bin",
    "has_shell_bin",
    "has_interp_bin",
    "has_lotl_bin",
    "has_enum_bin",
    "n_enum_bins",            # enumeration burst = several at once
    "has_privesc_bin",
    "has_evasion_tok",
    # --- obfuscation / encoding ---
    "has_base64_blob",
    "b64_run_len",            # longest base64-ish run
    "has_hex_escape",
    "has_eval",
    "nonprintable_ratio",
    "digit_ratio",
    "special_ratio",         # non-alnum, non-space
    # --- sensitive targets ---
    "n_sensitive_paths",
    "has_shell_flag_i",       # ' -i ' interactive shell
    "has_exec_flag",          # -e / -c exec style
]


def _features_for_one(cmd: str) -> list:
    s = cmd
    low = s.lower()
    tokens = _WORD_RE.findall(low)
    token_set = set(tokens)
    n_chars = len(s)
    n_tokens = len(tokens)

    tok_lens = [len(t) for t in tokens] or [0]
    # token entropy: distribution over distinct tokens
    if tokens:
        tc = Counter(tokens)
        tok_entropy = -sum((c / n_tokens) * math.log2(c / n_tokens)
                           for c in tc.values())
    else:
        tok_entropy = 0.0

    n_ipv4 = len(_IPV4_RE.findall(s))
    b64_runs = _B64_RE.findall(s)
    b64_run_len = max((len(b) for b in b64_runs), default=0)
    nonprintable = sum(1 for ch in s if ord(ch) < 32 or ord(ch) > 126)
    digits = sum(ch.isdigit() for ch in s)
    specials = sum((not ch.isalnum()) and (not ch.isspace()) for ch in s)
    n_ports = len(re.findall(r":\d{2,5}\b", s))
    n_enum = sum(1 for b in _ENUM_BINS if b in token_set)

    return [
        n_chars,
        n_tokens,
        round(tok_entropy, 6),
        round(_shannon_entropy(s), 6),
        round(float(np.mean(tok_lens)), 6),
        max(tok_lens),
        low.count("|"),
        s.count(">") + s.count("<"),
        s.count(";"),
        low.count("&&") + low.count("||"),
        s.count("`") + s.count("$("),
        s.count('"') + s.count("'"),
        s.count("(") + s.count(")"),
        s.count("{") + s.count("}"),
        int(n_ipv4 > 0),
        n_ipv4,
        int(bool(_URL_RE.search(low))),
        int("/dev/tcp" in low or "/dev/udp" in low),
        n_ports,
        _has_any_token(token_set, _FETCH_BINS),
        _has_any_token(token_set, _SHELL_BINS),
        _has_any_token(token_set, _INTERP_BINS),
        _has_any_token(token_set, _LOTL_BINS),
        int(n_enum > 0),
        n_enum,
        _has_any_token(token_set, _PRIVESC_BINS),
        int(_count_any(low, _EVASION_TOK) > 0),
        int(b64_run_len >= 20),
        b64_run_len,
        int(bool(_HEX_RE.search(s))),
        int("eval" in token_set),
        round(nonprintable / n_chars, 6) if n_chars else 0.0,
        round(digits / n_chars, 6) if n_chars else 0.0,
        round(specials / n_chars, 6) if n_chars else 0.0,
        _count_any(low, _SENSITIVE_PATHS),
        int(bool(re.search(r"(?:^|\s)-\w*i", low)) and
            _has_any_token(token_set, _SHELL_BINS)),
        int(bool(re.search(r"(?:^|\s)-\w*[ec]\b", low))),
    ]


def featurize(commands) -> pd.DataFrame:
    """Map raw command strings to the fixed engineered feature matrix.

    Parameters
    ----------
    commands : iterable; each element is coerced via str(). Empty or
        whitespace-only commands produce an all-zero row.

    Returns
    -------
    pandas.DataFrame with columns == FEATURE_NAMES (numeric, one row per input).
    """
    rows = []
    for cmd in commands:
        s = str(cmd)
        if not s.strip():
            rows.append([0] * len(FEATURE_NAMES))
        else:
            rows.append(_features_for_one(s))
    frame = pd.DataFrame(rows, columns=FEATURE_NAMES)
    # sanity: contract is purely numeric, no NaN/inf leaking downstream
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("featurize produced non-finite values")
    return frame
