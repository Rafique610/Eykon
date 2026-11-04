# Phase 6.5 Step 01 — Ethics and Privacy Design, Supervisor and Ethics Sign-Off

## What

Before any code, a written design for how people data is handled:

1. **Data-flow diagram**: what is captured (keyframes, audio), what is
   derived (face descriptors, voiceprints, names, links), where it is stored
   (app-private storage, encrypted), who can see it (only the user on the
   phone), how long it is kept, how it is deleted.
2. **Principles** (from roadmap v2 and the handoff): opt-in, off by default;
   local only; only user-confirmed names; no bystander naming; deletion of a
   person at any time; no import of identities from other sources.
3. **Consent design**: a consent form for people who agree to be named
   (separate from the recording consent in Phase 3.1 Step 03), and the
   in-app flow that records consent before a name can be attached.
4. **Bystander policy**: faces of people the user has not named are not kept
   beyond a short window (for example a few days) and are never grouped across
   days.
5. **Risk analysis**: misuse scenarios (identifying strangers, covert
   recording, stolen phone) and the controls against each.
6. **Approval**: supervisor review; departmental ethics process if the
   department requires it (asked in Phase 3.1 Step 03 for recordings; asked
   again specifically for biometric data).

## Why

- Faces and voiceprints are biometric data; many universities and laws treat
  them as sensitive. A panel will ask how the design prevents misuse; a
  written answer approved by the supervisor is the right response.
- The handoff explicitly orders "privacy and ethics first".
- If approval does not arrive in time, this document is still a valuable
  thesis section (future work with a responsible design).

## How to implement

1. Write `docs/results/phase-6.5/ethics-design.md` with the sections above and
   a one-page summary for the supervisor.
2. Consent form `docs/results/phase-6.5/people-consent-form.md`.
3. Send to the supervisor; record the reply and any conditions.
4. Map every principle to a concrete control in later steps (a table:
   principle → step → verification).

## Open decisions

- **Retention of unnamed faces.** Options: (a) not stored at all (descriptors
  computed and discarded unless they match a named person) — most private,
  no later naming of past meetings; (b) kept for a few days for naming, then
  discarded (draft); (c) kept until the user reviews them.
- **Encryption method.** Options: (a) Android Keystore-backed encryption of
  the people tables / files — strong, standard; (b) SQLCipher-style encrypted
  database — whole database, extra library and licence check; (c) (a) for
  descriptors only. Draft: (a).

## You test this

1. Read the ethics design as if you were a classmate who might be named. Would
   you agree? What would you want changed?
2. Send the summary to your supervisor (I draft the email; you send it).

## How this number could be lying

- No numbers here. The risk is a design that sounds good but is not
  implemented; the principle → step → verification table makes every promise
  checkable.

## Verification

- [ ] Ethics design with data-flow diagram, principles, consent, bystander
      policy, risks.
- [ ] Consent form written.
- [ ] Supervisor reply recorded (and ethics process outcome if required).
- [ ] Principle → control table complete.

## Files changed

- [NEW] `docs/results/phase-6.5/ethics-design.md`,
  `docs/results/phase-6.5/people-consent-form.md`
- [MODIFY] `README.md`

## Dependencies

- Phase 6 Step 07 (privacy controls this builds on).

## Common issues

- Writing principles that later steps quietly ignore; every later step's
  verification list includes the relevant principle checks.
