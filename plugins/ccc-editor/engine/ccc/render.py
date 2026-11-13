"""Render kroz Remotion: project.json → render-props.json → MP4."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .fonts import spec as font_spec
from .visuals import render_spec as top_spec
from .project import REMOTION, Job, remotion_cli


def captions_from(p: dict) -> float:
    """Split Screen: titlovi stoje na mestu hooka, pa kreću tek kad hook nestane (bez hooka: od starta)."""
    if (p.get("layout") or {}).get("type") == "split" and p.get("hook"):
        return float(p["hook"]["end"])
    return 0.0


MAX_FPS = 60.5  # izvoz nikad iznad 60 fps (Instagram/TikTok/telefoni)


def fps_mult(p: dict) -> int:
    """Koliko puta više frejmova od izvora renderujemo: Split Screen 2× (25 → 50, 30 → 60), ali nikad preko 60 fps."""
    if (p.get("layout") or {}).get("type") != "split":
        return 1
    return max(1, min(2, int(MAX_FPS // float(p["fps"]))))


def render_props(job: Job, p: dict) -> Path:
    props = {
        "video": p["media"]["video"],
        "audio": p["media"]["voice"],
        "fps": p["fps"],
        "segments": p["segments"],
        "captions": p.get("captions", []),
        "captionY": p.get("captionY", 1180),
        "captionStyle": p.get("caption_style") or "clean",
        "captionAccent": p.get("caption_accent") or "#FFE600",
        # Uvek eksplicitno: Remotion inače popuni nedostajuća polja podrazumevanim (probnim) vrednostima.
        "hook": p.get("hook"),
        "camera": p.get("camera") or [],
        "font": font_spec(p.get("font")),  # set fontova za titlove + hook (engine/ccc/fonts.py)
        "layout": p.get("layout"),          # None = ceo kadar; {"type": "split", "line", "cropY"} = Split Screen
        "captionsFrom": captions_from(p),
        "top": top_spec(job, p),            # Split Screen: momenti gornje polovine
        # Split Screen: render u 2× fps (npr. 25 → 50) — animacije gornje polovine su glatke; snimak se ne menja.
        # Nikad iznad MAX_FPS: snimak od 60 fps je dao izvoz od 120 fps (aazar-trial-1) — telefoni i QuickTime
        # ne stignu da ga dekodiraju u realnom vremenu, pa video izgleda usporeno i "traje" minutima.
        "fpsMult": fps_mult(p),
    }
    path = job.dir / "render-props.json"
    path.write_text(json.dumps(props, ensure_ascii=False))
    return path


def render(job: Job, p: dict, preview: bool) -> tuple[Path, float]:
    props = render_props(job, p)
    out = job.dir / ("preview.mp4" if preview else "final.mp4")
    args = remotion_cli("render", "CccEdit", str(out), f"--props={props}")
    if preview:
        args += ["--scale=0.5", "--crf=26"]
    t0 = time.time()
    r = subprocess.run(args, cwd=REMOTION, capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        tail = "\n".join((r.stderr or r.stdout).strip().splitlines()[-25:])
        raise SystemExit(f"Remotion render nije uspeo:\n{tail}")
    return out, time.time() - t0
