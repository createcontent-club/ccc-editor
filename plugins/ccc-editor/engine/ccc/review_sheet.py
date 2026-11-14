"""Pregled kadrova pre izvoza (recenzija test-video-petar v1, principles.md 51).

Automatske provere gledaju tajming, zvuk i fajlove, ali ne i SMISAO: v1 tog testa je prošao sve provere, a gore je bio
sam logo, tamna stranica sa sitnim tekstom umesto naslova i ikonice umesto radnji. Zato Split Screen build posle
provera NE izvozi odmah: napravi list kadrova (gornja polovina, poslednji kadar svakog momenta = konačni kadar posle
svih taktova) koji Claude mora da pogleda pre `ccc export`.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .project import REMOTION, SPLIT_LINE

COLS = 4
CELL_W = 420


def make_sheet(job, p: dict, items: list[dict]) -> Path:
    """work/<ime>/review/sheet.jpg — dva kadra gornje polovine po momentu (sredina, kraj), red po red: 2 momenta u redu."""
    video = job.dir / "final.mp4"
    out_dir = job.dir / "review"
    out_dir.mkdir(exist_ok=True)
    font = REMOTION / "public" / "fonts" / "Inter-Bold.ttf"
    tmp = Path(tempfile.mkdtemp(prefix="ccc-review-"))
    try:
        k = 0
        for n, it in enumerate(items, 1):
            s0, s1 = float(it["start"]), float(it["end"])
            # dva kadra po momentu: sredina (šta se dešava) + kraj (konačni kadar posle svih taktova, pre izlaza)
            for tag, t in (("a", s0 + (s1 - s0) * 0.55), ("b", max(s0 + 0.1, s1 - 0.15))):
                k += 1
                base = f"crop=iw:{SPLIT_LINE}:0:0,scale={CELL_W}:-2"
                vf = base
                if font.exists():
                    label = f"{n}{tag} · {it['kind']} · {t:.1f}s"
                    ff = str(font).replace("\\", "/").replace(":", r"\:")
                    vf += (f",drawbox=x=0:y=0:w=iw:h=44:color=black@0.62:t=fill,"
                           f"drawtext=fontfile='{ff}':text='{label}':x=12:y=11:fontsize=24:fontcolor=white")
                cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1"]
                r = subprocess.run(cmd + ["-vf", vf, str(tmp / f"{k:03d}.png")], capture_output=True)
                if r.returncode != 0:  # ffmpeg bez drawtext (bez freetype) → bez natpisa; redosled = 1a 1b 2a 2b…
                    subprocess.run(cmd + ["-vf", base, str(tmp / f"{k:03d}.png")], check=True)
        rows = (k + COLS - 1) // COLS
        sheet = out_dir / "sheet.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "%03d.png"),
                        "-vf", f"tile={COLS}x{rows}:padding=8:margin=8:color=white", "-frames:v", "1", "-q:v", "3",
                        str(sheet)], check=True)
        return sheet
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
