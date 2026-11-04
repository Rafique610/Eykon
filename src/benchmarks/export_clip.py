"""Export MobileCLIP-S2's image encoder to ONNX for the phone (card EYKO-6). Run: task export-clip

The weights are Apple's and are under the Apple Machine Learning Research Model License:
non-commercial research and academic use only. The exported file goes to models/ (not in git)
and is pushed to the phone by hand; it must not be put in the app package or released.

Also writes the vectors the phone must reproduce for the test pictures.
"""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import open_clip
import torch
from PIL import Image
from timm.utils import reparameterize_model

MODEL, PRETRAINED = "MobileCLIP-S2", "datacompdr"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "models/mobileclip_s2_image.onnx")  # optional: where to write the file
PICTURES = Path("android/app/src/test/resources/filters")
GOLDEN = Path("android/app/src/androidTest/assets/clip_golden.json")


class ImageEncoder(torch.nn.Module):
    """Picture in (1 x 3 x H x W, values 0 to 1), unit-length vector out."""

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, image):
        return torch.nn.functional.normalize(self.model.encode_image(image), dim=-1)


def main() -> None:
    model, _, preprocess = open_clip.create_model_and_transforms(MODEL, pretrained=PRETRAINED, device="cpu")
    print("preprocessing the phone must copy:\n", preprocess)
    encoder = ImageEncoder(reparameterize_model(model.eval())).eval()

    names = sorted(p.stem for p in PICTURES.glob("*.png"))
    batch = torch.stack([preprocess(Image.open(PICTURES / f"{n}.png").convert("RGB")) for n in names])
    with torch.no_grad():
        reference = encoder(batch).numpy()

    OUT.parent.mkdir(exist_ok=True)
    torch.onnx.export(
        encoder, batch[:1], str(OUT), input_names=["image"], output_names=["embedding"], opset_version=17, dynamo=False,
    )
    session = ort.InferenceSession(str(OUT), providers=["CPUExecutionProvider"])
    exported = np.concatenate([session.run(None, {"image": batch[i : i + 1].numpy()})[0] for i in range(len(names))])
    agreement = (reference * exported).sum(axis=1)
    print(f"file: {OUT} ({OUT.stat().st_size / 1e6:.1f} MB), vector size {exported.shape[1]}")
    print("ONNX against PyTorch, cosine per picture:", {n: round(float(c), 6) for n, c in zip(names, agreement)})
    if agreement.min() < 0.999:
        raise SystemExit("the exported model does not agree with the original")

    GOLDEN.write_text(
        json.dumps({"model": f"{MODEL}/{PRETRAINED}", "input": list(batch.shape[1:]),
                    "vectors": {n: [round(float(x), 6) for x in v] for n, v in zip(names, exported)}}) + "\n",
        encoding="utf-8",
    )
    print("how alike the test pictures are (cosine):")
    for i, a in enumerate(names):
        print(f"  {a:8}", " ".join(f"{float(exported[i] @ exported[j]):.3f}" for j in range(len(names))))


if __name__ == "__main__":
    main()
