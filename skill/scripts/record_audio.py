"""Record system audio (WASAPI loopback) into rotating WAV segments.

Writes a valid WAV header every `flush_every` seconds so a crash or a hard kill
still leaves playable files. Stops when the stop flag appears.
"""
import datetime
import os
import struct
import sys
import threading
import time

import pyaudiowpatch as pa

RATE = 44100
CH = 2


def wav_header(nbytes, rate, ch):
    return (b"RIFF" + struct.pack("<I", 36 + nbytes) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, ch, rate, rate * ch * 2, ch * 2, 16) +
            b"data" + struct.pack("<I", nbytes))


class Segment:
    def __init__(self, out_dir, rate, ch):
        self.rate, self.ch = rate, ch
        ts = datetime.datetime.now().strftime("%H%M%S")
        self.path = os.path.join(out_dir, f"audio_{ts}.wav")
        self.f = open(self.path, "wb", buffering=0)
        self.f.write(wav_header(0, rate, ch))
        self.n = 0
        self.t0 = time.time()
        self.t_last_header = 0

    def write(self, data):
        self.f.write(data)
        self.n += len(data)
        if time.time() - self.t_last_header > 15:
            self.t_last_header = time.time()
            self.f.seek(0)
            self.f.write(wav_header(self.n, self.rate, self.ch))
            self.f.seek(0, os.SEEK_END)

    def close(self):
        try:
            self.f.seek(0)
            self.f.write(wav_header(self.n, self.rate, self.ch))
            self.f.close()
        except Exception:
            pass


def main(out_dir, segment_seconds):
    os.makedirs(out_dir, exist_ok=True)
    stop_flag = os.path.join(out_dir, "stop.flag")
    p = pa.PyAudio()
    dev = p.get_default_wasapi_loopback()
    rate = int(dev["defaultSampleRate"])
    ch = min(2, dev["maxInputChannels"])
    stream = p.open(format=pa.paInt16, channels=ch, rate=rate, input=True,
                    input_device_index=dev["index"], frames_per_buffer=1024)
    print(f"audio device: {dev['name']} {rate}Hz {ch}ch", flush=True)
    seg = Segment(out_dir, rate, ch)
    stop_evt = threading.Event()

    def watch():
        while not os.path.exists(stop_flag) and not stop_evt.is_set():
            time.sleep(0.3)
        stop_evt.set()
        try:
            stream.stop_stream()
        except Exception:
            pass

    t = threading.Thread(target=watch, daemon=True)
    t.start()
    try:
        while not stop_evt.is_set() and not os.path.exists(stop_flag):
            data = stream.read(1024, exception_on_overflow=False)
            seg.write(data)
            if time.time() - seg.t0 >= segment_seconds:
                seg.close()
                seg = Segment(out_dir, rate, ch)
    except Exception as exc:
        print("audio loop ended:", repr(exc)[:120], flush=True)
    finally:
        seg.close()
        try:
            stream.stop_stream(); stream.close()
        except Exception:
            pass
        p.terminate()
        print("audio stopped", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]) if len(sys.argv) > 2 else 600)
