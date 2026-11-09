"""Isečen zvuk (voice.wav) iz istih, na frejm poravnatih segmenata kao slika — sa mikro-fade-om."""
from __future__ import annotations

import subprocess
from pathlib import Path

from .media import run


def build_voice(src: Path, segments: list[dict], out: Path, fade: float, total: float,
                codec: str = "pcm_s24le") -> float:
    parts, labels = [], []
    for i, s in enumerate(segments):
        d = s["srcEnd"] - s["srcStart"]
        f = min(fade, d / 4)
        parts.append(
            f"[0:a]atrim={s['srcStart']:.4f}:{s['srcEnd']:.4f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d={f:.4f},afade=t=out:st={d - f:.4f}:d={f:.4f}[a{i}]"
        )
        labels.append(f"[a{i}]")
    # Na kraju: dopuna/odsecanje na tačnu dužinu slike (razlika < pola frejma).
    graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(segments)}:v=0:a=1,apad,atrim=0:{total:.5f}[out]"
    out.parent.mkdir(parents=True, exist_ok=True)
    run("ffmpeg", "-hide_banner", "-y", "-i", str(src), "-filter_complex", graph, "-map", "[out]",
        "-c:a", codec, str(out))
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                         capture_output=True, text=True).stdout.strip()
    return float(dur)
