"""Sečenje — tajming iz energije zvuka, tekst iz Whisper-a.

1. Šta se izbacuje (po rečima/delovima): poštapalice, mucanje, retake-ovi (automatski) +
   ručne odluke (off-script, false-start…).
2. Šta ostaje = GLAS (Voice.runs: Silero + jak zvuk + suglasnici) minus izbačeno.
   Uzdah, dah i šum nisu glas → nestaju, i između rečenica i usred rečenice.
3. Svaka rupa bez glasa duža od max_gap nestaje; ostaje samo `pre`/`post` (~20 ms) uz glas.
   Video počinje na prvom slogu i završava se na poslednjem.
4. Zvuk se seče do uzorka; slika prati zvuk sa greškom ≤ pola frejma.
"""
from __future__ import annotations

import difflib
import re

from .energy import HOP, Voice

FILLERS = {"um", "uh", "uhm", "umm", "uhh", "erm", "er", "ah", "ahh", "hmm", "hm", "mm", "mhm", "eh"}
REPEAT_OK = {"that", "had", "is", "very", "really", "so", "no", "yeah", "yes", "bye", "ha", "go", "okay", "ok"}


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9$']", "", t.lower())


# ------------------------------------------------------------------ automatske odluke
def _retakes(words: list[dict], utterances: list[dict]) -> set[int]:
    """Deo je retake ako ga isti govornik odmah ponovi: sledeći (ili onaj posle) deo počinje
    istim rečima. "This is a..." / "This is how..." / "This is how I would explain it." → prva dva su retake."""
    toks = [[norm(w["text"]) for w in words if w["u"] == i] for i in range(len(utterances))]
    out = set()
    for i, a in enumerate(toks):
        a = [t for t in a if t and t not in FILLERS]
        if len(a) < 2:
            continue
        cut_off = utterances[i]["text"].rstrip().endswith(("...", "…", "-", "—"))
        for j in (i + 1, i + 2):
            if j >= len(toks):
                break
            b = [t for t in toks[j] if t and t not in FILLERS]
            prefix = 0
            while prefix < min(len(a), len(b)) and a[prefix] == b[prefix]:
                prefix += 1
            ratio = difflib.SequenceMatcher(None, a, b[: len(a)]).ratio()
            if (prefix >= 2 and (cut_off or ratio >= 0.75)) or ratio >= 0.85:
                out.add(i)
                break
    return out


def auto_removals(words: list[dict], utterances: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for ui in _retakes(words, utterances):
        for w in words:
            if w["u"] == ui:
                out[w["id"]] = "retake"
    for i, w in enumerate(words):
        if w["id"] in out:
            continue
        n = norm(w["text"])
        if n in FILLERS:
            out[w["id"]] = "filler"
        elif i + 1 < len(words):
            nxt = words[i + 1]
            if (n and n == norm(nxt["text"]) and n not in REPEAT_OK and nxt["u"] == w["u"]
                    and not re.search(r"[.,!?;:]$", w["text"]) and nxt["start"] - w["end"] < 0.5):
                out[w["id"]] = "stutter"
    return out


def resolve(words: list[dict], utterances: list[dict], decisions: list[dict]) -> dict[str, str]:
    """Automatske odluke + ručne (remove/keep). Kasnija odluka pobeđuje."""
    idx = {w["id"]: i for i, w in enumerate(words)}
    removed = auto_removals(words, utterances)
    for d in decisions:
        for i in range(idx[d["from"]], idx[d["to"]] + 1):
            wid = words[i]["id"]
            if d["action"] == "remove":
                removed[wid] = d["reason"]
            else:
                removed.pop(wid, None)
    return removed


# ------------------------------------------------------------------ segmenti
def _subtract(spans: list[tuple[float, float]], holes: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for s, e in spans:
        pieces = [(s, e)]
        for hs, he in holes:
            nxt = []
            for ps, pe in pieces:
                if he <= ps or hs >= pe:
                    nxt.append((ps, pe))
                    continue
                if hs > ps:
                    nxt.append((ps, hs))
                if he < pe:
                    nxt.append((he, pe))
            pieces = nxt
        out += [(a, b) for a, b in pieces if b - a >= 0.04]
    return out


QUIET_DB = 6.0     # ispod ovoga (dB iznad poda) je tišina
RISE_DB = 4.0      # porast iznad najtišeg dela = nov zvuk (udah) → rezerva staje
SAFE_PAD = 0.02    # prvih 20 ms uz glas uvek ostaje (stari standard), i kad nije tišina


def _quiet_edge(voice: Voice, t: float, pad: float, limit: float) -> float:
    """Ivica segmenta: od glasa (t) do `pad` sekundi pre (pad < 0) ili posle (pad > 0). Prolazi kroz rep
    reči i tišinu, a staje kad krene NOV zvuk (udah, šum): nivo poraste > RISE_DB iznad najtišeg dela
    viđenog do tada i pređe QUIET_DB — tako duža rezerva nikad ne uvuče uzdah, a ne seče rep reči."""
    sign, full = (1 if pad > 0 else -1), abs(pad)
    d = min(SAFE_PAD, full)
    low = float("inf")
    while d + HOP <= full + 1e-9:
        k = int((t + d) / HOP) if sign > 0 else int((t - d - HOP) / HOP)  # frejm koji bi se dodao
        if not 0 <= k < len(voice.rel):
            break
        r = float(voice.rel[k])
        if r > QUIET_DB and r > low + RISE_DB:
            break
        low = min(low, r)
        d += HOP
    x = t + sign * d
    return min(limit, x) if sign > 0 else max(limit, x)


def compute(words: list[dict], utterances: list[dict], removed: dict[str, str], voice: Voice,
            fps: float, cfg: dict) -> tuple[list[dict], list[dict]]:
    duration = voice.duration

    # Izbačeni delovi: ceo izgovoreni deo ako su sve reči izbačene, inače raspon izbačenih reči.
    holes: list[tuple[float, float, str]] = []
    for ui, u in enumerate(utterances):
        uw = [w for w in words if w["u"] == ui]
        if not uw:  # Whisper nije čuo reči (dah, šum, kašalj)
            holes.append((u["start"], u["end"], "noise"))
            continue
        if all(w["id"] in removed for w in uw):
            holes.append((u["start"], u["end"], "+".join(dict.fromkeys(removed[w["id"]] for w in uw))))
            continue
        k = 0
        while k < len(uw):
            if uw[k]["id"] not in removed:
                k += 1
                continue
            j = k
            while j + 1 < len(uw) and uw[j + 1]["id"] in removed:
                j += 1
            s = u["start"] if k == 0 else uw[k]["start"]
            e = u["end"] if j == len(uw) - 1 else uw[j]["end"]
            holes.append((s, e, "+".join(dict.fromkeys(removed[w["id"]] for w in uw[k:j + 1]))))
            k = j + 1

    hole_spans = [(s, e) for s, e, _ in holes]
    pieces = _subtract(voice.runs, hole_spans)
    # Zadržava se samo glas koji pripada zadržanoj reči. Sve ostalo (dah, šapat, pozadina,
    # zvuk pre/posle snimanja) ispada — i kad ga Silero prepozna kao "govor".
    tol = 0.15
    word_spans = [(w["start"] - tol, w["end"] + tol) for w in words if w["id"] not in removed]
    pieces = [(s, e) for s, e in pieces if any(ws < e and we > s for ws, we in word_spans)]
    if not pieces:
        raise SystemExit("Ništa ne ostaje posle sečenja.")

    def hole_between(a: float, b: float) -> tuple[float, float] | None:
        for s, e in hole_spans:
            if s < b and e > a:
                return s, e
        return None

    # Spajanje: komadi blizu jedan drugom (prirodna mikro-pauza) ostaju zajedno, osim preko izbačenog dela.
    kept_words = [w for w in words if w["id"] not in removed]

    def inside_word(a: float, b: float) -> bool:
        """Rupa je unutar jedne reči (npr. zatvaranje pre 'p' u "ex-plain") — to nije pauza."""
        return any(w["start"] <= a and b <= w["end"] for w in kept_words)

    raw: list[list[float]] = []
    for s, e in pieces:
        if raw and not hole_between(raw[-1][1], s):
            gap = s - raw[-1][1]
            if gap <= cfg["max_gap"] or (gap <= cfg["in_word_gap"] and inside_word(raw[-1][1], s)):
                raw[-1][1] = e
                continue
        raw.append([s, e])

    # Rezerva oko glasa (ne ulazi u izbačene delove ni u susedni segment).
    padded = []
    for i, (s, e) in enumerate(raw):
        lo = raw[i - 1][1] if i else 0.0
        hi = raw[i + 1][0] if i + 1 < len(raw) else duration
        for hs, he in hole_spans:
            if he <= s and he > lo:
                lo = he
            if hs >= e and hs < hi:
                hi = hs
        pre = cfg["lead"] if i == 0 else cfg["pre"]
        post = cfg["tail"] if i == len(raw) - 1 else cfg["post"]
        padded.append((_quiet_edge(voice, s, -pre, lo), _quiet_edge(voice, e, post, hi)))
    segs: list[list[float]] = []
    for s, e in padded:
        if segs and s <= segs[-1][1]:
            segs[-1][1] = max(segs[-1][1], e)
        else:
            segs.append([s, e])

    # Zvuk se seče TAČNO (do uzorka). Slika može samo po frejm, pa frejmove raspoređujemo
    # tako da prate zvuk: kumulativno zaokruživanje + izbor izvornog frejma koji poništava
    # grešku → slika nikad ne odstupa od zvuka više od pola frejma.
    segments, acc, prev_f = [], 0.0, 0
    for s, e in segs:
        out_start_audio = acc
        acc += e - s
        f_end = round(acc * fps)
        frames = f_end - prev_f
        drift = prev_f / fps - out_start_audio  # slika kasni (+) / žuri (−) za zvukom na početku segmenta
        segments.append({"srcStart": round(s, 4), "srcEnd": round(e, 4),
                         "vFrom": max(0, round((s + drift) * fps)), "vFrames": frames})
        prev_f = f_end

    # Izbačeno = sve između segmenata, sa razlogom.
    removed_spans = []
    bounds = [0.0] + [x for sg in segs for x in sg] + [duration]
    for s, e in zip(bounds[0::2], bounds[1::2]):
        if e - s < 0.005:
            continue
        reasons = [r for hs, he, r in holes if hs < e and he > s]
        if not reasons:
            reasons = ["lead-in"] if s == 0 else ["tail"] if e >= duration - 0.01 else ["pause"]
        ids = [w["id"] for w in words if w["start"] >= s - 0.05 and w["end"] <= e + 0.05]
        removed_spans.append({"srcStart": round(s, 3), "srcEnd": round(e, 3),
                              "reason": "+".join(dict.fromkeys("+".join(reasons).split("+"))), "words": ids})
    return segments, removed_spans
