# Chapter 6 — Model Selection and Justification

## 6.1 Four paradigms, each chosen over a named alternative

**Every model is carried for something the others structurally cannot do.**

**Table 6.1 — Five shipped models across four paradigms.** Configurations are in
Table 7.1.

<!-- cols: 1.05 0.85 0.80 2.35 1.45 -->

| Model | Paradigm | Input | Chosen over — and why | Grounding |
|---|---|---|---|---|
| `xgboost`, `xgboost_hybrid` | Boosting | 43 features; hybrid adds 3,000 char n-grams | **A linear or distance-based learner on the same vector.** Axis-aligned splits learn conjunctive threshold rules — fetch binary *and* pipe *and* shell — on mixed scales and Ch. 3's heavy tails, where a linear model is unbounded; gain keeps the surface auditable. | Chen & Guestrin, KDD 2016; shell-command GBDTs, Trizna et al., ACM TOPS 2026 |
| `cnn1d` | Representation learning | raw characters | **A word- or token-level model.** Shell vocabulary is open and adversarial, so tokens face unbounded out-of-vocabulary; a width-*k* convolution is a learned character-*k*-gram detector firing on `/dev/tcp` wherever it sits. | Kim, EMNLP 2014 (parallel widths; ours 3/5/7); character-CNN on PowerShell, Hendler et al., AsiaCCS 2018 |
| `random_forest` | Bagging | 43 features | **A second boosted model.** Bagging decorrelates by construction, so its MDI is an independent view in Ch. 4, not a re-run of gain, and it holds D1's lowest supervised false-alarm rate (FPR 0.0337 against the hybrid's 0.0415) at the highest precision (0.8782). | Breiman, *Machine Learning* 45(1), 2001; shell-command RF, ShellCore, IEEE IoT J. 9(4), 2022 |
| `isolation_forest` | Unsupervised anomaly | 43 features, benign rows only | **A fifth supervised model.** Fitted with attack rows dropped, so "suspicious" means unlike normal traffic rather than like our labelled attacks — the only component that can flag unlabelled tradecraft. | Liu, Ting & Zhou, ICDM 2008; extended, ACM TKDD 6(1), 2012 |

## 6.2 The axis the portfolio does not span

**Four paradigms is not four representations, and the representation is what
binds.** Four of the five read the same 43 features, leaving the CNN alone on
that axis; and every supervised model, the CNN included, is fitted on the same
attack corpus, free to learn its idiom rather than its behaviour. Only the
Isolation Forest, which reads no attack label, escapes that. **The project's
weakest standalone detector (Ch. 8) is carried anyway**, because its errors are
decorrelated by construction rather than by luck — what the cascade's first stage
requires.
