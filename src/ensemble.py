"""
ensemble.py -- hybrid behavioural cascade (Ch8.4) + an LLM-arbitration hook.

The cascade is the assignment's recommended shape:

    Stage 1  Isolation Forest (fast, unsupervised, high-sensitivity filter).
             Commands it is confident are benign are cleared immediately.
    Stage 2  A supervised model (XGBoost) categorises everything the first
             stage flagged as anomalous, discarding ambient noise.
    Stage 3  (optional) an LLM arbitrates the residual disagreements /
             low-confidence cases -- Noam owns the LLM layer; Ben's B.3 evaluates
             its verdicts on those edge cases. The `arbitrator` hook keeps this
             file runnable before that layer exists.

Ch8.4 is Noam's to assemble in the report, but the code lives in the shared
skeleton so both owners' models plug into it. This module is dataset-agnostic.
"""
from __future__ import annotations

import numpy as np


class CascadeDetector:
    def __init__(self, stage1, stage2, stage1_clear_below: float = 0.15,
                 stage2_uncertain=(0.35, 0.65), arbitrator=None,
                 stage1_retain_recall: float = 0.99):
        """
        stage1 : unsupervised detector with decision_scores/predict_proba
        stage2 : supervised classifier with predict_proba
        stage1_clear_below : stage-1 anomaly score under this -> cleared benign.
                             Ignored when stage1_retain_recall is set (the
                             threshold is then calibrated on the training data).
        stage2_uncertain   : (lo, hi) stage-2 prob band routed to arbitration
        arbitrator : optional callable(command, context)->dict for stage 3
        stage1_retain_recall : if not None, calibrate stage1_clear_below on the
                             training attacks so this fraction of them survive
                             stage 1. A high-sensitivity first filter must clear
                             ONLY confident-benign traffic; calibrating to 0.99
                             stops stage 1 from silently discarding attacks
                             (the failure mode of a naive fixed threshold).
        """
        self.stage1 = stage1
        self.stage2 = stage2
        self.stage1_clear_below = stage1_clear_below
        self.stage2_uncertain = stage2_uncertain
        self.arbitrator = arbitrator
        self.stage1_retain_recall = stage1_retain_recall

    def fit(self, X, y):
        self.stage1.fit(X, y)
        self.stage2.fit(X, y)
        if self.stage1_retain_recall is not None:
            y = np.asarray(y).astype(int)
            s1 = self._s1_scores(np.asarray(X, dtype=object))
            attack_scores = s1[y == 1]
            if len(attack_scores):
                # clear below the (1 - retain)-quantile of attack scores, so
                # `stage1_retain_recall` of attacks score above it and survive.
                q = 1.0 - self.stage1_retain_recall
                self.stage1_clear_below = float(np.quantile(attack_scores, q))
        return self

    def _s1_scores(self, X):
        if hasattr(self.stage1, "decision_scores"):
            return np.asarray(self.stage1.decision_scores(X))
        return np.asarray(self.stage1.predict_proba(X))[:, 1]

    def predict_with_trace(self, X):
        """Return (labels, trace) where trace records which stage decided each
        sample -- used for the LLM-call-count / routing stats in Ch8.4 & B.4."""
        X = np.asarray(X, dtype=object)
        n = len(X)
        labels = np.zeros(n, dtype=int)
        decided_by = np.empty(n, dtype=object)

        s1 = self._s1_scores(X)
        cleared = s1 < self.stage1_clear_below      # stage 1 says "benign, done"
        decided_by[cleared] = "stage1_clear"

        flagged = ~cleared
        idx = np.where(flagged)[0]
        if len(idx):
            p2 = np.asarray(self.stage2.predict_proba(X[idx]))[:, 1]
            lo, hi = self.stage2_uncertain
            for j, i in enumerate(idx):
                p = p2[j]
                if lo <= p <= hi and self.arbitrator is not None:
                    context = {"stage1_anomaly": round(float(s1[i]), 3),
                               "stage2_p_malicious": round(float(p), 3)}
                    labels[i] = int(self.arbitrator(str(X[i]), context)["label"])
                    decided_by[i] = "stage3_llm"
                else:
                    labels[i] = int(p >= 0.5)
                    decided_by[i] = "stage2_supervised"
        return labels, {"decided_by": decided_by,
                        "n_cleared_stage1": int(cleared.sum()),
                        "n_to_stage2": int(flagged.sum())}

    def predict(self, X):
        return self.predict_with_trace(X)[0]

    def predict_proba(self, X):
        # stage-2 probability where reached, else the stage-1 anomaly score
        X = np.asarray(X, dtype=object)
        s1 = self._s1_scores(X)
        out = s1.copy()
        flagged = s1 >= self.stage1_clear_below
        idx = np.where(flagged)[0]
        if len(idx):
            out[idx] = np.asarray(self.stage2.predict_proba(X[idx]))[:, 1]
        return np.column_stack([1.0 - out, out])
