"""Pokreti kamere (bez reference — CCC predlog, za ispravke).

1. Punch-in na VIDLJIVIM rezovima: dva kadra, ŠIRI (100%) i BLIŽI (115%), smenjuju se tamo gde se
   skok u slici zaista vidi — jump cut tako izgleda kao prelaz na drugu kameru. Vidljivost se meri:
   razlika poslednjeg i prvog frejma oko reza ≥ JUMP_MIN i ≥ JUMP_RATIO × normalno kretanje između
   dva susedna frejma (na test-video-1: retake 6 s → skok 4.9 vs 0.5; izbačeno 40 ms → 0.8 vs 0.8).
   Nevidljivi rezovi ne menjaju kadar; između dve promene mora proći ≥ MIN_SHOT.
2. Spor push-in: kadar duži od PUSH_MIN lagano ide +PUSH (3%) do svog kraja — slika nikad nije mrtva.
3. Zum je centriran na lice (sredina lica) — lice ostaje na mestu; skala ≥ 1 → nema crnih ivica.
Titlovi i hook su na posebnom, nezumiranom sloju.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

from .project import ROOT

WIDE, PUNCH = 1.0, 1.15
MIN_SHOT = 0.4      # s — najkraći razmak između dve promene kadra (da slika ne trza)
JUMP_MIN, JUMP_RATIO = 2.0, 2.5
PUSH, PUSH_MIN = 0.03, 3.0


def _faces(job, times: list[float]) -> list[dict]:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "engine")}
    r = subprocess.run([sys.executable, "-m", "ccc.face", str(job.public / "video.mp4"), json.dumps(times)],
                       capture_output=True, text=True, env=env)
    return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else []


def _gray(video: str, n: int, fps: float):
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(n + 0.5) / fps:.3f}", "-i", video, "-frames:v", "1",
                          "-vf", "scale=108:192", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).astype(float)


def visible_jumps(job, p: dict) -> list[dict]:
    """Za svaki rez: koliko se slika razlikuje preko reza u odnosu na normalno kretanje."""
    video, fps, segs = str(job.public / "video.mp4"), p["fps"], p["segments"]
    out = []
    for i in range(1, len(segs)):
        a, b = segs[i - 1], segs[i]
        last, first = a["vFrom"] + a["vFrames"] - 1, b["vFrom"]
        fl = _gray(video, last, fps)
        jump = float(abs(fl - _gray(video, first, fps)).mean())
        normal = float(abs(_gray(video, last - 1, fps) - fl).mean())
        out.append({"seg": i, "jump": round(jump, 2), "normal": round(normal, 2),
                    "visible": jump >= JUMP_MIN and jump >= JUMP_RATIO * max(normal, 0.5)})
    return out


def build(job, p: dict) -> list[dict]:
    fps, segs = p["fps"], p["segments"]
    # Izlazno vreme početka/kraja svakog segmenta (po frejmovima slike).
    spans, f = [], 0
    for g in segs:
        spans.append((f / fps, (f + g["vFrames"]) / fps))
        f += g["vFrames"]

    # 1. Kadrovi: nova promena na svakom vidljivom skoku (uz minimalni razmak).
    jumps = {j["seg"]: j for j in visible_jumps(job, p)}
    shots, cur, last_switch = [], [0], 0.0
    for i in range(1, len(segs)):
        start = spans[i][0]
        if jumps[i]["visible"] and start - last_switch >= MIN_SHOT:
            shots.append(cur)
            cur, last_switch = [i], start
        else:
            cur.append(i)
    shots.append(cur)

    # 2. Lice u sredini svakog kadra (izvorno vreme) → centar zuma.
    mids = []
    for sh in shots:
        g = segs[sh[len(sh) // 2]]
        mids.append(round((g["vFrom"] + g["vFrames"] / 2) / fps, 3))
    found = {round(x["t"], 3): x for x in _faces(job, mids)}
    H = 1920
    default = p.get("face", {})
    plan = []
    for k, sh in enumerate(shots):
        fc = found.get(mids[k])
        if fc:
            sc = 1920 / fc["H"]
            ox, oy = fc["cx"] * sc, (fc["chin"] - fc["face_h"] / 2) * sc
        else:
            ox, oy = 540, default.get("chin", 1000) - default.get("face_h", 280) / 2
        base = WIDE if k % 2 == 0 else PUNCH
        t0, t1 = spans[sh[0]][0], spans[sh[-1]][1]
        push = PUSH if t1 - t0 >= PUSH_MIN else 0.0
        for i in sh:
            a, b = spans[i]
            plan.append({"seg": i, "shot": k,
                         "from": round(base + push * (a - t0) / (t1 - t0), 4),
                         "to": round(base + push * (b - t0) / (t1 - t0), 4),
                         "ox": round(ox), "oy": round(min(max(oy, 0), H))})
    return plan


def hidden_jumps(job, p: dict) -> list[dict]:
    """Vidljivi skokovi na kojima se kadar NIJE promenio (za proveru)."""
    plan = {c["seg"]: c for c in p.get("camera") or []}
    # Početak svakog kadra (izlazno vreme): skok koji planer NAMERNO nije menjao jer je stigao < MIN_SHOT posle
    # prethodne promene kadra (ili od početka) nije greška — provera ga je ranije kažnjavala (QA 0.8.0, P0).
    fps, f, start, shot_start = p["fps"], 0, [], {}
    for g in p["segments"]:
        start.append(f / fps)
        f += g["vFrames"]
    for c in sorted(plan.values(), key=lambda c: c["seg"]):
        shot_start.setdefault(c["shot"], start[c["seg"]] if c["seg"] < len(start) else 0.0)
    out = []
    for j in visible_jumps(job, p):
        a, b = plan.get(j["seg"] - 1), plan.get(j["seg"])
        if j["visible"] and a and b and a["shot"] == b["shot"]:
            if j["seg"] < len(start) and start[j["seg"]] - shot_start.get(b["shot"], 0.0) < MIN_SHOT:
                continue
            out.append(j)
    return out


def summary(plan: list[dict]) -> str:
    shots = {}
    for c in plan:
        shots.setdefault(c["shot"], []).append(c)
    n_punch = sum(1 for cs in shots.values() if cs[0]["from"] >= PUNCH - 1e-6)
    pushes = sum(1 for cs in shots.values() if cs[-1]["to"] - cs[0]["from"] > 1e-3)
    return f"{len(shots)} kadrova ({n_punch} bliži, {len(shots) - n_punch} širi), push-in u {pushes}"


def max_chin_after_zoom(p: dict) -> float:
    """Najniža tačka brade pri najvećem zumu (za proveru da brada ne dođe do titla)."""
    face = p["face"]
    worst = face["chin"]
    for c in p.get("camera") or []:
        s = max(c["from"], c["to"])
        worst = max(worst, c["oy"] + s * (face["chin"] - c["oy"]))
    return worst


def min_head_after_zoom(p: dict) -> float:
    face = p["face"]
    best = face["head_top"]
    for c in p.get("camera") or []:
        s = max(c["from"], c["to"])
        best = min(best, c["oy"] + s * (face["head_top"] - c["oy"]))
    return best
