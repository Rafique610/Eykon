# Step 01 — Literature Review & Research Document

## What
Produce a formal Literature Review (LR) document covering the academic and industry landscape for on-device VLMs, mobile AI inference, and RAG-based memory systems. This directly addresses the panel's #1 criticism.

## Why
The panel explicitly stated: *"Literature review (LR) is missing and must be added."* This document becomes part of the re-defense submission.

## How to Implement

### 1.1 Research Topics to Cover

| Topic | Key Papers / Systems to Reference |
|---|---|
| Vision-Language Models (VLMs) | LLaVA (Liu et al. 2023), MobileVLM (Chu et al. 2024), Moondream2, PaliGemma (Beyer et al. 2024) |
| On-device / Edge AI Inference | MLC-LLM, ExecuTorch (Meta), LiteRT (Google), llama.cpp, ONNX Runtime Mobile |
| Quantization for Mobile | GPTQ, AWQ, GGUF format, QLoRA, BitsAndBytes — quality vs compression tradeoffs |
| RAG (Retrieval-Augmented Generation) | Lewis et al. 2020 (original RAG), Hybrid Search (BM25 + Dense), Cross-Encoder Re-ranking |
| Lifelong / Episodic Memory Systems | EgoMem, MemoryBank, personal knowledge bases |
| Thermal / Energy Management on Mobile | Mobile SoC thermal throttling, NPU delegation strategies, duty cycling |
| Competitor Analysis | Google Gemini (cloud), Apple Intelligence (on-device), "Gamma" (as cited by panel) |

### 1.2 Document Structure

```
docs/additional/literature-review.md

1. Introduction
2. Vision-Language Models
   2.1 Cloud-scale VLMs (GPT-4o, Gemini Pro)
   2.2 Edge-optimized VLMs (Moondream2, PaliGemma, MobileVLM)
   2.3 Why edge models are required (privacy, latency, offline)
3. Model Compression & Quantization
   3.1 INT8, INT4, GGUF format
   3.2 Quality-compression tradeoff literature
4. Mobile AI Inference Runtimes
   4.1 LiteRT-LM (Google) — our choice, validated in Phase 1
   4.2 MLC-LLM, ExecuTorch, llama.cpp
   4.3 NPU vs GPU vs CPU delegation
5. RAG Architecture for Personal Memory
   5.1 Dense retrieval + BM25 fusion
   5.2 Cross-encoder re-ranking
   5.3 Our Phase 1 benchmark results as evidence
6. Thermal & Energy Constraints on Mobile Devices
   6.1 Duty cycling and frame sampling strategies
   6.2 Context window management (sliding window, summary eviction)
7. Competitor Analysis
   7.1 Cloud-based solutions
   7.2 Gamma and similar local-first assistants
   7.3 Our differentiation: fully offline, source-agnostic RAG
8. Conclusion & Gap Analysis
```

### 1.3 Output File
- `docs/additional/literature-review.md`

## Verification
- [ ] Document is >3000 words
- [ ] Covers all 7 topics from the table above
- [ ] References at least 15 academic papers / technical reports
- [ ] Includes a comparison table: our approach vs competitors
- [ ] Panel's specific concerns (context window, compute, thermals, Gamma) are each addressed in dedicated subsections

## Files Changed
- [NEW] `docs/additional/literature-review.md`

## Dependencies
- None (research step only, no code changes)

## Common Issues
- Avoid making the LR a generic "AI overview" — it must be targeted at our specific problem (on-device VLM + RAG for personal memory)
- Every section should conclude with "how this relates to our project"
