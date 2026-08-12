"""
llm_triage.py -- LLM arbitration layer scaffolding (Bonus chapter).

Noam owns the live LLM integration (Hugging Face Inference, Llama 3.1 8B) and
plugs it into the cascade (ensemble.py). Ben owns **B.3**: evaluating the LLM's
verdicts on high-uncertainty edge cases. This module gives both a shared
contract so B.3 can run and be written now, against a stub, and swap in the real
client with a one-line change.

An *arbitrator* is any callable: (command:str, context:dict) -> dict with keys
    {"label": 0|1, "reasoning": str, "latency_s": float}

`select_edge_cases()` is the B.3 selection logic: the samples where the primary
models disagree or are unconfident -- exactly the population the LLM is meant to
arbitrate. Nothing here is dataset-aware.
"""
from __future__ import annotations

import time

import numpy as np

# --- prompt template (B.2), kept here so B.3's harness and Noam's live layer
# use the identical wording ------------------------------------------------- #
TRIAGE_PROMPT = """You are a Linux security analyst triaging a single shell command.
Decide if it is MALICIOUS (part of an attack: reverse shell, download-and-execute,
LotL/GTFOBins abuse, enumeration burst, privilege escalation, persistence, or
log/anti-forensics tampering) or BENIGN (ordinary administration or development).

Command:
{command}

Model signals (for context, may disagree):
{signals}

Reason step by step over the command's structure and intent, then end with
exactly one line:
VERDICT: MALICIOUS
or
VERDICT: BENIGN
"""


def format_signals(context: dict) -> str:
    parts = []
    for k, v in context.items():
        parts.append(f"- {k}: {v}")
    return "\n".join(parts) if parts else "- (none)"


def select_edge_cases(model_scores: dict, y_true=None, disagree_gap: float = 0.4,
                      uncertain_band=(0.35, 0.65)):
    """Pick indices that are genuine edge cases for the LLM to arbitrate.

    model_scores : {model_name: array of P(malicious)} for the same rows
    Returns a dict: index -> reason ("disagreement" or "low_confidence").
    """
    names = list(model_scores)
    S = np.column_stack([np.asarray(model_scores[n]) for n in names])
    n = S.shape[0]
    edge = {}
    lo, hi = uncertain_band
    for i in range(n):
        row = S[i]
        if row.max() - row.min() >= disagree_gap:      # models disagree
            edge[i] = "disagreement"
        elif np.any((row >= lo) & (row <= hi)):         # someone unconfident
            edge.setdefault(i, "low_confidence")
    return edge


# --------------------------------------------------------------------------- #
# arbitrators                                                                  #
# --------------------------------------------------------------------------- #
def stub_arbitrator(command: str, context: dict) -> dict:
    """Deterministic offline stand-in so B.3 runs with no network / token.

    It is a transparent heuristic (NOT the graded LLM): flags a few unambiguous
    LotL motifs. Its only purpose is to exercise the harness end-to-end; the
    report must clearly label results from this stub as a placeholder for
    Noam's live Llama arbitration.
    """
    t0 = time.time()
    low = command.lower()
    hard_malicious = ("/dev/tcp" in low or "nc -e" in low or "bash -i" in low
                      or ("curl" in low and "| sh" in low)
                      or ("wget" in low and "|sh" in low)
                      or "base64 -d" in low)
    label = 1 if hard_malicious else 0
    return {"label": label,
            "reasoning": ("matched a hard LotL motif" if hard_malicious
                          else "no hard motif; defaulting benign"),
            "latency_s": time.time() - t0}


def huggingface_arbitrator(model_id: str = "meta-llama/Llama-3.1-8B-Instruct"):
    """Return a real HF-Inference arbitrator. Requires HF_TOKEN in the env
    (never committed). Noam wires this into the cascade; B.3 can call it too.

    Kept lazy so importing this module needs no huggingface_hub / token.
    """
    import os

    from huggingface_hub import InferenceClient

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("set HF_TOKEN in the environment (do not commit it)")
    client = InferenceClient(model=model_id, token=token)

    def _arb(command: str, context: dict) -> dict:
        t0 = time.time()
        prompt = TRIAGE_PROMPT.format(command=command,
                                      signals=format_signals(context))
        out = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256, temperature=0.0)
        text = out.choices[0].message.content
        verdict = text.strip().upper().rsplit("VERDICT:", 1)[-1]
        label = 1 if "MALICIOUS" in verdict else 0
        return {"label": label, "reasoning": text, "latency_s": time.time() - t0}

    return _arb


def ollama_arbitrator(model: str = "llama3.1:8b",
                      base_url: str = "http://localhost:11434"):
    import urllib.request, json as _json
    def _arb(command: str, context: dict) -> dict:
        import time
        t0 = time.time()
        prompt = TRIAGE_PROMPT.format(command=command,
                                      signals=format_signals(context))
        payload = _json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0}
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=120)
        text = _json.loads(resp.read())["message"]["content"]
        verdict = text.strip().upper().rsplit("VERDICT:", 1)[-1]
        label = 1 if "MALICIOUS" in verdict else 0
        return {"label": label, "reasoning": text, "latency_s": time.time() - t0}
    return _arb
