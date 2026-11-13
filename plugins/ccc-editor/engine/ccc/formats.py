"""Formati — glavni meni (CCC Editing Style Menu) i pravila svakog formata.

Svaki format kaže samo dve stvari:
  1. ŠTA PREUZIMA IZ BASIC-A (`from_basic`) i sa kojim pravilima;
  2. ŠTA JE SAMO NJEGOVO (`own`) — elementi koje gradimo posebno za taj format.

Pravila za element iz Basic-a (hook, captions, camera):
  • izostavljen ključ      → isto kao u Basic-u (klijent bira sve što bira i u Basic-u)
  • False                  → element ne postoji u ovom formatu (npr. nema hooka)
  • {"styles": [...]}      → klijent bira samo među ovim stilovima
  • {"positions": ["above"]}, {"modes": ["static"]} … → jedna vrednost = zaključano, klijent to ne bira
  • {"optional": False}    → (hook) hook je obavezan, nema "No text hook"
  • {"modes": ["chill"]}   → (pacing) fast = tesni rezovi, chill = malo više vazduha; jedna vrednost = zaključano
  • {"choices": ["ccc"]}   → (font) set fontova za titlove + hook (engine/ccc/fonts.py); jedna vrednost = zaključano
Sečenje (tight cuts) i zvuk (-14 LUFS) uvek važe — to je CCC standard za svaki format.

Primer novog formata:
    fmt("talking-points", "Talking Points", "…", status="soon",
        from_basic={"hook": {"positions": ["above"], "optional": False},
                    "captions": {"styles": ["karaoke", "minimal"]},
                    "camera": {"modes": ["static"]}},
        own=["numbered points on screen"])

Status: "ready" = radi i klijent ga bira; "soon" = kartica "Coming soon" u meniju (ne može se izabrati).
"""
from __future__ import annotations

import re

import os

from .fonts import IDS as FONT_IDS, SETS as FONT_SETS

HOOK_STYLES = ["box", "serif", "color", "stack"]
HOOK_POSITIONS = ["below", "above"]
FORMAT_ONLY = {"hook.positions": ["line"]}  # vrednosti koje Basic ne nudi, ali format sme da zaključa
DEV = bool(os.environ.get("CCC_DEV"))       # razvoj: "soon" formati se mogu editovati (klijenti ne)
CAPTION_STYLES = ["clean", "karaoke", "box", "minimal"]
CAMERA_MODES = ["zoom", "static"]
PACING_MODES = ["fast", "chill"]

BASIC = {
    "hook": {"styles": HOOK_STYLES, "positions": HOOK_POSITIONS, "optional": True},
    "captions": {"styles": CAPTION_STYLES},
    "camera": {"modes": CAMERA_MODES},
    "font": {"choices": FONT_IDS},
    "pacing": {"modes": PACING_MODES},
}

# Imena za klijenta (engleski) — za "Set by this format" i izveštaje.
NAMES = {
    "hook.styles": {"box": "TikTok Box hook", "serif": "Editorial Serif hook", "color": "Color Block hook",
                    "stack": "Stacked hook"},
    "hook.positions": {"below": "hook below the captions", "above": "hook above your head",
                       "line": "hook on the split line, then captions there"},
    "captions.styles": {"clean": "Clean captions", "karaoke": "Karaoke captions", "box": "Box Fill captions",
                        "minimal": "Minimal captions"},
    "camera.modes": {"zoom": "zoom on jump cuts", "static": "static camera"},
    "font.choices": {k: f"{v['name']} font" for k, v in FONT_SETS.items()},
    "pacing.modes": {"fast": "fast-paced cuts", "chill": "chill pacing"},
}


def fmt(id: str, title: str, tagline: str, *, status: str = "soon", from_basic: dict | None = None,
        own: list[str] | None = None, includes: list[str] | None = None, layout: str = "full") -> dict:
    """Napravi format: Basic elementi sa pravilima ovog formata + njegovi sopstveni elementi."""
    rules = from_basic or {}
    unknown = set(rules) - set(BASIC)
    if unknown:
        raise ValueError(f"{id}: nepoznat Basic element {unknown} (postoje: {list(BASIC)})")
    elements: dict = {}
    for name, base in BASIC.items():
        rule = rules.get(name, {})
        if rule is False:
            continue
        el = dict(base)
        for k, v in rule.items():
            if k not in base:
                raise ValueError(f"{id}: {name}.{k} ne postoji (postoje: {list(base)})")
            if isinstance(base[k], list):
                ok = base[k] + FORMAT_ONLY.get(f"{name}.{k}", [])
                bad = set(v) - set(ok)
                if bad or not v:
                    raise ValueError(f"{id}: {name}.{k} = {v} — dozvoljeno: {ok}")
                v = [x for x in ok if x in v]  # redosled kao u Basic-u
            el[k] = v
        elements[name] = el
    return {"id": id, "title": title, "tagline": tagline, "status": status, "elements": elements,
            "own": own or [], "includes": includes or [], "layout": layout}


# ------------------------------------------------------------------ registar (redosled = redosled u meniju)
FORMATS: list[dict] = [
    fmt("basic", "Basic Edit",
        "Your talking-head video, edited the CCC way — tight cuts, a scroll-stopping hook, captions and clean audio.",
        status="ready",
        includes=["Tight cuts", "Text hook", "Captions", "Camera zoom", "Clean audio"]),
    # Split Screen: 50/50 — sadržaj gore, govornik dole; hook prvih ~3 s na liniji podele,
    # pa na istom mestu titlovi (bez hooka titlovi od starta); kamera uvek statična; ostalo kao Basic.
    fmt("split-screen", "Split Screen",
        "You below, what you're talking about above — animated visuals, real logos and headlines, or your own screenshots.",
        status="ready",
        from_basic={"hook": {"positions": ["line"]}, "camera": {"modes": ["static"]}},
        own=["50/50 split: visuals on top, you below", "top half filled automatically (or with your files)"],
        includes=["50/50 split", "Animated visuals", "Real logos & headlines", "Your screenshots", "Captions"],
        layout="split"),
    # Sledeći formati: dok se grade stoje kao "soon" (kartica Coming soon); kad su gotovi → status="ready".
    fmt("tier-list", "Tier List",
        "Rank anything from S to F on screen while you talk — the format people can't help commenting on."),
]
BY_ID = {f["id"]: f for f in FORMATS}


def get(fid: str | None) -> dict:
    f = BY_ID.get(fid or "basic")
    if not f:
        raise ValueError(f"Unknown format: {fid}")
    return f


def fixed(f: dict) -> list[str]:
    """Šta je u ovom formatu zaključano (klijent ne bira) — rečenice za stranicu."""
    out = []
    if "hook" not in f["elements"]:
        out.append("no text hook")
    for el, key in (("hook", "styles"), ("hook", "positions"), ("captions", "styles"), ("camera", "modes"),
                    ("font", "choices"), ("pacing", "modes")):
        vals = f["elements"].get(el, {}).get(key)
        if vals and len(vals) == 1:
            out.append(NAMES[f"{el}.{key}"][vals[0]])
    return out


def menu() -> list[dict]:
    return [{k: f[k] for k in ("id", "title", "tagline", "status", "includes")} for f in FORMATS]


CHOICE_KEYS = ("format", "hook_text", "hook_style", "hook_position", "caption_style", "font", "color", "camera",
               "pacing", "top_style", "web", "links", "assets")


def carry_over(cur: dict, new_format: str) -> dict:
    """Promena formata: zadrži svaki izbor koji novi format dozvoljava (ranije su ostajali samo hook tekst i boja —
    QA 0.8.0, P1-32); ostalo se vraća na podrazumevano novog formata."""
    f = get(new_format)
    el = f["elements"]
    allowed = {
        "hook_style": (el.get("hook") or {}).get("styles", []), "hook_position": (el.get("hook") or {}).get("positions", []),
        "caption_style": el["captions"]["styles"], "camera": (el.get("camera") or {}).get("modes", []),
        "pacing": (el.get("pacing") or {}).get("modes", []), "font": (el.get("font") or {}).get("choices", []),
    }
    out = {"format": f["id"]}
    for k, v in cur.items():
        if k == "format":
            continue
        if k in allowed:
            if v in allowed[k]:
                out[k] = v
        elif k in ("top_style", "web", "links", "assets"):
            if f.get("layout") == "split":
                out[k] = v
        elif k == "hook_text" and el.get("hook") or k == "color":
            out[k] = v
    return out


def validate(d: dict) -> dict:
    """Izbori sa stranice (ili iz `ccc choices`) → čisti izbori za engine, po pravilima formata.
    ValueError sa porukom za klijenta (engleski)."""
    from .captions import parse_color
    f = get(d.get("format"))
    if f["status"] != "ready" and not DEV:
        raise ValueError(f"{f['title']} isn't available yet — it's coming soon.")
    el = f["elements"]
    title = f["title"]

    def pick(value, allowed: list, what: str):
        """Izbor klijenta ili podrazumevano (prva dozvoljena); nedozvoljeno → jasna poruka."""
        value = value or allowed[0]
        if value not in allowed:
            if len(allowed) == 1:
                raise ValueError(f"{title} always uses {NAMES[what][allowed[0]]}.")
            raise ValueError(f"That option isn't available in {title}.")
        return value

    hook = el.get("hook")
    text = (d.get("hook_text") or "").strip() if hook else ""
    hook_style = pos = None
    if hook:
        if not text and not hook["optional"]:
            raise ValueError("This format needs a text hook — please type one.")
        if len(text) > 160:
            raise ValueError("The hook text is too long — keep it under 160 characters.")
        if text:
            if not d.get("hook_style") and len(hook["styles"]) > 1:
                raise ValueError("Please pick a hook style.")
            hook_style = pick(d.get("hook_style"), hook["styles"], "hook.styles")
        pos = pick(d.get("hook_position"), hook["positions"], "hook.positions")

    caps = el["captions"]
    if not d.get("caption_style") and len(caps["styles"]) > 1:
        raise ValueError("Please pick a caption style.")
    cap = pick(d.get("caption_style"), caps["styles"], "captions.styles")

    cam = el.get("camera")
    camera = pick(d.get("camera"), cam["modes"], "camera.modes") if cam else "static"

    pac = el.get("pacing")
    pacing = pick(d.get("pacing"), pac["modes"], "pacing.modes") if pac else "fast"
    fnt = el.get("font")
    font = pick(d.get("font"), fnt["choices"], "font.choices") if fnt else "ccc"

    top_style, split_extra = None, {}
    if f.get("layout") == "split":  # Split Screen: stil gornje polovine
        top_style = d.get("top_style") or "dark"
        if top_style not in ("dark", "light"):
            raise ValueError("Top half style must be Dark or Light.")
        # Pravi vizuali sa interneta (podrazumevano uključeno) + linkovi koje je klijent naveo (nivo 1 hijerarhije).
        w = d.get("web", True)
        web = not (w is False or str(w).strip().lower() in ("off", "no", "false", "0"))
        raw = d.get("links") or []
        if isinstance(raw, str):
            raw = re.split(r"[\s,]+", raw)
        links = [str(u).strip()[:500] for u in raw if str(u).strip()]
        links = [u if re.match(r"^https?://", u, re.I) else "https://" + u
                 if re.match(r"^(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)+(/\S*)?$", u, re.I) else u for u in links]
        bad = [u for u in links if not re.match(r"^https?://[^\s.]+\.\S+$", u, re.I)]
        if bad:
            raise ValueError(f"That's not a full link: {bad[0][:60]} — paste the full link (copy it from the address bar)")
        split_extra = {"top_style": top_style, "web": web, "links": links[:20]}

    color = None
    if d.get("color"):
        try:
            color = parse_color(d["color"])
        except ValueError:
            raise ValueError("That color isn't valid — use a hex like #FF5A1F.")
    return {"format": f["id"], "hook_text": text, "hook_style": hook_style, "hook_position": pos or "below",
            "caption_style": cap, "font": font, "color": color, "camera": camera,
            "pacing": pacing, **split_extra}
