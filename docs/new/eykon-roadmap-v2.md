# Eykon Roadmap v2 (Draft for Discussion)

Written 06 October 2026. Planning only. This extends docs/plans/00-roadmap.md. Nothing in the existing plans is deleted; this document says what to add and in what order.

## 1. What we are building now

A fully offline, on-device daily-life helper that watches and listens through a phone (later glasses), remembers what matters, and answers questions with evidence. It is no longer only an object finder. It has one shared core and several scenario packs on top.

Shared core: capture, cheap gates, novelty detection, event segmentation, hierarchical memory, state tracking, time-aware retrieval, evidence-first answers.

Scenario packs, each with its own questions and its own scores:
- Pack A, objects and daily life: where are my keys, what did I do after lunch, did I see X.
- Pack B, meetings: record a roughly 30 minute meeting, know who spoke, give a summary with action items.
- Pack C, classroom: a lecture is a meeting with one main speaker plus slides or a whiteboard. Questions like what did the teacher say about topic X.
- Pack D, people (stretch only): faces and voices that the user names. Off by default, local only.

## 2. Design principles

1. Pre-recorded video and audio first. Live capture comes later, but replay at real speed so backlog problems still show up.
2. One fixed record format (slot schema) between perception and memory. Whatever produces the record, a small vision-language model or a cheap perception stack, writes the same fields, so they can be compared fairly.
3. LLM-optional. Everything that can work without a generative model should. A generative model is a switchable layer, and we measure exactly what it adds.
4. Evidence first. Every answer shows time, picture or quoted words. Summaries link back to timestamps.
5. Probes before commitments. The risky unknowns get small cheap tests before big phases are built on them.
6. Honest measurement. Minimum 30 questions and 30 minutes per condition, worst case reported, held-out data, human checks. Every step has a "how this number could be lying" section.

## 3. The LLM question as an experiment

Configurations compared on the same data and questions:
- L0: no generative model anywhere. Cheap perception, rules, templates, quoted text.
- L1: L0 plus a small extractive answer model.
- L2: L0 perception, generative model for answers and summaries only.
- L3: vision-language model for extraction plus generative answers (the current plan).

Metrics: accuracy per question type, latency, RAM, battery and thermal on both phones, model calls per hour. Honest note: speech recognition is a neural model and stays in every configuration. It is a recogniser, not a reasoning assistant.

## 4. Phase map

Existing phases keep their numbers. New phases use decimals, the same way Phase 1.1 was added.

Tier meaning: must means needed for a defensible project, should means strongly wanted, stretch means only if time remains.

### Phase 1, 1.1, 2 (existing)
Text RAG, retrieval improvements, Android port. Phase 2 is mostly done. Keep as is.

### Phase 3, vision pipeline on pre-recorded video (existing, finish it). Tier: must
Remaining steps in this order: 11 (cross-pipeline quality and model comparison), 12 (answer quality with an automated judge, plus human cross-check), 14 (end-to-end mega test), 15 (honest audit of all results), 16 (citation verification and literature review v2), then 13 (re-defense package). Step 14 now also produces the reference numbers for configuration L3.

### Phase 3.1, scenario data and direction probes (new). Tier: must
Goal: get data for all scenario packs and settle the riskiest questions before building.
Draft steps:
1. Scenario and question taxonomy. Add categories: meeting_summary, who_said, action_items, lecture_recall, on top of the existing seven.
2. Public and YouTube data sourcing. Creative Commons only, kept local, licences and platform terms checked, supervisor informed. Candidate public sets to verify: AMI meeting corpus (meetings), EPIC-KITCHENS (kitchen action boundaries), Ego4D subset if licence allows.
3. Own consented recordings: mock meetings (about 30 minutes each), a lecture or study group, plus the egocentric sessions already planned in Phase 4 Step 01.
4. Annotation tooling and ground truth (events, speakers, moves, summaries).
5. Probe A: how often does a small VLM invent or miss objects? About 100 frames, human marked, split by object size and lighting. Decide the unacceptable rate before looking.
6. Probe B: cheap perception (hand tracker plus hand-centred crop matched against object names with image-text embeddings) versus VLM captions on pick-up and put-down events in a 10 minute keys recording.
7. Probe C: speech recognition and speaker separation quality on meeting audio, clean and noisy.
8. Phone sensor spike: reuse Phase 4 Step 03, do not duplicate.
9. Decision note: what each probe showed and which direction is chosen.
Exit: at least 30 questions per category, probe results written honestly, direction agreed with the supervisor.
Risk: data collection takes weeks. Cap it with a time limit.

### Phase 4, keyframe intelligence (existing). Tier: must
Keep the plan (online cascade, ablation B0 to B6, held-out set, phone parity gate). Additions: a hand-activity trigger as an optional extra gate, and plan the extraction step (Step 09) as two paths that write the same record format. Phase 4 Step 01 (dataset) may move earlier or be merged with Phase 3.1; the plan writer should decide.

### Phase 4.1, object interaction tracking (new). Tier: should, depends on Probe B
Goal: detect hold, carry, release, place, take for objects, with no language model, and feed state changes to memory.
Draft steps:
1. Shortlist hand, detector, tracker and image-text encoder models. Each must have a phone-ready version and a licence usable in an app (some popular detector releases are AGPL, check).
2. Hand-centred crop matching against a user-editable list of object names.
3. Object tracking and place recognition (cluster frame embeddings into places, name by text matching or by the user once).
4. Interaction state machine and state-change records.
5. Evaluation against annotated moves, per object size, with occlusion failures listed.
6. Comparison with the VLM path.
Exit: precision and recall reported per object size.
Risk: small and hidden objects. If Probe B fails, shrink or drop this phase and say why.

### Phase 5, hierarchical memory and temporal state (existing). Tier: must
Keep as planned. Additions: the entity-state table also accepts interaction events from Phase 4.1; the router and time parser stay rules-first.

### Phase 5.1, conversation intelligence: meetings and classroom (new). Tier: must (meetings), should (classroom)
Goal: record a 30 minute conversation, then after it ends give a faithful summary with who said what.
Draft steps:
1. Schema extension: sessions, speakers, transcripts, topics.
2. Voice enrolment for "me" (a short sample makes a voiceprint).
3. Speaker separation for the others (speaker 1, 2, 3), evaluated honestly; it will not be perfect.
4. Session start and stop by button first; automatic detection of a meeting later.
5. Aligned transcript with speaker and time.
6. Topic splitting, reusing the change-detection idea from video.
7. Chunked summaries and action items, each line linked to its timestamp, run after the session or while charging.
8. Slide and whiteboard capture: slide changes are keyframes, text read by OCR.
9. Human faithfulness audit of summaries (made-up items, wrong speakers).
10. Classroom variant and lecture questions.
11. Phone parity for the after-session processing.
Exit: at least 10 meetings or lectures judged by humans, error types counted.
Risk: noisy audio, overlapping speech, small models summarising badly.

### Phase 5.2, answer layer and LLM-optional evaluation (new). Tier: must
Goal: show exactly where a generative model helps.
Draft steps: one answer interface with three levels (template, quoted text, generated); template answers from the state table; quoted-text answers for conversations; the optional generative level; run L0 to L3 on all scenario questions; compare latency, memory and battery; write the conclusion whichever way it goes.

### Phase 6, live capture and stress (existing, moved after the above). Tier: must
Add: a full 30 minute live meeting run, a full-day run, thermal and battery on Pixel and Infinix.

### Phase 6.5, people layer: faces and voices (new). Tier: stretch
Face detection and numeric face data on the phone, grouping, the user names a group, "Alex said". Opt-in, local only, only user-confirmed names, deletion supported, ethics section for the panel. Linking a face to the current speaker is hard from a chest or head camera and will be reported with its failures.

### Phase 7, glasses and split computing (existing). Tier: stretch
Can be kept as an analysis or simulation if time is short.

### Phase 8, final evaluation, thesis and defense (existing). Tier: must

## 5. Experiment order

1. Phase 3 honest audit and citation check, so baselines and references are correct.
2. Multi-scenario dataset and question set.
3. Probes A, B, C and the phone sensor spike. Decision note.
4. Gate cascade ablation (uniform sampling versus each added filter).
5. Perception comparison: VLM extraction versus cheap perception and interaction tracking.
6. Memory experiments: state table, time-window search, routing, forgetting, 7-day storage replay.
7. Conversation experiments: speaker labels, topic splitting, summary faithfulness.
8. LLM-optional comparison across all question types (L0 to L3).
9. Held-out test on new places and new meetings, then phone parity gates, then live and thermal stress.
10. Faces and glasses only if time remains.

## 6. Decision gates

- Gate 1, after Phase 3.1: is the VLM invention rate acceptable, is the cheap hand-centred method viable, is speaker separation usable? Decides Phase 4.1 scope and Phase 5.1 depth.
- Gate 2, after Phase 4 ablation: does the cascade beat uniform sampling on the held-out set?
- Gate 3, after Phase 5.2: is the LLM needed, and for which question types? Decides the final system claim.
- Gate 4, after the phone parity gates: do results hold on both phones?

## 7. If time runs short, cut in this order

Faces (Phase 6.5), glasses (Phase 7), classroom variant, automatic meeting detection, Phase 4.1 (keep only the probe result), semantic memory in Phase 5. Do not cut: the cascade ablation, the state table, meeting summaries with honest evaluation, the LLM-optional comparison, the held-out test.

## 8. Mapping to the panel's three complex-computing components

- Keyframe extraction: the online cascade, with the ablation as evidence.
- Memory hierarchy management: levels, state table, time gating, routing, forgetting.
- Performance and thermal management across image, audio, video and text: scheduling on one phone, the cheap path versus the VLM path, post-session processing for meetings while charging.

## 9. Open questions

- Final defense date and weeks available.
- Who can be recorded with consent, and how many mock meetings are realistic.
- Whether the supervisor accepts "LLM-optional with measured comparison" or insists on zero LLM.
- Whether YouTube downloads are acceptable to the department.
- Which phone is the primary target if time forces a choice.
