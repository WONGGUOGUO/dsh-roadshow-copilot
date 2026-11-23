"""Repair WAV headers after a hard stop: rebuild RIFF/data sizes from file length."""
import glob
import os
import struct
import sys


def fix(path):
    size = os.path.getsize(path)
    if size <= 44:
        return False
    with open(path, "r+b") as f:
        head = f.read(44)
        if head[:4] != b"RIFF" or head[8:12] != b"WAVE":
            return False
        ch = struct.unpack("<H", head[22:24])[0]
        rate = struct.unpack("<I", head[24:28])[0]
        bits = struct.unpack("<H", head[34:36])[0]
        data = size - 44
        f.seek(4); f.write(struct.pack("<I", 36 + data))
        f.seek(40); f.write(struct.pack("<I", data))
    return True


def main():
    session = sys.argv[1]
    audio_dir = os.path.join(session, "audio")
    files = glob.glob(os.path.join(audio_dir, "*.wav")) or glob.glob(os.path.join(session, "*.wav"))
    fixed = 0
    for p in files:
        if os.path.getsize(p) < 20000:      # < ~0.1s, drop empty tails
            os.remove(p)
            continue
        if fix(p):
            fixed += 1
    print(f"finalized {fixed} wav files", flush=True)


if __name__ == "__main__":
    main()
