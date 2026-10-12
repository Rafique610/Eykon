# Phase 4.1 Step 08 — Place Recognition and Place Naming

## What

Answer "where" for put-down and place events, without a language model:

1. **Place embeddings**: for each keyframe (from the Phase 4 cascade), an
   image embedding of the whole frame (the shared encoder if Step 02 chose
   one).
2. **Place clusters**: group embeddings into places (e.g. "desk area",
   "kitchen counter", "front door") with online clustering, so a new place
   creates a new cluster.
3. **Fine location** at put-down: a crop **below and around the hand** at
   release time, matched against "surface" names (desk, shelf, bag, drawer,
   pocket) — the object's immediate container or surface.
4. **Naming**: a place cluster gets a name either by text matching against a
   small place vocabulary, or by the user naming it once ("this is my desk")
   — see open decision.
5. **Output**: a `place` field `{label, cluster_id, surface, confidence,
   source}` in slot records.

## Why

- "Where are my keys?" needs a place answer the user understands. The VLM
  path writes places as words; the cheap path needs its own way.
- Two levels (room-level cluster and surface at release) match how people
  describe locations: "in the bag on the chair in my room".
- Clustering lets the system recognise **returning** to the same place
  across days, which Phase 5's routines and the state table use.

## How to implement

1. **Embeddings**: reuse keyframe embeddings from Phase 4 Step 08 where
   possible; no second pass over frames.
2. **Online clustering** in `src/perception/places.py`: assign to the
   nearest cluster centre if similarity is above a threshold; otherwise start
   a new cluster; update centres with a running mean. Thresholds tuned on the
   tuning sessions against annotated places.
3. **Surface matching** at put-down: crop below the hand at release, match to
   surface text prompts; combine with the room cluster.
4. **Naming flow**:
   - text matching: cluster centre vs place-name text embeddings;
   - user naming: the app shows a thumbnail of a new cluster and asks "name
     this place?" (designed here, built at Step 15);
   - names stored in a `places` table (id, cluster centre, name, source,
     created_at).
5. **Evaluation**: place accuracy at put-down events (room-level and surface
   level), cluster purity against annotated places, number of clusters per
   real place (over-splitting).

## Open decisions

- **Place naming** (handoff §6). Options: (a) text matching only — no user
  effort, often vague or wrong names; (b) user labels once per new place —
  accurate and personal, small effort, needs UI; (c) text-matched suggestion
  that the user confirms or edits — middle ground (draft).
- **Clustering method.** Options: (a) online threshold clustering (draft) —
  simple, order-dependent; (b) periodic offline re-clustering while charging
  — better clusters, ids can change (needs remapping); (c) (a) live plus (b)
  nightly with stable name mapping.
- **Surface vocabulary.** Options: (a) fixed list (desk, table, shelf, bag,
  drawer, pocket, bed, floor) — simple; (b) user-editable — flexible;
  (c) fixed list plus user additions.

## You test this

1. Look at the cluster gallery (thumbnails per cluster) for your tuning
   sessions. Does each cluster look like one place? Are any places split into
   many clusters?
2. Name 5 clusters through the naming flow on the laptop page.
3. Check 10 put-down events: is the surface right ("bag", "desk")?

## How this number could be lying

- Recording sessions in a few rooms makes clustering easy; held-out sessions
  in new places (Step 12) test real behaviour.
- Lighting changes (day / night) can split one place into two clusters;
  report per-lighting purity.
- Surface matching at release is judged only where the annotation names a
  surface; unknown surfaces are excluded and counted.

## Verification

- [ ] `places.py` under 300 lines; places table created idempotently.
- [ ] Cluster purity and over-splitting reported on tuning sessions.
- [ ] Room-level and surface-level put-down accuracy reported.
- [ ] Naming flow works on the laptop page.

## Files changed

- [NEW] `src/perception/places.py`
- [MODIFY] `src/memories/database.py` (`places` table), `src/config.py`
- [NEW] `docs/results/phase-4.1/step08-places.md`
- [MODIFY] `src/perception/vocab_app.py` (naming page), `README.md`

## Dependencies

- Step 02 (encoder); Phase 4 Step 08 (keyframe embeddings) if available.

## Common issues

- Similar-looking rooms (two plain bedrooms) merge; that is a real
  limitation; user naming plus time context helps.
- Bags move: "bag" is both a surface and a tracked object. If the bag is in
  the user's object list, the keys' place becomes "in bag", and the bag's own
  place answers the next question. Recorded as a design rule for Step 09.
