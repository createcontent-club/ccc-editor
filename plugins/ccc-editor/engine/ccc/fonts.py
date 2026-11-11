"""Fontovi za titlove i text hook — klijent bira jedan set u Style Menu-ju (izbor `font`).

Jedan izvor istine: engine odavde meri tekst (prelom hooka, širina), a render dobija `spec()` kao prop,
pa Remotion učitava iste fajlove pod istim imenima porodica (vidi remotion/src/style.ts).

  ccc       — CCC podrazumevani (odobren izgled): Inter titlovi, TikTok Sans hook (TikTok Box / Color Block),
              Inter Bold za Stacked.
  ostali    — jedan font za titlove i hook (TikTok Box / Color Block / Stacked).
Editorial Serif hook uvek ostaje Instrument Serif (to je suština tog stila).
Samo javni fontovi (OFL, Google Fonts) — fajlove skida setup/install.py.

Novi font: dodaj unos ovde + fajlove u setup/install.py (FONTS) i tools/doctor.py.
"""
from __future__ import annotations

from functools import lru_cache

from PIL import ImageFont

from .project import FONTS as FONT_DIR

CAPTION_FAMILY = "CCC Inter"   # imena porodica u Remotion-u (ostaju ista, menjaju se fajlovi)
HOOK_FAMILY = "CCC Hook"

# weights: težina → fajl (statični fontovi) ili None za varijabilni fajl `variable`.
# tracking (em): titl / hook boks / Stacked.  hook_axes: TikTok Sans (opsz, wdth) — samo CCC set.
SETS: dict[str, dict] = {
    "ccc": {
        "name": "CCC Signature", "desc": "Our signature look",
        "caption": {"files": {300: "Inter-Light.ttf", 600: "Inter-SemiBold.ttf", 700: "Inter-Bold.ttf"}},
        "hook": {"variable": "TikTokSans-Variable.ttf", "range": "300 900", "stretch": "75% 150%"},
        "tracking": {"caption": -0.045, "hook": 0.0, "stack": -0.03},
        "hook_axes": {"opsz": 36, "wdth": 95},
    },
    "poppins": {
        "name": "Poppins", "desc": "Round & friendly",
        "caption": {"files": {300: "Poppins-Light.ttf", 600: "Poppins-SemiBold.ttf", 700: "Poppins-Bold.ttf",
                              800: "Poppins-ExtraBold.ttf"}},
        "hook": None,  # isti fajlovi kao titl
        "tracking": {"caption": -0.025, "hook": -0.01, "stack": -0.025},
    },
    "jakarta": {
        "name": "Plus Jakarta Sans", "desc": "Modern & premium",
        "caption": {"variable": "PlusJakartaSans-Variable.ttf", "range": "200 800"},
        "hook": None,
        "tracking": {"caption": -0.03, "hook": -0.015, "stack": -0.03},
    },
    "bricolage": {
        "name": "Bricolage Grotesque", "desc": "Bold & characterful",
        "caption": {"variable": "BricolageGrotesque-Variable.ttf", "range": "200 800"},
        "hook": None,
        "tracking": {"caption": -0.03, "hook": -0.015, "stack": -0.03},
    },
}
IDS = list(SETS)
DEFAULT = "ccc"


def get(font_id: str | None) -> dict:
    return SETS.get(font_id or DEFAULT) or SETS[DEFAULT]


def _file_for(src: dict, weight: int) -> str:
    if "variable" in src:
        return src["variable"]
    files = src["files"]
    return files[min(files, key=lambda w: abs(w - weight))]


@lru_cache(maxsize=256)
def load(font_id: str, role: str, weight: int, px: int) -> ImageFont.FreeTypeFont:
    """PIL font za merenje: role 'caption' (titl i Stacked) ili 'hook' (TikTok Box / Color Block)."""
    s = get(font_id)
    src = (s["hook"] or s["caption"]) if role == "hook" else s["caption"]
    f = ImageFont.truetype(str(FONT_DIR / _file_for(src, weight)), px)
    if "variable" in src:
        # Iste ose kao u Chrome-u: wght = font-weight, opsz = veličina u px (font-optical-sizing: auto),
        # ostale na podrazumevanim; CCC hook ima svoje (TikTok Sans wdth 95, opsz 36).
        fixed = s.get("hook_axes", {}) if role == "hook" else {}
        vals = []
        for ax in f.get_variation_axes():
            name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
            lo, hi = ax["minimum"], ax["maximum"]
            if name == "Weight":
                v = weight
            elif name == "Optical size":
                v = fixed.get("opsz", px)
            elif name == "Width":
                v = fixed.get("wdth", ax["default"])
            else:
                v = ax["default"]
            vals.append(max(lo, min(hi, v)))
        f.set_variation_by_axes(vals)
    return f


def tracking(font_id: str | None, role: str) -> float:
    return get(font_id)["tracking"][role]


def spec(font_id: str | None) -> dict:
    """Prop za Remotion: koje fajlove učitati pod kojim imenom porodice + tracking po ulozi."""
    fid = font_id if font_id in SETS else DEFAULT
    s = SETS[fid]

    def faces(family: str, src: dict) -> list[dict]:
        if "variable" in src:
            f = {"family": family, "file": src["variable"], "weight": src["range"]}
            if src.get("stretch"):
                f["stretch"] = src["stretch"]
            return [f]
        return [{"family": family, "file": file, "weight": str(w)} for w, file in src["files"].items()]

    return {
        "id": fid,
        "faces": faces(CAPTION_FAMILY, s["caption"]) + faces(HOOK_FAMILY, s["hook"] or s["caption"]),
        "tracking": s["tracking"],
        "hookAxes": s.get("hook_axes"),
    }


def files() -> list[str]:
    """Svi fajlovi svih setova (za proveru instalacije)."""
    out = []
    for s in SETS.values():
        for src in (s["caption"], s["hook"]):
            if src:
                out += [src["variable"]] if "variable" in src else list(src["files"].values())
    return sorted(set(out))
