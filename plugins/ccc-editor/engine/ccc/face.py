"""Pozicija lica kroz video (OpenCV YuNet) → gde ide titl; obris osobe (MODNet) → pravi vrh kose (hook iznad glave).

Pokreće se kao ZASEBAN proces (`python -m ccc.face <video> <json segmenti>`): OpenCV i PyAV
(faster-whisper) nose svaki svoj libavdevice i ne smeju u isti proces.
"""
from __future__ import annotations

import json
import subprocess
import sys

from .project import MODELS


def chin_track(video: str, times: list[float]) -> list[dict]:
    import cv2
    import numpy as np

    det = None
    out = []
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "json", video],
                                     capture_output=True, text=True).stdout)["streams"][0]
    w, h = info["width"], info["height"]
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        if len(raw) != w * h * 3:
            continue
        img = np.frombuffer(raw, np.uint8).reshape(h, w, 3)
        if det is None:
            det = cv2.FaceDetectorYN.create(str(MODELS / "face" / "face_detection_yunet_2023mar.onnx"), "", (w, h), 0.6)
        _, faces = det.detect(img)
        if faces is None or not len(faces):
            continue
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])[:4]
        rec = {"t": t, "chin": float(y + fh), "face_h": float(fh), "cx": float(x + fw / 2), "H": h}
        hair = hair_top(img, float(x), float(y), float(fw))
        if hair is not None:  # nikad niže od stare procene: obris ume da izgubi sedu/svetlu kosu na svetloj pozadini
            rec["hair"] = min(hair, float(y) - 0.25 * float(fh))
        out.append(rec)
    return out


_MATTE = None


def hair_top(img, x: float, y: float, fw: float) -> float | None:
    """Pravi vrh glave (kosa, kapa) iznad lica: MODNet obris osobe (Apache 2.0, onnxruntime koji već dolazi uz
    faster-whisper), red gde je ≥ 30% trake iznad lica osoba. YuNet vidi lice od obrva, ne kosu: ranija procena
    "vrh lica − 25%" je kod kose sa volumenom stavila hook na čelo (PLAN §23). Nema modela/greška → None (procena)."""
    global _MATTE
    import numpy as np
    path = MODELS / "person" / "modnet.onnx"
    if _MATTE is None:
        try:
            import onnxruntime as ort
            _MATTE = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"]) if path.exists() else False
        except Exception:
            _MATTE = False
    if _MATTE is False:
        return None
    try:
        import cv2
        h, w = img.shape[:2]
        sw, sh = (288, 512) if h >= w else (512, 288)       # ulaz deljiv sa 32, razmera kadra
        small = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), (sw, sh)).astype(np.float32) / 255.0
        a = _MATTE.run(None, {_MATTE.get_inputs()[0].name: ((small - 0.5) / 0.5).transpose(2, 0, 1)[None]})[0][0, 0]
        mask = cv2.resize(a, (w, h)) > 0.5
        x0, x1 = int(max(0, x + 0.2 * fw)), int(min(w, x + 0.8 * fw))
        if x1 <= x0 or y <= 1:
            return None
        rows = np.where(mask[:int(y), x0:x1].mean(1) > 0.3)[0]
        if not len(rows):
            return None
        # samo deo spojen sa licem (od lica naviše bez prekida) — ne neko/nešto iznad glave
        top = int(y) - 1
        while top - 1 >= 0 and mask[top - 1, x0:x1].mean() > 0.3:
            top -= 1
        return float(top) if top < y else None
    except Exception:
        return None


def image_face(path: str) -> dict | None:
    """Najveće lice na slici (fotografija osobe) → {x, y, w, h} u px slike, ili None."""
    import cv2
    img = cv2.imread(path)
    if img is None:
        return None
    h, w = img.shape[:2]
    det = cv2.FaceDetectorYN.create(str(MODELS / "face" / "face_detection_yunet_2023mar.onnx"), "", (w, h), 0.7)
    _, faces = det.detect(img)
    if faces is None or not len(faces):
        return None
    x, y, fw, fh = [float(v) for v in max(faces, key=lambda f: f[2] * f[3])[:4]]
    if fw * fh < 0.004 * w * h:  # sitno lice u gomili — nije portret
        return None
    # n = koliko krupnih lica ima (≥ 35% najvećeg): 2+ = kolaž/dva kadra — `cover` u uskom okviru bi ih presekao
    n = sum(1 for f in faces if float(f[2]) * float(f[3]) >= 0.35 * fw * fh)
    return {"x": round(x), "y": round(y), "w": round(fw), "h": round(fh), "n": n}


if __name__ == "__main__":
    if sys.argv[1] == "--image":
        print(json.dumps(image_face(sys.argv[2])))
    else:
        video, times = sys.argv[1], json.loads(sys.argv[2])
        print(json.dumps(chin_track(video, times)))
