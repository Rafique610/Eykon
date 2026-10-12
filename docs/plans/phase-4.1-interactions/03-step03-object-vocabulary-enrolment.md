# Phase 4.1 Step 03 — Object Vocabulary and Personal Object Enrolment

## What

Give the user control over **which objects Eykon tracks**, and let them teach
it **their own** objects with a few photos:

1. **User object list**: a small editable list (e.g. keys, wallet, glasses,
   passport, charger, medicine box) stored in SQLite, with name, synonyms,
   size class, and whether tracking is on.
2. **Personal enrolment**: for each object, the user takes 3–8 photos of
   their own item (in hand, on a table, from different sides). Image
   embeddings of these photos are stored as the object's "prototypes" and
   used in crop matching alongside the text name.
3. **Laptop side**: a Streamlit page (separate file) to manage the list and
   enrol objects from image files or the webcam.
4. **Phone side**: a simple screen in the app (list + "add photos" with the
   camera) — implemented in Step 15 at the parity gate, designed here.

## Why

- A generic "keys" text prompt matches any keys; the user's own keys with a
  red keyring are far easier to recognise from their own photos. Personal
  enrolment is cheap and usually a large accuracy gain for image-text
  matching (to be measured in Step 05, not assumed).
- A short, user-chosen list keeps the matching problem small and the system
  honest: it tracks what the user asked it to, nothing more (a privacy plus).
- Look-alike objects (two black wallets) can only be separated by personal
  photos, not by names.

## How to implement

1. **Storage**: new table `tracked_objects` (id, name, synonyms_json,
   size_class, enabled, created_at) and `object_prototypes` (id, object_id,
   embedding BLOB or JSON, source_photo_path, created_at). Added through the
   idempotent `init_db()` pattern; coordinated with Phase 5 Step 01 schema v2
   (the two steps must agree on table names — whichever runs first defines
   them, the other references them).
2. **`src/perception/vocab.py`**: `list_objects()`, `add_object()`,
   `enrol_photos(object_id, images)`, `prototypes_for(object_ids)`. Plain
   `sqlite3`, parameterised queries (core.md).
3. **Enrolment embedding**: the Step 02 image-text model; embeddings
   normalised; photos resized the same way as live crops.
4. **Quality check on enrolment**: warn if two objects' prototypes are very
   similar (look-alike warning shown to the user), or if photos are blurry
   (reuse the Phase 4 Tier 0b blur function).
5. **Streamlit page** `src/perception/vocab_app.py` (not inside
   `src/ui/app.py`).
6. **Import** the per-session vocabularies from Phase 3.1 so existing
   recordings can be re-run with the same names.

## Open decisions

- **How many photos per object.** Options: (a) 3 — quick for the user, may
  be too few for varied views; (b) 8 — better coverage, more effort;
  (c) start with 3, suggest more when Step 05 confidence is low for that
  object. Step 05 measures accuracy versus photo count.
- **Prototype use in matching.** Options: (a) text embedding only (no
  enrolment) — baseline; (b) prototypes only; (c) combined score (weighted
  mix of text and prototype similarity) — likely best, one more weight to
  tune. Measured in Step 05.
- **Enrolment photos stored or only embeddings.** Options: (a) keep photos —
  lets us re-embed when the model changes; (b) embeddings only — less
  storage, more private; (c) keep photos in app-private storage, deletable by
  the user. Draft: (c).

## You test this

1. Enrol your own keys, wallet and charger with 3 photos each on the laptop
   page. Was it quick? Did any warning appear?
2. Enrol a look-alike object (a second similar charger) and check whether the
   look-alike warning appears.
3. Delete one object and confirm its prototypes are gone from the database.

## How this number could be lying

- Enrolment photos taken in the same room as test sessions make matching look
  better than in new places. Step 12 reports held-out results in new places.
- Users will not always enrol objects carefully; test with quick, imperfect
  photos too.

## Verification

- [ ] Tables created idempotently; Phase 1 benchmark scores unchanged.
- [ ] Add / enrol / delete work; deletion removes prototypes and photos.
- [ ] Look-alike and blur warnings work on test cases.
- [ ] Phase 3.1 session vocabularies imported.
- [ ] Files under 300 lines; no direct environment variable reads.

## Files changed

- [NEW] `src/perception/vocab.py`, `src/perception/vocab_app.py`
- [MODIFY] `src/memories/database.py` (new tables via `init_db()`)
- [MODIFY] `Taskfile.yml` — `vocab-app`, `README.md`

## Dependencies

- Step 02 (encoder). Coordinate with Phase 5 Step 01 (schema v2).

## Common issues

- Photos taken with the laptop webcam look different from phone crops;
  allow enrolment from phone photos copied to the laptop.
- Very small objects in enrolment photos: crop to the object before
  embedding (a manual crop box on the page).
