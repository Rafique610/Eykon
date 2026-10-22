# Handoff: Context for the Model That Will Write the Detailed Plans

Written 06 October 2026. You are a strong language model reading this before writing detailed phase and step plans for the Eykon final year project. Read this whole file first. It explains what exists, what was decided, what is still open, and exactly what to produce. Read eykon-roadmap-v2.md next; it holds the phase list this file refers to.

## 0. How to work

1. Read this file, then eykon-roadmap-v2.md, then the existing plan files named in section 3 as needed.
2. Before writing anything, ask the user the questions in section 7 (all at once, short). Do not guess answers to them.
3. Then write the documents listed in section 8, in that order, one phase at a time, and wait for the user to approve each phase before starting the next.
4. Flag problems instead of silently fixing them. Never delete existing plans; annotate them.

The user is a CS student. Explain in plain, beginner-friendly prose, avoid jargon without definition, and avoid decorative formatting (no emoji, little bold). Plan documents themselves follow the format in section 8.

## 1. The project in brief

Eykon is a fully offline, on-device system that perceives through an egocentric camera and microphone, decides online (no look-ahead) which moments are worth remembering, stores structured timestamped memory in SQLite, tracks object and entity state as the world changes, and answers questions by text or voice with evidence and zero network calls at runtime. Laptop is the lab, phones are the exam (Pixel 9 Pro XL as flagship, Infinix Note 12 as low end), glasses are a later capture device.

New direction decided in discussion: it is a general daily-life helper made of one shared core and scenario packs (objects and daily life, meetings, classroom, and a stretch pack for named people). Work on pre-recorded video and audio first, live capture later.

Panel feedback (latest): the idea is good and well defended, but do we really need an LLM? They named three possible complex-computing components: video keyframe extraction, memory hierarchy management, and performance and thermal management across image, audio, video and text with a local model. The supervisor asked to explore doing the project without an LLM, using embeddings, object detection and tracking. Our answer, still to be proven by experiment: make the LLM optional and measure what it adds (configurations L0 to L3 in the roadmap).

## 2. Current state

- Phase 1 done: text RAG with SQLite, bge-small embeddings, FTS5 plus dense with reciprocal rank fusion, query expansion, wider pool, cross-encoder rerank. Benchmark on 499 memories and 30 questions: Hit@5 93.3 percent, MRR 0.834.
- Phase 1.1 done (steps 09 to 12).
- Phase 2 Android app: mostly done (Room, LiteRT-LM Gemma 4 E2B generation, text and voice capture). Check the domain index for its true status.
- Phase 3 steps 01 to 10 done (literature review v1, environment, frame extraction, captioning, orchestrator, memory integration, Streamlit video page, benchmark suite, experiments A1 to A3, laptop soak test A4). Remaining: 11, 12, 14, 15, 16, then 13.
- Phases 4 and 5 are planned at plan level (13 and 12 step docs). Phases 6 to 8 are only described in the roadmap.
- Known device facts: Infinix averaged 4.68 W and 58.9 C SoC in a query-only run; Pixel 4.7 s per query and 1.42 W. The Phase 3 soak test ran 136 frames in 30 minutes on a fan-cooled laptop (13.3 s per frame, about 0.075 fps), so live captioning with that setup is impossible without gating.

## 3. Inventory of the existing documents

Rules and routing
- AGENTS.md: the single source of working rules. Routes to docs/invariants. Cadence: one step at a time, test yourself, explain in plain language, give the user terminal commands, wait for approval, rename approved step docs with a check mark, never commit without user confirmation, never add the agent as co-author.
- INSTRUCTIONS.md: the older detailed rules. AGENTS.md says it was split and superseded, but it still contains rules (README update every step, .memory/tasks.md logging, Ponytail ladder, uv and pnpm, two-stage Docker). Treat AGENTS.md and docs/invariants as primary, INSTRUCTIONS.md as background.
- docs/invariants/core.md (always load): feature-based folders, files under about 300 lines, real data only, Ponytail ladder (laziest working solution), settings through Pydantic with MEMORY_ prefix, parameterised SQLite, phase parity, no silent destructive actions.
- backend.md, frontend.md, security.md, tooling.md, processes.md: stack rules. processes.md defines how plans are written (section 8 below).
- Two files called index.md: docs/docs/index.md (knowledge map, outdated phase statuses) and docs/domain/eykon/index.md (project facts, constants, key decisions, also outdated).

Project background
- new_Dev.md: a brainstorming chat transcript. Source of the original architecture and ideas. Contains citations and numbers that could not all be verified (see section 5). Do not copy from it without verification.
- architecture-overview.md: Phase 1 only and outdated (mentions Ollama and old folder names).
- literature-review.md (v1): generic, several references unverifiable.
- 00-roadmap.md: master roadmap for Phases 3 to 8 (research problems P1 to P4, laptop-versus-phone protocol, three-layer testing, pessimist rules, global targets, open decisions, issue list). Still valid; roadmap v2 extends it.

Plans
- Phase 1: 01-phase1-implementation.md plus steps 01 to 08. Done; some step docs still say "Not started" or mention Ollama although the final system uses LiteRT-LM.
- Phase 1.1: 02-phase1.1-retrieval-improvement.md plus steps 09 to 12 (done). Step 12 holds the final evaluation numbers.
- Phase 2: 00-phase2-implementation.md plus steps 01 to 07 (Android).
- Phase 3: 00-phase3-vision-pipeline.md (carries a realignment note dated 05 October 2026) plus steps 01 to 16. Steps 11, 12, 14 carry realignment notes. Step 15 (honest audit) and 16 (citation verification) are new.
- Phase 4: 00-phase4-keyframe-intelligence.md plus steps 01 to 13 (dataset, emulation harness, phone sensor spike, uniform baseline, gates 0a/0b/0c, embedding novelty, structured extraction, segmenter, ablation, held-out test, phone parity).
- Phase 5: 00-phase5-hierarchical-memory.md plus steps 01 to 12 (schema v2, current memory, short-term store, audio, episodic consolidation, semantic memory, state table, temporal queries, router, lifecycle, evaluation, parity).

## 4. Decisions already made

- General daily-life helper: shared core plus scenario packs. Faces and glasses are stretch.
- Pre-recorded first, live later, replayed at wall-clock speed.
- LLM-optional design with one fixed slot schema between perception and memory; compare L0 to L3.
- Meetings (about 30 minutes) are the committed new niche: speaker labels, post-session summary with timestamp links. Classroom is a variant.
- Keep the Phase 4 cascade and the Phase 5 hierarchy and state table.
- Use the roadmap rules: mobile emulation profile, parity gate at the end of each phase, three-layer testing, pessimist rules.

## 5. Traps and inconsistencies to handle

- Phase step numbers collide across phases (several phases have a step 12). Always say "Phase X Step Y".
- File names carry a check mark or underscore prefix for approved steps; some files' internal titles do not match their file number (for example the re-defense package is file 13 but titled Step 12).
- Status fields in older docs are stale (Phase 2 "4 of 7 done", Phase 3 "planned"). Reconcile against the latest logs and ask the user.
- INSTRUCTIONS.md says ORM only for databases; core.md says the actual convention is raw parameterised sqlite3. AGENTS.md asks to confirm uv versus Pixi for tooling. Ask or follow core.md and record the choice.
- new_Dev.md cites papers that could not be found (Mem-Alpha, TokenPilot, "EgoLife on Edge Devices") and quotes LightMem-Ego numbers that differ from the paper (the paper reports R@3 74.1, MRR 0.627, QA accuracy 51.9 percent judged by a model and 55.6 percent by humans, P50 latency 5.86 s on phone for short-term and 14.87 s for long-term). Never use unverified citations or numbers. Phase 3 Step 16 verifies them.
- Phase 3 evidence is thin (3 short clips, 9 questions, laptop only). Do not build on it as if it were strong evidence.
- Some popular detector releases are AGPL licensed. Check licences for anything the app will ship.
- Phase 5 Step 04 flags that phone voice input may use an online recogniser; ambient capture must be verified in airplane mode.

## 6. Open decisions (do not decide silently)

- Detector strategy: fine-tune a small detector, open-vocabulary detector, or hand-centred crop matching. Decided after Probe B.
- Place naming: text matching or user labels.
- FTS on Android: FTS4, FTS5 via a bundled library, or none (roadmap section 8).
- Primary on-device VLM and whether a small one handles provisional captions.
- Speaker separation model and speech recognition language scope (English only or English plus Urdu).
- Citation style (check the department handbook first).
- Whether Phase 4 Step 01 (dataset) merges into Phase 3.1.
- Answer layer default (templates and quotes by default, generative as a toggle is the current lean).

## 7. Ask the user first

1. Final defense date and weeks available. This decides which tiers are real.
2. Can consented mock meetings and a lecture be recorded soon, and how many people can help?
3. Has the supervisor accepted "LLM-optional with a measured comparison"?
4. Is downloading Creative Commons YouTube videos acceptable to the department?
5. Which phone is the primary target if time forces a choice?
6. Should the current Phase 2 status be taken from the latest logs, and where are they?

## 8. What to write

Order, each phase approved before the next:
1. Annotation block on 00-roadmap.md pointing to roadmap v2 (additions only).
2. Phase 3.1 plan: overview file plus step docs.
3. Phase 4 and 4.1 additions: edits (annotations) to existing Phase 4 docs, new overview and steps for 4.1.
4. Phase 5 additions, then Phase 5.1 and 5.2 full plans.
5. Phase 6 and 6.5 plans, then outlines for 7 and 8.
6. Updated experiment register (all experiments, hypothesis, data, metric, success and failure criteria, decision it feeds).

Each step doc must follow the project format from processes.md: What, Why, How to implement, Open decisions (only if genuinely open, each with two or three options and a real trade-off note), You test this (concrete instructions for the user), How this number could be lying, Verification (checkboxes), Files changed, Dependencies, Common issues. Each phase overview needs: goal, why this phase exists, architecture, step table, exit criteria, risks. Steps must be small, testable, with explicit dependencies, and use feature-based folders and the 300 line limit.

## 9. Content briefs for the new phases

Phase 3.1: the point is risk reduction. Define the three probes precisely: sample sizes, who labels, split by object size and lighting, the unacceptable rate fixed in advance, outputs and the decision they feed. Include a data sourcing step with licence and consent handling, and a time cap.

Phase 4.1: model shortlist with verified phone versions and licences; interaction state machine states (appears in hand, carried, released, placed, taken); state-change record fields (entity, attribute, new value, time, confidence, evidence frame); evaluation on annotated moves; failure taxonomy (occlusion, small objects, look-alikes).

Phase 5.1: session model, voice enrolment, speaker separation evaluation, aligned transcripts, topic splitting by embedding change, chunked summarisation with timestamp evidence links, after-session scheduling while charging, slide and whiteboard keyframes with OCR, human faithfulness audit with an error taxonomy, classroom questions. Cover noisy audio and overlapping speech honestly.

Phase 5.2: one answer interface, three levels, configurations L0 to L3, per-question-type tables, latency and energy, and a conclusion section that is written whichever way the data points.

Phase 6.5: privacy and ethics first (opt-in, local, only user-confirmed names, deletion, no bystander naming), then technical steps, then a hard scope limit because it is a stretch.

## 10. Quality bar

- Real data only; no invented numbers, citations or results. If unsure, write "to be measured" or "to be verified".
- Every claim of improvement needs a baseline and at least 30 questions or 30 minutes per condition; report worst cases and held-out results separately.
- Each phase ends with a mobile parity gate on both phones, as in the roadmap.
- Keep steps small enough to finish and test in a few days. If a step needs a research decision, put it in Open decisions with real trade-offs, not a recommendation dressed as a choice.
- State clearly what is must, should and stretch, and what to cut first if time runs short.
- Keep the user's voice in mind: they want to understand every step, and they will defend this to a strict panel.

## 11. Things to verify during writing

Candidate models and tools (confirm each has a phone-ready version and an acceptable licence): hand landmark model, small detectors, trackers, image-text encoders for novelty and crop matching, speech recognition (whisper.cpp tiny and base), voice activity detection, speaker embedding and diarization models, OCR engines. Candidate datasets: AMI, EPIC-KITCHENS, Ego4D subset. Papers: everything in new_Dev.md and literature-review.md must be checked against the real source before use; keep the citation ledger from Phase 3 Step 16 as the single list of verified references.

## 12. Output checklist

- Questions in section 7 asked and answered.
- All new documents follow the step format and numbering, with "Phase X Step Y" references.
- Existing documents annotated, not deleted.
- Inconsistencies in section 5 listed back to the user.
- A summary table at the end: phase, tier, steps, dependencies, gate.
