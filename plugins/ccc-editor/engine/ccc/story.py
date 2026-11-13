"""Split Screen — priča pre šablona (PLAN.md §13).

Svaki video se planira iz SVOJE priče: glavna tema, konkretna pominjanja (osoba, firma, događaj) i uloga svakog
dela. Ovaj modul proverava gotov plan i vraća upozorenja ("!" linije koje Claude mora da reši):

  • pominje se nešto konkretno za šta postoji pravi materijal, a gore je šablon (ikonice, naslov…)
  • glavna tema videa (research.json → subject) se pominje, a ne vidi se njen pravi materijal
  • isti šablon se ponavlja (dva zaredom, više od 2 po videu, isti raspored flow-a)
  • scena samo najavljuje tekst koji sledeća scena ponovo prikazuje (spoji ih)
  • struktura liči na neki raniji video na ovom računaru (istorija u <HOME>/history/structures.json —
    služi SAMO da se izbegne ponavljanje, nikad kao šablon)
"""
from __future__ import annotations

import datetime
import difflib
import json
import re
from pathlib import Path

from .project import HOME

# Šabloni (animacije bez pravog materijala). Pravi materijal: image, video, photo, screenshot, logo, news, post.
TEMPLATES = {"stat", "week", "steps", "flow", "versus", "chart", "checklist", "chat", "filter", "headline",
             "notify", "key", "comment"}
REAL = {"image", "video", "photo", "screenshot", "logo", "news", "post", "mediatext", "posts", "spotlight"}
MAX_SAME = 2          # isti šablon najviše 2 puta po videu
SIMILAR = 0.6         # sličnost sa ranijim videom od koje se upozorava
HISTORY = HOME / "history" / "structures.json"


def _files(node) -> set[str]:
    out: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("file", "logo", "image", "avatar") and isinstance(v, str) and "." in v:
                out.add(v)
            out |= _files(v)
    elif isinstance(node, list):
        for v in node:
            out |= _files(v)
    return out


def _texts(node) -> list[str]:
    out: list[str] = []
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k in ("file", "logo", "image", "avatar", "src", "icon", "platform", "tone", "layout"):
                continue
            out += _texts(v)
    elif isinstance(node, list):
        for v in node:
            out += _texts(v)
    return out


def _words(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9$%]+", s.lower()) if len(w) > 2 or w[0].isdigit() or w[0] == "$"]


def _mentions(kept: list[dict], phrases: list[str]) -> set[str]:
    """Sva pominjanja fraza ("glass box", "Kevin") u zadržanom tekstu → id-jevi prve reči svakog pominjanja."""
    norm = [re.sub(r"[^a-z0-9$]+", "", w["text"].lower()) for w in kept]
    out: set[str] = set()
    for ph in phrases:
        toks = [re.sub(r"[^a-z0-9$]+", "", x) for x in str(ph).lower().split()]
        toks = [x for x in toks if x]
        if not toks:
            continue
        for i in range(len(norm) - len(toks) + 1):
            if all(norm[i + j].startswith(toks[j]) if j == len(toks) - 1 else norm[i + j] == toks[j] for j in range(len(toks))):
                out.add(kept[i]["id"])
    return out


def research(job) -> dict:
    f = job.dir / "research.json"
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except json.JSONDecodeError:
        return {}


def signature(items: list[dict]) -> list[str]:
    """Struktura videa: vrste momenata redom (flow sa rasporedom) — za poređenje sa ranijim videima."""
    return [it["kind"] + (f":{(it.get('data') or {}).get('layout') or 'row'}" if it["kind"] == "flow" else "") for it in items]


def story_warnings(job, p: dict, items: list[dict]) -> list[str]:
    from .visuals import _out_time
    out: list[str] = []
    if not items:
        return out
    t_of = {}
    removed = {w for r in p.get("removed", []) for w in r["words"]}  # isečene reči (retake, pauza…) se ne računaju
    for w in p["words"]:
        if w["id"] in removed:
            continue
        t = _out_time(p, w["start"])
        if t is not None:
            t_of[w["id"]] = t
    r = research(job)

    def in_item(wid: str) -> int | None:
        t = t_of.get(wid)
        if t is None:
            return None
        for i, it in enumerate(items):
            if it["start"] - 0.01 <= t < it["end"]:
                return i
        return None

    # 1) konkretna pominjanja → pravi materijal, ne šablon
    subj = r.get("subject") or {}
    ents = list(r.get("entities") or [])
    if subj.get("name"):
        ents = [{**subj, "_subject": True}] + ents
    kept = [w for w in p["words"] if w["id"] in t_of]
    for e in ents:
        assets = {a for a in (e.get("assets") or []) if isinstance(a, str)}
        words = set(e.get("words") or []) | _mentions(kept, e.get("match") or [])
        hit = sorted({i for w in words if (i := in_item(w)) is not None})
        if not assets:
            if hit and e.get("type") in ("person", "event", "product", "character") and \
                    e.get("status") not in ("not found", "asked client", "client file"):
                out.append(f"'{e.get('name')}' ({e.get('type')}) se pominje (moment {hit[0] + 1}), a nema materijala "
                           f"(status: {e.get('status') or '—'}) — osobe, likovi i događaji se uvek traže; "
                           "šablon samo kad stvarno ne postoji (status \"not found\")")
            continue
        for i in hit:
            it = items[i]
            if it["kind"] in TEMPLATES and not (_files(it.get("data")) & assets):
                what = "GLAVNA TEMA videa" if e.get("_subject") else f"'{e.get('name')}'"
                out.append(f"moment {i + 1} ({it['kind']}, {it['start']:.1f}s) pominje {what}, a postoji pravi materijal "
                           f"({', '.join(sorted(assets))}) — pokaži njega umesto šablona")
    if subj.get("name") and not subj.get("assets") and subj.get("status") not in ("asked client", "client file"):
        out.append(f"glavna tema '{subj['name']}' nema pravi materijal — nađi snimak/fotografiju; ako postoji samo na "
                   "Instagramu/TikToku i ne može da se preuzme, zamoli klijenta da ga ubaci (status: \"asked client\")")

    # 2) raznovrsnost unutar videa
    kinds = [it["kind"] for it in items]
    for i in range(1, len(items)):
        if kinds[i] == kinds[i - 1] and kinds[i] in TEMPLATES:
            out.append(f"momenti {i} i {i + 1} su oba '{kinds[i]}' zaredom — drugi oblik za jedan od njih")
    for k in sorted(set(kinds) & TEMPLATES):
        n = kinds.count(k)
        if n > MAX_SAME:
            out.append(f"'{k}' je {n}× u videu (najviše {MAX_SAME}) — video postaje monoton; zameni deo drugim oblikom "
                       f"ili pravim materijalom")
    mt = [i for i, k in enumerate(kinds) if k == "mediatext"]
    if len(mt) > 4:
        out.append(f"'mediatext' je {len(mt)}× u videu (najviše 4) — deo prikaži drugačije (pun snimak/slika, kartica osobe, broj u natpisu)")
    for a_, b_ in zip(mt, mt[1:]):
        if b_ == a_ + 1:
            out.append(f"momenti {a_ + 1} i {b_ + 1} su oba 'mediatext' zaredom — drugi oblik za jedan od njih")
        elif (items[a_].get("data") or {}).get("side", "left") == (items[b_].get("data") or {}).get("side", "left"):
            out.append(f"'mediatext' u momentima {a_ + 1} i {b_ + 1} je na istoj strani — promeni side (left/right) da se ne ponavlja")
    shown: dict[str, list[int]] = {}
    for i, it in enumerate(items):
        for f in _files(it.get("data")):
            if not f.startswith("web-logo") and "logo" not in f:  # logo se sme ponoviti (doslednost brenda)
                shown.setdefault(f, []).append(i + 1)
    for f, where in shown.items():
        if len(where) > 2:
            out.append(f"'{f}' je na ekranu u {len(where)} momenta ({', '.join(map(str, where))}) — najviše 2 (namerni povratak); za ostale nađi drugi materijal")
    lays = [(i, (it.get("data") or {}).get("layout") or "row") for i, it in enumerate(items) if it["kind"] == "flow"]
    for (i, a), (j, b) in zip(lays, lays[1:]):
        if a == b:
            out.append(f"flow u momentima {i + 1} i {j + 1} ima isti raspored '{a}' — promeni layout (row/column/quad)")

    # 3) najava teksta koji sledeća scena opet prikazuje → spoji
    for i in range(len(items) - 1):
        a, b = items[i], items[i + 1]
        if a["kind"] not in ("headline", "key"):
            continue
        wa = set(_words(" ".join(_texts(a.get("data")))))
        wb = set(_words(" ".join(_texts(b.get("data")))))
        if len(wa) >= 2 and len(wa & wb) / len(wa) >= 0.6:
            out.append(f"moment {i + 1} ({a['kind']}) samo najavljuje tekst koji moment {i + 2} ({b['kind']}) opet "
                       "prikazuje — spoji ih (npr. natpis od početka, vrednost na reč)")

    # 4) svaki moment ima razlog
    no_why = [str(i + 1) for i, it in enumerate(items) if not str(it.get("why") or "").strip()]
    if no_why:
        out.append(f"momenti bez \"why\" (zašto baš taj vizual za tu rečenicu): {', '.join(no_why)}")

    # 5) sličnost sa ranijim videima na ovom računaru (samo da se izbegne ponavljanje)
    sig = signature(items)
    for h in _history():
        if h.get("name") == job.name or len(sig) < 6:
            continue
        ratio = difflib.SequenceMatcher(None, sig, h.get("seq") or []).ratio()
        if ratio >= SIMILAR or sig[:4] == (h.get("seq") or [])[:4]:
            out.append(f"struktura liči na raniji video '{h['name']}' ({ratio:.0%} isti redosled vizuala"
                       + (", isti početak" if sig[:4] == (h.get('seq') or [])[:4] else "")
                       + ") — svaki video ima svoju priču: promeni raspored i oblike")
            break
    return out


def _history() -> list[dict]:
    try:
        return json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    except (OSError, json.JSONDecodeError):
        return []


def remember(job, items: list[dict]) -> None:
    """Posle izvoza: zapamti strukturu ovog videa (samo za upozorenje o ponavljanju; najviše 30 videa)."""
    if not items:
        return
    hist = [h for h in _history() if h.get("name") != job.name]
    hist.append({"name": job.name, "date": datetime.date.today().isoformat(), "seq": signature(items)})
    try:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        HISTORY.write_text(json.dumps(hist[-30:], indent=1))
    except OSError:
        pass
