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
import re
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
    # PRIČA I LJUDI faza 1 (14. nov 2026): sve činjenice iz izvora; slike lica centrirane automatski
    "timeline": {"required": ["events"], "optional": ["title"]},  # events [{year|date, label, file, at, tone}] 2–5
    "quote": {"required": ["text"], "optional": ["file", "name", "sub", "highlight", "source", "at"]},  # tačan citat, highlight [{text, at}]
    "network": {"required": ["people"], "optional": ["links", "title"]},  # people [{file, name, role, at, tone}] 2–4; links [{between: [0, 1], label, at, tone}]
    "dossier": {"required": ["name"], "optional": ["file", "facts", "kicker", "start"]},  # facts [{label, value, at, tone}] ≤ 4
    "lowerthird": {"required": ["file", "name"], "optional": ["sub", "place", "tag", "at", "start"]},  # snimak/foto + TV natpis
    "compare": {"required": ["before", "after"], "optional": ["title"]},  # before/after {file, label, at}: brisanje na after.at
    # PRIČA I LJUDI faza 2: mapa, breaking news, grafik sa događajima, rang lista sa licima
    "map": {"required": ["pins"], "optional": ["lines", "focus", "zoom", "title"]},  # pins [{lat, lon, label, sub, file, at, tone}] ≤ 8; lines [{between, at, tone}]
    "breaking": {"required": ["headline"], "optional": ["file", "label", "ticker", "channel", "live", "at", "start"]},  # tačan naslov vesti preko snimka
    "trend": {"required": ["points"], "optional": ["events", "label", "x", "tone", "source"]},  # points [{value, label}] iz izvora; events [{index, label, at, tone}] ≤ 3
    "ranking": {"required": ["items"], "optional": ["title", "countdown", "source"]},  # items [{file, name, value, at, tone}] 3–5
    # Stubići sa licem/logom na vrhu svakog (recenzija aazar-trial-1 v3, s02/s27): bars: [{file, name, logo}] × 2–3,
    # sets: [{label, at, values: [n…], display: ["$4.2M"…], tones: [...], note: {text, at, tone}}] — skup se smenjuje na reč.
    "pillars": {"required": ["bars", "sets"], "optional": []},
    # Full-screen custom animacija (principles.md 36): actors [{id, file|icon|text, x, y, size, aspect, at}] + beats [{at, do, target…}].
    "scene": {"required": ["actors"], "optional": ["beats"]},  # slika/snimak + rečenice {"text","at"}; more: [{"file","at"}] — još slika u istom okviru
    # Verna rekreacija alata (principles.md 45–47): app claude|chatgpt|notion|sheets + događaji na reč — menu {items,
    # highlight {text, at}, badge, at, close}, input {text, at}, send {at}, reply, rec {at}, voice {at, label}, notes [{text, at}],
    # card {title, at, steps [{text, at, tone}], run {at}, center, cont, status}, tabs [{label, at, tone, page, active}],
    # cursor [{to, at, click}], zoom [{to, at, scale}], cont (nastavak prethodnog app momenta, bez ulaza).
    "app": {"required": ["app"], "optional": ["theme", "title", "greeting", "placeholder", "model", "user", "workspace", "pages",
                                               "icon", "blocks", "cells", "input", "send", "reply", "menu", "cursor", "rec", "voice",
                                               "notes", "card", "tabs", "zoom", "cont", "dim",
                                               # faza 1 UI kita (14. nov 2026): instagram / iphone / gmail / n8n·zapier·make / web
                                               "screen", "handle", "name", "bio", "avatar", "verified", "posts", "followers",
                                               "following", "grid", "follow", "button", "own", "story", "category", "link",
                                               "metric", "chart", "rows", "period", "dates", "threads", "requests",
                                               "notifications", "date", "time", "wallpaper", "emails", "count", "compose",
                                               "nodes", "run", "file", "url", "marks", "scroll",
                                               # faza 2: gemini / perplexity / midjourney / slack / calendar / stripe·shopify / google
                                               "sources", "images", "generate", "upscale", "channel", "channels", "messages",
                                               "events", "month", "label", "counter", "payments", "overview", "results", "query",
                                               # faza 3: terminal / cursor·vscode / canva / capcut / ads / ytstudio / tiktok
                                               "lines", "code", "add", "files", "project", "elements", "background", "variants",
                                               "cuts", "captions", "caption", "media", "length", "campaigns", "metrics", "videos",
                                               "likes", "like", "commentCount", "comments", "saves", "shares", "sound",
                                               # faza B: custom (bilo koji alat)
                                               "brand", "type", "columns"]},
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
        out.append(f"prvi moment je '{items[0]['kind']}' — otvaranje mora pokazati pravu temu videa "
                   f"(video, spotlight, faceoff, photo ili scene — principles.md 30–34), ne naslov/broj")
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
        if "—" in json.dumps(d, ensure_ascii=False):  # pravilo vlasnika: "—" nikad u tekstu na ekranu
            errs.append(f"moment {i} ({k}): tekst na ekranu sadrži '—' — zameni tačkom, zarezom ili dvotačkom")
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
        if k == "app":
            errs += _app_errors(i, d, job)
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
        if k in ("timeline", "quote", "network", "dossier", "lowerthird", "compare", "map", "breaking", "trend", "ranking"):
            errs += _story_errors(i, k, d, job)
        if k in ("logo", "screenshot", "news", "photo", "post", "search", "faceoff", "pillars", "scene", "flow",
                 "timeline", "quote", "network", "dossier", "compare", "map", "ranking"):
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
    return "\n".join(lines + [f"! [must] {x}" for x in problems]
                     + [f"! [{severity(x)}] {x}" for x in warnings(items)] + [f"! [{story_severity(x)}] {x}" for x in story])


# [must] = mora da se popravi pre build-a (čitljivost, tajming, prazan kadar); [aim] = cilj koji zavisi od materijala
# (pravi materijal %, raznovrsnost, portreti…) — najviše 2 kruga ispravki, pa objasniti u rezimeu (QA 0.8.0, P0:
# "popravi svaki !" je vodilo u beskonačne ispravke ili u ignorisanje svega).
MUST_MARKERS = ("je na ekranu", "pre kraja", "prvi deo se pojavljuje", "izbačen", "van momenta", "ne postoji",
                "nema reči", "prazn", "fokus screenshot-a")


APPS = ("claude", "chatgpt", "notion", "sheets", "instagram", "iphone", "gmail", "n8n", "zapier", "make", "web",
        "gemini", "perplexity", "midjourney", "slack", "calendar", "stripe", "shopify", "google",
        "terminal", "cursor", "vscode", "canva", "capcut", "ads", "ytstudio", "tiktok",
        # faza B: aplikacije kao podaci (remotion/src/components/AppSpec.tsx) + custom = bilo koji alat
        "copilot", "grok", "deepseek", "metaai", "lechat", "outlook", "hubspot", "linear",
        "gumroad", "kajabi", "paypal", "analytics", "beehiiv", "custom")
SPEC_CHAT = ("copilot", "grok", "deepseek", "metaai", "lechat")
SPEC_LIST = ("outlook", "hubspot", "linear")
SPEC_DASH = ("gumroad", "kajabi", "paypal", "analytics", "beehiiv")
SPEC_COLS = {"outlook": ("from", "subject", "time"), "hubspot": ("name", "stage", "amount"), "linear": ("id", "title", "status")}
APP_MENU = {  # isto kao MENU_DEFAULT u remotion/src/components/AppUI.tsx (ostale aplikacije: meni samo sa svojim items)
    "claude": ["Add files or photos", "Take a screenshot", "Add to project", "Use a skill"],
    "chatgpt": ["Add photos & files", "Create image", "Deep research", "Agent mode"],
    "notion": ["Text", "Heading 1", "To-do list", "Table", "Ask AI"],
    "sheets": ["Add-ons", "Macros", "Apps Script"],
}
IG_SCREENS = ("profile", "insights", "inbox")
APP_ICONS = {"instagram", "gmail", "stripe", "shopify", "calendar", "messages", "whatsapp", "slack", "paypal", "sheets",
             "notion", "openai", "chatgpt", "claude", "webhook", "typeform", "calendly", "hubspot", "zoom", "tiktok", "youtube",
             "linkedin", "x", "discord", "airtable", "schedule", "cron", "code", "filter", "if", "ai", "agent", "email", "mail",
             "database", "crm"}  # isto kao APP_ICON_NAMES u remotion/src/components/appIcons.tsx


def _app_anchor_names(app: str, d: dict) -> set[str]:
    """Imenovani delovi aplikacije na koje ciljaju kamera (zoom.to) i kursor/dodir (cursor.to) — isto kao anchors() u skinu."""
    if app == "claude":
        return {"window", "rail", "main", "greeting", "input", "plus", "toggle", "model", "mic", "send", "chat"}
    if app == "chatgpt":
        return {"window", "rail", "main", "greeting", "input", "plus", "mic", "send", "model", "chat"}
    if app == "notion":
        return {"window", "sidebar", "page", "title", "blocks", "input"}
    if app == "sheets":
        return {"window", "title", "menubar", "toolbar", "formula", "grid", "input"} | {f"{c}{r}" for c in "ABCDE" for r in range(1, 9)}
    if app == "instagram":
        sc = d.get("screen") or "profile"
        if sc == "insights":
            return {"header", "period", "metric", "value", "chart", "rows"} | {f"row{j}" for j in range(len(d.get("rows") or []))}
        if sc == "inbox":
            return {"header", "search", "requests", "list", "input"} | {f"row{j}" for j in range(8)}
        return {"header", "avatar", "stats", "posts", "followers", "following", "bio", "button", "grid", "profile"} | {f"tile{j}" for j in range(9)}
    if app == "iphone":
        return {"clock", "list"} | {f"n{j}" for j in range(5)}
    if app == "gmail":
        return {"compose", "inbox", "search", "list", "sidebar", "draft", "input", "send", "toast", "main"} | {f"row{j}" for j in range(8)}
    if app in ("n8n", "zapier", "make"):
        return {"canvas", "title", "flow"} | {f"node{j}" for j in range(len(d.get("nodes") or []))}
    if app == "gemini":
        return {"window", "rail", "main", "greeting", "input", "plus", "mic", "send", "model", "chat"}
    if app == "perplexity":
        return {"window", "rail", "logo", "input", "send", "question", "sources", "answer"} | {f"src{j}" for j in range(min(4, len(d.get("sources") or [])))}
    if app == "midjourney":
        return {"window", "input", "send", "grid"} | {f"tile{j}" for j in range(4)}
    if app == "slack":
        return {"window", "sidebar", "channel", "list", "input", "send"} | {f"msg{j}" for j in range(len(d.get("messages") or []))}
    if app == "calendar":
        return {"window", "header", "week"} | {f"day{j}" for j in range(5)} | {f"ev{j}" for j in range(len(d.get("events") or []))}
    if app in ("stripe", "shopify"):
        return {"window", "sidebar", "metric", "value", "chart", "list"} | {f"row{j}" for j in range(5)}
    if app == "google":
        return {"window", "search", "input", "overview", "results"} | {f"res{j}" for j in range(len(d.get("results") or []))}
    if app == "terminal":
        return {"window", "lines", "input", "send", "header"} | {f"line{j}" for j in range(len(d.get("lines") or []))}
    if app in ("cursor", "vscode"):
        n = len(d.get("code") or []) + len(d.get("add") or [])
        return {"window", "tree", "editor", "chat", "input", "send"} | ({"diff"} if d.get("add") else set()) | {f"line{j}" for j in range(n)}
    if app == "canva":
        return {"window", "toolbar", "canvas", "share", "magic", "variants"}
    if app == "capcut":
        return {"window", "preview", "timeline", "captions", "track0", "track1", "track2"}
    if app == "ads":
        return {"window", "metrics", "table", "spent", "results", "roas"} | {f"row{j}" for j in range(len(d.get("campaigns") or []))}
    if app == "ytstudio":
        return {"window", "metrics", "chart", "list", "m0", "m1", "m2", "row0", "row1", "row2"}
    if app == "tiktok":
        return {"video", "likes", "comments", "share", "caption", "drawer", "rail"}
    kind = d.get("type") if app == "custom" else ("chat" if app in SPEC_CHAT else "list" if app in SPEC_LIST else "dashboard" if app in SPEC_DASH else None)
    if kind == "chat":
        return {"window", "rail", "main", "greeting", "input", "plus", "mic", "send", "model", "chat"}
    if kind == "list":
        return {"window", "sidebar", "header", "button", "list"} | {f"row{j}" for j in range(8)}
    if kind == "dashboard":
        return {"window", "sidebar", "metric", "value", "chart", "list"} | {f"row{j}" for j in range(5)}
    if app == "web":
        return {"page", "bar", "focus"} | {f"mark{j}" for j in range(len(d.get("marks") or []))} \
            | {_t(m).lower() for m in d.get("marks") or []}
    return set()


def _app_errors(i: int, d: dict, job=None) -> list[str]:
    """Oblik `app` momenta: poznata aplikacija, stavka menija postoji, kamera/kursor ciljaju postojeće delove,
    podaci svake aplikacije potpuni (faza 1: instagram / iphone / gmail / n8n·zapier·make / web)."""
    errs = []
    app = d.get("app")
    if app not in APPS:
        return [f"moment {i} (app): app mora biti {' | '.join(APPS)} (dobijeno {app!r})"]
    menu = d.get("menu") if isinstance(d.get("menu"), dict) else None
    if menu and app not in APP_MENU and not menu.get("items"):
        errs.append(f"moment {i} (app): {app} nema podrazumevani meni — daj menu.items")
    items = [_t(x) for x in (menu.get("items") or APP_MENU.get(app, []))] if menu else []
    names = _app_anchor_names(app, d) | {"menu", "top", "window"}
    if menu and menu.get("highlight"):
        h = _t(menu["highlight"]).lower()
        if h not in [x.lower() for x in items]:
            errs.append(f"moment {i} (app): menu.highlight \"{_t(menu['highlight'])}\" nije među stavkama menija {items} — "
                        "dodaj ga u menu.items (tačan tekst kao u aplikaciji)")
        names.add("item")
    if menu and len(items) > 6:
        errs.append(f"moment {i} (app): meni ima {len(items)} stavki (najviše 6 staje i čita se)")
    card = d.get("card") if isinstance(d.get("card"), dict) else None
    if card:
        names.add("card")
        if not _t(card.get("title")):
            errs.append(f"moment {i} (app): card traži title (ime skill-a / dokumenta)")
        if len(card.get("steps") or []) > 6:
            errs.append(f"moment {i} (app): kartica ima najviše 6 koraka")
    tabs = d.get("tabs") or []
    if len(tabs) > 4:
        errs.append(f"moment {i} (app): najviše 4 taba")
    if tabs and app in ("instagram", "iphone"):
        errs.append(f"moment {i} (app): {app} je telefon — tabovi pregledača ne postoje")
    names |= {f"tab{j}" for j in range(len(tabs))}
    for z in d.get("zoom") or []:
        if isinstance(z, dict) and str(z.get("to")) not in names:
            errs.append(f"moment {i} (app): zoom.to \"{z.get('to')}\" ne postoji (za {app}: {', '.join(sorted(names))})")
    for c in d.get("cursor") or []:
        to = c.get("to") if isinstance(c, dict) else None
        if not isinstance(to, dict) and str(to) not in names:
            errs.append(f"moment {i} (app): cursor.to \"{to}\" ne postoji (za {app}: {', '.join(sorted(names))})")
    if len(d.get("notes") or []) > 3:
        errs.append(f"moment {i} (app): najviše 3 beleške (notes) po momentu")
    if d.get("send") and not d.get("input"):
        errs.append(f"moment {i} (app): send bez input-a — šta se šalje?")
    # --- podaci po aplikaciji
    if app == "instagram":
        sc = d.get("screen") or "profile"
        if sc not in IG_SCREENS:
            errs.append(f"moment {i} (app): instagram screen mora biti {' | '.join(IG_SCREENS)}")
        if sc == "insights" and not isinstance(d.get("metric"), dict):
            errs.append(f"moment {i} (app): instagram insights traži metric {{label, value, from, at, delta}} — broj koji raste")
        if sc == "inbox":
            th = d.get("threads") or []
            if not th:
                errs.append(f"moment {i} (app): instagram inbox traži threads [{{name, text, at}}] — poruke koje stižu")
            if len(th) > 8:
                errs.append(f"moment {i} (app): inbox prikazuje najviše 8 razgovora")
            for x in th:
                if not (isinstance(x, dict) and _t(x.get("name")) and _t(x.get("text"))):
                    errs.append(f"moment {i} (app): svaki thread traži name + text")
                    break
        if sc == "profile" and not _t(d.get("handle")):
            errs.append(f"moment {i} (app): instagram profile traži handle (korisničko ime)")
        if len(d.get("grid") or []) > 9:
            errs.append(f"moment {i} (app): grid ima najviše 9 polja")
    if app == "iphone":
        ns = d.get("notifications") or []
        if not 1 <= len(ns) <= 6:
            errs.append(f"moment {i} (app): iphone traži 1–6 notifications [{{app, title, body, at}}]")
        for x in ns:
            if not (isinstance(x, dict) and _t(x.get("title"))):
                errs.append(f"moment {i} (app): svaka notifikacija traži title (i body)")
                break
    if app == "gmail":
        em = d.get("emails") or []
        if len(em) > 8:
            errs.append(f"moment {i} (app): gmail prikazuje najviše 8 mejlova")
        for x in em:
            if not (isinstance(x, dict) and _t(x.get("from")) and _t(x.get("subject"))):
                errs.append(f"moment {i} (app): svaki mejl traži from + subject")
                break
        if d.get("input") and not d.get("compose"):
            errs.append(f"moment {i} (app): gmail input se kuca u Compose — dodaj compose {{at, to, subject}}")
    if app in ("n8n", "zapier", "make"):
        ns = d.get("nodes") or []
        if not 2 <= len(ns) <= 6:
            errs.append(f"moment {i} (app): {app} traži 2–6 nodes [{{app, label, at}}] (okidač pa koraci)")
        for x in ns:
            if not (isinstance(x, dict) and _t(x.get("label"))):
                errs.append(f"moment {i} (app): svaki čvor traži label")
                break
    if app == "perplexity" and len(d.get("sources") or []) > 4:
        errs.append(f"moment {i} (app): perplexity prikazuje najviše 4 izvora")
    if app == "midjourney":
        if not (d.get("send") or d.get("generate")):
            errs.append(f"moment {i} (app): midjourney traži send (posle input-a) ili generate {{at}} — kad slike počnu da se razvijaju")
        if len(d.get("images") or []) > 4:
            errs.append(f"moment {i} (app): midjourney ima 4 slike")
        up = d.get("upscale")
        if isinstance(up, dict) and not 0 <= int(up.get("index", 0) or 0) <= 3:
            errs.append(f"moment {i} (app): upscale.index je 0–3")
    if app == "slack":
        if not (d.get("messages") or d.get("input")):
            errs.append(f"moment {i} (app): slack traži messages [{{name, text, at}}] ili input (poruka koja se kuca)")
        for x in d.get("messages") or []:
            if not (isinstance(x, dict) and _t(x.get("name")) and _t(x.get("text"))):
                errs.append(f"moment {i} (app): svaka slack poruka traži name + text")
                break
    if app == "calendar":
        evs = d.get("events") or []
        if not evs:
            errs.append(f"moment {i} (app): calendar traži events [{{title, day, start, end, at}}] (pon–pet, 9–17 h)")
        for x in evs:
            if not (isinstance(x, dict) and _t(x.get("title"))):
                errs.append(f"moment {i} (app): svaki događaj traži title")
                break
        if len(evs) > 12:
            errs.append(f"moment {i} (app): najviše 12 događaja u nedelji (čitljivost)")
    if app in ("stripe", "shopify"):
        if not isinstance(d.get("metric"), dict) and not d.get("payments"):
            errs.append(f"moment {i} (app): {app} traži metric {{label, value, start, at}} i/ili payments [{{amount, customer, at}}]")
        if len(d.get("payments") or []) > 5:
            errs.append(f"moment {i} (app): {app} prikazuje najviše 5 uplata/porudžbina")
    if app == "google":
        if not (d.get("input") or d.get("query")):
            errs.append(f"moment {i} (app): google traži input (upit koji se kuca) ili query")
        if len(d.get("results") or []) > 3:
            errs.append(f"moment {i} (app): google prikazuje najviše 3 rezultata (krupno i čitljivo)")
    if app == "terminal":
        ls = d.get("lines") or []
        if not ls and not d.get("input"):
            errs.append(f"moment {i} (app): terminal traži lines [{{text, kind, at}}] (kind: cmd | out | ok | err | claude | tool) ili input")
        for x in ls:
            if isinstance(x, dict) and x.get("kind") not in (None, "cmd", "out", "ok", "err", "claude", "tool", "prompt"):
                errs.append(f"moment {i} (app): terminal kind \"{x.get('kind')}\" ne postoji (cmd | out | ok | err | claude | tool)")
                break
    if app in ("cursor", "vscode"):
        if not (d.get("code") or d.get("add")):
            errs.append(f"moment {i} (app): {app} traži code (postojeće linije) i/ili add [{{text, at}}] (linije koje se dopisuju)")
        if len(d.get("code") or []) + len(d.get("add") or []) > 14:
            errs.append(f"moment {i} (app): editor prikazuje najviše 14 linija koda (čitljivost)")
    if app == "canva" and not d.get("elements"):
        errs.append(f"moment {i} (app): canva traži elements [{{text | file, at}}] (prvi tekst = naslov dizajna)")
    if app == "capcut" and not (d.get("captions") or d.get("cuts")):
        errs.append(f"moment {i} (app): capcut traži captions {{at, text}} i/ili cuts [{{at}}]")
    if app == "ads":
        cs = d.get("campaigns") or []
        if not cs:
            errs.append(f"moment {i} (app): ads traži campaigns [{{name, results, cost, roas, at, tone, off}}]")
        if len(cs) > 5:
            errs.append(f"moment {i} (app): ads prikazuje najviše 5 kampanja")
    if app == "ytstudio" and len(d.get("metrics") or []) > 3:
        errs.append(f"moment {i} (app): ytstudio ima 3 metrike (Views, Watch time, Subscribers)")
    if app == "tiktok" and len(d.get("comments") or []) > 4:
        errs.append(f"moment {i} (app): tiktok fioka prikazuje najviše 4 komentara")
    if app == "custom":
        b = d.get("brand") if isinstance(d.get("brand"), dict) else {}
        if not _t(b.get("name")):
            errs.append(f"moment {i} (app): custom traži brand {{name, color, logo: {{file}}}} — ime alata (logo iz `ccc logo` kad postoji)")
        if b.get("color") and not re.match(r"^#[0-9a-fA-F]{6}$", str(b.get("color"))):
            errs.append(f"moment {i} (app): brand.color mora biti hex (#RRGGBB)")
        if d.get("type") not in ("chat", "list", "dashboard"):
            errs.append(f"moment {i} (app): custom type mora biti chat | list | dashboard (AI asistent / inbox-CRM-zadaci / prihod-pretplatnici)")
        if isinstance(b.get("logo"), str):
            errs.append(f"moment {i} (app): brand.logo je objekat {{\"file\": \"web-logo-….png\"}}")
    kind = d.get("type") if app == "custom" else ("list" if app in SPEC_LIST else "dashboard" if app in SPEC_DASH else None)
    if kind == "list":
        rows = d.get("rows") or []
        if not rows:
            errs.append(f"moment {i} (app): {app} traži rows [{{…, at, tone}}] — redovi koji stižu na reč")
        if len(rows) > 7:
            errs.append(f"moment {i} (app): lista prikazuje najviše 7 redova")
        keys = SPEC_COLS.get(app) or tuple(str((c.get("key") if isinstance(c, dict) else c)) for c in d.get("columns") or []) or ("name", "status", "time")
        for r in rows:
            if isinstance(r, dict) and not any(_t(r.get(k)) for k in keys):
                errs.append(f"moment {i} (app): red u listi nema nijedno polje od {list(keys)}")
                break
    if kind == "dashboard":
        if not isinstance(d.get("metric"), dict) and not (d.get("payments") or d.get("rows")):
            errs.append(f"moment {i} (app): {app} traži metric {{label, value, start, at}} i/ili payments [{{amount, customer, at}}]")
        if len(d.get("payments") or d.get("rows") or []) > 5:
            errs.append(f"moment {i} (app): dashboard prikazuje najviše 5 redova")
    if app == "web":
        if not d.get("file"):
            errs.append(f"moment {i} (app): web traži file — screenshot stranice iz `ccc shot` (sa --mark za fraze koje se klikću/ističu)")
        elif job is not None:
            from .web import sources as _src
            from .assets import nfc
            ws = _src(job).get(nfc(str(d["file"])))
            if not ws or ws.get("kind") != "screenshot":
                errs.append(f"moment {i} (app): web file '{d['file']}' nije screenshot iz `ccc shot`")
            else:
                found = {str(m.get("text", "")).lower() for m in ws.get("marks") or [] if m.get("rect")}
                for m in d.get("marks") or []:
                    if _t(m).lower() not in found:
                        errs.append(f"moment {i} (app): web mark \"{_t(m)}\" nije snimljen na stranici — ccc shot … --mark \"{_t(m)}\"")
    return errs


def _story_errors(i: int, k: str, d: dict, job=None) -> list[str]:
    """Priča i ljudi (faza 1): oblik podataka — broj delova, veze ka postojećim licima, citat koji se ističe postoji u citatu."""
    errs: list[str] = []
    if k == "timeline":
        ev = d.get("events") or []
        if not 2 <= len(ev) <= 5:
            errs.append(f"moment {i} (timeline): 2–5 events [{{year | date, label, file, at}}]")
        for x in ev:
            if not (isinstance(x, dict) and _t(x.get("label") or x.get("text")) and (x.get("year") or x.get("date"))):
                errs.append(f"moment {i} (timeline): svaki event traži year (ili date) + label")
                break
    if k == "quote":
        q = str(d.get("text") or "")
        if len(q) > 160:
            errs.append(f"moment {i} (quote): citat ima {len(q)} znakova (najviše 160) — pokaži glavnu rečenicu citata (sa … ako je skraćen)")
        for h in d.get("highlight") or []:
            if _t(h) and _t(h).lower() not in q.lower():
                errs.append(f"moment {i} (quote): highlight \"{_t(h)}\" nije deo citata — isticanje samo tačnih reči iz citata")
        if not d.get("name"):
            errs.append(f"moment {i} (quote): citat traži name (ko je to rekao) — i file (njegov portret) kad postoji")
    if k == "network":
        ppl = d.get("people") or []
        if not 2 <= len(ppl) <= 4:
            errs.append(f"moment {i} (network): 2–4 people [{{file, name, role, at}}]")
        for x in ppl:
            if not (isinstance(x, dict) and _t(x.get("name"))):
                errs.append(f"moment {i} (network): svaka osoba traži name")
                break
        for l in d.get("links") or []:
            try:
                ab = l.get("between") if isinstance(l, dict) else None
                ok = isinstance(ab, list) and len(ab) == 2 and all(0 <= int(x) < len(ppl) for x in ab) and int(ab[0]) != int(ab[1])
            except (TypeError, ValueError):
                ok = False
            if not ok:
                errs.append(f"moment {i} (network): link traži between: [osoba, osoba] — brojevi osoba (0–{len(ppl) - 1}), različiti")
                break
    if k == "dossier":
        if len(d.get("facts") or []) > 4:
            errs.append(f"moment {i} (dossier): najviše 4 činjenice")
        if not d.get("file"):
            errs.append(f"moment {i} (dossier): dosije traži file (pravi portret osobe)")
    if k == "compare":
        for side in ("before", "after"):
            v = d.get(side)
            if not (isinstance(v, dict) and v.get("file")):
                errs.append(f"moment {i} (compare): {side} traži {{file, label}} (pravi snimak tada / sada)")
    if k == "map":
        pins = d.get("pins") or []
        if not 1 <= len(pins) <= 8:
            errs.append(f"moment {i} (map): 1–8 pins [{{lat, lon, label, at}}]")
        for x in pins:
            try:
                ok = isinstance(x, dict) and -60 <= float(x.get("lat")) <= 85 and -180 <= float(x.get("lon")) <= 180
            except (TypeError, ValueError):
                ok = False
            if not ok:
                errs.append(f"moment {i} (map): svaki pin traži lat (−60…85) i lon (−180…180) kao brojeve — koordinate mesta iz izvora")
                break
        for l in d.get("lines") or []:
            ab = l.get("between") if isinstance(l, dict) else None
            if not (isinstance(ab, list) and len(ab) == 2 and all(isinstance(v, int) and 0 <= v < len(pins) for v in ab) and ab[0] != ab[1]):
                errs.append(f"moment {i} (map): line traži between: [pin, pin] (brojevi pinova 0–{len(pins) - 1})")
                break
        if d.get("zoom") is not None and not (isinstance(d.get("zoom"), (int, float)) and 4 <= d["zoom"] <= 360):
            errs.append(f"moment {i} (map): zoom = širina pogleda u stepenima (4–360; grad ~6, država ~25, kontinent ~70, svet 360)")
    if k == "breaking":
        if len(str(d.get("headline") or "")) > 90:
            errs.append(f"moment {i} (breaking): naslov najviše 90 znakova (tačan naslov vesti, skraćen sa …)")
    if k == "trend":
        pts = d.get("points") or []
        if not 3 <= len(pts) <= 24:
            errs.append(f"moment {i} (trend): 3–24 points [{{value, label}}] — prave vrednosti iz izvora")
        for e in d.get("events") or []:
            if not (isinstance(e, dict) and isinstance(e.get("index"), int) and 0 <= e["index"] < len(pts) and _t(e.get("label"))):
                errs.append(f"moment {i} (trend): event traži index (tačka 0–{len(pts) - 1}) + label")
                break
        if len(d.get("events") or []) > 3:
            errs.append(f"moment {i} (trend): najviše 3 događaja na grafiku")
    if k == "ranking":
        its = d.get("items") or []
        if not 3 <= len(its) <= 5:
            errs.append(f"moment {i} (ranking): 3–5 items [{{file, name, value, at}}]")
        for x in its:
            if not (isinstance(x, dict) and _t(x.get("name")) and str(x.get("value") or "")):
                errs.append(f"moment {i} (ranking): svaki red traži name + value")
                break
    if k == "lowerthird":
        if not d.get("file"):
            errs.append(f"moment {i} (lowerthird): traži file — pravi snimak ili foto osobe")
        elif job is not None:
            from .assets import nfc, prepare
            m = prepare(job).get(nfc(str(d["file"])))
            if m is None:
                errs.append(f"moment {i}: fajl '{d['file']}' ne postoji u {assets_dir(job)}")
            elif m["kind"] == "video" and d.get("start") and float(d["start"]) >= m.get("duration", 0):
                errs.append(f"moment {i}: start {d['start']}s je posle kraja klipa ({m.get('duration')}s)")
    return errs


STORY_MUST = ("fokus screenshot-a",)  # priča/smisao je inače [aim]; ovo se ne isporučuje (principles.md 51)


def story_severity(msg: str) -> str:
    return "must" if any(m in msg for m in STORY_MUST) else "aim"


def severity(msg: str) -> str:
    return "must" if any(m in msg for m in MUST_MARKERS) else "aim"


LIST_FIELDS = ("items", "nodes", "words", "bars", "sets", "actors", "beats", "lines", "rows", "messages", "sides",
               "logos", "more", "marks", "values", "highlight", "x", "display", "tones")


def _types(plan: dict) -> list[str]:
    """Tipovi polja koje šabloni koriste bez provere: `from`/`at` su id reči (tekst), liste su liste, brojevi brojevi."""
    errs: list[str] = []
    items = plan.get("items")
    if not isinstance(items, list):
        return ["plan mora imati listu 'items'"]

    def walk(n, path):
        if isinstance(n, dict):
            for key, v in n.items():
                here = f"{path}.{key}"
                if key in ("from", "at") and not isinstance(v, str):
                    errs.append(f"{here}: mora biti id reči kao tekst (npr. \"w42\"), a ne {type(v).__name__}")
                elif key in LIST_FIELDS and key not in ("highlight", "x") and v is not None and not isinstance(v, list) \
                        and not (key == "rows" and isinstance(v, int)):  # resource: rows = broj praznih redova je OK
                    errs.append(f"{here}: mora biti lista")
                elif key in ("text", "label", "name", "title", "line1", "line2", "kicker") and v is not None \
                        and not isinstance(v, (str, dict)):
                    errs.append(f"{here}: mora biti tekst (npr. \"$4.2M\"), a ne {type(v).__name__}")
                elif key in ("n", "size", "x", "y", "rx", "ry", "scale", "speed", "cols", "gap", "aspect") \
                        and (".actors[" in here or ".beats[" in here) and v is not None and not isinstance(v, (int, float)):
                    # samo položaji u sceni (chart koristi x = lista oznaka, y = naziv ose — 0.8.1 ih je odbijao)
                    errs.append(f"{here}: mora biti broj")
                walk(v, here)
        elif isinstance(n, list):
            for j, v in enumerate(n):
                walk(v, f"{path}[{j}]")

    for i, it in enumerate(items, 1):
        if not isinstance(it, dict):
            errs.append(f"moment {i}: mora biti objekat {{from, kind, why, data}}")
            continue
        walk(it, f"moment {i}")
        d = it.get("data") or {}
        if it.get("kind") == "pillars":
            for s_ in d.get("sets") or []:
                if isinstance(s_, dict) and any(not isinstance(v, (int, float)) or v < 0 for v in s_.get("values") or []):
                    errs.append(f"moment {i} (pillars): values su brojevi ≥ 0 (visine stubića); tekst ide u display")
        if it.get("kind") == "scene":
            for b in d.get("beats") or []:
                nn = b.get("n") if isinstance(b, dict) else None
                if isinstance(b, dict) and b.get("do") == "clone" and isinstance(nn, (int, float)) and not 2 <= nn <= 24:
                    errs.append(f"moment {i} (scene): clone n je broj 2–24 (više kopija ne staje na ekran)")
            for a_ in d.get("actors") or []:
                ax, ay = (a_.get("x"), a_.get("y")) if isinstance(a_, dict) else (None, None)
                ax = ax if isinstance(ax, (int, float)) else 540
                ay = ay if isinstance(ay, (int, float)) else 480
                if isinstance(a_, dict) and (not 0 <= ax <= 1080 or not 120 <= ay <= 900):
                    errs.append(f"moment {i} (scene): glumac '{a_.get('id')}' je van pozornice (x 0–1080, y 120–900)")
        errs += _lengths(i, it.get("kind"), d if isinstance(d, dict) else {})
    return errs[:20]


def _t(x) -> str:
    return x if isinstance(x, str) else str(x.get("text") or x.get("label") or "") if isinstance(x, dict) else ""


def _lengths(i: int, kind, d: dict) -> list[str]:
    """Najduži tekst koji šablon još čita: auto-fit ga smanjuje do ~60%, duži postaje sitan (QA 0.8.0, P1-23)."""
    out = []

    def cap(txt: str, mx: int, what: str):
        if len(txt) > mx:
            out.append(f"moment {i} ({kind}): {what} \"{txt[:40]}…\" ima {len(txt)} znakova (najviše {mx}) — skrati; "
                       "ceo izgovor je već u titlu")
    if kind == "faceoff":
        for s_ in d.get("sides") or []:
            if isinstance(s_, dict):
                cap(_t(s_.get("name")), 28, "ime")
                for v in s_.get("values") or []:
                    cap(_t(v), 26, "vrednost")
                    if isinstance(v, dict):
                        cap(_t(v.get("label")), 40, "natpis")
    elif kind == "pillars":
        for b in d.get("bars") or []:
            if isinstance(b, dict):
                cap(_t(b.get("name")), 22, "ime stubića")
        for s_ in d.get("sets") or []:
            if isinstance(s_, dict):
                cap(_t(s_.get("label")), 60, "natpis skupa")
                cap(_t(s_.get("note")), 44, "note")
                for x in s_.get("display") or []:
                    cap(_t(x), 10, "prikaz vrednosti")
    elif kind == "resource":
        cap(_t(d.get("title")), 60, "naslov")
        cap(_t(d.get("sub")), 90, "podnaslov")
        cap(_t(d.get("badge")), 28, "badge")
        for r in d.get("rows") if isinstance(d.get("rows"), list) else []:
            cap(_t(r), 70, "red")
    elif kind == "app":
        m = d.get("menu") if isinstance(d.get("menu"), dict) else {}
        for x in m.get("items") or []:
            cap(_t(x), 26, "stavka menija")
        cap(_t(d.get("input")), 70, "kucani tekst")
        cap(_t(d.get("reply")), 140, "odgovor")
        for n in d.get("notes") or []:
            cap(_t(n), 42, "beleška")
        c = d.get("card") if isinstance(d.get("card"), dict) else {}
        cap(_t(c.get("title")), 30, "naslov kartice")
        for st in c.get("steps") or []:
            cap(_t(st), 30, "korak")
        for tb in d.get("tabs") or []:
            cap(_t(tb), 18, "tab")
        for x in d.get("threads") or []:
            if isinstance(x, dict):
                cap(_t(x.get("name")), 24, "ime u inbox-u")
                cap(_t(x.get("text")), 44, "poruka u inbox-u")
        for x in d.get("notifications") or []:
            if isinstance(x, dict):
                cap(_t(x.get("title")), 32, "naslov notifikacije")
                cap(_t(x.get("body")), 80, "tekst notifikacije")
        for x in d.get("emails") or []:
            if isinstance(x, dict):
                cap(_t(x.get("from")), 22, "pošiljalac")
                cap(_t(x.get("subject")) + " " + _t(x.get("snippet")), 70, "naslov + početak mejla")
        for x in d.get("nodes") or []:
            if isinstance(x, dict):
                cap(_t(x.get("label")), 22 if d.get("app") != "zapier" else 36, "čvor")
        for x in d.get("rows") or []:
            if isinstance(x, dict):
                cap(_t(x.get("label")), 26, "red")
        cap(_t(d.get("bio")), 120, "bio")
        for x in d.get("messages") or []:
            if isinstance(x, dict):
                cap(_t(x.get("text")), 60, "slack poruka")
        for x in d.get("events") or []:
            if isinstance(x, dict):
                cap(_t(x.get("title")), 20, "događaj")
        for x in d.get("results") or []:
            if isinstance(x, dict):
                cap(_t(x.get("title")), 60, "naslov rezultata")
                cap(_t(x.get("snippet")), 80, "opis rezultata")
        for x in d.get("sources") or []:
            if isinstance(x, dict):
                cap(_t(x.get("title")), 44, "izvor")
        if isinstance(d.get("overview"), dict):
            cap(_t(d["overview"]), 180, "AI Overview")
        for x in d.get("lines") or []:
            cap(_t(x), 60, "linija terminala")
        for x in (d.get("code") or []) + (d.get("add") or []):
            cap(_t(x), 52, "linija koda")
        for x in d.get("campaigns") or []:
            if isinstance(x, dict):
                cap(_t(x.get("name")), 34, "ime kampanje")
        for x in d.get("comments") or []:
            if isinstance(x, dict):
                cap(_t(x.get("text")), 70, "komentar")
        cap(_t(d.get("caption")), 90, "opis videa")
    elif kind == "timeline":
        for x in d.get("events") or []:
            if isinstance(x, dict):
                cap(_t(x.get("label") or x.get("text")), 46, "opis događaja")
                cap(str(x.get("year") or x.get("date") or ""), 12, "godina/datum")
    elif kind == "network":
        for x in d.get("people") or []:
            if isinstance(x, dict):
                cap(_t(x.get("name")), 20, "ime")
                cap(_t(x.get("role")), 24, "uloga")
        for x in d.get("links") or []:
            if isinstance(x, dict):
                cap(_t(x.get("label")), 18, "oznaka veze")
    elif kind == "dossier":
        for x in d.get("facts") or []:
            if isinstance(x, dict):
                cap(_t(x.get("label")), 26, "oznaka činjenice")
                cap(str(x.get("value") or ""), 20, "vrednost")
    elif kind == "map":
        for x in d.get("pins") or []:
            if isinstance(x, dict):
                cap(_t(x.get("label")), 22, "oznaka pina")
    elif kind == "breaking":
        cap(str(d.get("ticker") or ""), 120, "traka")
    elif kind == "trend":
        for x in d.get("events") or []:
            if isinstance(x, dict):
                cap(_t(x.get("label")), 22, "oznaka događaja")
    elif kind == "ranking":
        for x in d.get("items") or []:
            if isinstance(x, dict):
                cap(_t(x.get("name")), 22, "ime")
                cap(str(x.get("value") or ""), 10, "vrednost")
    elif kind == "lowerthird":
        cap(_t(d.get("name")), 26, "ime")
        cap(" · ".join(filter(None, [_t(d.get("sub")), _t(d.get("place"))])), 44, "uloga · mesto")
    elif kind == "scene":
        for b in d.get("beats") or []:
            if isinstance(b, dict) and b.get("do") in ("tag", "stamp"):
                cap(_t(b.get("text")), 30, b["do"])
        for a_ in d.get("actors") or []:
            if isinstance(a_, dict) and isinstance(a_.get("text"), str):
                cap(a_["text"], 60, "tekst glumca")
    return out


def save_plan(job, p: dict, path: Path) -> None:
    """Proveri oblik plana i sačuvaj ga; vremenske probleme (prekratko, izbačena reč) prikazuje `describe`."""
    try:
        plan = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise SystemExit(f"Plan nije sačuvan: fajl {path} ne postoji")
    except json.JSONDecodeError as err:
        raise SystemExit(f"Plan nije sačuvan: neispravan JSON ({err})")
    errs = _types(plan) or validate_plan(plan, job)
    if not errs:
        # Probni prolaz na KOPIJI pre čuvanja: plan koji prođe proveru oblika, a ruši timeline/describe, ranije se
        # sačuvao pa je svaka sledeća komanda (visuals, stills, build) pucala dok se ne postavi novi (QA 0.8.0, P0).
        import copy
        q = copy.deepcopy(p)
        q["visuals"] = {"items": copy.deepcopy(plan["items"])}
        try:
            describe(q, None)
        except Exception as err:  # noqa: BLE001
            errs = [f"plan ne može da se prikaže ({type(err).__name__}: {err}) — proveri tipove polja (from/at = id reči "
                    "kao tekst, liste kao liste, tekstovi kao tekst)"]
    if errs:
        raise SystemExit("Plan nije sačuvan:\n" + "\n".join(f"  ✗ {x}" for x in errs))
    p["visuals"] = {"items": plan["items"]}
