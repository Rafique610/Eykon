"""Get the phone's copy of the Phase 1 text embedder (card EYKO-12). Run:

    task export-bge -- [<where to put the .onnx>]

The model is BAAI/bge-small-en-v1.5 (MIT), the same one src/memories/embedder.py loads. Its
repository already holds an ONNX file, so nothing is converted: the file is copied out, checked
against the laptop's embedder, and the phone's tokenizer and encoder get numbers to reproduce:
  android/app/src/main/assets/bge_vocab.txt                  the model's word pieces, one per line
  android/app/src/test/resources/bge/tokens_golden.json      token ids for the test sentences
  android/app/src/androidTest/assets/bge_golden.json         their vectors
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download

from src.config import Settings
from src.memories.embedder import Embedder

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "models/bge_small_en_v1.5.onnx")
VOCAB = Path("android/app/src/main/assets/bge_vocab.txt")
TOKENS = Path("android/app/src/test/resources/bge/tokens_golden.json")
VECTORS = Path("android/app/src/androidTest/assets/bge_golden.json")
SENTENCES = [
    "laptop, chair and keyboard, 7 people, in a classroom, typing on a laptop",
    "car, 2 people, inside a car, walking",
    "nothing recognised",
    "Where are my keys?",
    "dining table, 1 person, in an office, talking to someone",
    "It's 3 o'clock; don't forget the 2nd laptop!",
    "  extra   spaces\tand\nlines  ",
    "café table with a crème brûlée",
    "supercalifragilisticexpialidocious",
    "a",
]


def main() -> None:
    repo = Settings().EMBEDDING_MODEL
    embedder = Embedder()
    tokenizer = embedder._model.tokenizer
    reference = np.array(embedder.embed_batch(SENTENCES), dtype=np.float32)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hf_hub_download(repo, "onnx/model.onnx"), OUT)
    session = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
    print("inputs:", [(i.name, i.type) for i in session.get_inputs()], "outputs:", [o.name for o in session.get_outputs()])

    ids, vectors = [], []
    for sentence in SENTENCES:
        encoded = tokenizer(sentence, truncation=True, max_length=512)
        ids.append(encoded["input_ids"])
        feed = {k: np.array([encoded[k]], dtype=np.int64) for k in ("input_ids", "attention_mask", "token_type_ids")}
        first = session.run(None, feed)[0][0, 0]  # the vector at the [CLS] position is the sentence's vector
        vectors.append(first / np.linalg.norm(first))
    exported = np.array(vectors, dtype=np.float32)
    agreement = (reference * exported).sum(axis=1)
    print(f"file: {OUT} ({OUT.stat().st_size / 1e6:.1f} MB), vector size {exported.shape[1]}")
    print("ONNX against the laptop's embedder, lowest cosine over the sentences:", round(float(agreement.min()), 6))
    if agreement.min() < 0.999:
        raise SystemExit("the ONNX file does not agree with the laptop's embedder")

    VOCAB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hf_hub_download(repo, "vocab.txt"), VOCAB)
    print(f"word pieces: {VOCAB} ({len(VOCAB.read_text(encoding='utf-8').splitlines())} lines)")
    TOKENS.parent.mkdir(parents=True, exist_ok=True)
    TOKENS.write_text(json.dumps({"sentences": dict(zip(SENTENCES, ids))}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    VECTORS.write_text(
        json.dumps({"model": repo, "vectors": {s: [round(float(x), 6) for x in v] for s, v in zip(SENTENCES, exported)}}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("golden files:", TOKENS, VECTORS)


if __name__ == "__main__":
    main()
