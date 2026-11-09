"""Primeri stilova za Style Picker — 8 kratkih klipova u petlji (4 hooka, 4 titla).

Prave se JEDNOM (iz agencijskog snimka) i idu uz skill, pa se stranica otvara odmah.
Zamena snimka: `./ccc prepare <novi snimak>` → `./ccc captions/camera` → `./ccc previews <ime>`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .project import REMOTION, remotion_cli

ASSETS = Path(__file__).resolve().parent / "picker" / "assets"
CAPTION_STYLES = ["clean", "karaoke", "box", "minimal"]
HOOK_STYLES = ["box", "serif", "color", "stack"]
DEMO_HOOK = {"box": "how to become a big dog in your industry",
             "serif": "how to become a big dog in your industry",
             "color": "how to become a big dog in your industry",
             "stack": "how to go viral | start growing, stop guessing"}
DEMO_COLORS = {"karaoke": "#FFE600", "color": "#FFE600", "stack": "#FF3B30"}
CAPTION_WINDOW = (4.0, 9.0)   # s izlaza: kontinuiran govor, bez hooka
HOOK_WINDOW = (0.0, 4.2)      # s izlaza: hook (do 3.44 s) + prvi titlovi posle


def _render(props: dict, frames: tuple[int, int], out: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(props, f)
        pf = f.name
    r = subprocess.run(remotion_cli("render", "CccEdit", str(out), f"--props={pf}",
                                    f"--frames={frames[0]}-{frames[1]}", "--scale=0.5", "--crf=26", "--muted"),
                       cwd=REMOTION, capture_output=True, text=True)
    Path(pf).unlink(missing_ok=True)
    if r.returncode != 0 or not out.exists():
        raise SystemExit(f"Render primera nije uspeo ({out.name}):\n" + "\n".join((r.stderr or r.stdout).splitlines()[-15:]))


def _poster(clip: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.5", "-i", str(clip), "-frames:v", "1", "-q:v", "4",
                    str(clip.with_suffix(".jpg"))], check=True)


def build(job, p: dict, voice_runs) -> list[Path]:
    from . import captions as cap
    from . import hook as hk
    from .render import render_props

    base = json.loads(render_props(job, p).read_text())
    fps = p["fps"]
    ASSETS.mkdir(parents=True, exist_ok=True)
    made = []

    for style in CAPTION_STYLES:
        q = dict(p, caption_style=style, caption_accent=DEMO_COLORS.get(style, p.get("caption_accent")))
        props = dict(base, captions=cap.build(q, voice_runs, style), captionStyle=style,
                     captionAccent=q.get("caption_accent") or cap.DEFAULT_ACCENT, hook=None)
        out = ASSETS / f"caption-{style}.mp4"
        _render(props, (round(CAPTION_WINDOW[0] * fps), round(CAPTION_WINDOW[1] * fps) - 1), out)
        made.append(out)

    clean_caps = cap.build(dict(p, caption_style="clean"), voice_runs, "clean")
    q = dict(p, caption_style="clean")
    for style in HOOK_STYLES:
        h = hk.build(q, DEMO_HOOK[style], style, DEMO_COLORS.get(style), "below")
        props = dict(base, captions=clean_caps, captionStyle="clean", hook=h)
        out = ASSETS / f"hook-{style}.mp4"
        _render(props, (round(HOOK_WINDOW[0] * fps), round(HOOK_WINDOW[1] * fps) - 1), out)
        made.append(out)

    for clip in made:
        _poster(clip)
    (ASSETS / "source.json").write_text(json.dumps({"video": p["name"], "fps": fps}, indent=1))
    return made


def clear() -> None:
    shutil.rmtree(ASSETS, ignore_errors=True)
