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
TEMPLATES = {"stat", "week", "steps", "flow", "versus", "chart", "checklist", "chat", "filter", "headline", "resource",
             "notify", "key", "comment", "search"}
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
    s = re.sub(r"(?<=\d),(?=\d{3})", "", s)  # "$38,000" i "$38000" su ista cifra
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
            # nativni Instagram UI (komentar/DM) ne nosi logo — ključna reč u komentaru je tekst platforme
            if it["kind"] in ("comment", "chat") and (it.get("data") or {}).get("platform") == "instagram":
                continue
            if it["kind"] in TEMPLATES and not (_files(it.get("data")) & assets):
                what = "GLAVNA TEMA videa" if e.get("_subject") else f"'{e.get('name')}'"
                out.append(f"moment {i + 1} ({it['kind']}, {it['start']:.1f}s) pominje {what}, a postoji pravi materijal "
                           f"({', '.join(sorted(assets))}) — pokaži njega umesto šablona")
    if subj.get("name") and not subj.get("assets") and subj.get("status") not in ("asked client", "client file"):
        out.append(f"glavna tema '{subj['name']}' nema pravi materijal — nađi snimak/fotografiju; ako postoji samo na "
                   "Instagramu/TikToku i ne može da se preuzme, zamoli klijenta da ga ubaci (status: \"asked client\")")

    # 2) raznovrsnost unutar videa
    kinds = [it["kind"] for it in items]
    # framework (steps) se namerno vraća za svaki korak — njega vodi provera pokrivenosti (3b c), ne ograničenje ponavljanja
    for i in range(1, len(items)):
        if kinds[i] == kinds[i - 1] and kinds[i] in TEMPLATES and kinds[i] != "steps":
            out.append(f"momenti {i} i {i + 1} su oba '{kinds[i]}' zaredom — drugi oblik za jedan od njih")
    for k in sorted(set(kinds) & TEMPLATES - {"steps"}):
        n = kinds.count(k)
        lays_k = [(it.get("data") or {}).get("layout") or "row" for it in items if it["kind"] == k]
        if k == "flow" and n <= 3 and len(set(lays_k)) == n:  # flow u 3 različita oblika (hub, kolona, petlja) nije monotono
            continue
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

    # 3b) recenzija test-video-3 v1 → pravila za svaki video (skills/ccc-edit/principles.md)
    said_in = []  # izgovorene reči po momentu
    for it in items:
        said_in.append([w for w in kept if it["start"] - 0.01 <= t_of[w["id"]] < it["end"]])
    # (a) alat/platforma/brend pomenut u hooku → njegov logo jasno vidljiv u hook animaciji
    brandish = ("brand", "product", "tool", "app", "platform", "company", "website")
    told: set[frozenset] = set()
    for e in ents:
        logos = {a for a in (e.get("assets") or []) if isinstance(a, str) and "logo" in a}
        if not logos or (e.get("type") not in brandish and not e.get("_subject")) or frozenset(logos) in told:
            continue
        told.add(frozenset(logos))
        hook_hit = [w for w in _mentions(kept, e.get("match") or []) if in_item(w) == 0]
        if hook_hit and not (_files(items[0].get("data")) & logos):
            out.append(f"hook (moment 1) pominje '{e.get('name')}', a njegov logo nije u hook animaciji — alat/platforma "
                       f"iz hooka mora biti jasno vidljiv ceo ({', '.join(sorted(logos))})")
    # (b) screenshot samo kad je stranica TO o čemu se govori — ne kao ukras ni "dokaz da postoji"
    try:
        from .web import sources
        shots = {n for n, s in sources(job).items() if s.get("kind") == "screenshot"}
    except Exception:  # noqa: BLE001 — bez zapisa porekla nema ni screenshot-ova
        shots = set()
    # hook se nikad ne gradi na screenshot-u (previše statičan, recenzija v2 s01) — pokret: pravi snimak ili custom animacija
    if items and (items[0]["kind"] in ("screenshot", "news") or (_files(items[0].get("data")) & shots)
                  or (items[0]["kind"] == "post" and (items[0].get("data") or {}).get("file"))):
        out.append(f"hook (moment 1, {items[0]['kind']}) je screenshot/statična stranica — hook mora imati pokret: pravi "
                   "snimak teme ili custom animacija koja dramatizuje rečenicu (logo alata unutra)")
    for i, it in enumerate(items):
        d = it.get("data") or {}
        used = _files(d) & shots
        if not used:
            continue
        if it["kind"] != "screenshot":
            out.append(f"moment {i + 1} ({it['kind']}) koristi screenshot stranice ({', '.join(sorted(used))}) kao sliku uz tekst — "
                       "screenshot ne daje kontekst kad nije TO o čemu se govori; prikaži ideju (logo + animacija)")
            continue
        page = set(_words(" ".join(str(m.get("text", "")) for m in d.get("marks") or [])))
        said = set(_words(" ".join(w["text"] for w in said_in[i])))
        if page and len(page & said) / len(page) < 0.34:
            out.append(f"moment {i + 1} (screenshot): istaknut tekst na stranici ('{' / '.join(m.get('text', '') for m in d.get('marks') or [])}') "
                       "nije ono što se govori — screenshot samo kad govornik priča o toj stranici/vesti/objavi; "
                       "inače rekreiraj ono što kaže (custom animacija)")
    # (c) framework: ako video ima korake (steps), isti okvir pokriva SVAKI korak (i uvod/kraj ako postoje)
    groups: dict[tuple, list[int]] = {}
    for i, it in enumerate(items):
        if it["kind"] == "steps":
            d = it.get("data") or {}
            key = tuple(_texts(d.get("items")))
            groups.setdefault(key, []).append(int(d.get("active") or 0))
    for key, acts in groups.items():
        n = len(key)
        miss = [str(a + 1) for a in range(n) if a not in acts]
        if miss and len(acts) >= 1:
            out.append(f"framework '{' / '.join(key)}' pokriva {n - len(miss)} od {n} koraka — isti okvir se koristi za "
                       f"SVAKI korak kroz ceo video (nedostaju koraci {', '.join(miss)})")
    # (d) CTA "comment <reč>" → nativni Instagram komentar sa ključnom reči, krupno (comment + typing)
    for w in kept:
        if re.sub(r"[^a-z]", "", w["text"].lower()) == "comment":
            i = in_item(w["id"])
            if i is not None and items[i]["kind"] != "comment":
                out.append(f"moment {i + 1} ({items[i]['kind']}): CTA 'comment …' na {t_of[w['id']]:.1f}s — prikaži nativni "
                           "Instagram komentar sa ključnom reči (kind comment, platform instagram, typing: true)")
            break

    # 3c) recenzija ai-actor-0 v1 → pravila za svaki video (skills/ccc-edit/principles.md 15–21)
    # (e) video o konkretnoj osobi/proizvodu/događaju: gornja polovina je PRVENSTVENO pravi materijal
    concrete = bool(subj.get("name")) or any(e.get("type") in ("person", "character", "product", "event") for e in ents)
    if concrete and len(items) >= 6:
        real = [i for i, it in enumerate(items) if it["kind"] in REAL and _files(it.get("data"))]
        share = len(real) / len(items)
        if share < 0.5:
            out.append(f"video je o nečem konkretnom ('{subj.get('name') or ents[0].get('name')}'), a pravi materijal je u samo "
                       f"{len(real)}/{len(items)} momenata ({share:.0%}) — cilj je bar polovina: nađi još fotografija/snimaka "
                       "za trenutke koji se opisuju (šablon samo za apstraktno)")
        if subj.get("type") in ("person", "character"):
            subj_files = {a for a in (subj.get("assets") or []) if isinstance(a, str)}
            seen = [i + 1 for i, it in enumerate(items) if _files(it.get("data")) & subj_files]
            distinct = {f for it in items for f in _files(it.get("data")) & subj_files}
            if len(distinct) < 4:
                out.append(f"glavna tema je osoba/lik '{subj['name']}', a vidi se samo {len(distinct)} različitih slika "
                           f"(momenti {', '.join(map(str, seen)) or '—'}) — nađi bar 4 različite slike/snimka koja odgovaraju "
                           "onome što se tada opisuje (svakodnevica, uloga, reklama…)")
    # (f) konkretna brojka/tvrdnja o temi → DOKAZ (izvor sa markerom na toj cifri), nikad custom grafika
    if concrete:
        for i, it in enumerate(items):
            if it["kind"] not in ("stat", "notify", "chart", "week", "checklist", "versus", "headline"):
                continue
            nums = [t for t in _texts(it.get("data")) if re.search(r"\d", t)]
            said_nums = [w["text"] for w in said_in[i] if re.search(r"\d", w["text"])]
            if nums and said_nums:
                out.append(f"moment {i + 1} ({it['kind']}): konkretna brojka ('{nums[0]}') o temi videa kao custom grafika — "
                           "tvrdnje i brojke se dokazuju: screenshot izvora sa markerom (--mark) na toj cifri, ili prava objava/profil")
    # (g) screenshot sa širokim/dugim istaknutim delom → izgovorena cifra/fraza mora imati marker u boji brenda
    try:
        from .web import sources as _src
        wsrc = _src(job)
    except Exception:  # noqa: BLE001
        wsrc = {}
    for i, it in enumerate(items):
        if it["kind"] != "screenshot":
            continue
        d = it.get("data") or {}
        s_ = wsrc.get(str(d.get("file"))) or {}
        rect, W_ = s_.get("rect") or {}, s_.get("w") or 0
        long_part = rect and W_ and (rect.get("w", 0) / W_ > 0.4 or rect.get("h", 0) > 110)
        if long_part and not [m for m in d.get("marks") or [] if not m.get("blur")]:
            out.append(f"moment {i + 1} (screenshot): istaknut je veći deo teksta bez markera — označi tačno ono što se tada "
                       "izgovara (cifra, ime) markerom u boji brenda: ccc shot … --mark \"<tekst>\" + marks u planu")
    # (h) CTA: vizual komentara ulazi kad se izgovori "comment", ne ranije (prethodna scena nosi ponudu)
    for w in kept:
        if re.sub(r"[^a-z]", "", w["text"].lower()) == "comment":
            i = in_item(w["id"])
            if i is not None and items[i]["kind"] == "comment" and t_of[w["id"]] - items[i]["start"] > 0.6:
                out.append(f"moment {i + 1} (comment) počinje {t_of[w['id']] - items[i]['start']:.1f}s pre reči 'comment' — "
                           "CTA ulazi tačno na reč; ponuda pre nje dobija svoj dinamičan vizual")
            break

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
