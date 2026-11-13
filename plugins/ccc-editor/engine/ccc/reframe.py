"""Reframe horizontalnog snimka za Split Screen: virtuelna kamera koja prati lice govornika.

Donja polovina Split Screen-a je 1080×960 (odnos 9:8). Umesto da se 16:9 kadar umanji na pun ekran
(tanka traka, glava odsečena), iz izvora se iseca prozor 9:8 oko govornika:
  1. Lice (YuNet) svakih STEP s kroz ceo izvor; rupe (okret glave, ruka preko lica) se popune susedima.
  2. Zum je JEDAN za ceo video (medijana visine lica) — glava zauzima ~HEAD_FILL donje polovine, nema „disanja".
  3. Kamera prati lice sa mrtvom zonom (sitni pokreti glave ne pomeraju kadar) i mekim prelazom (Gauss,
     SMOOTH s) — kao snimatelj koji lagano dopraća govornika, nikad trzaj.
  4. Prozor nikad ne izlazi iz izvora (bez crnih ivica); podpikselni pomak (warpAffine) → bez treperenja.
Izlaz je 1080×1920 sa govornikom u DONJOJ polovini (gornja je crna i nikad se ne vidi) — ostatak
pipeline-a (split_place → cropY = 960, titlovi, provere) radi nepromenjen.

Zaseban proces (`python -m ccc.reframe <ulaz> <izlaz> <fps>`): OpenCV i PyAV ne smeju u isti proces.
"""
from __future__ import annotations

import json
import subprocess
import sys

from .project import MODELS

OUT_W, OUT_H, HALF = 1080, 1920, 960   # izlazni kadar i visina donje polovine
STEP = 0.25          # s — razmak uzoraka lica
HEAD_FILL = 0.47     # glava (teme → brada) zauzima ovaj deo visine donje polovine
HEAD_TOP_AT = 150    # px od linije podele do temena (mesto za titl/hook na liniji)
MAX_UPSCALE = 2.0    # prozor nikad manji od HALF/MAX_UPSCALE px izvora (oštrina)
DEAD_X, DEAD_Y = 0.07, 0.05  # mrtva zona (deo širine/visine prozora) — kamera miruje dok je lice u njoj
SMOOTH = 0.45        # s — sigma Gauss-ovog izglađivanja putanje kamere


def _probe(video: str) -> tuple[int, int]:
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "json", video],
                                     capture_output=True, text=True).stdout)["streams"][0]
    return info["width"], info["height"]


def track(video: str, fps: float) -> tuple[int, int, list[dict | None]]:
    """Lice na svakih STEP s (dekodira se ceo snimak jednom, na smanjenoj fps) → [{cx, top, chin, fh} | None]."""
    import cv2
    import numpy as np
    W, H = _probe(video)
    det = cv2.FaceDetectorYN.create(str(MODELS / "face" / "face_detection_yunet_2023mar.onnx"), "", (W, H), 0.6)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={1 / STEP}",
                             "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    out, n = [], W * H * 3
    while True:
        raw = proc.stdout.read(n)
        if len(raw) < n:
            break
        _, faces = det.detect(np.frombuffer(raw, np.uint8).reshape(H, W, 3))
        if faces is None or not len(faces):
            out.append(None)
            continue
        x, y, fw, fh = [float(v) for v in max(faces, key=lambda f: f[2] * f[3])[:4]]
        out.append({"cx": x + fw / 2, "top": y - 0.25 * fh, "chin": y + fh, "fh": fh})
    proc.wait()
    return W, H, out


def _fill(vals: list[float | None]) -> list[float]:
    """Rupe (nema lica) → linearno između suseda; na krajevima najbliži poznat."""
    known = [i for i, v in enumerate(vals) if v is not None]
    if not known:
        return []
    out = list(vals)
    for i in range(len(out)):
        if out[i] is None:
            a = max((k for k in known if k < i), default=None)
            b = min((k for k in known if k > i), default=None)
            if a is None:
                out[i] = vals[b]
            elif b is None:
                out[i] = vals[a]
            else:
                out[i] = vals[a] + (vals[b] - vals[a]) * (i - a) / (b - a)
    return out


def _follow(target: list[float], dead: float) -> list[float]:
    """Mrtva zona: kamera stoji dok se cilj ne udalji više od `dead`; onda ga dopraća do ivice zone."""
    if not target:
        return []
    cur, out = target[0], []
    for v in target:
        if v > cur + dead:
            cur = v - dead
        elif v < cur - dead:
            cur = v + dead
        out.append(cur)
    return out


def _smooth(vals: list[float], sigma_samples: float) -> list[float]:
    import numpy as np
    if len(vals) < 3 or sigma_samples <= 0:
        return vals
    r = int(3 * sigma_samples) + 1
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_samples) ** 2)
    k /= k.sum()
    a = np.pad(np.asarray(vals, float), r, mode="edge")
    return list(np.convolve(a, k, mode="valid"))


def plan(W: int, H: int, faces: list[dict | None]) -> dict:
    """Putanja kamere: jedan zum za ceo video + (x0, y0) gornjeg levog ugla prozora za svaki uzorak."""
    import statistics
    seen = [f for f in faces if f]
    if not seen:  # nema lica → mirni centralni kadar pune visine
        ch = float(H)
        cw = ch * OUT_W / HALF
        if cw > W:
            cw, ch = float(W), W * HALF / OUT_W
        return {"cw": cw, "ch": ch, "x0": [(W - cw) / 2], "y0": [(H - ch) / 2], "faces": 0, "samples": len(faces)}
    head = statistics.median(f["chin"] - f["top"] for f in seen)
    ch = head * HALF / (HEAD_FILL * HALF)       # visina prozora u px izvora: glava = HEAD_FILL prozora
    ch = max(HALF / MAX_UPSCALE, min(float(H), ch))
    cw = ch * OUT_W / HALF                      # 9:8
    if cw > W:
        cw, ch = float(W), W * HALF / OUT_W
    s = HALF / ch                               # px izvora → px izlaza
    cx = _fill([f["cx"] if f else None for f in faces])
    top = _fill([f["top"] if f else None for f in faces])
    # Cilj: lice horizontalno u sredini; teme HEAD_TOP_AT px ispod linije podele.
    tx = _follow([c - cw / 2 for c in cx], DEAD_X * cw)
    ty = _follow([t - HEAD_TOP_AT / s for t in top], DEAD_Y * ch)
    sig = SMOOTH / STEP
    x0 = [min(max(v, 0.0), W - cw) for v in _smooth(tx, sig)]
    y0 = [min(max(v, 0.0), H - ch) for v in _smooth(ty, sig)]
    return {"cw": cw, "ch": ch, "x0": x0, "y0": y0, "faces": len(seen), "samples": len(faces)}


def render(src: str, dst: str, fps: float, cam: dict, W: int, H: int) -> None:
    """Svaki frejm: prozor (podpikselno, između uzoraka linearno) → 1080×960 u donjoj polovini 1080×1920."""
    import cv2
    import numpy as np
    s = HALF / cam["ch"]
    xs, ys = cam["x0"], cam["y0"]
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{OUT_W}x{OUT_H}", "-r", f"{fps}", "-i", "-", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "14", "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst], stdin=subprocess.PIPE)
    frame = np.zeros((OUT_H, OUT_W, 3), np.uint8)
    bottom = frame[OUT_H - HALF:]
    n, i = W * H * 3, 0
    while True:
        raw = dec.stdout.read(n)
        if len(raw) < n:
            break
        img = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        # Uzorak k je na vremenu (k + 0.5) * STEP (ffmpeg fps filter uzima sredinu intervala).
        q = min(max((i + 0.5) / fps / STEP - 0.5, 0.0), len(xs) - 1.0)
        k = int(q)
        f = q - k
        k2 = min(k + 1, len(xs) - 1)
        x0 = xs[k] + (xs[k2] - xs[k]) * f
        y0 = ys[k] + (ys[k2] - ys[k]) * f
        m = np.float32([[s, 0, -x0 * s], [0, s, -y0 * s]])
        cv2.warpAffine(img, m, (OUT_W, HALF), dst=bottom, flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        enc.stdin.write(frame.tobytes())
        i += 1
    enc.stdin.close()
    dec.wait()
    if enc.wait() != 0:
        raise SystemExit("Reframe: enkodovanje nije uspelo.")


def reframe(src: str, dst: str, fps: float) -> dict:
    W, H, faces = track(src, fps)
    cam = plan(W, H, faces)
    render(src, dst, fps, cam, W, H)
    xs = cam["x0"]
    return {"source": [W, H], "window": [round(cam["cw"]), round(cam["ch"])], "scale": round(HALF / cam["ch"], 3),
            "faces": cam["faces"], "samples": cam["samples"],
            "pan_px": round(max(xs) - min(xs)) if xs else 0}


if __name__ == "__main__":
    print(json.dumps(reframe(sys.argv[1], sys.argv[2], float(sys.argv[3]))))
