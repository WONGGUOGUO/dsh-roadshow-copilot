"""Extract distinct slides from captured frames.

Usage: python slides.py <session_dir> [--threshold 40]
Writes <session_dir>/keyframes/*.jpg and <session_dir>/keyframes.json
"""
import argparse
import glob
import json
import os

import numpy as np
from PIL import Image


def ahash(img, size=16):
    g = img.convert("L").resize((size, size))
    a = np.asarray(g, dtype=np.float32)
    return (a > a.mean()).flatten()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--threshold", type=int, default=40)
    ap.add_argument("--min-gap", type=float, default=0.0)
    args = ap.parse_args()

    src = os.path.join(args.session, "frames")
    dst = os.path.join(args.session, "keyframes")
    os.makedirs(dst, exist_ok=True)
    meta = {}
    for line in open(os.path.join(args.session, "frames.jsonl"), encoding="utf-8"):
        try:
            d = json.loads(line)
            meta[d["file"]] = d
        except Exception:
            pass

    prev = None
    out = []
    for f in sorted(glob.glob(os.path.join(src, "*.jpg"))):
        try:
            im = Image.open(f).convert("RGB")
        except Exception:
            continue
        h = ahash(im)
        diff = 999 if prev is None else int((h != prev).sum())
        if diff > args.threshold:
            name = os.path.basename(f)
            out.append({"file": name, "ts": meta.get(name, {}).get("ts", ""),
                        "title": meta.get(name, {}).get("title", "")})
            im.save(os.path.join(dst, name), "JPEG", quality=90)
            prev = h
    json.dump(out, open(os.path.join(args.session, "keyframes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{len(out)} keyframes")


if __name__ == "__main__":
    main()
