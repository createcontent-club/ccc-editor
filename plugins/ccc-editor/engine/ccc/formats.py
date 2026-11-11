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

HOOK_STYLES = ["box", "serif", "color", "stack"]
HOOK_POSITIONS = ["below", "above"]
CAPTION_STYLES = ["clean", "karaoke", "box", "minimal"]
CAMERA_MODES = ["zoom", "static"]

BASIC = {
    "hook": {"styles": HOOK_STYLES, "positions": HOOK_POSITIONS, "optional": True},
    "captions": {"styles": CAPTION_STYLES},
    "camera": {"modes": CAMERA_MODES},
}

# Imena za klijenta (engleski) — za "Set by this format" i izveštaje.
NAMES = {
    "hook.styles": {"box": "TikTok Box hook", "serif": "Editorial Serif hook", "color": "Color Block hook",
                    "stack": "Stacked hook"},
    "hook.positions": {"below": "hook below the captions", "above": "hook above your head"},
    "captions.styles": {"clean": "Clean captions", "karaoke": "Karaoke captions", "box": "Box Fill captions",
                        "minimal": "Minimal captions"},
    "camera.modes": {"zoom": "zoom on jump cuts", "static": "static camera"},
}


def fmt(id: str, title: str, tagline: str, *, status: str = "soon", from_basic: dict | None = None,
        own: list[str] | None = None, includes: list[str] | None = None) -> dict:
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
                bad = set(v) - set(base[k])
                if bad or not v:
                    raise ValueError(f"{id}: {name}.{k} = {v} — dozvoljeno: {base[k]}")
                v = [x for x in base[k] if x in v]  # redosled kao u Basic-u
            el[k] = v
        elements[name] = el
    return {"id": id, "title": title, "tagline": tagline, "status": status, "elements": elements,
            "own": own or [], "includes": includes or []}


# ------------------------------------------------------------------ registar (redosled = redosled u meniju)
FORMATS: list[dict] = [
    fmt("basic", "Basic Edit",
        "Your talking-head video, edited the CCC way — tight cuts, a scroll-stopping hook, captions and clean audio.",
        status="ready",
        includes=["Tight cuts", "Text hook", "Captions", "Camera zoom", "Clean audio"]),
    # Sledeći formati: dok se grade stoje kao "soon" (kartica Coming soon); kad su gotovi → status="ready".
    fmt("split-screen", "Split Screen",
        "You and what you're talking about, side by side — two views on screen at once."),
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
    for el, key in (("hook", "styles"), ("hook", "positions"), ("captions", "styles"), ("camera", "modes")):
        vals = f["elements"].get(el, {}).get(key)
        if vals and len(vals) == 1:
            out.append(NAMES[f"{el}.{key}"][vals[0]])
    return out


def menu() -> list[dict]:
    return [{k: f[k] for k in ("id", "title", "tagline", "status", "includes")} for f in FORMATS]


def validate(d: dict) -> dict:
    """Izbori sa stranice (ili iz `ccc choices`) → čisti izbori za engine, po pravilima formata.
    ValueError sa porukom za klijenta (engleski)."""
    from .captions import parse_color
    f = get(d.get("format"))
    if f["status"] != "ready":
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

    color = None
    if d.get("color"):
        try:
            color = parse_color(d["color"])
        except ValueError:
            raise ValueError("That color isn't valid — use a hex like #FF5A1F.")
    return {"format": f["id"], "hook_text": text, "hook_style": hook_style, "hook_position": pos or "below",
            "caption_style": cap, "color": color, "camera": camera}
