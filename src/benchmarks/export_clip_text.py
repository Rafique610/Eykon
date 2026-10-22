"""Export MobileCLIP-S2's text encoder to ONNX for the phone (core of card EYKO-19).

    task export-clip-text -- [<where to write the .onnx>]

Same weights and licence as the image encoder (Apple Machine Learning Research Model License:
research and academic use only; the file is pushed to the phone by hand, never packaged).

Also writes what the phone's own tokenizer and encoder must reproduce:
  android/app/src/main/assets/clip_bpe_merges.txt       the tokenizer's merge rules, one per line
                                                        (from OpenAI CLIP's vocabulary, MIT)
  android/app/src/test/resources/clip/tokens_golden.json   token ids for the test sentences
  android/app/src/androidTest/assets/clip_text_golden.json their vectors
"""
import gzip
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import open_clip
import torch
from open_clip.tokenizer import default_bpe
from timm.utils import reparameterize_model

MODEL, PRETRAINED = "MobileCLIP-S2", "datacompdr"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "models/mobileclip_s2_text.onnx")
MERGES = Path("android/app/src/main/assets/clip_bpe_merges.txt")
TOKENS = Path("android/app/src/test/resources/clip/tokens_golden.json")
VECTORS = Path("android/app/src/androidTest/assets/clip_text_golden.json")
SENTENCES = [
    "a person wearing a motorcycle helmet",
    "where are my keys?",
    "a backpack on a desk",
    "Two people talking in a classroom.",
    "my phone, wallet & glasses",
    "it's 3 o'clock; don't forget the 2nd laptop!",
    "  extra   spaces\tand\nlines  ",
    "café table with a crème brûlée",
    "a",
    "supercalifragilisticexpialidocious antidisestablishmentarianism",
]


class TextEncoder(torch.nn.Module):
    """Token ids in (1 x 77), unit-length vector out."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, tokens):
        return torch.nn.functional.normalize(self.model.encode_text(tokens), dim=-1)


def main() -> None:
    # The encoder finds the end-of-text marker with argmax over the token ids. The phone's ONNX
    # Runtime (1.18, Android) has no ArgMax for whole numbers, so the ids are compared as
    # decimals instead; every id is far below the size where that could change the answer.
    import open_clip.transformer as transformer
    pool = transformer.text_global_pool
    transformer.text_global_pool = lambda x, text=None, *args, **kwargs: pool(x, None if text is None else text.float(), *args, **kwargs)

    model, _, _ = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED, device="cpu")
    tokenizer = open_clip.get_tokenizer(MODEL)
    print("tokenizer:", type(tokenizer).__name__, "length", tokenizer.context_length, "start", tokenizer.sot_token_id, "end", tokenizer.eot_token_id)
    encoder = TextEncoder(reparameterize_model(model.eval())).eval()
    tokens = tokenizer(SENTENCES)
    with torch.no_grad():
        reference = encoder(tokens).numpy()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(encoder, tokens[:1], str(OUT), input_names=["tokens"], output_names=["embedding"], opset_version=17, dynamo=False)
    session = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
    exported = np.concatenate([session.run(None, {"tokens": tokens[i : i + 1].numpy()})[0] for i in range(len(SENTENCES))])
    agreement = (reference * exported).sum(axis=1)
    print(f"file: {OUT} ({OUT.stat().st_size / 1e6:.1f} MB), vector size {exported.shape[1]}")
    print("ONNX against PyTorch, lowest cosine over the sentences:", round(float(agreement.min()), 6))
    if agreement.min() < 0.999:
        raise SystemExit("the exported model does not agree with the original")

    # The merge rules the tokenizer uses: the same slice of the vocabulary file open_clip reads.
    lines = gzip.open(default_bpe()).read().decode("utf-8").split("\n")
    merges = lines[1 : 49152 - 256 - 2 + 1]
    MERGES.parent.mkdir(parents=True, exist_ok=True)
    MERGES.write_text("\n".join(merges) + "\n", encoding="utf-8", newline="\n")
    print(f"merge rules: {MERGES} ({len(merges)} lines, {MERGES.stat().st_size / 1e3:.0f} KB)")

    ids = [[int(t) for t in row if t != 0] for row in tokens]
    TOKENS.parent.mkdir(parents=True, exist_ok=True)
    TOKENS.write_text(json.dumps({"context_length": tokenizer.context_length, "sentences": dict(zip(SENTENCES, ids))}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    VECTORS.write_text(
        json.dumps({"model": f"{MODEL}/{PRETRAINED}", "vectors": {s: [round(float(x), 6) for x in v] for s, v in zip(SENTENCES, exported)}}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("golden files:", TOKENS, VECTORS)


if __name__ == "__main__":
    main()
