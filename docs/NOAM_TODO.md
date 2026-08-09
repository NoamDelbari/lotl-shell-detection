# Noam's Remaining Work — LotL Shell Detection
**Due: Aug 14 (report freeze) / Aug 15 (ZIP submission)**

Ben's side is complete. The items below are Noam's responsibility per `WORK_DIVISION.md`.
All of Ben's report files are in `report/` and results in `results/summary.json` — reference them freely.

---

## Report Chapters to Write

### Title Page (required, no points)
Create the title page in the final .docx:
- Course: Using AI for Intrusion and Malware Detection
- Title: AI-Driven Detection of LotL Shell Attacks (MITRE ATT&CK T1059.004)
- Group Number: [insert]
- Team: Ben Volovelsky & Noam Delbari (with emails)
- Date: August 15, 2026

---

### Executive Summary — 5 pts
Max 1 page. Cover:
- Threat: T1059.004 Living-off-the-Land Unix shell attacks, provenance-based labeling
- Two datasets: D1 (curated: HackTricks, GTFOBins, Atomic Red Team, etc.) and D2 (operational: Cowrie honeypot + bash history)
- Four models: XGBoost-hybrid (F1 0.871 / 0.846), 1D-CNN (0.853 / 0.841), Random Forest (0.761 / 0.696), Isolation Forest (0.264 / 0.082)
- Cascade: 3-stage (Isolation Forest → XGBoost-hybrid → LLM); cascade F1 0.873 D1 / 0.838 D2 with tighter FPR (0.029 / 0.032)
- Key finding: in-domain F1 ~0.87 but transfer collapses (D1→D2 0.534, D2→D1 0.184) due to corpus-style shortcuts

---

### Chapter 1 — Threat Characterization (15 pts, partial)
Ben has written **3 rows** of the mapping table (`report/ch1_threat_mapping.md`):
T1059.004 (reverse shells), T1105 (download cradles), T1033 (whoami/id discovery).

**You need to add:**
1. **Section 1.1 — Deep-Dive Threat Analysis**: from your preliminary proposal §2–3. Define T1059.004 and sub-techniques, explain how LotL attacks execute at the OS layer, and why shell command logs are the right telemetry.
2. **Your 4 mapping-table rows**: Pick 4 additional sub-techniques (e.g., T1027 obfuscated commands/base64, T1548.003 sudo abuse, T1070.003 shell history deletion, T1083 file/dir discovery). For each row use the 5-column assignment format:
   - Adversarial Behavioral Characteristic
   - Required Telemetry Source (shell command log / Cowrie JSONL)
   - Specific Log Attributes / Raw Fields (the `command` field)
   - Derived / Engineered Feature (e.g., `base64_present`, `sudo_present` from `src/features.py`)
   - Detailed Explanation of the relationship
3. **Section 1.3 — Theoretical Feature Rationale**: For each feature in `src/features.py`, explain the semantic security relationship. (Ben's ch1 covers detectability; you cover the feature→behavior mapping.)

---

### Chapter 2 — Literature Review (10 pts, partial)
Ben has written the **Trizna/SLP + QuasarNix** half (`report/ch2_literature_review.md`).

**You need to add the ShellCore paper section:**
- Feature extraction matrix: what features does ShellCore use? What model?
- Comparative analysis: ShellCore (Paper A) vs Trizna/SLP (Paper B) — feature differences, model differences, dataset differences
- Which ShellCore features did you adopt/modify/reject for this project?

---

### Chapter 3 — EDA (15 pts, partial)
Ben has written Dataset 1 EDA (`report/ch3_eda_findings.md`) and generated figures for both datasets.

**You need to write Dataset 2 EDA analysis** (figures already exist in `report/figures/`):
- `ch3_length_dist_dataset2.png` — what does the length distribution say about D2 vs D1?
- `ch3_variance_by_label_dataset2.png` — which features discriminate best in D2?
- `ch3_corr_heatmap_dataset2.png` — any strong correlations to watch for leakage?
- Write 3–4 paragraphs, matching the style and depth of Ben's D1 analysis.

---

### Chapter 5 — Multi-Dataset Harmonization (10 pts) — FULL CHAPTER, YOUR RESPONSIBILITY

This chapter is entirely yours. Write:

**5.1 Unified Feature Schema Definition**
The unified feature is the raw shell command string (`command` column), present in both datasets. From it, `src/features.py` extracts 38 identical behavioral features regardless of dataset. Map this back to your Step 1–4 findings. Reference the features that appear in both datasets' top-20 importance charts.

**5.2 Cross-Dataset Distribution Shift Analysis**
Pick 5–8 key features (e.g., `shell_bins`, `lotl_bins`, `pipe_count`, `url_present`, `command_length`). For each, show how its mean/variance/distribution differs between D1 and D2 using the figures in `report/figures/`. Explain WHY: D1 is curated/stylized text; D2 is live attacker input. Note the `shell_bins` D1→D2 inversion that Ch4 found (D1: `shell_bins` gain 0.194; D2: `lotl_bins` gain 0.177, `shell_bins` 0.052).

**5.3 Data Scaling & Scaling Remedies**
The pipeline uses `StandardScaler` fitted only on the training fold (inside the sklearn Pipeline) to prevent leakage. Explain why Z-score normalization is appropriate here (the features are counts/ratios with different scales). Reference `src/preprocessing.py` — specifically `EngineeredFeatures` and `build_hybrid_pipeline()` which wrap the scaler inside `Pipeline([...])` so CV splits can't leak.

---

### Chapter 6 — Model Selection (5 pts, partial)
Ben has written justification for XGBoost + CNN (`report/ch6_model_justification.md`).

**You need to add:**
- **Random Forest justification**: why RF on engineered features for LotL? (Gini importance, robust to outliers, interpretable, no scaling needed.) Cite one paper applying RF to shell/command detection.
- **Isolation Forest justification**: why unsupervised anomaly detection? (No attack labels needed at stage 1, computationally cheap as a filter.) Cite one paper. Note its known weakness: F1 0.264 / 0.082 standalone, which is why it's stage-1 only in the cascade.
- **Explicit hyperparameters** for both: RF `n_estimators`, `max_depth`, `class_weight`; IF `n_estimators`, `contamination`. (Check `src/models.py` for actual values.)

---

### Chapter 7 — Pipeline (10 pts, partial)
Ben has written sensitivity analysis for XGBoost and CNN (`report/ch7_sensitivity_findings.md`).

**You need to add:**
- **RF sensitivity analysis**: vary `n_estimators` (50/100/200/500) and `max_depth` (None/10/20). Report F1 and FPR. Show which setting was chosen and why.
- **IF sensitivity analysis**: vary `contamination` (0.05/0.10/0.20/0.30). Report F1 and FPR. (Note: IF F1 is low regardless — show that the operating point was set to maximize recall as a filter, not F1.)

To run these, you can add sweep scripts similar to `analysis/ch7_train.py`.

---

### Chapter 8 — Error Analysis & Ensemble (20 pts, partial)
Ben has written:
- 8.1 for XGBoost + CNN → `report/ch8_findings.md`
- 8.2 cross-dataset table → same file
- 8.3 vs Trizna/TOPS → `report/ch8_3_tops_comparison.md`
- 8.4 cascade results (stub) → `report/ch8_4_cascade_findings.md`

**You need:**

**8.1 for RF and IF** — Write error forensics:
- How many FN/FP does RF make on D1 and D2?
- What types of commands does IF flag (which benign sources have highest FPR)?
- Compare: when RF fails, does XGBoost succeed? (This motivates the cascade.)
- Run `python main.py holdout random_forest` and `python main.py holdout isolation_forest` and read `results/holdout_random_forest_*.json` and `results/holdout_isolation_forest_*.json`.

**8.3 vs ShellCore** — Benchmark your RF and IF results against ShellCore. How do your results compare? Why are they different (different dataset, different features)?

**8.4 Cascade with real LLM** — See Bonus section below. Replace the stub arbitrator.

---

## Bonus Chapter — LLM Triage (+10 pts)

This is optional but worth 10 pts. The code scaffolding is already in place.

### What exists already:
- `src/llm_triage.py`: `build_prompt()`, `parse_verdict()`, `select_edge_cases()`, `stub_arbitrator`, `huggingface_arbitrator`
- `src/ensemble.py`: `CascadeDetector` wired to use the arbitrator
- `analysis/bonus_b3_llm_eval.py`: evaluation script (Ben wrote this)
- `report/bonus_b3_findings.md`: has stub results (NOT graded — replace with real)
- `report/ch8_4_cascade_findings.md`: has stub cascade results (replace with real)

### What you need to do:

**Step 1: Get HF_TOKEN**
Create a free account at huggingface.co and generate a personal access token. Export it:
```bash
export HF_TOKEN="hf_..."
```
Do NOT commit the token to the repo.

**Step 2: Run the real evaluation**
```bash
cd lotl-shell-detection-new
python analysis/bonus_b3_llm_eval.py --hf
```
This routes edge cases (model disagreements / uncertainty band) to Llama 3.1-8B via HF Inference and saves results to `results/bonus_b3_edge_eval.json`.

**Step 3: Update the report files** with real numbers (replace the stub table in `bonus_b3_findings.md` and `ch8_4_cascade_findings.md`).

**Step 4: Write B.1, B.2, B.4:**
- **B.1**: Model = `meta-llama/Llama-3.1-8B-Instruct` via `huggingface_hub.InferenceClient`. Token from env var `HF_TOKEN`. Latency ~1–3s per call. Document exact call count from the evaluation run.
- **B.2**: The prompt template is in `src/llm_triage.py`'s `build_prompt()`. Copy it into the report and explain the chain-of-thought structure.
- **B.4**: Report wall-clock latency per call, total calls, and conclude honestly whether this is production-viable (hint: at 36–42% edge fraction, ~800–1100 calls per test run × 1–3s = 15–55 minutes — not production-viable as-is; the cascade band needs to be tightened).

---

## Packaging (your responsibility)

1. **Assemble the .docx**: Merge all markdown chapters (title page + exec summary + Ch1–Ch8 + Bonus + Appendices) into one Word document. Max **15 pages** at 1.5 spacing, Arial/Calibri 11pt.

2. **Appendix A — Code Execution**:
   ```
   pip install -r requirements.txt
   python main.py all                  # run all models on both datasets
   python main.py holdout xgboost_hybrid --dataset 1
   python analysis/bonus_b3_llm_eval.py --hf   # requires HF_TOKEN
   ```

3. **Appendix B — Hardware/Software**:
   - Python 3.11, scikit-learn 1.5, XGBoost 2.0, PyTorch 2.3 (MPS on Apple Silicon)
   - macOS (Apple M-series GPU used for CNN training via `torch.device("mps")`)

4. **AI logs naming**: the assignment requires `ai_logs/<tool_name>_log.txt`. Rename/copy:
   ```
   ai_logs/claude_session.md  →  ai_logs/claude_code_log.txt
   ```
   (Keep the .md too; just add the .txt copy for the ZIP.)

5. **ZIP it**:
   ```
   Group_[XX]_Final_Project.zip
   ├── code/              (this repo)
   ├── report.docx
   └── ai_logs/
       └── claude_code_log.txt
   ```

---

## Cross-Review (required before Aug 14 freeze)

Per WORK_DIVISION.md: **read Ben's chapters before Aug 14 and flag any issues.**
Ben's files to review:
- `report/ch1_threat_mapping.md` — 3 rows
- `report/ch2_literature_review.md` — Trizna section (note: sourcing note at top about TOPS paper — if instructor assigned a specific DOI, ask them)
- `report/ch3_eda_findings.md`
- `report/ch4_ranking_findings.md`
- `report/ch6_model_justification.md`
- `report/ch7_sensitivity_findings.md`
- `report/ch8_findings.md`
- `report/ch8_3_tops_comparison.md`

---

## Quick Results Reference

All numbers from `results/summary.json` (full data, no limit):

| Model | D1 F1 | D2 F1 | D1 ROC-AUC | D2 ROC-AUC |
|---|---|---|---|---|
| XGBoost-hybrid | **0.871** | **0.846** | 0.978 | 0.965 |
| 1D-CNN | 0.853 | 0.841 | 0.976 | 0.960 |
| Random Forest | 0.761 | 0.696 | 0.921 | 0.898 |
| Isolation Forest | 0.264 | 0.082 | 0.722 | 0.602 |
| Baseline TF-IDF | 0.881 | 0.863 | 0.980 | 0.964 |

Transfer (cross-dataset):

| Model | D1→D2 F1 | D2→D1 F1 |
|---|---|---|
| XGBoost-hybrid | 0.534 | 0.184 |
| 1D-CNN | 0.529 | 0.331 |
| Random Forest | 0.509 | 0.175 |
| Isolation Forest | 0.078 | 0.248 |
