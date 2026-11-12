"""Titlovi po referenci (references/captions/, prvih 5 s).

Izmereno na referenci:
  - 1–4 reči, ≤ ~16 znakova, prelom posle interpunkcije ("did I just do," / "dude?");
  - originalna mala/velika slova i interpunkcija;
  - titl se pojavljuje na početku prve reči i nestaje na kraju poslednje (između titlova
    ostaju prazni frejmovi ako govornik ćuti);
  - centar titla je 0.095 × visina lica ispod brade.
Stil i animacija (Inter SemiBold 58 px, meka senka, fade+blur ulaz ~4 frejma, trenutan izlaz)
su u remotion/src/components/Captions.tsx.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys

from .project import ROOT

# Stilovi titlova (izgled je u remotion/src/components/Captions.tsx). Pravila podele po stilu:
STYLES = {
    # Stil 1 "Clean" — po referenci: Inter SemiBold 58 px, meka senka, blur-in.
    "clean": {"max_words": 4, "max_chars": 16, "target": 13, "half_h": 36},
    # Stil 2 "Karaoke" — isti izgled kao Stil 1, samo druga animacija (pop + aktivna reč žuta).
    "karaoke": {"max_words": 4, "max_chars": 16, "target": 13, "half_h": 36},
    # Stil 4 "Minimal Contrast" — isti tekst, jedna glavna reč u Inter Bold, ostalo Inter Light.
    "minimal": {"max_words": 4, "max_chars": 16, "target": 13, "half_h": 36},
    # Stil 3 "Box Fill" — isti tekst na crnom boksu (85%); reči se pune 20% → 100% dok se izgovaraju; tvrd prelaz.
    # Boks je viši od reda teksta (padding 16/18 px) → veća polovina visine za hook/proveru.
    "box": {"max_words": 4, "max_chars": 16, "target": 13, "half_h": 54},
}
BREAK_AFTER = (",", ".", "?", "!", ":", ";", "—")
BELOW_CHIN = 0.30   # × visina lica: centar titla ispod brade (referenca 0.095 → tvoja korekcija: dalje od brade)


def half_h(p: dict) -> int:
    """Pola visine reda titla za stil projekta (hook i provere računaju od ovoga)."""
    return STYLES[p.get("caption_style") or "clean"]["half_h"]


def span_to_out(s: float, e: float, segments: list[dict]) -> tuple[float, float] | None:
    """Izvorni raspon reči → izlazno vreme, preko dela reči koji je OSTAO u videu.
    (Whisper ume da stavi početak reči u uzdah koji je isečen — reč ne sme da ispadne zbog toga.)"""
    acc, first, last = 0.0, None, None
    for g in segments:
        a, b = max(s, g["srcStart"]), min(e, g["srcEnd"])
        if a < b:
            o = acc + a - g["srcStart"]
            first = o if first is None else first
            last = acc + b - g["srcStart"]
        acc += g["srcEnd"] - g["srcStart"]
    return (first, last) if first is not None else None


def snap_to_voice(t: float, runs: list[tuple[float, float]], edge: int, lo: float, hi: float) -> float:
    """Whisper vreme reči pomeri na stvarni početak/kraj glasa ako je blizu (≤ lo pre / ≤ hi posle)."""
    near = [r[edge] for r in runs if t - lo <= r[edge] <= t + hi]
    return min(near, key=lambda v: abs(v - t)) if near else t


def display(word: str) -> str:
    """Tekst reči u titlu BEZ interpunkcije. Ostaje ono što je deo reči: apostrof (don't),
    crtica u složenici (12-year-old), $ i zarez/tačka unutar broja ($3,600)."""
    w = word.replace("…", "").replace("—", "").replace("–", "")
    w = re.sub(r"[.,]+$", "", w)                       # tačka/zarez na kraju reči — uvek
    w = re.sub(r"(?<!\d)[.,](?!\d)", "", w)          # tačka/zarez osim unutar broja
    w = re.sub(r"[?!:;\"“”‘()\[\]]", "", w)
    w = re.sub(r"^['’-]+|['’-]+$", "", w)              # apostrof/crtica samo na ivicama
    return w.strip()


def _cost(ws: list[dict], last_in_run: bool, st: dict) -> float:
    """Cena jednog titla: blizu ciljne dužine, preko maksimuma skupo, sama reč usred misli skupa."""
    chars = len(" ".join(display(w["text"]) for w in ws))
    cost = abs(chars - st["target"]) * 0.3
    if chars > st["max_chars"]:
        cost += (chars - st["max_chars"]) * 4 + (30 if len(ws) > 1 and chars > st["max_chars"] + 4 else 0)
    if len(ws) == 1 and not last_in_run:
        cost += 6
    if len(ws) == 1 and last_in_run and chars <= 4:  # "it." sam na kraju
        cost += 4
    return cost


def _split_run(run: list[dict], st: dict) -> list[list[dict]]:
    """Optimalna podela jedne misli (bez interpunkcije unutra) na titlove — dinamičko programiranje."""
    n = len(run)
    best = [0.0] + [float("inf")] * n
    back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(max(0, j - st["max_words"]), j):
            c = best[i] + _cost(run[i:j], j == n, st)
            if c < best[j]:
                best[j], back[j] = c, i
    out, j = [], n
    while j > 0:
        out.append(run[back[j]:j])
        j = back[j]
    return out[::-1]


def chunk(words: list[dict], st: dict) -> list[list[dict]]:
    """Reči → titlovi. Interpunkcija i novi izgovoreni deo uvek prekidaju; unutar misli biramo
    najujednačeniju podelu (reference: "What the f*ck" / "did I just do," / "dude?")."""
    runs, cur = [], []
    for w in words:
        if cur and w.get("_newline"):
            runs.append(cur)
            cur = []
        cur.append(w)
        if w["text"].endswith(BREAK_AFTER):
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return [c for r in runs for c in _split_run(r, st)]


# Pomoćne reči koje nikad nisu "glavna reč" titla (Stil 4).
STOPWORDS = set("""a an the and or but so if then than that this these those to of in on at by for with from up down out
over into as is are was were be been being am do does did done have has had having will would can could should may might
must shall i me my mine you your yours he him his she her hers it its we us our ours they them their theirs what which who
whom whose when where why how not no yes just very really also too all any some each every more most much many such own
same other there here about like get got go going gonna let let's i'm you're it's that's don't can't won't didn't
because versus though although while until unless since whether also actually basically literally maybe even only still
already again ever never always okay ok yeah""".split())


def key_word(texts: list[str]) -> int:
    """Indeks "glavne reči" titla: brojevi/iznosi prvo, zatim najduža reč sa sadržajem; pomoćne reči nikad
    (osim ako titl nema nijednu drugu)."""
    def score(w: str) -> float:
        n = w.lower().strip("'’")
        if re.search(r"[\d$€£%]", n):
            return 100 + len(n)
        if n in STOPWORDS:
            return -1 + len(n) / 100  # samo ako u titlu nema ničeg drugog: najduža pomoćna reč ("like", ne "a")
        return len(n)
    scores = [score(w) for w in texts]
    best = max(range(len(texts)), key=lambda i: (scores[i], i))  # izjednačeno → kasnija reč (naglasak na kraju fraze)
    return best


def _key_for(c: list[dict], shown: list, overrides: dict) -> int:
    """Glavna reč titla: ručni izbor (Claude/klijent) ako postoji za ovaj titl, inače pravilo."""
    if not shown:
        return 0
    want = overrides.get(c[0]["id"])
    if want:
        for i, (_, d) in enumerate(shown):
            if d.lower() == want.lower():
                return i
    return key_word([d for _, d in shown])


def build(p: dict, voice_runs: list[tuple[float, float]], style: str = "clean") -> list[dict]:
    st = STYLES[style]
    removed = {w for r in p["removed"] for w in r["words"]}
    segs = p["segments"]
    kept = []
    for w in p["words"]:
        if w["id"] in removed:
            continue
        s = snap_to_voice(w["start"], voice_runs, 0, 0.12, 0.08)
        e = snap_to_voice(w["end"], voice_runs, 1, 0.08, 0.12)
        span = span_to_out(min(s, w["start"]), max(e, w["end"]), segs)
        if span is None:
            continue
        kept.append({**w, "o_start": span[0], "o_end": max(span[1], span[0] + 0.05)})
    # Novi titl i na svakom rezu gde je izbačen ceo deo (retake, off-script) — misao se prekida.
    for a, b in zip(kept, kept[1:]):
        if b["u"] != a["u"]:
            b["_newline"] = True
    caps = []
    for c in chunk(kept, st):
        shown = [(w, display(w["text"])) for w in c]
        shown = [(w, d) for w, d in shown if d]
        caps.append({"text": " ".join(d for _, d in shown), "words": [w["id"] for w in c],
                     # vreme svake reči (izlazna vremenska linija) — karaoke boji reč koja se izgovara
                     "wt": [{"text": d, "start": round(w["o_start"], 3)} for w, d in shown],
                     "key": _key_for(c, shown, p.get("key_overrides") or {}),
                     "start": round(c[0]["o_start"], 3), "end": round(c[-1]["o_end"], 3)})
    # Titl stoji dok ne krene sledeći. Whisper ume da zatvori reč pre nego što je izgovorena
    # ("$3,600" je trajao kraće od "three thousand six hundred dollars"), a montaža nema pauza —
    # pa između titlova nikad nema praznog ekrana dok se govori.
    total = sum(g["vFrames"] for g in segs) / p["fps"]
    if caps:
        caps[0]["start"] = 0.0                      # video kreće na prvom slogu → i titl
        for a, b in zip(caps, caps[1:]):
            a["end"] = b["start"]
        caps[-1]["end"] = round(total, 3)           # poslednji titl do poslednjeg frejma
    return caps


def caption_y(job, p: dict) -> tuple[int, dict]:
    """Medijana pozicije brade kroz zadržane delove (frejm svakih ~1.5 s) → y centra titla."""
    times = []
    for s in p["segments"]:
        t = s["srcStart"] + 0.1
        while t < s["srcEnd"] - 0.05:
            times.append(round(t, 2))
            t += 1.5
    env = {**os.environ, "PYTHONPATH": str(ROOT / "engine")}
    r = subprocess.run([sys.executable, "-m", "ccc.face", str(job.public / "video.mp4"), json.dumps(times[:60])],
                       capture_output=True, text=True, env=env)
    track = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else []
    if not track:
        return 1180, {"faces": 0}
    H = track[0]["H"]
    chins = sorted(f["chin"] for f in track)
    chin = chins[int(0.8 * (len(chins) - 1))] * 1920 / H  # brada je u 80% kadrova iznad ove linije (govornik se pomera)
    face_h = statistics.median(f["face_h"] for f in track) * 1920 / H
    # Gornja ivica titla ostaje na istoj udaljenosti od brade kao kod Stila 1 (odobreno);
    # viši stilovi (npr. boks) se spuštaju za razliku u visini.
    y = round(chin + BELOW_CHIN * face_h + half_h(p) - STYLES["clean"]["half_h"])
    # Teme: YuNet okvir lica ne uključuje kosu → +25% visine lica; uzimamo najviši položaj glave
    # (20. percentil), da hook iznad glave ne dođe preko temena kad se govornik pomeri.
    tops = sorted(f["chin"] - f["face_h"] for f in track)
    head_top = tops[int(0.2 * (len(tops) - 1))] * 1920 / H - 0.25 * face_h
    return y, {"faces": len(track), "samples": len(times[:60]), "chin": round(chin), "face_h": round(face_h),
               "head_top": round(head_top),
               "chin_spread": round((max(f["chin"] for f in track) - min(f["chin"] for f in track)) * 1920 / H)}


def split_place(p: dict) -> None:
    """Split Screen: titl na liniji podele; donja polovina = isečak izvora (cropY) tako da teme
    govornika bude ~SPLIT_HEADROOM ispod linije (mesto za titl/hook), a lice u kadru."""
    lay = p["layout"]
    line = lay["line"]
    half = 1920 - line
    face = p.get("face") or {}
    head = face.get("head_top")
    crop = (head - SPLIT_HEADROOM) if head is not None else (1920 - half) // 2
    lay["cropY"] = int(max(0, min(1920 - half, round(crop))))
    p["captionY"] = line


def to_output_y(p: dict, y: float) -> float:
    """y u izvornom kadru → y na ekranu (Split Screen pomera govornika u donju polovinu)."""
    lay = p.get("layout") or {}
    if lay.get("type") == "split":
        return y - lay.get("cropY", 0) + lay["line"]
    return y


SPLIT_HEADROOM = 110  # px između linije podele i temena govornika (titl/hook stoje na liniji)


# ------------------------------------------------------------------ boja naglaska (Karaoke)
# Paleta za upitnik; klijent može da upiše i svoju boju brenda (hex).
ACCENT_PALETTE = {
    "yellow": "#FFE600",   # podrazumevana (CCC)
    "green": "#3DFF6E",
    "blue": "#3DA5FF",
    "orange": "#FF8A1F",
    "pink": "#FF4FB4",
    "red": "#FF3B30",
    "purple": "#B57BFF",
    "cyan": "#2EF2FF",
}
DEFAULT_ACCENT = ACCENT_PALETTE["yellow"]


def parse_color(value: str) -> str:
    """'#ff5a1f', 'FF5A1F', '#F50' ili naziv iz palete → '#RRGGBB'."""
    v = value.strip().lower()
    if v in ACCENT_PALETTE:
        return ACCENT_PALETTE[v]
    v = v.lstrip("#")
    if re.fullmatch(r"[0-9a-f]{3}", v):
        v = "".join(ch * 2 for ch in v)
    if not re.fullmatch(r"[0-9a-f]{6}", v):
        raise ValueError(f"Nepoznata boja '{value}'. Upiši hex (npr. #FF5A1F) ili: {', '.join(ACCENT_PALETTE)}")
    return "#" + v.upper()


def luminance(hex_color: str) -> float:
    """Relativna osvetljenost (WCAG), 0 = crna, 1 = bela."""
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


MIN_ACCENT_LUMINANCE = 0.2  # tamnije boje se ne čitaju na tamnim delovima kadra (titl ima samo meku senku)
