"""Slušanje gotovog reza (aazar-trial-1, 13. nov 2026).

Transkript sirovog snimka nije isto što i gotov zvuk: Whisper zna da "proguta" ponovljeni pokušaj (u transkriptu
jedan "Same format", a u zvuku ih je dva), da da pogrešna vremena (reč "počne" 4 s pre nego što je izgovorena), a
ručno izbacivanje retake-a može da obriše SVE verzije neke rečenice. Zato posle reza:

  1. ponovo transkribujemo GOTOV zvuk (public/voice.wav) i poravnamo ga sa zadržanim rečima;
  2. ponovljena fraza koja se čuje, a nije u zadržanom tekstu = zaostali pokušaj → upozorenje sa izvornim vremenom;
  3. zadržane reči koje se ne čuju = možda isečen govor → upozorenje;
  4. zadržane reči dobijaju vremena iz gotovog zvuka (titlovi idu tačno sa glasom), uvek unutar svog segmenta;
  5. retake izbačen bez zadržane kopije (obe verzije "Fourth problem" obrisane) → upozorenje.
"""
from __future__ import annotations

import difflib
import os
import re

from .media import decode_mono
from .project import MODELS


def _n(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


def _seg_of(segs: list[tuple[float, float]], t: float) -> tuple[int, float]:
    """Vreme u gotovom zvuku → (indeks segmenta, izvorno vreme)."""
    acc = 0.0
    for i, (a, b) in enumerate(segs):
        if t < acc + (b - a):
            return i, a + (t - acc)
        acc += b - a
    return len(segs) - 1, segs[-1][1]


def kept_words(p: dict) -> list[dict]:
    rm = {w for r in p.get("removed", []) for w in r["words"]}
    segs = [(s["srcStart"], s["srcEnd"]) for s in p["segments"]]
    return [w for w in p["words"] if w["id"] not in rm and any(a < w["end"] and b > w["start"] for a, b in segs)]


def listen(job, p: dict, retime: bool = True) -> list[str]:
    """Transkribuj gotov zvuk, nađi zaostale ponovljene fraze i nečujne reči; opciono pomeri vremena reči."""
    from faster_whisper import WhisperModel

    segs = [(s["srcStart"], s["srcEnd"]) for s in p["segments"]]
    kept = kept_words(p)
    if not kept or not segs:
        return []
    audio = decode_mono(job.public / "voice.wav")
    model = WhisperModel(str(MODELS / "whisper" / "large-v3-turbo"), device="cpu", compute_type="int8",
                         cpu_threads=os.cpu_count() or 4)
    names = " ".join(dict.fromkeys(w["text"] for w in kept if w["text"][:1].isupper()))[:200]
    lang = p.get("language") or "en"
    SR = 16000
    total = len(audio) / SR

    def run(clip, t0):
        out, _ = model.transcribe(clip, language=lang, word_timestamps=True, vad_filter=False,
                                  condition_on_previous_text=False, initial_prompt=names or None)
        return [(w.word.strip(), t0 + w.start, t0 + w.end) for sg in out for w in sg.words or [] if w.word.strip()]

    def windows(offset: float, win: float = 12.0, step: float = 10.0):
        """Kratki prozori: preko dužeg zvuka Whisper sam "spoji" ponovljenu frazu u jednu — baš ono što tražimo."""
        heard, t = [], 0.0 if offset == 0 else offset - step
        while t < total:
            a = max(0.0, t)
            ws = run(audio[int(a * SR):int(min(total, t + win) * SR)], a)
            lo = a + (0.0 if a == 0 else (win - step) / 2)
            hi = t + win - (0.0 if t + win >= total else (win - step) / 2)
            heard += [x for x in ws if lo <= (x[1] + x[2]) / 2 < hi]
            t += step
        return heard

    # Tri slušanja: ceo zvuk (stabilna vremena) + dva niza kratkih prozora pomerena za pola koraka (Whisper u kratkom
    # prozoru čuje ponovljenu frazu koju preko dužeg zvuka "spoji" — aazar-trial-1). Ponavljanje važi ako ga čuje
    # BILO KOJE slušanje; reč "se ne čuje" samo ako je ne čuje NIJEDNO (granice prozora ne prave lažne uzbune).
    passes = [run(audio, 0.0), windows(0.0), windows(5.0)]
    A = [_n(w["text"]) for w in kept]
    problems: list[str] = []
    repeats: dict[int, str] = {}
    singles: dict[int, set[int]] = {}
    singles_txt: dict[int, str] = {}
    unheard: list[set[int]] = []
    moved = 0
    for pi, heard in enumerate(passes):
        B = [_n(t) for t, _, _ in heard]
        miss: set[int] = set()
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
            if op == "equal" and retime and pi == 0:
                for k in range(i2 - i1):
                    w = kept[i1 + k]
                    _, s, e = heard[j1 + k]
                    ie, ne = _seg_of(segs, max(s + 0.03, e - 0.015))
                    is_, ns = _seg_of(segs, s + 0.015)
                    if is_ != ie:  # Whisper je početak reči razvukao preko reza → reč počinje sa svojim segmentom
                        ns = segs[ie][0]
                    a, b = segs[ie]
                    ns, ne = max(ns, a + 0.012), min(ne, b - 0.012)
                    if ne - ns >= 0.05 and (abs(ns - w["start"]) > 0.08 or abs(ne - w["end"]) > 0.08):
                        w["start"], w["end"] = round(ns, 3), round(ne, 3)
                        moved += 1
            elif op == "insert" or (op == "replace" and j2 - j1 > i2 - i1):
                extra = B[j1:j2]
                # čuje se nešto čega nema u tekstu: ako ponavlja reči odmah pre/posle → zaostali pokušaj
                around = B[max(0, j1 - 6):j1] + B[j2:j2 + 6]
                rep = [x for x in extra if x and x in around]
                _, src = _seg_of(segs, heard[j1][1] + 0.02)
                key = round(src)
                if len(rep) >= 2 or (len(extra) >= 2 and " ".join(extra) in " ".join(around)):
                    if not any(abs(key - k2) <= 1 for k2 in repeats):
                        repeats[key] = " ".join(t for t, _, _ in heard[j1:j2])
                elif len(extra) == 1 and len(extra[0]) > 3 and extra[0] in (B[j1 - 1] if j1 else "", B[j2] if j2 < len(B) else ""):
                    # jedna ponovljena reč ("Selena's Selena's"): važi tek kad je čuju bar 2 slušanja (Whisper ume
                    # da "udvoji" reč na tvrdom rezu)
                    singles.setdefault(key, set()).add(pi)
                    singles_txt[key] = heard[j1][0]
            if op == "delete" or op == "replace":
                miss |= set(range(i1, i2))
        unheard.append(miss)
    for key, ps in singles.items():
        near = [k for k in singles if abs(k - key) <= 1]
        if len(set().union(*(singles[k] for k in near))) >= 2 and not any(abs(key - k2) <= 1 for k2 in repeats):
            repeats[key] = f"{singles_txt[key]} {singles_txt[key]}"
    for key in sorted(repeats):
        problems.append(f"slušanje reza: na ~{key}s (izvorno) čuje se ponovljeno \"{repeats[key]}\" — zaostao pokušaj? "
                        "Izbaci ga (prazan deo u utterances ili ccc remove) i ponovo preslušaj")
    never = sorted(set.intersection(*unheard)) if unheard else []
    runs: list[list[int]] = []
    for i in never:
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    for r in runs:
        if len(r) >= 2:
            txt = " ".join(kept[i]["text"] for i in r)
            problems.append(f"slušanje reza: zadržane reči {kept[r[0]]['id']}–{kept[r[-1]]['id']} \"{txt[:60]}\" se ne "
                            f"čuju u gotovom zvuku — isečen govor ili pogrešno vreme; ccc listen oko {kept[r[0]]['start']:.1f}s")
    if moved:
        problems.append(f"(info) slušanje reza: {moved} reči dobilo tačnija vremena iz gotovog zvuka")
    return problems


def cache_key(p: dict) -> str:
    """Otisak reza: isti segmenti i isti zadržani tekst = isti gotov zvuk → slušanje ne mora ponovo (svaki build
    posle izmene titla/hooka/boje je ranije ponovo slušao ceo video, ~1.5× trajanja videa)."""
    import hashlib
    import json
    seg = [(s["srcStart"], s["srcEnd"]) for s in p.get("segments", [])]
    txt = [w["text"] for w in kept_words(p)]
    return hashlib.sha1(json.dumps([seg, txt, bool(p.get("audio"))]).encode()).hexdigest()[:16]


def lost_retakes(p: dict) -> list[str]:
    """Retake izbačen ručno, a nijedna njegova verzija nije zadržana (npr. obe "Fourth problem" obrisane)."""
    from .cut import resolve
    removed = resolve(p["words"], p["utterances"], p.get("decisions", []))
    kept = [w for w in p["words"] if w["id"] not in removed]
    idx = {w["id"]: i for i, w in enumerate(p["words"])}
    out = []
    FILL = {"okay", "ok", "yeah", "thank", "you", "um", "uh", "hmm", "so", "and", "the", "a", "here", "we", "go"}
    for d in p.get("decisions", []):
        if d.get("action") != "remove" or d.get("reason") != "retake":
            continue
        # samo reči koje su i POSLE svih odluka izbačene (kasniji `keep` vraća jednu verziju)
        span = [w for w in p["words"][idx[d["from"]]: idx[d["to"]] + 1] if w["id"] in removed]
        toks = [_n(w["text"]) for w in span if _n(w["text"]) and _n(w["text"]) not in FILL]
        if len(toks) < 3:
            continue
        t0, t1 = span[0]["start"], span[-1]["end"]
        near = [_n(w["text"]) for w in kept if t0 - 30 <= w["start"] <= t1 + 90 and _n(w["text"]) not in FILL]
        # retake je ista misao ponovo (često malo drugačijim rečima): najsličniji zadržani odlomak iste dužine
        L = min(len(toks), 12)
        probe = toks[:L]
        best = 0.0
        for i in range(max(1, len(near) - L + 1)):
            for ln in (L - 2, L, L + 2):
                win = near[i:i + max(1, ln)]
                best = max(best, difflib.SequenceMatcher(None, probe, win).ratio())
        if best < 0.4:
            txt = " ".join(w["text"] for w in span)
            out.append(f"retake {d['from']}–{d['to']} \"{txt[:70]}\" je izbačen, a nijedna njegova verzija nije zadržana "
                       f"u blizini (najsličnije {best:.0%}) — da li je to stvarno ponovljeno? Zadrži poslednju potpunu "
                       "verziju (ccc keep)")
    return out
