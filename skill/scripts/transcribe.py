"""Transcribe a captured session with whisper.cpp (pywhispercpp).

Usage:
  python transcribe.py <session_dir> [--model PATH] [--threads N] [--limit-min N]

Reads audio/audio_*.wav (44.1k stereo), converts to 16 kHz mono, runs Whisper
(small by default) and writes transcript.txt + transcript.jsonl.
"""
import argparse
import glob
import json
import os
import re
import sys
import tempfile
import time
import wave

import numpy as np

SR = 16000
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def to_16k_mono(path, out_path):
    with wave.open(path) as w:
        ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    a = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    a = a.astype(np.float32)
    if sr != SR:
        idx = np.arange(0, len(a), sr / SR)
        a = np.interp(idx, np.arange(len(a)), a)
    with wave.open(out_path, "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR)
        o.writeframes(np.clip(a, -32768, 32767).astype(np.int16).tobytes())
    return len(a) / SR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("session")
    ap.add_argument("--model", default=os.path.join(HERE, "models", "whisper", "ggml-small.bin"))
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--limit-min", type=float, default=0)
    ap.add_argument("--language", default="zh")
    args = ap.parse_args()

    vend = os.path.join(HERE, "vendor")
    if os.path.isdir(vend):
        os.add_dll_directory(vend)
        sys.path.insert(0, vend)

    from pywhispercpp.model import Model

    if not os.path.exists(args.model):
        dl = os.path.join(HERE, "scripts", "dl.py")
        sys.exit(
            f"model not found: {args.model}\n"
            "download it once with:\n"
            f'  python "{dl}" '
            "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-small.bin "
            f'"{args.model}" 8')

    model = Model(args.model, n_threads=args.threads, print_progress=False, language=args.language)

    audio_dir = os.path.join(args.session, "audio")
    files = sorted(glob.glob(os.path.join(audio_dir, "audio_*.wav")) or
                   glob.glob(os.path.join(args.session, "audio_*.wav")))
    if not files:
        sys.exit("no audio files")

    out_jsonl = os.path.join(args.session, "transcript.jsonl")
    out_txt = os.path.join(args.session, "transcript.txt")
    total_audio = 0.0
    t0 = time.time()
    tmpdir = os.path.join(args.session, "_tmp16k")
    os.makedirs(tmpdir, exist_ok=True)

    with open(out_jsonl, "w", encoding="utf-8") as jf, open(out_txt, "w", encoding="utf-8") as tf:
        for path in files:
            base = os.path.basename(path)
            base_sec = 0
            m = re.search(r"audio_(\d{2})(\d{2})(\d{2})", base)
            if m:
                base_sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            if args.limit_min and total_audio / 60 >= args.limit_min:
                break
            wav16 = os.path.join(tmpdir, base)
            dur = to_16k_mono(path, wav16)
            total_audio += dur
            segs = model.transcribe(wav16, language=args.language, print_progress=False)
            for s in segs:
                text = (s.text or "").strip()
                if not text:
                    continue
                start = s.t0 / 100.0  # pywhispercpp reports centiseconds
                sec = base_sec + int(start)
                hh, rem = divmod(sec, 3600)
                mm, ss = divmod(rem, 60)
                stamp = f"{hh % 24:02d}:{mm:02d}:{ss:02d}"
                tf.write(f"[{stamp}] {text}\n"); tf.flush()
                jf.write(json.dumps({"t": stamp, "start": round(start, 2), "text": text},
                                    ensure_ascii=False) + "\n"); jf.flush()
            os.remove(wav16)
            print(f"{base} {dur/60:.1f}min done", flush=True)

    dt = time.time() - t0
    print(f"total audio {total_audio/60:.1f} min, wall {dt/60:.1f} min, "
          f"speed x{total_audio/max(dt,1):.2f} realtime", flush=True)


if __name__ == "__main__":
    main()
