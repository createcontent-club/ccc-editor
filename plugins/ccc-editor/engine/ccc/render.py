"""Render kroz Remotion: project.json → render-props.json → MP4."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .project import REMOTION, Job, remotion_cli


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
