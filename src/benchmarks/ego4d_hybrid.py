"""Hybrid search over caption windows (card EYKO-61), scored with ego4d_eval's NLQ rules.
    task ego4d-hybrid -- [A|B]

Fixed before scoring (20 October 2026):
  windows   the captions of the kept frames in each W-second stretch (W = 15 or 30, CapMem's best was 30), joined
  keywords  Okapi BM25 (k1 1.2, b 0.75) over the windows, words lower-cased, common words dropped
  meaning   bge-small-en-v1.5 (the app's ONNX file and word pieces), [CLS] vector, cosine; the question gets bge's
            search prefix "Represent this sentence for searching relevant passages: "
  pictures  MobileCLIP-S2 text against each kept frame (what the app does today)
  fusion    reciprocal rank fusion, 1 / (60 + rank) summed; a frame takes its window's keyword and meaning ranks
Variants: pictures only, pictures + keywords, pictures + meaning, all three; each window size.
Every variant is then scored with every window-growth setting of ego4d_eval (frame, grow 0.95 ... 0.8).
"""
import json
import math
import re
import sys
from collections import Counter

import numpy as np
import onnxruntime as ort
import open_clip
from tokenizers import BertWordPieceTokenizer

from src.benchmarks import ego4d_eval as ev
from src.benchmarks.ego4d_pipeline import ASSETS

BGE = "D:/eykon-cache/models/bge_small_en_v1.5.onnx"
PREFIX = "Represent this sentence for searching relevant passages: "
STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does", "for", "from", "had", "has", "have", "he", "her", "his", "how", "i", "in", "is", "it", "its", "me", "my", "of", "on", "or", "our", "she", "that", "the", "their", "them", "there", "they", "this", "to", "was", "we", "were", "what", "when", "where", "which", "who", "whom", "why", "will", "with", "you", "your", "am", "been", "being", "into", "than", "then", "these", "those", "up", "down", "out", "off", "over", "under", "again"}
K = 60


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP]


def bm25(query: list[str], docs: list[list[str]], k1: float = 1.2, b: float = 0.75) -> np.ndarray:
    n, avg = len(docs), sum(map(len, docs)) / max(1, len(docs))
    df = Counter(w for d in docs for w in set(d))
    out = np.zeros(n)
    for i, d in enumerate(docs):
        tf = Counter(d)
        for w in query:
            if tf[w]:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                out[i] += idf * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(d) / avg))
    return out


class Bge:
    def __init__(self):
        self.tok = BertWordPieceTokenizer(str(ASSETS / "bge_vocab.txt"), lowercase=True)
        self.session = ort.InferenceSession(BGE, providers=["CPUExecutionProvider"])
        self.cache: dict[str, np.ndarray] = {}

    def __call__(self, text: str) -> np.ndarray:
        if text not in self.cache:
            ids = self.tok.encode(text).ids[:512]
            feed = {"input_ids": np.array([ids], np.int64), "attention_mask": np.ones((1, len(ids)), np.int64), "token_type_ids": np.zeros((1, len(ids)), np.int64)}
            v = self.session.run(None, feed)[0][0, 0]
            self.cache[text] = v / np.linalg.norm(v)
        return self.cache[text]


def ranks(scores: np.ndarray) -> np.ndarray:
    r = np.empty(len(scores), int)
    r[np.argsort(-scores)] = np.arange(len(scores))
    return r


def ranker(sources: tuple[str, ...], width: float, clip_text, bge: Bge):
    def rank(uid: str, kept: list[dict], image: np.ndarray, query: str) -> np.ndarray:
        times = np.array([k["t"] for k in kept])
        fused = np.zeros(len(kept))
        if "pictures" in sources:
            fused += 1 / (K + ranks(image @ clip_text(query)))
        if {"keywords", "meaning"} & set(sources):
            win = (times // width).astype(int)
            ids = sorted(set(win))
            texts = [" . ".join(dict.fromkeys(k["caption"] for k, w in zip(kept, win, strict=True) if w == i)) for i in ids]
            where = {i: j for j, i in enumerate(ids)}
            if "keywords" in sources:
                r = ranks(bm25(words(query), [words(t) for t in texts]))
                fused += 1 / (K + np.array([r[where[w]] for w in win]))
            if "meaning" in sources:
                q = bge(PREFIX + query)
                r = ranks(np.array([bge(t) @ q for t in texts]))
                fused += 1 / (K + np.array([r[where[w]] for w in win]))
        return fused
    return rank


def main(which: str = "A") -> None:
    ev.SET = which
    tok = open_clip.get_tokenizer("MobileCLIP-S2")
    text = ort.InferenceSession(str(ev.TEXT_MODEL), providers=["CPUExecutionProvider"])
    cache: dict[str, np.ndarray] = {}

    def clip_text(q: str) -> np.ndarray:
        if q not in cache:
            cache[q] = text.run(None, {"tokens": tok([q]).numpy().astype(np.int64)})[0][0]
        return cache[q]

    bge = Bge()
    results = {}
    for sources in (("pictures",), ("pictures", "keywords"), ("pictures", "meaning"), ("pictures", "keywords", "meaning")):
        for width in ((30.0,) if sources == ("pictures",) else (15.0, 30.0)):
            name = "+".join(sources) + f" {width:g}s"
            results[name] = ev.nlq_scores(ranker(sources, width, clip_text, bge))
            o = results[name]["objects"]
            print(f"{name:42s} objects grow0.85 R@1 {o['grow 0.85 R@1 0.3']:5.1f}/{o['grow 0.85 R@1 0.5']:5.1f}  "
                  f"R@5 {o['grow 0.85 R@5 0.3']:5.1f}/{o['grow 0.85 R@5 0.5']:5.1f}  hit@1 {o['hit@1']:5.1f}", flush=True)
    ev.OUT.mkdir(parents=True, exist_ok=True)
    (ev.OUT / f"hybrid-{which}.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:])
