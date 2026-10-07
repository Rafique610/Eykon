# Step 08 — Tier 1: Embedding Novelty Gate + Adaptive Hysteresis

## What
For frames that pass Tier 0, compute a compact image embedding with a tiny
vision encoder and compare it to (a) the last keyframe and (b) a short rolling
window mean. Trigger the heavy model only when novelty exceeds a threshold
that **rises with dwell time** in a stable scene:
`τ(t) = τ_base + α · log(1 + Δt_static)` (from `new_Dev.md`), plus a hard
minimum interval and a maximum "heartbeat" interval (so long static scenes
still get one refresh every N minutes).

## Why
Pixel change can't tell "same desk, slightly different angle" from "new
object on the desk". A semantic embedding can — at a fraction of VLM cost.
Hysteresis fixes the desk-for-3-hours flood.

## How to implement
1. **Model shortlist (only models with a verified mobile artifact)** — research
   sub-task: for each candidate record params, input size, embedding dim,
   `.tflite`/LiteRT availability, laptop ms/frame, licence.
2. `src/vision/novelty.py`: embedder wrapper (one runtime per platform), cosine
   novelty, hysteresis state machine (`STABLE`, `CHANGING`), heartbeat.
3. Sweep `τ_base`, `α`, min/max interval on tuning set; plot heavy calls/hour vs
   short-event recall (Pareto front).
4. Store the embedding with the keyframe — Phase 5 can reuse it for
   image-side retrieval.

## Open decisions
- **Encoder**: (a) MobileNetV3/V4-small ImageNet features — tiny, fast,
  official TFLite, but not semantically aligned with text; (b) MobileCLIP-S0 —
  Apple, CLIP-aligned (enables text→image search later), mobile-oriented,
  need to verify LiteRT conversion; (c) SigLIP-base / SigLIP2 small —
  strong semantics, heavier, conversion risk.
- **Comparison target**: (a) last keyframe only — simplest; (b) rolling
  window mean — robust to jitter; (c) both, trigger if either exceeds.

## You test this
- Desk test on laptop webcam: sit 5 minutes doing nothing special → expect 1–2
  keyframes. Then put your phone, then a cup, then your keys on the desk one by
  one, 30 s apart → expect a keyframe for each. Tell me what it missed.
- Review the Pareto plot with me and pick the operating point *you* would ship
  (you are the user).

## How this number could be lying
- Embedding cosine thresholds differ wildly between models — never compare
  thresholds across models, only Pareto curves.
- Small objects (keys) change the global embedding very little → the
  short-event recall for small objects must be reported separately. This may
  be the cascade's weakest point; if so, say it and consider hand/object-region
  cropping as follow-up.

## Verification
- [ ] Shortlist table with verified mobile artifact links.
- [ ] Pareto plots per candidate on tuning set.
- [ ] Chosen model + operating point recorded with reasoning.
- [ ] Golden fixtures with embeddings (rounded) + decisions.

## Files changed
- [NEW] `src/vision/novelty.py`, `tests/test_novelty.py`
- [MODIFY] `src/config.py`, `pyproject.toml` (only if a runtime is truly needed), `README.md`

## Dependencies
- Steps 05–07.

## Common issues
- Converting PyTorch models to TFLite often fails on unsupported ops — prefer
  models already published as `.tflite` / on Kaggle Models / LiteRT community.
