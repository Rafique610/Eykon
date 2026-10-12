# Phase 5.2 Step 13 — Answer UI in the App: Level Toggle and Evidence Display

## What

Bring the answer layer to the user on the phone (and the laptop page):

1. **Ask screen v2** (replacing the Phase 2 answer view): question box (text
   or voice, voice via the on-device ASR from Phase 5 Step 04), answer card,
   evidence strip (thumbnails, quote cards with play buttons, "last seen"
   card), confidence wording ("probably"), and a clear refusal card.
2. **Level setting**: "Answer style": Short facts (templates and quotes,
   default per handoff lean) / Smart answers (generative) — with a note on
   battery cost; per-question "explain more" button that re-asks at level G.
3. **Configuration indicator** in a debug section (L0–L3, model calls made,
   time taken) for demos and evaluation.
4. **Accessibility**: large text option, screen-reader labels for evidence,
   works in dark mode.
5. **Folds in Phase 2 Step 06 (full UI)** as decided on 07 October 2026.

## Why

- Evidence-first is a product feature, not only an evaluation rule: users
  trust "your keys are in the bag" when they see the picture.
- A visible, simple level toggle turns the LLM-optional research into a user
  choice ("fast and private" vs "smarter, uses more battery"), which is easy to
  demonstrate to the panel.
- Phase 2 Step 06 (full UI) was open; doing it here builds the UI once, on the
  final answer structure.

## How to implement

1. Kotlin: `answers/` package mirroring `src/answers/` (interface, evidence,
   templates, quotes, refusal; extractive and generative call existing
   runtimes); ViewModel exposes `Answer` state.
2. Compose components: `AnswerCard`, `EvidenceStrip`, `QuoteCard`
   (audio playback from session audio at time t), `LastSeenCard`,
   `RefusalCard`; reuse `RetrievedMemoryCard.kt` where it fits.
3. Settings screen entry for answer style; persisted locally.
4. Laptop: the same layout on the Streamlit evidence page (Step 02).
5. UX review with the **impeccable** skill (frontend review / polish routing
   in AGENTS.md) before the parity gate; visual redesign is out of scope
   unless requested (that would be **ui-ux-pro-max**).
6. Real data only: every value shown comes from the `Answer` record.

## Open decisions

- **Default answer style.** Options: (a) templates and quotes by default,
  generative on request (handoff lean); (b) generative by default on the
  Pixel, templates on the Infinix; (c) decided by Gate 3 numbers (draft — the
  UI supports all three).
- **Voice output.** Options: (a) none — text only; (b) Android on-device
  text-to-speech for answers — natural for glasses later, must be verified
  offline; (c) optional setting. Draft: (c) if offline TTS is verified.

## You test this

1. On the Pixel in airplane mode, ask 10 questions with "Short facts" and the
   same 10 with "Smart answers". Which would you leave on?
2. Tap every evidence item for 3 answers; check playback starts at the right
   moment.
3. Use the app with large text and the screen reader on for 2 questions.

## How this number could be lying

- Demo questions chosen by the developer always look good; the parity gate
  (Step 14) uses the fixed question subset.

## Verification

- [ ] Ask screen v2 with all card types on both phones.
- [ ] Level setting and "explain more" work; refusal card shown correctly.
- [ ] Evidence playback at the right time (±1 s).
- [ ] impeccable review done and findings addressed or listed.
- [ ] No fabricated values in the UI.

## Files changed

- [NEW] `android/.../answers/` package, `android/.../ui/components/AnswerCard.kt`,
  `EvidenceStrip.kt`, `QuoteCard.kt`, `LastSeenCard.kt`, `RefusalCard.kt`
- [MODIFY] `android/.../ui/screens/AskQuestionScreen.kt`,
  `AskQuestionViewModel.kt`, settings screen
- [MODIFY] `src/answers/evidence_page.py`, `README.md`

## Dependencies

- Steps 02–08.

## Common issues

- Audio playback of long session WAVs: seek without loading the whole file
  (`MediaPlayer.seekTo`).
