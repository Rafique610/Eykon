# Step 05 — Long-Term Episodic Consolidation

## What
A background job that turns stable short-term events into long-term
**episodes** (e.g. "Lunch at the cafeteria with Ali, 13:10–13:55: discussed
exam, I left my bottle on the table"), keeping pointers to source events.
Runs when idle/charging on the phone.

## Why
Searching thousands of micro-events for "what did I do Tuesday afternoon?" is
slow and noisy; LightMem-Ego and MemGPT-style systems consolidate to keep
query-time cost low. Pointers keep drill-down possible.

## How to implement
- Grouping: consecutive events by time gap + place + participants → candidate
  episode; Gemma 4 summarises with a strict "only from these events" prompt.
- `consolidated_into` set on source events; sources kept (no deletion yet —
  forgetting is Step 10).
- Trigger: count/age threshold, plus "charging + idle" on Android (WorkManager).

## Open decisions
- **When**: (a) nightly on charge — no impact on day battery, stale until
  night; (b) every N events — fresher, costs battery; (c) both.
- **Summary granularity**: (a) one paragraph per episode; (b) bullet facts with
  timestamps — better for exact recall; (c) both stored.

## You test this
- After a full replay day, read 15 episode summaries next to their source
  thumbnails; mark each faithful / missing key item / hallucinated.

## How this number could be lying
- Summaries read well even when wrong → audit against sources, not fluency.

## Verification
- [ ] Hallucination rate in audited summaries reported.
- [ ] Episode retrieval improves "summary" QA category vs events-only.
- [ ] Job is resumable (killed mid-run → no duplicates).

## Files changed
- [NEW] `src/memories/consolidate.py`, tests; Android Worker

## Dependencies
- Steps 03–04.
