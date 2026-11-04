# Phase 6 Step 08 — Network-Zero Verification

## What

Prove the KPI "runtime network calls: 0" (roadmap §7) with evidence, not
assertion:

1. **Manifest check**: the app's `INTERNET` permission status; if the
   permission exists (for example for model download), the runtime paths are
   shown never to use it.
2. **Airplane-mode runs**: every live experiment in this phase runs in
   airplane mode with Wi-Fi off; results include the airplane state read from
   settings.
3. **Network logging run**: one full live hour with Wi-Fi **on** and a
   network monitor (for example Android's per-app data usage counters, and a
   local VPN-based traffic logger or `adb` network statistics — method chosen
   below) showing zero bytes sent by the app during capture, processing and
   answering.
4. **Speech path check**: confirm that no component uses Android's online
   `RecognizerIntent` path at runtime (the Phase 2 voice path is replaced by
   the on-device ASR from Phase 5 Step 04); the old path is removed or behind
   a clearly labelled developer setting.
5. **Dependency audit**: list every library in the app and whether it can
   make network calls (analytics, crash reporting); remove or disable any that
   can.

## Why

- "Fully offline" is the project's core claim and a main difference from
  LightMem-Ego (which relies on cloud APIs). The panel can test it by asking
  for airplane mode in the demo; we should have tested it more strictly first.
- The roadmap issue list (§9 item 1) already flagged `RecognizerIntent` as a
  possible online path; this step closes that issue with evidence.

## How to implement

1. Write the method and results in `docs/results/phase-6/network-zero.md`.
2. Remove or gate the `NativeSpeechRecognizer` (`RecognizerIntent`) path in
   release builds.
3. Gradle dependency list review; any network-capable library documented.
4. Network logging hour on the Pixel (and a shorter check on the Infinix).

## Open decisions

- **Traffic logging method.** Options: (a) Android data-usage counters per
  app — built in, coarse; (b) a local VPN-based logger app — per-connection
  detail, an extra app on the phone; (c) `adb shell dumpsys netstats` before
  and after — scriptable, coarse. Draft: (a) + (c), (b) if any traffic
  appears.
- **INTERNET permission.** Options: (a) remove it entirely; models are copied
  over USB — strongest claim; (b) keep it only for an explicit "download
  models" button — practical, needs proof that runtime paths never use it;
  (c) separate downloader app. Draft: (a) if feasible.

## You test this

1. Turn Wi-Fi on, run memory for an hour, then check the app's data usage in
   Android settings. It should be zero.
2. Try voice input in airplane mode; it must work.

## How this number could be lying

- Data-usage counters may round small amounts to zero; the `netstats` method
  adds byte-level counts.
- One hour of logging may miss rare paths (crash reporting on a crash); the
  dependency audit covers those.

## Verification

- [ ] All Phase 6 live runs recorded in airplane mode.
- [ ] One-hour network logging run with zero bytes from the app.
- [ ] `RecognizerIntent` path removed or gated; on-device ASR in use.
- [ ] Dependency audit written.
- [ ] INTERNET permission decision recorded.

## Files changed

- [MODIFY] `AndroidManifest.xml`, `android/app/build.gradle.kts`,
  `NativeSpeechRecognizer.kt` usage
- [NEW] `docs/results/phase-6/network-zero.md`
- [MODIFY] `README.md`

## Dependencies

- Step 03; Phase 5 Step 04 (on-device ASR).

## Common issues

- Google Play services can make calls on behalf of apps (for example ML Kit
  model downloads); any ML Kit component must use bundled models, checked
  here.
