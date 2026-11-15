"""Ideje za text hook iz klijentovog videa ("Need ideas?" u Style Menu-u, Petar 15.11.).

Ranije su to bili isti primeri za svakog klijenta. Sada: rečenice iz transkripta (project.json → utterances,
bez izbačenih delova) koje najviše liče na hook, skraćene na dužinu koja se čita u prvim sekundama:
  • prva rečenica videa (to je obično izgovoreni hook)
  • brojevi, $, %   • pitanja   • imena (brendovi, ljudi)   • "you/your"   • jake reči (secret, mistake, never…)
Bez CTA rečenica (comment, follow, link in bio), bez nedovršenih, bez poštapalica, bez znaka em dash.
Radi lokalno i odmah (bez modela); dok prepare ne napravi transkript → ready: False (stranica pokazuje primere).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MAX = 55          # meter na stranici: do 45 "Good length", do 70 "A bit long"
MIN_WORDS = 4
LEAD = re.compile(r"^(?:(?:and|so|but|okay|ok|alright|all right|well|now|also|yeah|yes|plus|then|like|look|listen|honestly|basically|actually)\b[,]?\s+)+", re.I)
FILLER = re.compile(r"\b(?:um+|uh+|erm|you know,?|i mean,?|kind of|sort of)\s*", re.I)
CTA = re.compile(r"\b(?:comment|follow|subscribe|link in (?:my )?bio|dm me|if you want (?:access|this|the)|"
                 r"save this|share this|let me know|check out my)\b", re.I)
STRONG = re.compile(r"\b(?:secret|mistake|never|stop|nobody|everyone|why|how|best|worst|craziest|crazy|insane|real|"
                    r"free|only|first|new|just|finally|biggest|fastest|easiest|truth|wrong|actually|without)\b", re.I)
STOP_END = {"a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "at", "for", "with", "your", "my", "is",
            "are", "was", "that", "this", "it", "so", "because", "from", "by", "as", "if", "into", "can", "will",
            "you", "i", "we", "they", "its", "it's", "their", "our", "be", "has", "have", "than", "then", "about"}
SUBORD = re.compile(r"^(?:while|if|when|because|although|though|since|as|after|before|unless|whereas|once)\b", re.I)
# rez na granici reči samo ISPRED ovih reči (deo rečenice ostaje ceo: "...going viral" | "in your niche")
BREAK = {"in", "on", "at", "for", "with", "that", "which", "who", "from", "by", "into", "while", "when", "because",
         "right", "and", "but", "so", "or", "like", "than", "to", "after", "before", "without", "until", "where", "if"}
SPLIT_AT = (", because ", " because ", ", but ", " but ", ", and ", ", so ", ", which ", " which ", "; ", ": ", ", ")


def _sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text.replace("—", ", ").replace("–", ", ")).strip()
    text = re.sub(r"(?<=\d)\.(?=\d)", "\u2024", text)  # privremeno: decimalna tačka
    return [s.strip().replace("\u2024", ".") for s in re.findall(r"[^.?!]+[.?!]*", text) if s.strip()]


def _clean(s: str) -> str:
    s = FILLER.sub("", s)
    s = re.sub(r"\b(\w+)(?:,? \1\b)+", r"\1", s, flags=re.I)        # "I, I, I" → "I"
    s = LEAD.sub("", s).strip(" ,;:-")
    s = re.sub(r"\s+([,?!.])", r"\1", re.sub(r"\s+", " ", s))
    return s[:1].upper() + s[1:] if s else s


def _trim(s: str, mx: int = MAX) -> str | None:
    """Skrati na <= MAX: prvo po delu rečenice (zarez, because…), pa na granici reči. None = ne može lepo."""
    end = "?" if s.endswith("?") else "!" if s.endswith("!") else ""
    body = s.rstrip(".?!").strip()
    if len(body) <= mx:
        return body + end
    if SUBORD.match(body) and ", " in body:  # "While X did 740k, Rare Beauty did 4.2 million" → glavna rečenica
        main = body.split(", ", 1)[1].strip()
        if len(main.split()) >= MIN_WORDS:
            t = _trim(main[:1].upper() + main[1:] + end, mx)
            if t:
                return t
    low = body.lower()
    for sep in SPLIT_AT:
        k = low.find(sep)
        if 0 < k <= mx and len(body[:k].split()) >= MIN_WORDS + 1:
            return body[:k].rstrip(" ,;:")
    words, n = body.split(), 0
    while n < len(words) and len(" ".join(words[:n + 1])) <= mx:
        n += 1
    cut = next((k for k in range(n, MIN_WORDS - 1, -1)
                if k < len(words) and words[k].lower().strip(",") in BREAK and words[k - 1].lower().strip(",") not in STOP_END), 0)
    if not cut:
        return None
    return " ".join(words[:cut]).rstrip(" ,;:")


def _score(s: str, first: bool) -> float:
    sc = 3.0 if first else 0.0
    if re.search(r"\d|\$|%|\b(?:one|two|three|four|five|ten|hundred|thousand|million|billion)\b", s, re.I):
        sc += 2
    if s.endswith("?"):
        sc += 2
    if re.search(r"(?<!^)(?<![.?!] )\b[A-Z][a-zA-Z0-9]+", s[1:]) and not re.fullmatch(r".*\bI\b.*", s[1:]) or \
            len(re.findall(r"\b[A-Z][a-zA-Z0-9]+", s[1:])) >= 2:
        sc += 1
    if re.search(r"\byou(?:r|'re)?\b", s, re.I):
        sc += 1
    sc += min(2, len(STRONG.findall(s)))
    n = len(s)
    sc += 1.5 if 18 <= n <= 45 else 0.5 if n <= MAX else 0
    return sc


def ideas(p: dict, limit: int = 5) -> list[str]:
    """Do `limit` ideja iz transkripta projekta; prva izgovorena rečenica (ako valja) je uvek prva."""
    removed = {w for r in p.get("removed") or [] for w in r.get("words") or []}
    words = {w.get("id"): w for w in p.get("words") or [] if isinstance(w, dict)}
    cands: list[tuple[float, int, str]] = []
    seen: set[str] = set()
    order = 0
    for u in p.get("utterances") or []:
        if removed and u.get("from") in removed and u.get("to") in removed:
            continue  # izbačen deo (loš take, van scenarija)
        text = u.get("text") or ""
        if words and u.get("from") in words and removed:  # samo zadržane reči, kad je tako zapisano
            ids = [k for k in words if k]
            try:
                a, b = ids.index(u["from"]), ids.index(u["to"])
                kept = [words[k].get("text") or words[k].get("word") or "" for k in ids[a:b + 1] if k not in removed]
                if kept and all(kept):
                    text = " ".join(x.strip() for x in kept)
            except (ValueError, KeyError):
                pass
        for raw in _sentences(text):
            if raw.endswith("...") or not re.search(r"[.?!]$", raw) and raw is _sentences(text)[-1] and len(raw.split()) < 6:
                continue  # nedovršeno
            if CTA.search(raw):
                continue
            s = _clean(raw)
            if len(s.split()) < MIN_WORDS or len(s) < 16:
                continue
            if SUBORD.match(s) and ", " not in s:
                continue  # pola rečenice ("While Kylie only did 740k.")
            t = _trim(s, 70 if order == 0 else MAX)  # izgovoreni hook sme do 70 (meter: "a bit long")
            if not t or len(t.split()) < MIN_WORDS:
                continue
            key = re.sub(r"\W+", " ", t.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            cands.append((_score(t, order == 0), order, t))
            order += 1
    if not cands:
        return []
    first = [c for c in cands if c[1] == 0]
    rest = sorted((c for c in cands if c[1] != 0), key=lambda c: (-c[0], c[1]))
    out = (first + rest)[:limit]
    return [c[2].replace("—", ", ") for c in out]


def for_job(job_dir: Path) -> dict:
    """Za stranicu: {"ready": bool, "ideas": [...]} (čita project.json sa diska, jer ga prepare puni u pozadini)."""
    f = Path(job_dir) / "project.json"
    try:
        p = json.loads(f.read_text())
    except (OSError, ValueError):
        return {"ready": False, "ideas": []}
    if not p.get("utterances"):
        return {"ready": False, "ideas": []}
    return {"ready": True, "ideas": ideas(p)}
