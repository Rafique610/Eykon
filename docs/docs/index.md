# Knowledge Domain Map

## Project: Eykon (F26-220)

A "second brain": a persistent, local-first memory for a phone. It reads video and sound, keeps the moments worth remembering, and answers questions with proof ("where are my keys?") — everything runs offline on the device. Cheap specialised models do the perception; a vision-language model is an optional, measured alternative.

## Current plan

The active task list is the **Synverk board** (project Eykon, key `EYKO`), reached through the `synverk` MCP server in `.mcp.json`. Read the card and its flow before working. `docs/plans/` is background and method; where it disagrees with a card, the card wins.

## Domain Documents

| Domain | Document | Status |
|---|---|---|
| Eykon (this project) | [`docs/domain/eykon/index.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/domain/eykon/index.md) | ✅ Active |

## Invariant Rules

| Scope | Document | When to Load |
|---|---|---|
| Universal | [`docs/invariants/core.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/invariants/core.md) | Always |
| Python / backend | [`docs/invariants/backend.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/invariants/backend.md) | Any Python / service work |
| Streamlit / UI | [`docs/invariants/frontend.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/invariants/frontend.md) | Any UI work |
| Credentials, DB | [`docs/invariants/security.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/invariants/security.md) | Auth, DB, secrets |
| uv, Taskfile, paths | [`docs/invariants/tooling.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/invariants/tooling.md) | Package mgmt, build, Docker |
| Plans, ADRs, cadence | [`docs/invariants/processes.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/invariants/processes.md) | Planning, commits, memory log |

## Architecture Docs

| Document | Purpose |
|---|---|
| [`docs/additional/architecture-overview.md`](file:///c:/Users/rafique_/Desktop/New%20folder/FYP_Demo/docs/additional/architecture-overview.md) | Phase 1 pipeline diagram & data flow |

## Plans

| Phase | Location | Status |
|---|---|---|
| Phase 1 (Text RAG) | `docs/plans/done/` | ✅ Complete |
| Phase 2 (Android + Audio) | `docs/plans/phase 2/` | Steps 01–05 done; rest folded into the phone gate |
| Phase 3 (VLM vision pipeline) | `docs/plans/phase-3-vision/` | Steps 01–10 done; kept as the VLM reference |
| Roadmap and phases 3.1 – 8 | `docs/plans/00-roadmap.md`, `docs/plans/phase-*/` | Background and method, not the active task list |
| Cheap-model pipeline, evaluation, phone gate | Synverk cards `EYKO-1` … `EYKO-35` | Active |
