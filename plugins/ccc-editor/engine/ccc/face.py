"""Pozicija lica kroz video (OpenCV YuNet) → gde ide titl.

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
        out.append({"t": t, "chin": float(y + fh), "face_h": float(fh), "cx": float(x + fw / 2), "H": h})
    return out


if __name__ == "__main__":
    video, times = sys.argv[1], json.loads(sys.argv[2])
    print(json.dumps(chin_track(video, times)))
