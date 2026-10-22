# Step 14 — Experiment A8: The Mega Test (End-to-End Final Validation)

> [!NOTE]
> **Realignment 05 Oct 2026 (additions only):**
> - The "winner" from A8 is the **provisional caption model** going into
>   Phase 4, not a final mobile decision. Phase 4 Step 08 re-tests it under
>   structured extraction and gating, and the phone parity gate can overturn it.
> - "Phase 4 (Mobile Android)" below now refers to Phases 4–6 in
>   `docs/plans/00-roadmap.md`.
> - Add a column "Runs on Infinix? (Y/N, s/frame)" — a winner that cannot run
>   on the low-end phone must be flagged.

## What
A final gauntlet test before mobile deployment. This test combines all optimal configurations discovered in previous individual experiments (A2–A7) into one massive evaluation for each of the top VLM candidates: Moondream2, Gemma 4 E2B, and SmolVLM.

## Why
We must conclusively prove which model balances Speed, Peak RAM, and True Answer Accuracy. Testing elements individually leaves gaps (e.g., SmolVLM might have 100% retrieval hits but terrible answer generation flow when the final response is constructed). The Mega Test ensures the entire system pipeline functions flawlessly and produces the actual conversational answers users expect (e.g., "Where are my keys?" -> "You left them on the kitchen counter").

---

## The Gauntlet Matrix

For each candidate VLM (Moondream2, Gemma 4, SmolVLM), run the complete pipeline with these locked variables:

1. **Optimal Frame Rate (from A2):** e.g., 1 frame per 5 seconds.
2. **Optimal Caption Style (from A3):** e.g., Short concise sentences.
3. **Database Environment (from A5):** A fully mixed database of hundreds of text memories + 50 video memories to simulate real-world noise.
4. **Hardware Simulation (from A4):** CPU-only inference, measuring strict Peak RAM and latency per frame.

### The Pipeline Execution
1. Ingest a standard test video and process it using the locked variables.
2. Store the memories in the mixed database.
3. Query the database using the ground-truth user questions.
4. Generate the final answer using the candidate LLM/VLM setup.
5. Evaluate the generated answer using the **LLM-as-a-Judge (A7)** protocol for True Answer Accuracy.

## Output Matrix

| VLM Candidate | Peak System RAM | Captions/sec | Retrieval Hit@5 | True Answer Score (1-5) | Winner? |
|---|---|---|---|---|---|
| Moondream2 (1.8B) | — | — | — | — | [ ] |
| Gemma 4 E2B (Shared) | — | — | — | — | [ ] |
| SmolVLM (500M) | — | — | — | — | [ ] |

## Success Criteria
- **Mobile Viability:** The winning architecture MUST remain securely under 4 GB total system RAM.
- **Answer Accuracy:** The model must score an average of ≥ 4.0/5.0 from the LLM Judge for natural conversational phrasing, not just successfully retrieve keywords.
- **Conclusion:** The model that secures the highest Answer Score while remaining under the thermal/RAM threshold will be definitively selected for the native Android transition.

---

## Implementation Details

### 14.1 Script: `src/benchmarks/mega_test.py`
A monolithic script that orchestrates the entire gauntlet for all three models sequentially.

### 14.2 Taskfile Entry
```yaml
experiment-a8-mega:
  desc: Run the final End-to-End Mega Test gauntlet across all models
  cmd: uv run python src/benchmarks/mega_test.py
```

## Verification
- [ ] All three models run the same gauntlet successfully.
- [ ] Final output JSON is generated with RAM, latency, and Answer Accuracy metrics.
- [ ] The definitive winner is recorded and approved for Phase 4 (Mobile Android).
