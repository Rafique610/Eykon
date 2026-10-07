# Step 13 — Mobile Parity Gate 4 (Gating Cascade on Pixel + Infinix)

## What
Port the frozen cascade (Tier 0a/0b/0c, Tier 1, segmenter; Tier 2 using the
phone's model) to Kotlin, run it on golden fixtures and on replayed Step 03
phone sessions on **both** phones, and measure real per-tier cost.

## Why
Phase 4 isn't finished until the phone makes the same decisions at a known
cost. This is the exam at the end of the phase (roadmap §4).

## How to implement
- Kotlin: `gates/`, `novelty/`, `segmenter/` packages mirroring Python
  function-for-function; Tier 1 encoder via LiteRT; image ops via
  Android `Bitmap`/`YuvImage` or OpenCV-Android (decide below).
- Instrumented test runs golden fixtures → writes `parity_report.json`
  (decision agreement %, embedding cosine to Python reference).
- Replay harness on device: feed Step 03 session frames at wall-clock rate.
- Measure per tier: ms/frame (P50/P90), current draw delta, thermal status,
  RSS; and full-cascade 30-min replay battery %.
- Fill the **measured slowdown factor** table (laptop ms ÷ phone ms) per tier.

## Open decisions
- **Image ops on Android**: (a) OpenCV-Android — same functions as Python,
  ~20–30 MB native libs; (b) hand-written Kotlin on downscaled arrays —
  tiny, but rounding/resize differences risk parity; (c) RenderScript
  replacement via Vulkan/GPU — fast, overkill for 128×128.

## You test this
- Run the replay on each phone yourself (one button), keep the phone in your
  pocket for the 30-min replay, then tell me how warm it felt and check the
  battery %. Compare with the report.

## How this number could be lying
- Replay ≠ live camera: camera sensor/ISP power is missing → report replay
  power as *compute-only*; full live power comes in Phase 6.
- Infinix may pass at 1 fps but not at 3 fps → report max sustainable fps per
  device, not a pass/fail.

## Verification
- [ ] Decision agreement ≥ 95 % on golden fixtures (both phones).
- [ ] Per-tier cost table with P50/P90 on both phones.
- [ ] Measured slowdown factors recorded in `docs/domain/eykon/index.md`.
- [ ] Every mismatch > 5 % explained in the report.

## Files changed
- [NEW] `android/.../gates/`, `android/.../novelty/`, `android/.../segmenter/`, instrumented tests
- [NEW] `docs/additional/phase4-parity-report.md`
- [MODIFY] `README.md`, `Taskfile.yml`

## Dependencies
- Steps 02, 03, 12.

## Common issues
- YUV→RGB/gray conversion differences break parity → compare on Y plane
  (luma) directly on both sides.
