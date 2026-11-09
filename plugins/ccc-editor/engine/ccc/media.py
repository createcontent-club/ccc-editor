"""Prijem snimka: ffprobe, normalizacija za Remotion, dekodiranje zvuka."""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np

STANDARD_FPS = (23.976, 24, 25, 29.97, 30, 50, 59.94, 60)


def run(*args: str) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"Komanda nije uspela: {' '.join(args[:3])}…\n{r.stderr[-1500:]}")


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                         capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise SystemExit("Fajl nema video.")
    r_fps = float(Fraction(v["r_frame_rate"]))
    avg_fps = float(Fraction(v.get("avg_frame_rate", "0/1") or "0/1")) or r_fps
    rotation = 0
    for sd in v.get("side_data_list", []):
        rotation = int(sd.get("rotation", rotation))
    rotation = int(v.get("tags", {}).get("rotate", rotation))
    return {
        "codec": v["codec_name"],
        "width": v["width"],
        "height": v["height"],
        "fps": round(r_fps, 3),
        "vfr": abs(r_fps - avg_fps) > 0.05,
        "rotation": rotation % 360,
        "duration": float(info["format"]["duration"]),
        "has_audio": a is not None,
        "audio_channels": a["channels"] if a else 0,
    }


def nearest_standard_fps(fps: float) -> float:
    return min(STANDARD_FPS, key=lambda s: abs(s - fps))


def normalize(src: Path, info: dict, video_out: Path, audio_out: Path) -> dict:
    """Video bez zvuka za Remotion (+ CFR ako treba) i zvuk u punom kvalitetu (WAV 48 kHz)."""
    video_out.parent.mkdir(parents=True, exist_ok=True)
    audio_out.parent.mkdir(parents=True, exist_ok=True)
    fps = info["fps"]
    reencode = info["vfr"] or info["rotation"] or info["codec"] not in ("h264", "hevc") \
        or abs(nearest_standard_fps(fps) - fps) > 0.01
    if reencode:
        fps = 30.0 if info["vfr"] else nearest_standard_fps(fps)
        run("ffmpeg", "-hide_banner", "-y", "-i", str(src), "-map", "0:v:0", "-an", "-vf", f"fps={fps}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(video_out))
    else:
        run("ffmpeg", "-hide_banner", "-y", "-i", str(src), "-map", "0:v:0", "-an", "-c", "copy",
            "-movflags", "+faststart", str(video_out))
    if info["has_audio"]:
        run("ffmpeg", "-hide_banner", "-y", "-i", str(src), "-map", "0:a:0", "-vn",
            "-ar", "48000", "-c:a", "pcm_s24le", str(audio_out))
    return {"fps": fps, "reencoded": bool(reencode)}


def decode_mono(path: Path, rate: int = 16000) -> np.ndarray:
    """Zvuk kao mono float32 (za Whisper i analizu energije) — preko ffmpeg-a, ne PyAV."""
    pcm = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)
