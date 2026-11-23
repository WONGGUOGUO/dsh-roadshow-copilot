"""Capture every visible meeting window as JPEG frames (change-detected).

For each tick it enumerates top-level windows whose title matches an allow-listed
keyword, skips minimised or covered windows, and saves a cropped screenshot per
window. Unrelated windows (chat, browser tabs, documents) are never captured.

Frames are tagged with the window title in frames.jsonl so a session that watches
several roadshows at once can still be split per event afterwards.
"""
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import sys
import time
from datetime import datetime

from PIL import ImageGrab

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32
GA_ROOT = 2

# 64-bit safe prototypes (ctypes defaults to int and truncates HWNDs)
user32.GetForegroundWindow.restype = wt.HWND
user32.WindowFromPoint.restype = wt.HWND
user32.WindowFromPoint.argtypes = [wt.POINT]
user32.GetAncestor.restype = wt.HWND
user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsIconic.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]

DEFAULT_KEYWORDS = [
    "腾讯会议", "Tencent Meeting", "Zoom", "Teams", "飞书", "Feishu", "钉钉",
    "小鹅通", "微吼", "路演", "直播", "发布会", "说明会", "推介会", "投资",
]

MAX_WINDOWS = 4          # capture at most this many windows per tick
MIN_W, MIN_H = 480, 320  # ignore tiny windows
SAMPLES = 5              # points probed to decide whether a window is visible


def window_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n == 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def rect_of(hwnd):
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def enum_windows():
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
            title = window_text(hwnd)
            if title:
                found.append((hwnd, title, rect_of(hwnd)))
        return True

    user32.EnumWindows(cb, 0)
    return found


def visible_ratio(hwnd, rect):
    """Fraction of sample points that belong to this window (not covered)."""
    l, t, r, b = rect
    pts = [((l + r) // 2, (t + b) // 2),
           (l + (r - l) // 4, t + (b - t) // 4),
           (r - (r - l) // 4, t + (b - t) // 4),
           (l + (r - l) // 4, b - (b - t) // 4),
           (r - (r - l) // 4, b - (b - t) // 4)]
    hits = 0
    for x, y in pts:
        h = user32.WindowFromPoint(wt.POINT(x, y))
        if h and user32.GetAncestor(h, GA_ROOT) == hwnd:
            hits += 1
    return hits / len(pts)


def slug(title):
    keep = [c for c in title if c.isalnum()][:12]
    return "".join(keep) or "win"


def main(out_dir, keywords, interval, duration):
    frames_dir = os.path.join(out_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    log_path = os.path.join(out_dir, "frames.jsonl")
    stop_flag = os.path.join(out_dir, "stop.flag")
    start = time.time()
    last_hash = {}
    saved = 0

    with open(log_path, "a", encoding="utf-8") as log:
        while time.time() - start < duration:
            if os.path.exists(stop_flag):
                break
            try:
                cands = []
                for hwnd, title, rect in enum_windows():
                    low = title.lower()
                    if not any(k.lower() in low for k in keywords):
                        continue
                    l, t, r, b = rect
                    if r - l < MIN_W or b - t < MIN_H:
                        continue
                    if l < -30000 or t < -30000:      # minimised
                        continue
                    if visible_ratio(hwnd, rect) < 0.6:  # mostly covered
                        continue
                    cands.append((hwnd, title, rect))
                # foreground window first, then largest
                fg = user32.GetForegroundWindow()
                cands.sort(key=lambda c: (c[0] != fg, -(c[2][2] - c[2][0]) * (c[2][3] - c[2][1])))
                for hwnd, title, (l, t, r, b) in cands[:MAX_WINDOWS]:
                    img = ImageGrab.grab(bbox=(l, t, r, b), all_screens=True)
                    small = img.convert("L").resize((64, 36))
                    h = hashlib.md5(small.tobytes()).hexdigest()
                    if last_hash.get(hwnd) == h:
                        continue
                    last_hash[hwnd] = h
                    ts = datetime.now().strftime("%H%M%S")
                    name = f"f_{ts}_{slug(title)}.jpg"
                    img.convert("RGB").save(os.path.join(frames_dir, name), "JPEG", quality=88)
                    saved += 1
                    log.write(json.dumps({"ts": datetime.now().isoformat(timespec="seconds"),
                                          "title": title, "hwnd": hwnd,
                                          "file": name}, ensure_ascii=False) + "\n")
                    log.flush()
            except Exception as exc:  # keep recording through transient errors
                print("ERR", repr(exc)[:200], flush=True)
            time.sleep(interval)
    print(f"frames saved: {saved}", flush=True)


if __name__ == "__main__":
    out = sys.argv[1]
    kw = sys.argv[2].split("|") if len(sys.argv) > 2 and sys.argv[2] else DEFAULT_KEYWORDS
    itv = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 6 * 3600
    main(out, kw, itv, dur)
