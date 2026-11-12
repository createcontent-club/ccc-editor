"""Putanje i project.json — jedini izvor istine za jedan video."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path

# CODE: gde je kod (razvoj: ovaj folder; kod klijenta: folder plugina — menja se pri svakom ažuriranju).
# HOME: gde su teški i trajni podaci (Python, Node, modeli, fontovi, Remotion, projekti). Kod klijenta je to
# ${CLAUDE_PLUGIN_DATA} (preživljava ažuriranja), koji wrapper `ccc` prosleđuje kao CCC_HOME.
CODE = Path(__file__).resolve().parents[2]
ROOT = CODE  # PYTHONPATH za pod-procese = ROOT / "engine"
HOME = Path(os.environ.get("CCC_HOME") or CODE).expanduser()
WORK = HOME / "work"
REMOTION = HOME / "remotion"
PUBLIC_JOBS = REMOTION / "public" / "jobs"
MODELS = HOME / "tools" / "models"
FONTS = HOME / "tools" / "fonts"


def remotion_cli(*args: str) -> list[str]:
    """Remotion preko Node-a direktno (ne `npm run` — na Windows-u se `npm` ne pokreće isto iz Python-a)."""
    return ["node", str(REMOTION / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"), *args]


def ff_path(p) -> str:
    """Putanja kao argument ffmpeg filtera: kose crte i escape-ovana dvotačka (Windows 'C:')."""
    return str(Path(p)).replace("\\", "/").replace(":", "\\:")

DEFAULT_CUT = {
    "utterance_gap": 0.25,  # tišina koja deli izgovorene delove (za transkripciju i retake-ove)
    "max_gap": 0.04,        # rupa bez glasa duža od ovoga nestaje (uzdah, pauza)…
    "in_word_gap": 0.12,    # …osim unutar jedne reči (zatvaranje suglasnika), do 120 ms
    "pre": 0.05,            # …ostaje 50 ms pre glasa (meki počeci reči: h, f, s — 20 ms je znao da ih iseče)
    "post": 0.07,           # …i 70 ms posle glasa → između rečenica ~0.12 s
    "lead": 0.01,           # video kreće 10 ms pre prvog sloga (provera: glas ≤ 1 frejm od početka)
    "tail": 0.03,           # i završava 30 ms posle poslednjeg (≤ 1 frejm, bez pauze na kraju)
    "fade": 0.005,          # mikro-fade zvuka na svakom rezu (s)
}

SPLIT_LINE = 960  # Split Screen: linija podele (px na 1920) — sadržaj gore, govornik dole

# Pacing (izbor klijenta `pacing`): razlika u odnosu na DEFAULT_CUT (= "fast").
# Oba: bez pauze na početku/kraju, svi loši take-ovi isečeni; chill samo ostavlja malo više vazduha.
PACING = {
    "fast": {},
    "chill": {"max_gap": 0.15,   # kratke pauze u rečenici (≤ 150 ms) ostaju prirodne
              "pre": 0.10, "post": 0.15},  # duže pauze se skraćuju na ~0.25 s
}


class Job:
    def __init__(self, name: str):
        self.name = name
        self.dir = WORK / name
        self.public = PUBLIC_JOBS / name
        self.file = self.dir / "project.json"

    @property
    def exists(self) -> bool:
        return self.file.exists()

    def load(self) -> dict:
        if not self.exists:
            raise SystemExit(f"Nema projekta '{self.name}'. Prvo: ./ccc prepare <video>")
        return json.loads(self.file.read_text())

    def save(self, p: dict) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(p, indent=1, ensure_ascii=False))
        tmp.replace(self.file)

    def public_rel(self, filename: str) -> str:
        """Putanja u odnosu na remotion/public (za staticFile)."""
        return f"jobs/{self.name}/{filename}"


def slug(stem: str) -> str:
    """Ime projekta iz imena fajla: mala slova, cifre i crtice ("My Video (final).MOV" → "my-video-final")."""
    s = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "video"
