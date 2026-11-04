# Phase 6.5 Step 04 — Face Descriptors on Device, Encrypted Storage

## What

1. **Descriptor model**: a small on-device model that turns a detected face
   into a numeric vector (a "face descriptor") such that the same person's
   faces are close together. Shortlisted with the same filters (licence,
   phone artifact); several published face-embedding models are research-only
   — those are excluded.
2. **Storage**: descriptors in a `face_descriptors` table (id, keyframe id,
   time, descriptor, quality score, cluster id NULL, expires_at), encrypted at
   rest (Step 01 decision), in app-private storage.
3. **Quality filter**: blurry, tiny or side-on faces get low quality and are
   not used for grouping.
4. **Retention**: unnamed descriptors expire after the Step 01 window; a
   background job deletes them.

## Why

- Grouping and naming (Step 05) need descriptors; storing numbers instead of
  face images reduces privacy risk.
- Expiry is the bystander policy made concrete.

## How to implement

1. Shortlist and choose the descriptor model; ledger rows.
2. `src/people/descriptors.py` and Kotlin mirror; same file both sides; parity
   check on fixtures (descriptor cosine between laptop and phone).
3. Encryption via Android Keystore (phone); on the laptop, research data stays
   in the git-ignored data folder and is deleted after evaluation.
4. Expiry job (WorkManager) and a test that expired rows are gone.

## Open decisions

- **Descriptor model** from the shortlist (licence and phone version first,
  accuracy second).
- **Quality threshold.** Options: (a) strict — fewer, better descriptors;
  (b) loose — more coverage, noisier groups; (c) tuned on the consented test
  set (draft).

## You test this

1. Check the debug view shows quality scores; side-on faces should score low.
2. Set a short expiry for testing; confirm unnamed descriptors disappear.

## How this number could be lying

- Descriptor accuracy published on celebrity photo benchmarks does not
  transfer to egocentric frames; only our consented frames count.

## Verification

- [ ] Descriptor model with verified licence and phone artifact.
- [ ] Encrypted storage on the phone; expiry job tested.
- [ ] Laptop–phone descriptor agreement on fixtures.

## Files changed

- [NEW] `src/people/descriptors.py`, `android/.../people/FaceDescriptors.kt`,
  `FaceExpiryWorker.kt`
- [MODIFY] database schema (people tables), `README.md`

## Dependencies

- Step 03.

## Common issues

- Keystore keys lost on app reinstall make old data unreadable; acceptable
  (and private), but documented.
