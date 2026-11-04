# Option C candidates: licence and phone format (14 October 2026)

**In one line:** four vision-language models can run on the phone in the format the app already
uses for Gemma (LiteRT-LM), all with licences that allow this project; SmolVLM and Florence-2 have
ONNX files but would need our own text-generation loop; Moondream2 and the Qwen2.5 and Qwen3
models are left out for now.

Checked from each Hugging Face repository's own metadata, file list and licence text. Nothing
was downloaded and nothing was run, so none of this says how well or how fast a model works.

## What was found

| Model | Licence (read from the repository) | Phone-ready file | Size | Runtime the app would need |
|---|---|---|---|---|
| Gemma 4 E2B (`litert-community/gemma-4-E2B-it-litert-lm`) | Apache-2.0 | `.litertlm`, already on the Pixel | 2.59 GB | LiteRT-LM, already in the app |
| Gemma 4 E4B (`litert-community/gemma-4-E4B-it-litert-lm`) | Apache-2.0 | `.litertlm` | 3.66 GB | LiteRT-LM |
| Qwen2-VL-2B (`litert-community/Qwen2-VL-2B`, from `Qwen/Qwen2-VL-2B-Instruct`) | Apache-2.0 | `.litertlm` (updated 7 Oct 2026) | 1.78 GB | LiteRT-LM |
| LFM2.5-VL-450M (`litert-community/LFM2.5-VL-450M`) | LFM Open License v1.0 | `.litertlm`, int4 and int8 | 407 MB (int4), 564 MB (int8) | LiteRT-LM |
| LFM2.5-VL-1.6B (`litert-community/LFM2.5-VL-1.6B`) | LFM Open License v1.0 | `.litertlm`, int4 and int8 | 1.30 GB (int4), 1.81 GB (int8) | LiteRT-LM |
| SmolVLM-256M / 500M, and SmolVLM2 (`HuggingFaceTB/...`) | Apache-2.0 | ONNX in the official repository: vision encoder, token embedding, decoder, several precisions | 256M: about 200 MB at 4-bit; 500M: about 500 MB at 4-bit | ONNX Runtime (in the app) plus a text-generation loop we write |
| Florence-2 base / large (`onnx-community/...`, from `microsoft/...`) | MIT | ONNX: encoder and decoder, several precisions | base: about 250 MB at 4-bit; large: about 700 MB at 4-bit | ONNX Runtime plus a generation loop and its own tokenizer |
| Moondream2 (`vikhyatk/moondream2`) | Apache-2.0 | None: weights only (3.85 GB). A GGUF repository exists from April 2024 with no licence stated | 3.75 GB (GGUF, f16) | llama.cpp, not in the app |
| Qwen3-VL-2B (`Qwen/Qwen3-VL-2B-Instruct`) | Apache-2.0 | Official GGUF; an `onnx-community` ONNX copy with no licence or description in it | about 1 to 2 GB at 4-bit | llama.cpp, or ONNX from an unofficial copy |
| Qwen2.5-VL-3B (`Qwen/Qwen2.5-VL-3B-Instruct`) | Qwen Research License: non-commercial, research or evaluation only | Not checked further | | |

Sizes are those of the listed files; the ONNX ones are the sum of the parts needed at 4-bit and
are approximate.

## The licences in plain words

- **Apache-2.0 and MIT** (Gemma 4, Qwen2-VL, SmolVLM, Florence-2, Moondream2, Qwen3-VL): free
  to use, change and share, including in a product, keeping the notices.
- **LFM Open License v1.0** (both LFM2.5-VL models): Apache-like; commercial use is allowed only
  for organisations with less than 10 million US dollars of yearly revenue. A university
  project is well inside it.
- **Qwen Research License** (Qwen2.5-VL-3B): research and evaluation only, like the MobileCLIP
  weights we already use. Allowed for this project, but there is an Apache-2.0 Qwen at the same
  size, so there is no reason to take it.
- **No AGPL** anywhere in the list.

## Shortlist

**On the phone, with nothing new in the app:** Gemma 4 E2B (the baseline), Qwen2-VL-2B, and
LFM2.5-VL-450M as the small end. LFM2.5-VL-1.6B and Gemma 4 E4B if time allows. All five use the
LiteRT-LM runtime the app already has, so trying one is a file push and a few lines of code.

**Laptop first:** Florence-2 base, because besides captions it can find named things in a
picture, which goes at the small-object gap, and SmolVLM-256M as the smallest model of all.
Both would need a text-generation loop written for the phone, so they only go further if the
laptop shows they are worth it.

**Left out for now:** Moondream2 and Qwen3-VL-2B (no phone format that the app can run without
adding llama.cpp, or only an unofficial copy), Qwen2.5-VL-3B (research-only licence when an
Apache-2.0 alternative exists).

## Open questions before trying them

- The app uses LiteRT-LM 0.16.1. The Qwen2-VL and LFM2.5-VL files were updated in October 2026
  and may need a newer runtime; this is only known by trying.
- The LFM repositories have files named `_fixB` next to the plain ones; their model cards need
  reading to know which to use.
- Gemma 4 E2B on the Pixel uses the general file; the repository also has files built for
  Tensor G5 and G6 chips, not for the Pixel 9's Tensor G4.
