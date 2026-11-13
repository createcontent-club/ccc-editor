"""Split Screen — gornja polovina: vremenska linija "momenata" (PLAN.md §11).

Plan pravi Claude (skill) iz transkripta i klijentovih fajlova i upisuje ga sa `ccc visuals <ime> --set plan.json`:

    {"items": [
      {"from": "w9",  "kind": "key",   "data": {"icon": "clock", "line1": "3–4 hours a week", "line2": "on content. Max."}},
      {"from": "w189", "kind": "steps", "data": {"items": ["Top-of-funnel content", "Keyword CTA", "AI comment check"], "active": 1}},
      {"from": "w315", "kind": "image", "data": {"file": "audit.png"}}
    ]}

Svaki moment je vezan za REČ (`from`) — počinje kad krene ta reč, traje do sledećeg momenta (poslednji do kraja).
Zato preživi promenu pacinga i izbacivanje delova. Prvi moment uvek kreće od 0 (gornja polovina nikad prazna).
Stil (dark / light) bira klijent (`top_style`); akcenat = boja brenda, font = izabrani font.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

# Vrste momenata. Delovi unutar momenta mogu imati "at": "<id reči>" — pojavljuju se TAČNO kad se ta reč izgovori
# (engine pretvara u "atT" = sekunde od početka momenta). Bez "at" delovi se ravnomerno pojavljuju.
KINDS = {
    "stat": {"required": ["value"], "optional": ["label", "sub", "at", "ring", "of", "tone", "source"]},
    "week": {"required": ["value"], "optional": ["label", "per", "days", "sub", "at"]},
    "steps": {"required": ["items"], "optional": ["active", "title", "total", "icon"]},  # items: tekst ili {"text","at"}; active -1 = uvod (framework), n = svi otkriveni
    "flow": {"required": ["nodes"], "optional": ["title", "hero", "layout", "loop", "center"]},  # nodes: {"icon"|"file","label","at"}; layout: row|column|quad|hub; loop/center samo uz quad
    "versus": {"required": ["left", "right"], "optional": ["title"]},           # {"label","sub","at"}
    "chart": {"required": ["bars"], "optional": ["label", "value", "at", "y", "x", "note", "tone", "source"]},  # bars: brojevi
    "checklist": {"required": ["items"], "optional": ["title"]},               # items: tekst ili {"text","at"}
    "chat": {"required": ["messages"], "optional": ["title", "platform"]},     # {"from": "them"|"you","text","at"}
    "filter": {"required": ["label"], "optional": ["total", "keep", "at", "sub", "icon"]},
    "headline": {"required": ["words"], "optional": ["accent", "sub", "tone"]},  # words: fraze ili {"text","at"}
    "notify": {"required": ["items"], "optional": []},                         # {"icon","title","body","at"}
    "key": {"required": ["line1"], "optional": ["icon", "line2"]},
    "search": {"required": ["logo"], "optional": ["query", "meter", "placeholder"]},  # logo {"file"}, query {"text","at"}, meter {"value","label","used","at","tone"}
    "resource": {"required": ["title"], "optional": ["sub", "badge", "badgeAt", "icon", "rows", "kicker", "at"]},  # CTA resurs (izveštaj/vodič) kao predmet
    "comment": {"required": ["text"], "optional": ["user", "reply", "at", "platform", "author", "typing"]},  # typing: CTA — ključna reč se kuca u Instagram polje
    "logo": {"required": [], "optional": ["file", "name", "sub", "logos", "title", "at"]},      # pravi logo(i) sa interneta
    "screenshot": {"required": ["file"], "optional": ["focus", "highlight", "device", "zoomAt", "url", "marks"]},  # marks: [{"text","at"}] iz ccc shot --mark
    "news": {"required": ["headline", "outlet"], "optional": ["logo", "image", "date", "highlight", "at"]},
    "photo": {"required": ["file"], "optional": ["name", "sub", "at", "focus"]},   # prava fotografija (osoba/proizvod/mesto)
    "post": {"required": ["platform", "text"], "optional": ["name", "handle", "avatar", "time", "title", "community",
                                                             "headline", "verified", "likes", "comments", "reposts",
                                                             "views", "highlight", "file", "at"]},
    "image": {"required": ["file"], "optional": ["note", "caption"]},   # caption: tekst ili {"text","at"}
    "mediatext": {"required": ["file", "lines"], "optional": ["title", "side", "start", "more"]},
    # Dve strane koje se porede, OBE u kadru od početka (recenzija aazar-trial-1 v1, s01–s03):
    # sides: [{file, name, logo: {file}, values: [{text, at, tone, label}]}] × 2 — vrednosti ulaze na reč i smenjuju se.
    "faceoff": {"required": ["sides"], "optional": []},
    # Stubići sa licem/logom na vrhu svakog (recenzija aazar-trial-1 v3, s02/s27): bars: [{file, name, logo}] × 2–3,
    # sets: [{label, at, values: [n…], display: ["$4.2M"…], tones: [...], note: {text, at, tone}}] — skup se smenjuje na reč.
    "pillars": {"required": ["bars", "sets"], "optional": []},
    # Full-screen custom animacija (principles.md 36): actors [{id, file|icon|text, x, y, size, aspect, at}] + beats [{at, do, target…}].
    "scene": {"required": ["actors"], "optional": ["beats"]},  # slika/snimak + rečenice {"text","at"}; more: [{"file","at"}] — još slika u istom okviru
    "posts": {"required": ["items"], "optional": []},
    "spotlight": {"required": ["file"], "optional": ["title", "logo", "start", "fx"]},  # fx: {"type": "vanish", "at"} — slika zaigra i izbledi (preokret "ne postoji")  # hook: tema velika + naslov + logo na reč   # 2–3 objave jedna preko druge: post podaci ili {"file","at"}
    "video": {"required": ["file"], "optional": ["note", "caption", "start"]},   # start = s u klipu odakle kreće
}
ICONS = ["clock", "calendar", "chart", "trending", "money", "users", "user", "message", "mail", "target", "zap",
         "rocket", "check", "x", "eye", "search", "star", "heart", "bot", "phone", "camera", "video", "lock",
         "gift", "lightbulb", "megaphone", "filter", "link", "sparkles", "trophy", "instagram", "send", "file",
         "bell", "handshake", "inbox", "play", "comment", "crown", "flame", "ban", "hourglass", "shield", "folder", "question"]
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
MIN_LEN, MAX_LEN = 1.2, 4.0   # s — kraći se odbija; duži dobija upozorenje (gledalac mora stalno da dobija nešto novo)
STYLES = ["dark", "light"]


def assets_dir(job) -> Path:
    """Klijentovi fajlovi za gornju polovinu (dashboard drop zona ih kopira ovde)."""
    return job.dir / "assets"


def _out_time(p: dict, t: float) -> float | None:
    """Izvorno vreme → vreme u gotovom videu (None ako je deo izbačen)."""
    acc = 0.0
    for s in p["segments"]:
        if s["srcStart"] - 1e-3 <= t <= s["srcEnd"] + 1e-3:
            return acc + max(0.0, t - s["srcStart"])
        if t < s["srcStart"]:  # reč počinje u rupi pre segmenta (npr. dah ispred) → početak segmenta
            return acc
        acc += s["srcEnd"] - s["srcStart"]
    return None


def total(p: dict) -> float:
    return sum(s["vFrames"] for s in p["segments"]) / p["fps"]


def timeline(p: dict) -> tuple[list[dict], list[str]]:
    """Plan → momenti sa start/end u gotovom videu + lista problema (prazno = sve u redu)."""
    plan = p.get("visuals") or {}
    items, problems = plan.get("items") or [], []
    words = {w["id"]: w for w in p["words"]}
    removed = {w for r in p.get("removed", []) for w in r["words"]}
    end_all = total(p)
    order = [w["id"] for w in p["words"]]

    def next_kept(wid: str) -> str | None:
        """Izbačena reč (npr. klijent posle isporuke traži da se deo iseče) → prva sledeća zadržana."""
        for w in order[order.index(wid):]:
            if w not in removed:
                return w
        return None

    out, notes = [], []
    for i, it in enumerate(items):
        wid = it.get("from")
        if wid not in words:
            problems.append(f"moment {i + 1}: nepoznata reč {wid}")
            continue
        if wid in removed:
            nw = next_kept(wid)
            if nw is None or (i + 1 < len(items) and items[i + 1].get("from") in words
                              and order.index(nw) >= order.index(items[i + 1]["from"])):
                notes.append(f"moment {i + 1} ('{it['kind']}') je ispao — njegov deo je isečen iz videa")
                continue
            notes.append(f"moment {i + 1} ('{it['kind']}'): reč {wid} je isečena → kreće od {nw} '{words[nw]['text']}'")
            wid = nw
        t = _out_time(p, words[wid]["start"])
        if t is None:
            problems.append(f"moment {i + 1}: reč {wid} nije u videu")
            continue
        out.append({**it, "from": wid, "data": json.loads(json.dumps(it.get("data") or {})),
                    "start": 0.0 if not out else round(t, 3)})
    out.sort(key=lambda x: x["start"])
    for i, it in enumerate(out):
        it["end"] = out[i + 1]["start"] if i + 1 < len(out) else round(end_all, 3)
        ln = it["end"] - it["start"]
        if ln < MIN_LEN:
            problems.append(f"moment '{it['kind']}' od {it['start']:.2f}s traje {ln:.2f}s (< {MIN_LEN}s) — spoji ga sa susednim")

        def beats(node, where):  # "at" (reč) → "atT" (s od početka momenta), rekurzivno
            if isinstance(node, dict):
                if "at" in node:
                    w = node["at"]
                    if w in removed and next_kept(w):  # takt na isečenoj reči → sledeća zadržana
                        w = next_kept(w)
                    bt = _out_time(p, words[w]["start"]) if w in words and w not in removed else None
                    if bt is None:
                        problems.append(f"moment '{it['kind']}' od {it['start']:.2f}s: {where}.at = {w} nije zadržana reč")
                    elif not (it["start"] - 0.05 <= bt < it["end"]):
                        problems.append(f"moment '{it['kind']}' od {it['start']:.2f}s: {where}.at = {w} ({bt:.2f}s) je van momenta "
                                        f"({it['start']:.2f}–{it['end']:.2f}s)")
                    else:
                        node["atT"] = round(max(0.0, bt - it["start"]), 3)
                for k, v in node.items():
                    beats(v, f"{where}.{k}")
            elif isinstance(node, list):
                for j, v in enumerate(node):
                    beats(v, f"{where}[{j}]")
        beats(it["data"], "data")
    if out:
        out[0]["notes"] = notes
    if not out and end_all > 0:
        problems.append("gornja polovina nema nijedan moment")
    return out, problems


FILLER = {"the", "a", "an", "your", "my", "our", "so", "and", "but", "or", "to", "of", "in", "on", "it", "this",
          "that", "we", "you", "i", "is", "are", "what's", "what", "how", "why", "who"}


def warnings(items: list[dict]) -> list[str]:
    """Montažna pravila koja engine može da proveri (skill: formats/split-screen.md)."""
    out = list(items[0].get("notes", [])) if items else []
    for it in items:
        dur = it["end"] - it["start"]
        beats = []

        def walk(n, acc_text=None):
            if isinstance(n, dict):
                tx = n.get("text") or n.get("label") or n.get("title")
                if "atT" in n and tx:
                    beats.append((n["atT"], str(tx)))
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)
        walk(it["data"])
        alltimes = []  # svaki takt (i objave/slike bez teksta) je promena na ekranu

        def walk_t(n):
            if isinstance(n, dict):
                if "atT" in n:
                    alltimes.append(n["atT"])
                for v in n.values():
                    walk_t(v)
            elif isinstance(n, list):
                for v in n:
                    walk_t(v)
        walk_t(it["data"])
        last = max(alltimes + [b for b, _ in beats], default=0.0)
        # "Nešto novo na 1.5–3 s": dug moment je u redu samo ako ima taktove — ne sme dugo da stoji bez promene.
        moving = it["kind"] == "video" or (it["kind"] in ("mediatext", "spotlight") and
                                           str(it["data"].get("file", "")).lower().endswith(tuple(VIDEO_EXT)))
        if dur > MAX_LEN and dur - last > 2.5 and not moving:  # snimak se sam kreće
            out.append(f"moment '{it['kind']}' od {it['start']:.2f}s traje {dur:.1f}s, a poslednja promena je posle "
                       f"{last:.1f}s — {dur - last:.1f}s bez ičeg novog; podeli ga ili dodaj takt")
        # Tekst koji gledalac mora da PROČITA (naslov vesti, objava): ~3.5 reči/s + ulaz.
        body = it["data"].get("headline") if it["kind"] == "news" else it["data"].get("text") if it["kind"] == "post" else None
        if isinstance(body, str):
            n = len(body.split())
            # govornik ga čita naglas (read-along isticanje) → gledalac prati, ne mora sam da pročita svaku reč
            need = round(0.6 + n / (5.0 if it["data"].get("highlight") else 3.5), 1)
            if dur < need:
                out.append(f"'{it['kind']}' od {it['start']:.2f}s ima {n} reči, a na ekranu je {dur:.1f}s (treba ~{need}s da se "
                           f"pročita) — produži moment ili skrati tekst na glavni deo (pravi tekst, sa '…')")
        # Screenshot/slika sa isticanjem: ulaz + pokret kamere + MIRNA pauza za čitanje na kraju (TopHalf camTiming).
        if it["kind"] in ("screenshot", "image") and isinstance(it["data"].get("highlight"), dict):
            hl = it["data"]["highlight"].get("atT")
            need_end = 1.2  # posle reči sa isticanjem: isticanje + najmanje 0.9 s mirne scene
            if dur < 1.8:
                out.append(f"screenshot od {it['start']:.2f}s traje {dur:.1f}s — premalo za ulaz, pokret kamere i čitanje "
                           f"(bar 1.8 s): produži moment")
            elif hl is not None and dur - hl < need_end:
                out.append(f"screenshot od {it['start']:.2f}s: isticanje kreće {dur - hl:.1f}s pre kraja — gledalac nema "
                           f"vremena da pročita (bar {need_end:.1f}s): produži moment ili uvedi screenshot ranije")
        # Vreme za procesuiranje: tekst mora ostati dovoljno dugo da se pročita (i da se highlight iscrta).
        acc = str((it["data"].get("accent") or "")).lower()
        marks = {str(h.get("text", "")).lower() for h in (it["data"].get("highlight") or []) if isinstance(h, dict)} \
            if it["kind"] in ("post", "news") else set()
        for bt, tx in beats:
            need = max(0.9, 0.45 + 0.04 * len(tx)) + (0.4 if it["kind"] == "headline" and acc and acc in tx.lower() else 0)
            if tx.lower() in marks:  # isticanje teksta koji je već na ekranu (čita se naglas) — dovoljno da se vidi
                need = 0.7
            seen = dur - bt
            if seen + 0.05 < need:
                out.append(f"'{tx}' (od {it['start'] + bt:.2f}s) je na ekranu {seen:.1f}s, a treba bar {need:.1f}s da se "
                           f"pročita — neka uđe na početku fraze ili produži moment")
    # Nikad prazan kadar (recenzija ai-actor-0 v1, s15): u šablonima čiji se SVI delovi pojavljuju na reč, prvi deo
    # mora doći odmah — inače gornja polovina stoji prazna dok se ne izgovori.
    TIMED = ("flow", "notify", "headline", "comment", "chat")  # filter: natpis i mreža ulaze odmah
    for it in items:
        if it["kind"] not in TIMED and not (it["kind"] == "checklist" and not it["data"].get("title")):
            continue
        ts = []

        def walk_a(n):
            if isinstance(n, dict):
                if "atT" in n:
                    ts.append(n["atT"])
                for v in n.values():
                    walk_a(v)
            elif isinstance(n, list):
                for v in n:
                    walk_a(v)
        walk_a(it["data"])
        if it["kind"] == "comment":
            ts = [0.0]  # komentar se kuca od početka; odgovor na reč
        if ts and min(ts) > 0.7:
            out.append(f"'{it['kind']}' od {it['start']:.2f}s: prvi deo se pojavljuje tek posle {min(ts):.1f}s — gornja polovina je "
                       "prazna; prvi deo na prvu reč momenta ili kreni moment kasnije (nikad prazan kadar)")
    # Duža scena sa jednom slikom (recenzija ai-actor-0 v1, s21): smeni 2–3 slike u istom okviru.
    for it in items:
        d = it["data"]
        if it["kind"] == "mediatext" and not d.get("more") and it["end"] - it["start"] > 5.0 and \
                not str(d.get("file", "")).lower().endswith(tuple(VIDEO_EXT)) and "logo" not in str(d.get("file", "")):
            out.append(f"mediatext od {it['start']:.2f}s traje {it['end'] - it['start']:.1f}s sa jednom slikom — dodaj 1–2 slike "
                       "(more: [{file, at}]) da se smenjuju na reč")
    if items and items[0]["kind"] in ("headline", "key", "stat"):
        out.append(f"prvi moment je '{items[0]['kind']}' — otvaranje (dok traje hook) mora biti hero vizual: "
                   f"flow, versus, chart, filter ili week")
    for it in items:
        if it["kind"] != "headline":
            continue
        ws = it["data"].get("words") or []
        if len(ws) >= 2:
            first = ws[0] if isinstance(ws[0], str) else ws[0].get("text", "")
            nxt = ws[1].get("atT") if isinstance(ws[1], dict) else None
            alone = (nxt or 0) > 0.6
            if alone and (first.lower().strip(".,!?") in FILLER or len(first.split()) == 1 and len(first) <= 4):
                out.append(f"headline od {it['start']:.2f}s: '{first}' stoji sam {nxt:.1f}s — usamljen fragment; "
                           f"spoji ga sa sledećim delom ili kreni moment kasnije")
    return out


def validate_plan(plan: dict, job) -> list[str]:
    """Oblik plana: vrste, obavezna polja, fajlovi postoje i odgovarajućeg su tipa."""
    errs = []
    items = plan.get("items")
    if not isinstance(items, list) or not items:
        return ["plan mora imati listu 'items' sa bar jednim momentom"]
    for i, it in enumerate(items, 1):
        k = it.get("kind")
        if k not in KINDS:
            errs.append(f"moment {i}: nepoznata vrsta '{k}' (postoje: {', '.join(KINDS)})")
            continue
        d = it.get("data") or {}
        for f in KINDS[k]["required"]:
            if not d.get(f):
                errs.append(f"moment {i} ({k}): nedostaje data.{f}")
        unknown = set(d) - set(KINDS[k]["required"]) - set(KINDS[k]["optional"])
        if unknown:
            errs.append(f"moment {i} ({k}): nepoznata polja {sorted(unknown)}")
        if k == "key" and d.get("icon") and d["icon"] not in ICONS:
            errs.append(f"moment {i}: nepoznata ikonica '{d['icon']}' (postoje: {', '.join(ICONS)})")
        if k == "steps" and not (2 <= len(d.get("items") or []) <= 5):
            errs.append(f"moment {i}: steps ima 2–5 stavki")
        if k == "steps" and not (-1 <= int(d.get("active") or 0) <= len(d.get("items") or [])):
            errs.append(f"moment {i}: steps active je -1 (uvod) … {len(d.get('items') or [])} (svi otkriveni)")
        if k == "steps" and d.get("icon") and d["icon"] not in ICONS:
            errs.append(f"moment {i}: nepoznata ikonica '{d['icon']}'")
        if k == "flow" and not (2 <= len(d.get("nodes") or []) <= 4):
            errs.append(f"moment {i}: flow ima 2–4 čvora")
        if k == "flow" and d.get("layout") not in (None, "row", "column", "quad", "hub"):
            errs.append(f"moment {i}: flow layout je row | column | quad | hub")
        if k == "flow" and d.get("layout") == "hub" and len(d.get("nodes") or []) < 3:
            errs.append(f"moment {i}: hub traži 3–4 čvora (prvi gore, ostali ispod)")
        if k == "flow" and (d.get("loop") or d.get("center")) and d.get("layout") != "quad":
            errs.append(f"moment {i}: loop/center postoje samo uz layout quad (petlja kroz 3–4 čvora)")
        if k == "flow" and d.get("layout") == "quad" and len(d.get("nodes") or []) < 3:
            errs.append(f"moment {i}: quad raspored traži 3–4 čvora")
        if not str(it.get("why") or "").strip():
            errs.append(f"moment {i} ({k}): nedostaje \"why\" — jedna rečenica zašto baš taj vizual za tu rečenicu")
        for key in ("nodes", "items"):
            for x in d.get(key) or []:
                if isinstance(x, dict) and x.get("icon") and x["icon"] not in ICONS:
                    errs.append(f"moment {i}: nepoznata ikonica '{x['icon']}'")
        if k == "chart" and not (2 <= len(d.get("bars") or []) <= 7):
            errs.append(f"moment {i}: chart ima 2–7 stubića")
        if k == "pillars":
            bars, sets = d.get("bars") or [], d.get("sets") or []
            if not 2 <= len(bars) <= 3:
                errs.append(f"moment {i}: pillars ima 2–3 stubića (bars)")
            for b in bars:
                if not isinstance(b, dict) or not (b.get("file") or b.get("logo")):
                    errs.append(f"moment {i}: svaki stubić traži file (lice) ili logo — da se zna čiji je")
            for s in sets:
                if len(s.get("values") or []) != len(bars):
                    errs.append(f"moment {i}: pillars skup '{s.get('label', '')}' ima {len(s.get('values') or [])} vrednosti za {len(bars)} stubića")
        if k == "scene":
            ids = [a.get("id") for a in d.get("actors") or [] if isinstance(a, dict)]
            for a in d.get("actors") or []:
                if not isinstance(a, dict) or not a.get("id") or not (a.get("file") or a.get("icon") or a.get("text")):
                    errs.append(f"moment {i}: svaki glumac scene traži id i file | icon | text")
                elif a.get("icon") and a["icon"] not in ICONS:
                    errs.append(f"moment {i}: nepoznata ikonica '{a['icon']}'")
            DOS = ("move", "clone", "cycle", "tag", "stamp", "dim", "focus", "swap", "exit")
            for b in d.get("beats") or []:
                if b.get("do") not in DOS:
                    errs.append(f"moment {i}: scene beat 'do' je {' | '.join(DOS)} (dobijeno {b.get('do')!r})")
                if b.get("target") and b["target"] not in ids:
                    errs.append(f"moment {i}: scene beat cilja nepostojećeg glumca '{b['target']}'")
                if b.get("do") in ("move", "clone", "cycle", "dim", "focus", "swap", "exit") and not b.get("target"):
                    errs.append(f"moment {i}: scene beat '{b.get('do')}' traži target")
                if b.get("do") == "cycle" and not any(x.get("do") == "clone" and x.get("target") == b.get("target") for x in d.get("beats") or []):
                    errs.append(f"moment {i}: 'cycle' vrti kopije — prvo 'clone' istog glumca")
        if k == "faceoff":
            sides = d.get("sides") or []
            if len(sides) != 2:
                errs.append(f"moment {i}: faceoff ima tačno 2 strane (sides) — obe u kadru istovremeno")
            for j, s in enumerate(sides):
                if not isinstance(s, dict) or not s.get("file"):
                    errs.append(f"moment {i}: faceoff strana {j + 1} traži file (prava slika osobe/proizvoda)")
                elif set(s) - {"file", "name", "logo", "values"}:
                    errs.append(f"moment {i}: faceoff strana {j + 1}: nepoznata polja {sorted(set(s) - {'file', 'name', 'logo', 'values'})}")
                for v in (s.get("values") or []) if isinstance(s, dict) else []:
                    if not isinstance(v, dict) or not v.get("text"):
                        errs.append(f"moment {i}: faceoff vrednost traži {{text, at}} (npr. \"$4.2M\" na reč)")
        def files_in(n):
            if isinstance(n, dict):
                if isinstance(n.get("file"), str):
                    yield n["file"]
                for key, v in n.items():
                    if key in ("logo", "image", "avatar") and isinstance(v, str) and k in ("news", "post") and "." in v:
                        yield v
                    yield from files_in(v)
            elif isinstance(n, list):
                for v in n:
                    yield from files_in(v)
        if k == "post" and d.get("platform") not in ("x", "reddit", "linkedin", "threads"):
            errs.append(f"moment {i} (post): platform mora biti x | reddit | linkedin | threads")
        if k in ("logo", "screenshot", "news", "photo", "post", "search"):
            from .assets import nfc, prepare
            man = prepare(job)
            for f in files_in(d):
                m = man.get(nfc(f))
                if m is None:
                    errs.append(f"moment {i}: fajl '{f}' ne postoji u {assets_dir(job)}")
                elif m["kind"] != "image":
                    errs.append(f"moment {i}: '{f}' nije slika ({m.get('error') or m['kind']})")
            if k == "logo" and not d.get("file") and not d.get("logos"):
                errs.append(f"moment {i} (logo): potreban je data.file ili data.logos")
        if k == "screenshot":
            hl = d.get("highlight") if isinstance(d.get("highlight"), dict) else {}
            if any(key in hl for key in ("x", "y", "w", "h")) or d.get("focus"):
                errs.append(f"moment {i} (screenshot): ručne koordinate isticanja/fokusa nisu dozvoljene (seku tekst) — "
                            "uzmi ih iz stranice: ccc shot --find \"<fraza>\" (fokus) i --mark \"<ime/cifra>\" (oznake)")
            if d.get("marks"):
                from .web import sources
                src = sources(job).get(str(d["file"])) or {}
                got = {str(x.get("text", "")).lower(): x for x in src.get("marks") or []}
                main = src.get("rect")
                for mk in d["marks"]:
                    x = got.get(str((mk or {}).get("text", "")).lower())
                    if not x:
                        errs.append(f"moment {i} (screenshot): oznaka \"{(mk or {}).get('text')}\" nije snimljena — "
                                    f"ponovi ccc shot sa --mark \"{(mk or {}).get('text')}\"")
                    elif main and x.get("rect"):
                        r = x["rect"]
                        inside = (r["x"] >= main["x"] - 8 and r["y"] >= main["y"] - 8 and r["x"] + r["w"] <= main["x"] + main["w"] + 8
                                  and r["y"] + r["h"] <= main["y"] + main["h"] + 8)
                        if not inside:
                            errs.append(f"moment {i} (screenshot): oznaka \"{mk.get('text')}\" je van istaknutog dela (mali/zatamnjen "
                                        "element) — označi frazu iz naslova/istaknutog dela ili je izostavi")
        if k == "spotlight":
            from .assets import nfc, prepare
            man = prepare(job)
            m = man.get(nfc(str(d.get("file"))))
            if m is None or m["kind"] not in ("image", "video"):
                errs.append(f"moment {i} (spotlight): '{d.get('file')}' ne postoji ili nije slika/snimak")
            lg = d.get("logo")
            if lg is not None and not (isinstance(lg, dict) and (man.get(nfc(str(lg.get("file")))) or {}).get("kind") == "image"):
                errs.append(f"moment {i} (spotlight): logo je {{\"file\": \"web-logo-….png\", \"at\": \"wID\"}}")
            if len(str(d.get("title") if isinstance(d.get("title"), str) else (d.get("title") or {}).get("text", ""))) > 26:
                errs.append(f"moment {i} (spotlight): naslov ≤ 26 znakova — kratak i upadljiv")
        if k == "mediatext":
            from .assets import nfc, prepare
            m = prepare(job).get(nfc(str(d.get("file"))))
            if m is None:
                errs.append(f"moment {i}: fajl '{d.get('file')}' ne postoji u {assets_dir(job)}")
            elif m["kind"] not in ("image", "video"):
                errs.append(f"moment {i}: '{d.get('file')}' nije slika ni snimak ({m.get('error') or m['kind']})")
            if not (1 <= len(d.get("lines") or []) <= 4):
                errs.append(f"moment {i} (mediatext): 1–4 rečenice u lines")
            if d.get("side") not in (None, "left", "right"):
                errs.append(f"moment {i} (mediatext): side je left | right")
            # Slika se NIKAD ne seče (recenzija ai-actor-0 v1, s16): okvir medija je 430×560 (uspravan). Široka slika bez
            # lica ili sa 2+ lica (kolaž, dva kadra) bi bila presečena → oblik se bira prema slici (pun prikaz, photo, image).
            man = prepare(job)
            for x in [d] + [y for y in (d.get("more") or []) if isinstance(y, dict)]:
                mm = man.get(nfc(str(x.get("file"))))
                if x is not d and mm is None:
                    errs.append(f"moment {i} (mediatext): more → fajl '{x.get('file')}' ne postoji")
                    continue
                if not mm or mm["kind"] != "image" or not mm.get("w") or not mm.get("h") or "logo" in str(x.get("file")):
                    continue
                ar = mm["w"] / mm["h"]
                off = max(ar / (430 / 560), (430 / 560) / ar)
                fc = mm.get("face") or {}
                if off > 1.6 and (not fc or fc.get("n", 1) >= 2):
                    errs.append(f"moment {i} (mediatext): '{x.get('file')}' ({mm['w']}×{mm['h']}) bi bio isečen u uskom okviru"
                                + (" — na slici su 2+ lica (kolaž)" if fc else " — nema lica za centriranje")
                                + "; izaberi oblik prema slici (spotlight/photo/image ceo) ili drugu sliku")
        if k == "posts":
            from .assets import nfc, prepare
            man = prepare(job)
            its = d.get("items") or []
            if not (2 <= len(its) <= 3):
                errs.append(f"moment {i} (posts): 2–3 objave")
            for x in its:
                if not isinstance(x, dict):
                    errs.append(f"moment {i} (posts): svaka objava je objekat"); continue
                if x.get("file"):
                    if (man.get(nfc(x["file"])) or {}).get("kind") != "image":
                        errs.append(f"moment {i} (posts): '{x['file']}' ne postoji ili nije slika")
                elif x.get("platform") not in ("x", "reddit", "linkedin", "threads") or not x.get("text"):
                    errs.append(f"moment {i} (posts): objava treba file, ili platform (x|reddit|linkedin|threads) + text")
        if k in ("image", "video") and d.get("file"):
            from .assets import nfc, prepare
            m = prepare(job).get(nfc(d["file"]))
            if m is None:
                errs.append(f"moment {i}: fajl '{d['file']}' ne postoji u {assets_dir(job)}")
            elif m["kind"] == "error":
                errs.append(f"moment {i}: '{d['file']}' ne može da se koristi ({m['error']}) — reci klijentu")
            elif m["kind"] != k:
                errs.append(f"moment {i}: '{d['file']}' je {m['kind']}, a ne {k} — promeni \"kind\"")
            elif k == "video" and d.get("start") and float(d["start"]) >= m.get("duration", 0):
                errs.append(f"moment {i}: start {d['start']}s je posle kraja klipa ({m.get('duration')}s)")
    return errs


def publish_assets(job, items: list[dict]) -> None:
    """Pripremljene (_ready) verzije fajlova iz plana → remotion/public/jobs/<ime>/assets + putanje za render."""
    from .assets import prepare
    if not any(json.dumps(it.get("data") or {}).count('"file"') or (it.get("data") or {}).get("logo") for it in items):
        return
    man = prepare(job)
    dst = job.public / "assets"
    dst.mkdir(parents=True, exist_ok=True)
    from .assets import nfc

    from .web import sources as web_sources
    srcs = web_sources(job)

    def attach(node: dict, f: str) -> dict | None:
        """Fajl → pripremljena verzija u public/ + putanja i dimenzije na tom čvoru plana."""
        m = man.get(nfc(f))
        ws = srcs.get(nfc(f))
        if ws:  # pravi asset sa interneta: domen za okvir pregledača; nađen deo stranice = podrazumevani fokus
            node.setdefault("url", ws.get("url"))
            if ws.get("crop"):  # isečen element (npr. objava) → lebdeća kartica, ne prozor
                node["cropped"] = True
            f = (m or {}).get("w", 0) / ws["w"] if ws.get("w") and m and m.get("w") else 1.0
            if ws.get("rect") and "focus" not in node and ws.get("kind") == "screenshot":
                # koordinate su u originalnom screenshotu; pripremljena slika može biti smanjena (≤ 2000 px)
                node["focus"] = {k2: round(v * f) for k2, v in ws["rect"].items() if isinstance(v, (int, float))}
            if isinstance(node.get("marks"), list):  # izgovorene fraze → tačni pravougaonici sa stranice
                found = {str(x.get("text", "")).lower(): x for x in ws.get("marks") or [] if x.get("rect")}
                for mk in node["marks"]:
                    x = found.get(str(mk.get("text", "")).lower())
                    if x:
                        mk["rect"] = {k2: round(v * f) for k2, v in x["rect"].items()}
                        mk["lines"] = [{k2: round(v * f) for k2, v in q.items()} for q in x.get("lines") or []] or [mk["rect"]]
        if not m or m["kind"] == "error":
            return None
        for key in ("ready", "last"):
            if m.get(key):
                src, out = assets_dir(job) / "_ready" / m[key], dst / m[key]
                if not out.exists() or out.stat().st_size != src.stat().st_size:
                    shutil.copy2(src, out)
                node["src" if key == "ready" else "last"] = job.public_rel(f"assets/{m[key]}")
        node["clipDur"] = m.get("duration")
        node["mkind"] = m["kind"]  # image | video (medij + tekst bira prikaz)
        node["alpha"] = m["kind"] == "image" and m["ready"].endswith(".png")  # providna slika → bez okvira
        node["w"], node["h"] = m.get("w"), m.get("h")
        for key in ("edge", "edgeUniform", "edgeSides", "dark", "face"):  # način prikaza (pun/stapanje/prozor), tamni logo → beo
            if key in m:
                node[key] = m[key]
        return m

    def walk(n):
        if isinstance(n, dict):
            if isinstance(n.get("file"), str):
                attach(n, n["file"])
            for key in ("logo", "image", "avatar"):  # news/post: "logo"/"image"/"avatar" kao ime fajla
                if isinstance(n.get(key), str) and ("headline" in n or "platform" in n) and n[key].startswith(("web-", "")) \
                        and "." in n[key]:
                    n[key] = {"file": n[key]}
            for v in list(n.values()):
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)

    for it in items:
        walk(it.get("data") or {})
        d = it.get("data") or {}
        if d.get("src"):  # image/video: putanje i na samom momentu (Media)
            it["src"], it["last"] = d["src"], d.get("last")


SWEEP_GAP = 12.0  # s — "light sweep" je naglasak, ne efekat na svakom vizualu: najviše jedan na ~12 s
SWEEP_KINDS = ("stat", "week", "versus", "steps", "chart", "flow", "image", "video")  # "payoff" momenti


def mark_sweeps(items: list[dict]) -> None:
    """Gde ide light sweep: otvaranje + ručno označeni (`"sweep": true` u planu) + po potrebi payoff momenti,
    uvek razmaknuti bar SWEEP_GAP. Ostali momenti ga nemaju."""
    last = -1e9
    for i, it in enumerate(items):
        want = i == 0 or it.get("sweep") is True or (it["kind"] in SWEEP_KINDS and it.get("sweep") is not False)
        if want and it["start"] - last >= SWEEP_GAP and (i == 0 or it.get("sweep") is True or it["end"] - it["start"] >= 1.8):
            it["data"]["sweep"] = True
            last = it["start"]


def render_spec(job, p: dict) -> dict | None:
    """Prop za Remotion (samo Split Screen)."""
    if (p.get("layout") or {}).get("type") != "split":
        return None
    items, _ = timeline(p)
    publish_assets(job, items)
    from .captions import DEFAULT_ACCENT
    accent = (p.get("choices") or {}).get("color") or p.get("caption_accent") or DEFAULT_ACCENT
    style = (p.get("choices") or {}).get("top_style") or "dark"
    if items:
        items[0]["data"]["hero"] = True  # otvaranje: veći, bogatiji vizual (TopHalf.tsx)
    mark_sweeps(items)
    return {"style": style, "accent": accent, "items": items}


def describe(p: dict, job=None) -> str:
    items, problems = timeline(p)
    words = {w["id"]: w["text"] for w in p["words"]}
    lines = []
    for i, it in enumerate(items, 1):
        d = it.get("data") or {}
        def t(x):
            return x if isinstance(x, str) else (x.get("text") or x.get("label") or x.get("title") or "")
        parts = d.get("items") or d.get("nodes") or d.get("words") or d.get("messages") or []
        if d.get("left"):
            parts = [d["left"], d["right"]]
        if d.get("sides"):  # faceoff: "Ime (vrednosti) VS Ime (vrednosti)"
            parts = [{"text": f"{s.get('name', '')} ({' → '.join(v.get('text', '') for v in s.get('values') or [])})"}
                     for s in d["sides"]]
        what = (d.get("file") or d.get("value") or d.get("line1") or d.get("text") or d.get("label") or
                " · ".join(t(x) for x in parts))
        beats = []

        def walk(n):
            if isinstance(n, dict):
                if "atT" in n:
                    beats.append(f"{it['start'] + n['atT']:.1f}")
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for v in n:
                    walk(v)
        walk(d)
        what += f"  [taktovi: {', '.join(beats)}s]" if beats else ""
        lines.append(f"{i:2d}. {it['start']:6.2f}–{it['end']:6.2f}s  {it['kind']:7s} od {it['from']} '{words.get(it['from'], '?')}'  · {what}")
    story = []
    if job is not None:
        from .story import story_warnings
        story = story_warnings(job, p, items)
    return "\n".join(lines + [f"! {x}" for x in problems + warnings(items) + story])


def save_plan(job, p: dict, path: Path) -> None:
    """Proveri oblik plana i sačuvaj ga; vremenske probleme (prekratko, izbačena reč) prikazuje `describe`."""
    try:
        plan = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise SystemExit(f"Plan nije sačuvan: fajl {path} ne postoji")
    except json.JSONDecodeError as err:
        raise SystemExit(f"Plan nije sačuvan: neispravan JSON ({err})")
    errs = validate_plan(plan, job)
    if errs:
        raise SystemExit("Plan nije sačuvan:\n" + "\n".join(f"  ✗ {x}" for x in errs))
    p["visuals"] = {"items": plan["items"]}
