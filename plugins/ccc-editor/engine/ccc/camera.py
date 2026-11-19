"""Pokreti kamere (bez reference — CCC predlog, za ispravke).

1. Punch-in na VIDLJIVIM rezovima: dva kadra, ŠIRI (100%) i BLIŽI (115%), smenjuju se tamo gde se
   skok u slici zaista vidi — jump cut tako izgleda kao prelaz na drugu kameru. Vidljivost se meri:
   razlika poslednjeg i prvog frejma oko reza ≥ JUMP_MIN i ≥ JUMP_RATIO × normalno kretanje između
   dva susedna frejma (na test-video-1: retake 6 s → skok 4.9 vs 0.5; izbačeno 40 ms → 0.8 vs 0.8).
   Nevidljivi rezovi ne menjaju kadar; između dve promene mora proći ≥ MIN_SHOT.
2. Spor push-in: kadar duži od PUSH_MIN lagano ide +PUSH (3%) do svog kraja — slika nikad nije mrtva.
3. Zum je centriran na lice (sredina lica); kad bi brada pri zumu ušla u titl, sidro se spušta ka bradi
   (sa sidrom na bradi brada se ne pomera, lice raste nagore); ako ni to ne može bez sečenja lica, manji zum
   za taj kadar (PLAN §23). Brada svakog kadra iz uzoraka lica tog kadra. Skala ≥ 1 → nema crnih ivica.
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
PUNCH_STEPS = (PUNCH, 1.08, WIDE)  # bliži kadar kad sidro na bradi ne može: manji zum, pa širi (nikad pad izvoza)
FACE_TOP_MIN = 40   # px: vrh okvira lica (≈ obrve) ostaje u kadru i pri najvećem zumu (kosa sme da se iseče)
MOUTH = 0.22        # × visina lica iznad brade ≈ usta (titl nikad preko usta)


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

    # 2. Lice svakog kadra: uzorak iz sredine kadra + svi uzorci iz zajedničkog zapisa lica (captions.face_track)
    #    koji padaju u njegove segmente → najniža brada i najviše lice u tom kadru (govornik se pomera).
    mids = []
    for sh in shots:
        g = segs[sh[len(sh) // 2]]
        mids.append(round((g["vFrom"] + g["vFrames"] / 2) / fps, 3))
    found = {round(x["t"], 3): x for x in _faces(job, mids)}
    from .captions import face_track, half_h
    track = face_track(job, p)
    H = 1920
    default = p.get("face", {})
    cap_top = p["captionY"] - half_h(p) if "captionY" in p else None
    plan = []
    for k, sh in enumerate(shots):
        fc = found.get(mids[k])
        src = [(segs[i]["srcStart"], segs[i]["srcEnd"]) for i in sh]
        seen = [x for x in track if any(a <= x["t"] < b for a, b in src)] + ([fc] if fc else [])
        if seen:
            sc = 1920 / seen[0]["H"]
            chin = max(x["chin"] for x in seen) * sc
            top = min(x["chin"] - x["face_h"] for x in seen) * sc
            fh = sorted(x["face_h"] for x in seen)[len(seen) // 2] * sc
            hairs = [x["hair"] for x in seen if "hair" in x]
            head = min(hairs) * sc if hairs else top - 0.25 * fh  # pravi vrh kose (MODNet) ili procena
        else:
            chin, fh = default.get("chin", 1000), default.get("face_h", 280)
            top = chin - fh
            hairs, head = [], default.get("hair_top", top - 0.25 * fh)
        if fc:
            sc = 1920 / fc["H"]
            ox, cy = fc["cx"] * sc, (fc["chin"] - fc["face_h"] / 2) * sc
        else:
            ox, cy = 540, default.get("chin", 1000) - default.get("face_h", 280) / 2
        t0, t1 = spans[sh[0]][0], spans[sh[-1]][1]
        push = PUSH if t1 - t0 >= PUSH_MIN else 0.0
        steps = PUNCH_STEPS if k % 2 else (WIDE,)
        base, oy = _fit(steps, push, chin, top, cy, cap_top)
        for i in sh:
            a, b = spans[i]
            plan.append({"seg": i, "shot": k,
                         "from": round(base + push * (a - t0) / (t1 - t0), 4),
                         "to": round(base + push * (b - t0) / (t1 - t0), 4),
                         "ox": round(ox), "oy": round(min(max(oy, 0), H)),
                         # lice ovog kadra (za proveru i hook): brada, vrh okvira lica, teme (procena), visina lica
                         "chin": round(chin), "top": round(top), "head": round(head), "fh": round(fh),
                         "hair": bool(hairs) or "hair_top" in default,
                         "t0": round(a, 3), "want": PUNCH if k % 2 else WIDE})
    return plan


def _fit(steps, push: float, chin: float, top: float, cy: float, cap_top: float | None) -> tuple[float, float]:
    """Prvi zum iz `steps` (pa bez push-a) pri kome: brada ostaje iznad titla, a vrh lica u kadru.
    Sidro (oy) je sredina lica kad može; inače najmanje spušteno ka bradi koliko treba (najviše do brade)."""
    from .captions import CHIN_CLEAR
    limit = cap_top - CHIN_CLEAR if cap_top is not None else None
    tries = [(b, push) for b in steps] + ([(WIDE, 0.0)] if push else [])
    for base, pu in tries:
        s = base + pu
        if s <= 1.0 + 1e-6:
            return base, cy
        oy = cy
        if limit is not None and chin > oy:
            need = (s * chin - limit) / (s - 1)        # brada' = oy + s·(brada − oy) ≤ limit
            oy = min(max(cy, need), max(chin, cy))     # sidro nikad ispod brade
        if oy + s * (top - oy) >= FACE_TOP_MIN:       # lice (bar od obrva) ostaje u kadru
            return base, oy
    return WIDE, cy


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
    eased = sum(1 for cs in shots.values() if cs[0].get("want", 0) - cs[0]["from"] > 1e-3)
    return (f"{len(shots)} kadrova ({n_punch} bliži, {len(shots) - n_punch} širi), push-in u {pushes}"
            + (f", manji zum u {eased} (brada bi ušla u titl ili lice izašlo iz kadra)" if eased else ""))


def zoomed(c: dict, y: float) -> float:
    """y (na ekranu bez zuma) → y pri najvećem zumu ovog kadra."""
    s = max(c["from"], c["to"])
    return c["oy"] + s * (y - c["oy"])


def max_chin_after_zoom(p: dict) -> float:
    """Najniža tačka brade pri najvećem zumu (brada svakog kadra; stari planovi: brada celog videa)."""
    face = p["face"]
    worst = face["chin"]
    for c in p.get("camera") or []:
        worst = max(worst, zoomed(c, c.get("chin", face["chin"])))
    return worst


def chin_touches(p: dict, cap_top: float) -> tuple[list[dict], list[dict]]:
    """(kadrovi gde brada dodiruje titl, kadrovi gde bi titl prekrio usta) — po kadru, pri najvećem zumu."""
    face = p["face"]
    touch, mouth = {}, {}
    for c in p.get("camera") or []:
        chin = c.get("chin", face["chin"])
        fh = c.get("fh", face.get("face_h", 280))
        if zoomed(c, chin) > cap_top:
            touch.setdefault(c["shot"], c)
        if zoomed(c, chin - MOUTH * fh) > cap_top:
            mouth.setdefault(c["shot"], c)
    return list(touch.values()), list(mouth.values())


HAIR_OVERLAP = 1 / 3  # hook iznad glave sme da pokrije najviše gornju trećinu kose (od vrha kose do vrha lica)


def head_limits(p: dict, until: float | None = None) -> tuple[float, float]:
    """Hook iznad glave, na ekranu i pri zumu, samo kadrovi koji počinju pre `until` (hook traje ~3.4 s):
    (clear = najviši vrh kose → hook potpuno iznad glave, allowed = najdublje gde sme dno hooka: gornja trećina kose,
    nikad do čela). Bez pravog obrisa kose (stari projekti, nema modela) allowed = clear (procena nije pouzdana)."""
    face = p["face"]
    real = "hair_top" in face
    hair = face.get("hair_top", face["head_top"])
    ftop = face.get("face_top", face["chin"] - face.get("face_h", 280))
    clear, allowed = hair, (hair + HAIR_OVERLAP * max(0.0, ftop - hair)) if real else hair
    starts, f = [], 0
    for g in p["segments"]:
        starts.append(f / p["fps"])
        f += g["vFrames"]
    for c in p.get("camera") or []:
        t0 = c.get("t0", starts[c["seg"]] if c["seg"] < len(starts) else 0.0)
        if until is not None and t0 >= until:
            continue
        h = c.get("head", face["head_top"])
        clear = min(clear, zoomed(c, h))
        a = h + HAIR_OVERLAP * max(0.0, c.get("top", ftop) - h) if c.get("hair") else h
        allowed = min(allowed, zoomed(c, a))
    return clear, max(clear, allowed)


def keep_head_clear(p: dict, bottom: float, until: float) -> int:
    """Hook iznad glave (dno `bottom`): kadrovi dok hook traje ne smeju zumom da podignu kosu (dozvoljenu gornju
    trećinu) iznad dna hooka. Sidro zuma ide naviše koliko sme (brada i dalje iznad titla, ne gore nego pre);
    ako ne može, taj kadar ostaje širok (bez zuma). Menja p["camera"]; vraća broj izmenjenih kadrova."""
    from .captions import CHIN_CLEAR, half_h
    face = p["face"]
    limit = p["captionY"] - half_h(p) - CHIN_CLEAR
    starts, f = [], 0
    for g in p["segments"]:
        starts.append(f / p["fps"])
        f += g["vFrames"]
    shots = {}
    for c in p.get("camera") or []:
        if c.get("t0", starts[c["seg"]] if c["seg"] < len(starts) else 0.0) < until:
            shots.setdefault(c["shot"], []).append(c)
    shots = {k: [c for c in p["camera"] if c["shot"] == k] for k in shots}  # ceo kadar, ne samo deo pod hookom
    changed = 0
    for cs in shots.values():
        c = cs[0]
        s = max(max(x["from"], x["to"]) for x in cs)
        if s <= 1.0 + 1e-6:
            continue
        h = c.get("head", face["head_top"])
        a = h + HAIR_OVERLAP * max(0.0, c.get("top", h) - h) if c.get("hair") else h
        if c["oy"] + s * (a - c["oy"]) >= bottom - 0.5:
            continue
        oy_max = (s * a - bottom) / (s - 1)                       # kosa' = oy + s·(a − oy) ≥ dno hooka
        chin = c.get("chin", face["chin"])
        oy_min = min((s * chin - limit) / (s - 1), c["oy"])      # brada' ≤ titl (ili bar ne gore nego pre)
        if oy_max >= max(oy_min, 0.0):
            for x in cs:
                x["oy"] = round(oy_max)
        else:
            for x in cs:
                x["from"] = x["to"] = 1.0
        changed += 1
    return changed


def min_head_after_zoom(p: dict, until: float | None = None) -> float:
    """Najviša tačka temena pri zumu (kadrovi pre `until`)."""
    return head_limits(p, until)[0]
