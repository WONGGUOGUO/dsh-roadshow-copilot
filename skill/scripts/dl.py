"""Parallel ranged downloader with retry. Usage: python dl.py URL DEST [threads]"""
import os, ssl, sys, time, threading, urllib.request

CTX = ssl._create_unverified_context()

def head(url):
    r = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30, context=CTX)
    return int(r.headers["Content-Length"])

def download(url, dst, n=8):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    total = head(url)
    if os.path.exists(dst) and os.path.getsize(dst) == total:
        print("already complete", dst, total)
        return
    chunk = total // n + 1
    lock = threading.Lock()
    done = [0]
    errors = []

    def worker(i, start, end, path):
        for attempt in range(6):
            try:
                pos = start
                if os.path.exists(path):
                    pos += os.path.getsize(path)
                if pos > end:
                    break
                req = urllib.request.Request(url, headers={"Range": f"bytes={pos}-{end}"})
                r = urllib.request.urlopen(req, timeout=60, context=CTX)
                with open(path, "ab") as f:
                    while pos <= end:
                        b = r.read(256 * 1024)
                        if not b:
                            break
                        f.write(b); f.flush(); pos += len(b)
                        with lock:
                            done[0] += len(b)
                if pos > end:
                    break
            except Exception as e:
                print(f"part{i} retry {attempt}: {repr(e)[:100]}", flush=True)
                time.sleep(2)
        else:
            errors.append(i)

    threads = []
    t0 = time.time()
    for i in range(n):
        s = i * chunk; e = min((i + 1) * chunk - 1, total - 1)
        if s > e:
            break
        t = threading.Thread(target=worker, args=(i, s, e, dst + f".part{i}"))
        t.start(); threads.append(t)

    while any(t.is_alive() for t in threads):
        time.sleep(10)
        el = time.time() - t0
        print(f"{done[0]/1e6:.1f}MB {done[0]/el/1e6:.2f}MB/s", flush=True)

    if errors:
        raise SystemExit(f"parts failed: {errors}")
    with open(dst, "wb") as out:
        for i in range(n):
            p = dst + f".part{i}"
            if os.path.exists(p):
                with open(p, "rb") as f:
                    while True:
                        b = f.read(1 << 20)
                        if not b: break
                        out.write(b)
                os.remove(p)
    print("final", os.path.getsize(dst))

if __name__ == "__main__":
    download(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 8)
