"""
ch3_feature_audit.py -- evidence + verdict scaffolding for every engineered
feature (Noam's Ch3 deliverable; Ch4 shortcut probes included).

Per feature x per dataset (TRAIN SPLITS ONLY, via src.ingestion):

  signal     class-conditional mean/median; Mann-Whitney U p; effect size --
             Cliff's delta for continuous features (identical to the
             rank-biserial 2U/(n1*n2)-1, computed from scipy's U in
             O(n log n)) or Haldane-corrected odds ratio for binary features;
             per-feature AUC = U/(n1*n2).
  shortcut   solo-rule F1 (predict attack iff value > 0) vs the do-nothing
             floor 2p/(1+p) -- the KNOWN_ISSUES P8 probe generalized to every
             feature; source concentration (share of feature-positive attack
             rows owned by a single source) AND max per-source positive rate
             (a source whose rows ~always fire a feature is fingerprinted by
             it -- the direction that catches QuasarNix/IPv4 in the current
             build, where the source is small but fully saturated);
             Spearman rho vs dataset 2's RETIRED P1 selection markers
             (echoing a retired marker is flagged, not disqualifying).
  redundancy Spearman clusters at |rho| > RHO_MAX (edges pooled across
             datasets); one representative per cluster proposed by mean
             |AUC - 0.5|.

Survival gate (spec default; adjustable jointly at verdict time):
  p < ALPHA AND (|delta| >= DELTA_MIN or OR >= OR_HI or OR <= OR_LO)
  on >= 1 dataset.

Verdicts emitted here are PROPOSED ONLY. Final KEEP/REDEFINE/KILL calls are
made jointly (course AI policy) and recorded in
report/ch3_feature_decisions.md.

!! DO NOT RE-RUN THIS SCRIPT TO "REFRESH" report/ch3_feature_decisions.md. !!
That file was finalised by hand after the 2026-08-08/09 joint verdict session:
the `final verdict` column carries Noam's per-feature rulings and the file
gained a "Killed candidates" section preserving the 25 dropped candidates from
the original 68-candidate run (git 4c6ad99). A regeneration resets every final
verdict to PENDING and deletes that section -- ~92 lines of decisions the
script cannot reconstruct. Re-run for results/ch3_feature_audit.json only, and
`git checkout -- report/ch3_feature_decisions.md` afterwards; edit the markdown
by hand.

Run: python analysis/ch3_feature_audit.py
Outputs: results/ch3_feature_audit.json
         report/ch3_feature_decisions.md  (SCAFFOLD ONLY -- see warning above)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import ingestion                              # noqa: E402
from src.features import FEATURE_NAMES, featurize      # noqa: E402

SEED = 42
ALPHA = 0.01          # significance gate
DELTA_MIN = 0.10      # |Cliff's delta| gate, continuous features
OR_HI = 1.5           # odds-ratio gate, binary features
OR_LO = 1.0 / 1.5
RHO_MAX = 0.90        # Spearman redundancy threshold
CONC_FLAG = 0.90      # source-concentration flag level
SOLO_F1_FLAG = 0.85   # solo-rule F1 flag level (old-build P8 IPv4 ~ 0.94)
SRC_SAT_FLAG = 0.95   # per-source positive-rate saturation flag level
BEN_RARE_FLAG = 0.05  # ...only suspicious if the feature is rare in benign
MARKER_RHO_FLAG = 0.50

RESULTS = ROOT / "results"
REPORT = ROOT / "report"

# Dataset 2's RETIRED P1 selection markers (docs/KNOWN_ISSUES.md). Labels are
# provenance-based now; correlation with these is a flag for Ch4, not a ban.
_RETIRED_MARKERS = ("wget", "curl", "chmod +x", "| sh", "/dev/tcp", "nc -e",
                    "bash -i", "authorized_keys", "crontab", "history -c",
                    "> /var/log", "rm -rf /")

# Family grouping for the report; must exactly cover FEATURE_NAMES.
FAMILIES = {
    "shape/size": (
        "len_chars", "len_tokens", "mean_token_len", "max_token_len"),
    "structure/chaining": (
        "n_pipes", "n_redirect_out", "has_stderr_merge", "n_quotes"),
    "network/delivery": (
        "has_ipv4", "has_private_ip", "has_url", "has_dev_tcp"),
    "binary families": (
        "has_fetch_bin", "has_shell_bin", "has_interp_bin", "has_lotl_bin",
        "has_enum_bin", "has_evasion_tok"),
    "A: head/args": (
        "head_is_shell", "head_is_interp", "head_is_lotl", "head_is_privesc",
        "n_flags", "has_long_flag"),
    "B: exec micro-structure": (
        "has_pipe_to_shell", "has_fetch_exec_chain", "has_decode_exec",
        "has_ifs_expansion", "has_heredoc", "has_dev_null",
        "has_shell_flag_i", "has_exec_flag"),
    "C: paths/filesystem": (
        "n_abs_paths", "has_hidden_path", "has_staging_dir", "has_home_ref",
        "n_sensitive_paths"),
    "D: obfuscation": (
        "has_base64_blob", "b64_run_len", "has_hex_escape", "digit_ratio",
        "special_ratio", "has_quote_splice"),
}
_FAMILY_OF = {f: fam for fam, fs in FAMILIES.items() for f in fs}
assert set(_FAMILY_OF) == set(FEATURE_NAMES), (
    "FAMILIES drifted from FEATURE_NAMES: "
    f"{set(_FAMILY_OF) ^ set(FEATURE_NAMES)}")


def is_binary(name: str) -> bool:
    return name.startswith(("has_", "head_is_"))


def cliffs_delta(mal: np.ndarray, ben: np.ndarray) -> tuple:
    """(delta, p, auc). delta = 2U/(n1 n2) - 1 (== rank-biserial ==
    Cliff's delta); auc = U/(n1 n2). Positive delta => larger for attacks."""
    n1, n2 = len(mal), len(ben)
    if n1 == 0 or n2 == 0:
        return 0.0, 1.0, 0.5
    U, p = mannwhitneyu(mal, ben, alternative="two-sided")
    auc = float(U) / (n1 * n2)
    return 2.0 * auc - 1.0, float(p), auc


def odds_ratio(mal: np.ndarray, ben: np.ndarray) -> float:
    """Haldane-Anscombe corrected OR of (value > 0) for attack vs benign."""
    a = float((mal > 0).sum()) + 0.5   # attack, positive
    b = float((mal == 0).sum()) + 0.5  # attack, negative
    c = float((ben > 0).sum()) + 0.5   # benign, positive
    d = float((ben == 0).sum()) + 0.5  # benign, negative
    return (a / b) / (c / d)


def _selftest():
    rng = np.random.default_rng(SEED)
    hi, lo = rng.normal(2, 1, 500), rng.normal(0, 1, 500)
    d, p, auc = cliffs_delta(hi, lo)
    assert d > 0.5 and p < 1e-10 and auc > 0.75, "cliffs_delta broken"
    d0, _, auc0 = cliffs_delta(lo, lo.copy())
    assert abs(d0) < 1e-9 and abs(auc0 - 0.5) < 1e-9
    assert odds_ratio(np.ones(10), np.zeros(10)) > OR_HI
    assert odds_ratio(np.zeros(10), np.ones(10)) < OR_LO


class _UnionFind:
    def __init__(self, items):
        self.parent = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def main():
    _selftest()
    RESULTS.mkdir(exist_ok=True)
    REPORT.mkdir(exist_ok=True)
    datasets = ingestion.available_datasets()

    per_ds = {}        # ds -> dict(X, y, src, marker, prevalence)
    for ds in datasets:
        train, _ = ingestion.load(ds)
        X = featurize(train["command"])
        y = train["label"].to_numpy()
        low = train["command"].str.lower()
        marker = low.apply(
            lambda s: int(any(m in s for m in _RETIRED_MARKERS))).to_numpy()
        src = train["source"].to_numpy()
        attack_src_masks = [(s, (y == 1) & (src == s))
                            for s in sorted(set(src[y == 1]))]
        per_ds[ds] = dict(X=X, y=y, src=src, marker=marker,
                          attack_src_masks=attack_src_masks,
                          prevalence=float(y.mean()))
        print(f"[audit] {ds}: {len(X)} train rows, "
              f"prevalence {y.mean():.3f}, "
              f"retired-marker rate {marker.mean():.3f}")

    # ---- per-feature signal + shortcut stats --------------------------------
    per_feature = {f: {"family": _FAMILY_OF[f], "binary": is_binary(f),
                       "per_dataset": {}} for f in FEATURE_NAMES}
    for ds, blob in per_ds.items():
        X, y, src, marker = blob["X"], blob["y"], blob["src"], blob["marker"]
        for f in FEATURE_NAMES:
            x = X[f].to_numpy(dtype=float)
            mal, ben = x[y == 1], x[y == 0]
            dead = bool(x.var() == 0)
            if dead:
                delta, p, auc = 0.0, 1.0, 0.5
            else:
                delta, p, auc = cliffs_delta(mal, ben)
            if per_feature[f]["binary"]:
                orr = odds_ratio(mal, ben)
                effect_type, effect = "odds_ratio", orr
                passes = (p < ALPHA) and (orr >= OR_HI or orr <= OR_LO)
            else:
                effect_type, effect = "cliffs_delta", delta
                passes = (p < ALPHA) and (abs(delta) >= DELTA_MIN)
            solo_f1 = float(f1_score(y, (x > 0).astype(int),
                                     zero_division=0))
            pos_attack = (y == 1) & (x > 0)
            if pos_attack.any():
                conc = float(pd.Series(src[pos_attack])
                             .value_counts(normalize=True).iloc[0])
            else:
                conc = 0.0
            # reverse-direction P8 probe: is any single attack source
            # ~always firing this feature (i.e. the feature fingerprints
            # the source rather than the behaviour)?
            sat_rate, sat_src = 0.0, ""
            for s_name, mask in blob["attack_src_masks"]:
                rate = float((x[mask] > 0).mean()) if mask.any() else 0.0
                if rate > sat_rate:
                    sat_rate, sat_src = rate, s_name
            pos_rate_ben = float((ben > 0).mean()) if len(ben) else 0.0
            pos_rate_mal = float((mal > 0).mean()) if len(mal) else 0.0
            if dead or marker.var() == 0:
                rho = 0.0
            else:
                rho = spearmanr(x, marker).correlation
                rho = 0.0 if np.isnan(rho) else float(rho)
            per_feature[f]["per_dataset"][ds] = {
                "mean_mal": float(np.mean(mal)) if len(mal) else 0.0,
                "mean_ben": float(np.mean(ben)) if len(ben) else 0.0,
                "median_mal": float(np.median(mal)) if len(mal) else 0.0,
                "median_ben": float(np.median(ben)) if len(ben) else 0.0,
                "mwu_p": float(p),
                "effect_type": effect_type,
                "effect": float(effect),
                "auc": float(auc),
                "solo_rule_f1": solo_f1,
                "source_concentration": conc,
                "max_source_pos_rate": sat_rate,
                "max_source": sat_src,
                "pos_rate_mal": pos_rate_mal,
                "pos_rate_ben": pos_rate_ben,
                "retired_marker_rho": rho,
                "passes_gate": bool(passes and not dead),
                "dead": dead,
            }

    # ---- redundancy clusters (edges pooled across datasets) -----------------
    uf = _UnionFind(FEATURE_NAMES)
    edges = []
    for ds, blob in per_ds.items():
        Xf = blob["X"].astype(float)
        live = [f for f in FEATURE_NAMES if Xf[f].var() > 0]
        # pandas .corr always returns a matrix (scipy's spearmanr collapses
        # to a scalar for 2 columns, which would break after heavy pruning)
        rho_df = Xf[live].corr(method="spearman")
        for i in range(len(live)):
            for j in range(i + 1, len(live)):
                r = rho_df.iloc[i, j]
                if np.isfinite(r) and abs(r) > RHO_MAX:
                    uf.union(live[i], live[j])
                    edges.append((live[i], live[j], ds, round(float(r), 3)))
    groups = {}
    for f in FEATURE_NAMES:
        groups.setdefault(uf.find(f), []).append(f)
    clusters = sorted((sorted(g) for g in groups.values() if len(g) > 1),
                      key=lambda g: g[0])

    def _sep_score(f):  # mean distance from chance across datasets
        return float(np.mean([abs(d["auc"] - 0.5)
                              for d in per_feature[f]["per_dataset"].values()]))

    cluster_of, rep_of = {}, {}
    for idx, grp in enumerate(clusters):
        rep = max(grp, key=_sep_score)
        for f in grp:
            cluster_of[f] = idx
            rep_of[f] = rep

    # ---- flags + proposed verdicts ------------------------------------------
    for f in FEATURE_NAMES:
        info = per_feature[f]
        dss = info["per_dataset"]
        info["passes_gate_any"] = any(d["passes_gate"] for d in dss.values())
        info["cluster"] = cluster_of.get(f)
        info["is_representative"] = rep_of.get(f) == f if f in rep_of else None
        flags = []
        for ds, d in dss.items():
            if d["dead"]:
                flags.append(f"dead-on-{ds}")
            if ((d["source_concentration"] > CONC_FLAG
                    and d["solo_rule_f1"] > SOLO_F1_FLAG)
                    or (d["max_source_pos_rate"] >= SRC_SAT_FLAG
                        and d["pos_rate_ben"] <= BEN_RARE_FLAG
                        and not d["dead"])):
                flags.append(
                    f"P8-source-fingerprint-{ds}({d['max_source']})")
            if abs(d["retired_marker_rho"]) > MARKER_RHO_FLAG:
                flags.append(f"retired-marker-echo-{ds}")
        info["flags"] = flags
        if not info["passes_gate_any"]:
            verdict = "KILL (fails the agreed signal gate on every dataset)"
        elif f in rep_of and rep_of[f] != f:
            verdict = f"KILL (redundant: |rho|>{RHO_MAX} cluster, keep {rep_of[f]})"
        elif any(fl.startswith("P8-source-fingerprint") for fl in flags):
            verdict = "DISCUSS (source-fingerprint shortcut risk -- Ch4 exhibit)"
        elif any(fl.startswith("retired-marker-echo") for fl in flags):
            verdict = "KEEP (flag: echoes retired P1 marker -- note in Ch4)"
        else:
            verdict = "KEEP"
        info["proposed_verdict"] = verdict

    ipv4_f1 = {ds: per_feature["has_ipv4"]["per_dataset"][ds]["solo_rule_f1"]
               for ds in datasets}
    out = {
        "gate": {"alpha": ALPHA, "delta_min": DELTA_MIN, "or_hi": OR_HI,
                 "or_lo": OR_LO, "rho_max": RHO_MAX,
                 "conc_flag": CONC_FLAG, "solo_f1_flag": SOLO_F1_FLAG,
                 "src_sat_flag": SRC_SAT_FLAG,
                 "ben_rare_flag": BEN_RARE_FLAG,
                 "marker_rho_flag": MARKER_RHO_FLAG},
        "datasets": {ds: {"n_train": int(len(per_ds[ds]["X"])),
                          "prevalence": per_ds[ds]["prevalence"],
                          "do_nothing_f1_floor":
                              2 * per_ds[ds]["prevalence"]
                              / (1 + per_ds[ds]["prevalence"]),
                          "retired_marker_rate":
                              float(per_ds[ds]["marker"].mean())}
                     for ds in datasets},
        "p8_ipv4_solo_f1": ipv4_f1,
        "retired_marker_prevalence": {
            ds: float(per_ds[ds]["marker"].mean()) for ds in datasets},
        "clusters": clusters,
        "cluster_edges": edges,
        "per_feature": per_feature,
    }
    (RESULTS / "ch3_feature_audit.json").write_text(
        json.dumps(out, indent=1, sort_keys=False))
    print(f"[audit] wrote results/ch3_feature_audit.json "
          f"({len(FEATURE_NAMES)} features x {len(datasets)} datasets)")
    print(f"[audit] P8 check -- has_ipv4 solo-rule F1: "
          + ", ".join(f"{ds}={v:.3f}" for ds, v in ipv4_f1.items())
          + "  (0.938 was measured on the earlier 78k-row build; in the "
          "current curated build the saturated source is downsampled, so "
          "the shortcut survives as a source fingerprint -- see "
          "max_source_pos_rate)")

    _write_markdown(out, datasets)
    n_keep = sum(v["proposed_verdict"].startswith("KEEP")
                 for v in per_feature.values())
    n_kill = sum(v["proposed_verdict"].startswith("KILL")
                 for v in per_feature.values())
    n_disc = len(per_feature) - n_keep - n_kill
    print(f"[audit] proposed: {n_keep} KEEP / {n_kill} KILL / "
          f"{n_disc} DISCUSS -> joint review next "
          f"(report/ch3_feature_decisions.md)")


def _fmt_effect(d):
    if d["effect_type"] == "odds_ratio":
        return f"OR {d['effect']:.2f}"
    return f"d {d['effect']:+.2f}"


def _write_markdown(out, datasets):
    pf = out["per_feature"]
    lines = [
        "# Ch3 -- Feature audit & KEEP/REDEFINE/KILL decisions (Noam)",
        "",
        "> Evidence generated by `analysis/ch3_feature_audit.py` on TRAIN "
        "splits only. PROPOSED verdicts are the script's suggestions; the "
        "**final verdict** column is decided jointly (course AI policy) and "
        "filled in during review. Full numbers: "
        "`results/ch3_feature_audit.json`.",
        "",
        "## Setup",
        "",
        f"- Survival gate: p < {out['gate']['alpha']} AND "
        f"(|Cliff's d| >= {out['gate']['delta_min']} or OR >= "
        f"{out['gate']['or_hi']} / <= {out['gate']['or_lo']:.2f}) "
        "on >= 1 dataset.",
        f"- Redundancy: Spearman |rho| > {out['gate']['rho_max']}, one "
        "representative kept per cluster.",
    ]
    for ds in datasets:
        d = out["datasets"][ds]
        lines.append(
            f"- `{ds}`: {d['n_train']} train rows, prevalence "
            f"{d['prevalence']:.3f} (do-nothing F1 floor "
            f"{d['do_nothing_f1_floor']:.3f}), retired-P1-marker rate "
            f"{d['retired_marker_rate']:.3f}.")
    lines += [
        "",
        "## P8 headline (testbed-shortcut probe)",
        "",
        "Solo rule \"predict attack iff literal IPv4 present\" scores: "
        + ", ".join(f"**{v:.3f}** on `{ds}`"
                    for ds, v in out["p8_ipv4_solo_f1"].items())
        + ". KNOWN_ISSUES P8 measured **0.938** on the earlier 78k-row "
        "dataset1 build, where the IPv4-saturated source dominated the "
        "attack side; the current curated build downsamples that source, so "
        "the dataset-wide rule collapsed but the *source fingerprint* "
        "remains (a source can still be identified by the feature firing on "
        "~100% of its rows). That probe is `max_source_pos_rate`, the "
        "saturation percentage quoted in the bullet list immediately below "
        "(full per-feature values in `results/ch3_feature_audit.json`); "
        "saturated+benign-rare features are flagged "
        "`P8-source-fingerprint` (Ch4 exhibit A).",
        "",
        "### Source-fingerprint features (source saturation >= "
        f"{out['gate']['src_sat_flag']}, benign rate <= "
        f"{out['gate']['ben_rare_flag']})",
        "",
    ]
    fp_rows = []
    for f, info in pf.items():
        for ds, d in info["per_dataset"].items():
            if (d["max_source_pos_rate"] >= out["gate"]["src_sat_flag"]
                    and d["pos_rate_ben"] <= out["gate"]["ben_rare_flag"]
                    and not d["dead"]):
                fp_rows.append(
                    f"- `{f}` on `{ds}`: fires on "
                    f"{d['max_source_pos_rate']:.0%} of `{d['max_source']}` "
                    f"rows vs {d['pos_rate_ben']:.1%} of benign")
    lines += fp_rows or ["- none"]
    lines += [
        "",
        "## Redundancy clusters (|rho| > 0.9)",
        "",
    ]
    if out["clusters"]:
        for i, grp in enumerate(out["clusters"]):
            rep = next(f for f in grp
                       if pf[f]["is_representative"])
            lines.append(f"- cluster {i}: " +
                         ", ".join(f"`{f}`" for f in grp) +
                         f" -> keep `{rep}`")
    else:
        lines.append("- none")
    lines += ["", "## Per-feature evidence and verdicts", ""]
    hdr_ds = " | ".join(f"{ds}: effect / p / AUC / soloF1" for ds in datasets)
    for fam, feats in FAMILIES.items():
        lines += [f"### {fam}", "",
                  f"| feature | {hdr_ds} | flags | PROPOSED | FINAL |",
                  "|" + "---|" * (len(datasets) + 4)]
        for f in feats:
            cells = []
            for ds in datasets:
                d = pf[f]["per_dataset"][ds]
                cells.append(f"{_fmt_effect(d)} / {d['mwu_p']:.1e} / "
                             f"{d['auc']:.2f} / {d['solo_rule_f1']:.2f}")
            flags = ", ".join(pf[f]["flags"]) or "--"
            lines.append(f"| `{f}` | " + " | ".join(cells) +
                         f" | {flags} | {pf[f]['proposed_verdict']} "
                         "| PENDING |")
        lines.append("")
    lines += [
        "## Hand-off",
        "",
        "- Final verdicts pending joint review (Noam calls each; this line "
        "is replaced when done).",
        "- After the final set lands: Ben re-runs Ch4 ranking, holdouts, "
        "sensitivity and figures (results/* regenerate).",
        "- `report/ch4_ranking_findings.md` references feature names from an "
        "older iteration (`shell_bins`, `redirect_count`, `path_proc`) -- "
        "stale, regenerate after merge.",
    ]
    (REPORT / "ch3_feature_decisions.md").write_text("\n".join(lines))
    print("[audit] wrote report/ch3_feature_decisions.md")


if __name__ == "__main__":
    main()
