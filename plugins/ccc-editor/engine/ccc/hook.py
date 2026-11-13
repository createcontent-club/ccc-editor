"""Text hook — tekst unosi klijent PRE editovanja, stil bira u upitniku.

Zajednička pravila (svi stilovi): prvo slovo veliko, nestaje naglo na rezu oko 3.4 s; pozicija je izbor
klijenta — ispod titla (podrazumevano) ili iznad glave — uz prelaz na drugu ako izabrana nema mesta;
predugačak hook se prijavljuje.
Stilovi (izgled je u remotion/src/components/Hook.tsx):
  box   — Stil 1, po referenci (references/hook/): TikTok Sans 700/95 81 px, crn tekst na belim boksovima,
          prelom kao TikTok editor (pohlepno do ~834 px teksta).
  serif — Stil 2 "Editorial Serif": Instrument Serif 96 px, beli sa mekom senkom, bez boksa,
          balansiran prelom (redovi približno iste dužine).
  color — Stil 3 "Color Block": mere kao Stil 1, ali boks u boji brenda, tekst Extra Bold 800,
          oštrije ivice; boja teksta (crna/bela) se bira po većem kontrastu sa bojom brenda.
  stack — Stil 4 "Stacked" (po slici klijenta): dva oblika jedan na drugom — gornji beli boks sa krupnim
          crnim tekstom, donji manji boks u boji brenda odmah ispod, priljubljen (bez razmaka i bez preklapanja); isti font i debljina
          (Inter Bold) u oba; tekst se deli crtom "|" ili automatski; svaki deo u jednom redu.
"""
from __future__ import annotations

import re

from PIL import ImageFont

from . import fonts as F
from .captions import half_h
from .project import FONTS as _FONTS

FONTS = _FONTS
STYLES = {
    # box/color/stack: font i tracking iz izabranog seta (engine/ccc/fonts.py); serif uvek svoj.
    "box": {"weight": 700, "px": 81, "max_w": 834, "line_h": 129, "pitch": 84, "pad_x": 30, "balanced": False},
    "color": {"weight": 800, "px": 81, "max_w": 834, "line_h": 129, "pitch": 84, "pad_x": 30, "balanced": False},
    "stack": {"weight": 700, "px": 96, "max_w": 900, "line_h": 131, "pitch": 0, "pad_x": 34, "balanced": False},
    "serif": {"font": "InstrumentSerif-Regular.ttf", "axes": None, "px": 96, "tracking": -0.02,
              "max_w": 900, "line_h": 104, "pitch": 100, "pad_x": 0, "balanced": True},
}
GAP = 36                         # razmak hook ↔ titl / hook ↔ teme
SAFE_TOP, SAFE_BOTTOM = 220, 1540  # IG/TikTok UI zone (px na 1920)
END_DEFAULT = 3.44               # referenca: hook nestaje naglo na 3.44 s
END_WINDOW = (3.0, 4.0)          # …ako u ovom prozoru postoji rez, hook nestaje baš na njemu


def _font(st: dict, fid: str | None = None) -> tuple[ImageFont.FreeTypeFont, float]:
    """(font, tracking u em) za stil hooka u izabranom setu fontova."""
    if "font" in st:  # Editorial Serif — uvek svoj font
        return ImageFont.truetype(str(FONTS / st["font"]), st["px"]), st["tracking"]
    return F.load(fid or F.DEFAULT, "hook", st["weight"], st["px"]), F.tracking(fid, "hook")


def _width(font: tuple, st: dict, text: str) -> float:
    f, tr = font
    return f.getlength(text) + tr * st["px"] * max(0, len(text) - 1)


def wrap(text: str, st: dict, fid: str | None = None) -> list[str]:
    """Pohlepni prelom (TikTok); za balansirane stilove isti broj redova, ali ujednačene dužine."""
    font, lines, cur = _font(st, fid), [], ""
    words = text.split()
    for word in words:
        cand = f"{cur} {word}".strip()
        if cur and _width(font, st, cand) > st["max_w"]:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    if not st["balanced"] or len(lines) < 2:
        return lines
    # Balans: isti broj redova, minimalna dužina najdužeg reda (DP po granicama reči).
    n, k = len(words), len(lines)
    w = lambda i, j: _width(font, st, " ".join(words[i:j]))
    best = {(0, 0): (0.0, [])}
    for r in range(1, k + 1):
        for j in range(r, n + 1):
            opts = [(max(best[(i, r - 1)][0], w(i, j)), best[(i, r - 1)][1] + [j])
                    for i in range(r - 1, j) if (i, r - 1) in best]
            if opts:
                best[(j, r)] = min(opts)
    cuts = [0] + best[(n, k)][1]
    return [" ".join(words[a:b]) for a, b in zip(cuts, cuts[1:])]


def box_widths(hook: dict) -> list[float]:
    """Širina svakog reda na ekranu (tekst + boks), za proveru da staje u kadar."""
    if hook.get("style") == "stack":
        return _stack_layout(hook["text"], hook.get("font"))["widths"]
    st = STYLES[hook.get("style", "box")]
    font = _font(st, hook.get("font"))
    return [_width(font, st, l) + 2 * st["pad_x"] for l in hook["lines"]]


def sentence_case(text: str) -> str:
    """Hook uvek počinje velikim slovom (ostatak ostaje kako ga je klijent napisao)."""
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
    return text


def contrast(a: str, b: str) -> float:
    """WCAG odnos kontrasta dve boje (1–21)."""
    from .captions import luminance
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


LARGE_TEXT_CONTRAST = 3.0  # WCAG AA za krupan/debeo tekst (hook je uvek krupan)


def text_on(bg: str) -> str:
    """Beo tekst kad god ima bar 3:1 sa bojom (crvena, narandžasta, tamne boje — kao u praksi),
    inače crn (žuta, zelena, svetloplava)."""
    return "#FFFFFF" if contrast(bg, "#FFFFFF") >= LARGE_TEXT_CONTRAST else "#000000"


# Stil 4 "Stacked": veličine (px na 1080) i oblik.
STACK = {"weight": 700, "max_w": 900,  # font i tracking: izabrani set (F.load(…, "caption", 700, px))
         "top": {"px": 96, "min_px": 64, "h_ratio": 1.36, "pad_x": 34, "radius": 18},
         "sub": {"px": 52, "min_px": 38, "h_ratio": 1.5, "pad_x": 22, "radius": 14},
         "overlap": 0}  # oblici se dodiruju, bez preklapanja (odluka 11. nov 2026)
SPLIT_BEFORE = {"in", "with", "for", "to", "and", "so", "because", "without", "when", "if", "while", "but",
                "or", "from", "by", "using", "like", "before", "after", "until", "(start", "("}


def split_stack(text: str) -> list[str]:
    """Tekst za dva oblika: klijentova crta '|' ili prirodno mesto (ispred predloga/veznika, ~40–65% reči)."""
    if "|" in text:  # prvi NE-prazan deo gore, sve ostalo dole ("| tekst" ili "a | b | c" ne prave prazan oblik)
        parts = [s.strip() for s in text.split("|") if s.strip()]
        return [parts[0], " ".join(parts[1:])] if len(parts) > 1 else parts[:1] or [text.replace("|", "").strip()]
    words = text.split()
    if len(words) < 4:
        return [text]
    n = len(words)
    cands = [i for i in range(max(2, round(n * 0.4)), min(n - 1, round(n * 0.65)) + 1)
             if words[i].lower() in SPLIT_BEFORE or words[i - 1].endswith((",", ":", "—"))]
    i = min(cands, key=lambda i: abs(i - n / 2)) if cands else round(n / 2)
    return [" ".join(words[:i]).rstrip(",:—"), " ".join(words[i:])]


def _fit_px(part: str, spec: dict, fid: str | None = None) -> tuple[int, float]:
    """Najveća veličina (≤ px, ≥ min_px) na kojoj deo staje u jedan red."""
    tr = F.tracking(fid, "stack")
    for px in range(spec["px"], spec["min_px"] - 1, -2):
        f = F.load(fid or F.DEFAULT, "caption", STACK["weight"], px)
        w = f.getlength(part) + tr * px * max(0, len(part) - 1) + 2 * spec["pad_x"]
        if w <= STACK["max_w"]:
            return px, w
    return spec["min_px"], w


def _fit_split(text: str, fid: str | None) -> str:
    """Bez klijentove crte '|': od prirodnih mesta za prelom bira prvo na kom OBA dela staju u jedan red
    (test ai-actor-0: prelom posle "fortune" je bio predugačak, a "charges | a fortune…" staje)."""
    if "|" in text:
        return text
    words = text.split()
    n = len(words)
    if n < 4:
        return text
    first = split_stack(text)
    cands = [" ".join(first)] if len(first) == 2 else []
    dangling = {"a", "an", "the", "to", "of", "for", "and", "or", "in", "on", "with", "my", "your", "her", "his", "their"}
    order = sorted((i for i in range(2, n - 1) if words[i - 1].lower() not in dangling), key=lambda i: (not (words[i].lower() in SPLIT_BEFORE or words[i - 1].endswith((",", ":", "—"))),
                                                   abs(i - n / 2)))
    cands += [" ".join(words[:i]).rstrip(",:—") + " | " + " ".join(words[i:]) for i in order]
    for c in cands:
        c2 = c if "|" in c else c.replace(first[0], first[0] + " |", 1)
        parts = [x.strip() for x in c2.split("|", 1)]
        if all(_fit_px(pt if j else sentence_case(pt), [STACK["top"], STACK["sub"]][j], fid)[1] <= STACK["max_w"]
               for j, pt in enumerate(parts)):
            return c2
    return text


def _stack_layout(text: str, fid: str | None = None) -> dict:
    # Prvi deo uvek velikim slovom; drugi ostaje kako je napisan (nastavak rečenice: "in your industry").
    parts = split_stack(_fit_split(text, fid))
    parts = [sentence_case(parts[0])] + parts[1:]
    specs = [STACK["top"], STACK["sub"]][: len(parts)]
    sizes, widths, heights = [], [], []
    for part, spec in zip(parts, specs):
        px, w = _fit_px(part, spec, fid)
        sizes.append(px)
        widths.append(w)
        heights.append(round(px * spec["h_ratio"]))
    height = sum(heights) - (STACK["overlap"] if len(parts) == 2 else 0)
    return {"lines": parts, "sizes": sizes, "heights": heights, "widths": [round(w) for w in widths],
            "height": height, "too_wide": any(w > STACK["max_w"] for w in widths)}


def build(p: dict, text: str, style: str = "box", color: str | None = None, placement: str = "below") -> dict:
    from .camera import min_head_after_zoom

    st = STYLES[style]
    fid = p.get("font") if p.get("font") in F.SETS else F.DEFAULT
    fps = p["fps"]
    cuts, f = [], 0
    for g in p["segments"][:-1]:
        f += g["vFrames"]
        cuts.append(f / fps)
    in_window = [c for c in cuts if END_WINDOW[0] <= c <= END_WINDOW[1]]
    end = min(in_window, key=lambda c: abs(c - END_DEFAULT)) if in_window else round(END_DEFAULT * fps) / fps
    text = sentence_case(text.strip())
    # "|" je samo znak za prelom u Stacked stilu; u ostalim stilovima bi se video na ekranu ("How to grow | without")
    # — npr. kad klijent sa Stacked pređe na Box (QA 0.8.0). Novi redovi i višestruki razmaci → jedan razmak.
    if style != "stack":
        text = re.sub(r"\s*\|\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    extra = {}
    if style == "stack":
        lay = _stack_layout(text, fid)
        lines, height = lay["lines"], lay["height"]
        extra = {"sizes": lay["sizes"], "heights": lay["heights"], "overlap": STACK["overlap"]}
    else:
        lines = wrap(text, st, fid)
        height = (len(lines) - 1) * st["pitch"] + st["line_h"]
    # Hook i titlovi su na ekranu ISTOVREMENO. Pozicija 1 (podrazumevana): ispod titla, ako staje
    # iznad donje UI zone. Pozicija 2: iznad glave (ispod gornje UI zone). Inače: ispod titla.
    if placement == "line":  # Split Screen: centar hooka na liniji podele; titlovi tu kreću posle hooka
        line = (p.get("layout") or {}).get("line", 960)
        y = line - height / 2
        where = "na liniji podele"
        if y < SAFE_TOP or y + height > SAFE_BOTTOM:
            where = "NEMA MESTA — hook je predugačak"
        return _finish(p, text, style, fid, placement, color, lines, extra, st, end, y, height, where,
                       lay if style == "stack" else None)
    below = p["captionY"] + half_h(p) + GAP
    above = min_head_after_zoom(p) - GAP - height  # teme pri najvećem zumu
    # Klijent bira poziciju ("below" = ispod titla, "above" = iznad glave). Ako izabrana nema mesta,
    # koristi se druga i to se prijavljuje (skill obaveštava klijenta). Nikad preko UI zone ni lica.
    fits = {"below": below + height <= SAFE_BOTTOM, "above": above >= SAFE_TOP}
    spot = {"below": (below, "ispod titla"), "above": (above, "iznad glave")}
    other = "above" if placement == "below" else "below"
    if fits[placement]:
        y, where = spot[placement]
    elif fits[other]:
        y, where = spot[other][0], f"{spot[other][1]} (izabrano {spot[placement][1]}, ali tamo nema mesta)"
    else:  # predugačak hook — skill traži od klijenta kraći tekst
        y, where = below, "NEMA MESTA — hook je predugačak"
    return _finish(p, text, style, fid, placement, color, lines, extra, st, end, y, height, where,
                   lay if style == "stack" else None)


def _finish(p, text, style, fid, placement, color, lines, extra, st, end, y, height, where, lay) -> dict:
    colors = {}
    if style in ("color", "stack"):
        from .captions import DEFAULT_ACCENT
        bg = color or p.get("caption_accent") or DEFAULT_ACCENT  # podrazumevano: ista boja brenda kao titlovi
        colors = {"bg": bg, "fg": text_on(bg)}
    if lay is not None and lay["too_wide"]:
        where = "NEMA MESTA — deo hooka je predugačak za jedan red"
    return {"text": text, "style": style, "font": fid, "placement": placement, **colors, **extra, "lines": lines, "y": round(y),
            "pitch": st["pitch"],
            "start": 0.0, "end": round(end, 4), "bottom": round(y + height), "position": where,
            "fits": not where.startswith("NEMA")}
