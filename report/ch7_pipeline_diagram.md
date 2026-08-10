**Figure 7.1 — Three-stage cascade detector.** Raw command → Isolation Forest bulk-benign filter (stage 1) → XGBoost-hybrid classifier (stage 2: P(attack) > 0.65 → attack, < 0.35 → benign) → LLM arbitration (Llama 3.1-8B) on the 0.35–0.65 edge band.

```mermaid
flowchart TD
    IN(["Raw shell command string"]) --> S1["Stage 1 · Isolation Forest<br/>(unsupervised anomaly score)"]
    S1 --> D1{"score below<br/>calibrated threshold?"}
    D1 -->|"yes"| B1(["BENIGN — cleared<br/>(bulk benign filter)"])
    D1 -->|"no (anomalous)"| S2["Stage 2 · XGBoost-hybrid<br/>P(attack)"]
    S2 --> D2{"P(attack)?"}
    D2 -->|"0.65 – 1.00"| A1(["ATTACK<br/>(high confidence)"])
    D2 -->|"0.00 – 0.35"| B2(["BENIGN<br/>(high confidence)"])
    D2 -->|"0.35 – 0.65<br/>(edge case)"| S3["Stage 3 · LLM arbitration<br/>(Llama 3.1-8B)"]
    S3 --> D3{"final verdict"}
    D3 -->|"malicious"| A2(["ATTACK"])
    D3 -->|"benign"| B3(["BENIGN"])

    classDef attack fill:#f8d7da,stroke:#c0392b,color:#000
    classDef benign fill:#d4edda,stroke:#27ae60,color:#000
    classDef stage fill:#e7f0fb,stroke:#2a6fb0,color:#000
    class A1,A2 attack
    class B1,B2,B3 benign
    class S1,S2,S3 stage
```

> Thresholds are the shipped defaults: `CascadeDetector(stage2_uncertain=(0.35, 0.65))`
> in `src/ensemble.py:25`, passed explicitly at `analysis/ch8_4_cascade.py:63`. The
> stage-1 cut is not a literal — `stage1_retain_recall=0.99` overwrites it at `fit()`
> time with the 1st-percentile anomaly score of the training attacks
> (`src/ensemble.py:52-60`), which is why the decision node names a calibrated
> threshold rather than a number.
