"""Storyboard za svaki test video + feedback kao podaci za učenje (samo razvoj — ne ide klijentima).

Petlja (vidi CLAUDE.md):
  1. `ccc build` (u dev folderu) posle uspešnog izvoza sam pravi novu verziju storyboard-a:
     work/<ime>/storyboard/vN/ → storyboard.html + fr/*.jpg (3 kadra po sceni) + scenes.json (ceo kontekst
     scene: šta se govori, šta je gore, zašto, podaci iz plana) + meta.json + video.mp4 (ta verzija).
  2. Claude objavi storyboard.html kao Artifact (db) → korisnik oceni svaku scenu (dobro / popravi / ponovo)
     i ostavi komentare; komentari su u kolekciji "notes" (s01…, general).
  3. `ccc feedback <ime> --save notes.json` spaja ocene sa scenama → vN/feedback.json i
     <kod>/history/feedback.jsonl (jedan red po oceni — skup podataka za učenje, raste sa svakim testom).
  4. `ccc lessons` sažima sav feedback (po vrsti scene: koliko dobro/popravi/ponovo + svi komentari) —
     Claude ga čita pre planiranja sledećeg videa i iz njega pravi pravila (PLAN.md §13.1, skill, engine).

Storyboard za Split Screen = momenti gornje polovine; za ostale formate = izgovorene rečenice.
"""
from __future__ import annotations

import datetime
import html
import json
import shutil
import subprocess
from pathlib import Path

from .project import ROOT

TEMPLATE = ROOT / "tools" / "storyboard" / "template.html"
DATASET = ROOT / "history" / "feedback.jsonl"
VERDICTS = {"good": "dobro", "fix": "popravi", "redo": "ponovo"}

KIND = {"flow": "Flow", "image": "Slika", "screenshot": "Screenshot", "headline": "Naslov", "checklist": "Checklist",
        "versus": "Versus", "photo": "Fotografija", "filter": "Filter", "chart": "Grafikon", "stat": "Broj", "post": "Objava",
        "news": "Vest", "mediatext": "Medij + tekst", "posts": "Objave", "logo": "Logo", "video": "Snimak", "key": "Poziv",
        "spotlight": "Hook (spotlight)", "steps": "Koraci", "week": "Nedelja", "chat": "Chat", "notify": "Notifikacije",
        "comment": "Komentar", "speech": "Govor"}


def available() -> bool:
    """Storyboard postoji samo u razvojnom folderu (template nije u paketu za klijente)."""
    return TEMPLATE.exists()


def _t(x) -> str:
    return x if isinstance(x, str) else (x or {}).get("text") or (x or {}).get("label") or ""


def summary(k: str, d: dict) -> str:
    if k == "flow":
        return " → ".join(n.get("label") or "" for n in d.get("nodes", [])) + f"  [{d.get('layout', 'row')}]"
    if k == "mediatext":
        return f"{d.get('file')} · " + " / ".join(_t(x) for x in d.get("lines", []))
    if k == "posts":
        return " + ".join(x.get("file") or x.get("platform", "") for x in d.get("items", []))
    if k == "logo":
        return (" · ".join(x.get("name", "") for x in d.get("logos", [])) or d.get("name", "")) \
            + (f" · {_t(d.get('sub'))}" if d.get("sub") else "")
    if k == "headline":
        return " ".join(_t(w) for w in d.get("words", [])) + (f" · {_t(d.get('sub'))}" if d.get("sub") else "")
    if k == "stat":
        return f"{d.get('value', '')} — {d.get('label', '')}" + (f" · {_t(d.get('sub'))}" if d.get("sub") else "")
    if k == "checklist":
        return f"{d.get('title', '')}: " + " · ".join(_t(i) for i in d.get("items", []))
    if k == "notify":
        return " · ".join(f"{i.get('title', '')} ({i.get('body', '')})" for i in d.get("items", []))
    if k == "versus":
        return f"{_t(d.get('left'))} ✗ → {_t(d.get('right'))} ✓"
    if k == "steps":
        items = d.get("items", [])
        a = d.get("active", 0)
        return f"korak {a + 1}/{len(items)}: {items[a] if a < len(items) else ''}"
    if k == "chart":
        return f"{d.get('label', '')}: " + ", ".join(f"{x} {b}" for x, b in zip(d.get("x", []), d.get("bars", [])))
    if k == "key":
        return f"{d.get('line1', '')} · {d.get('line2', '')}"
    if k in ("screenshot", "image", "photo", "video", "spotlight"):
        return ((d.get("file") or "") + (f" · {d.get('name')}" if d.get("name") else "")
                + (" · oznake: " + ", ".join(m["text"] + (" (blur)" if m.get("blur") else "") for m in d.get("marks", []))
                   if d.get("marks") else ""))
    if k == "speech":
        return "govornik (bez gornje polovine)"
    return json.dumps(d, ensure_ascii=False)[:110]


def mmss(x: float) -> str:
    return f"{int(x // 60)}:{x % 60:04.1f}"


def _scenes(p: dict) -> list[dict]:
    """Scene sa izlaznim vremenom: momenti gornje polovine (Split) ili zadržane rečenice (ostali formati)."""
    from .visuals import _out_time, timeline
    removed = {w for r in p.get("removed", []) for w in r["words"]}
    words = [dict(w, o=_out_time(p, w["start"])) for w in p["words"] if w["id"] not in removed]
    words = [w for w in words if w["o"] is not None]
    total = sum(s["vFrames"] for s in p["segments"]) / p["fps"]
    if (p.get("layout") or {}).get("type") == "split" and p.get("visuals"):
        items, _ = timeline(p)
        raw = [{"kind": it["kind"], "start": it["start"], "end": it["end"], "data": it.get("data") or {},
                "why": it.get("why") or "", "from": it.get("from")} for it in items]
    else:  # rečenica po rečenica (do . ? !)
        raw, cur = [], []
        for w in words:
            cur.append(w)
            if w["text"].rstrip().endswith((".", "?", "!")):
                raw.append(cur)
                cur = []
        if cur:
            raw.append(cur)
        raw = [{"kind": "speech", "start": ws[0]["o"], "end": 0, "data": {}, "why": "", "from": ws[0]["id"]} for ws in raw]
        for a, b in zip(raw, raw[1:]):
            a["end"] = b["start"]
        if raw:
            raw[0]["start"], raw[-1]["end"] = 0.0, total
    out = []
    for n, it in enumerate(raw, 1):
        s0, s1 = it["start"], it["end"]
        said = " ".join(w["text"] for w in words if s0 - 0.01 <= w["o"] < s1 - 0.01)
        out.append({"id": f"s{n:02d}", "n": n, "kind": it["kind"], "start": round(s0, 2), "end": round(s1, 2),
                    "said": said, "what": summary(it["kind"], it["data"]), "why": it["why"], "from": it["from"],
                    "data": it["data"]})
    return out


def make(job, p: dict, label: str | None = None) -> dict:
    """Nova verzija storyboard-a iz gotovog videa (final.mp4) → {version, dir, html, scenes}."""
    if not available():
        raise SystemExit("Storyboard postoji samo u razvojnom folderu (nema tools/storyboard/template.html).")
    video = job.dir / "final.mp4"
    if not video.exists():
        raise SystemExit(f"Nema {video} — prvo ccc build {job.name}")
    base = job.dir / "storyboard"
    nums = [int(d.name[1:]) for d in base.glob("v*") if d.name[1:].isdigit()] if base.exists() else []
    v = max(nums, default=0) + 1
    out = base / f"v{v}"
    (out / "fr").mkdir(parents=True, exist_ok=True)
    scenes = _scenes(p)
    rows = []
    for s in scenes:
        s0, s1 = s["start"], s["end"]
        dd = s1 - s0
        for k, tt in (("a", s0 + min(0.45, dd * 0.2)), ("b", s0 + dd * 0.55), ("c", max(s0 + 0.1, s1 - 0.12))):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{tt:.2f}", "-i", str(video), "-frames:v", "1",
                            "-vf", "scale=270:480", "-q:v", "5", str(out / "fr" / f"s{s['n']}{k}.jpg")], check=True)
        rows.append({"id": s["id"], "n": s["n"], "kind": KIND.get(s["kind"], s["kind"]),
                     "t": f"{mmss(s0)}–{mmss(s1)}", "dur": round(dd, 1), "said": s["said"], "hook": s["n"] == 1 and bool(p.get("hook")),
                     "what": s["what"] + (f"\nZašto: {s['why']}" if s["why"] else "")})
    shutil.copy(video, out / "video.mp4")
    ch = p.get("choices") or {}
    label = label or f"{job.name} v{v}"
    meta = {"video": job.name, "version": v, "label": label, "created": datetime.datetime.now().isoformat(timespec="seconds"),
            "format": ch.get("format", "basic"), "choices": ch, "stats": p.get("stats"), "reframe": p.get("reframe"),
            "scenes": len(scenes), "artifact": None}
    (out / "scenes.json").write_text(json.dumps(scenes, indent=1, ensure_ascii=False))
    (out / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    chips = [f"{job.name} · {mmss(p['stats']['video'])}" if p.get("stats") else job.name, f"verzija {v}",
             ch.get("format", "basic"), (ch.get("top_style") or "dark").capitalize() if ch.get("top_style") else None,
             f"titlovi: {ch.get('caption_style', '?')}", f"font: {ch.get('font', '?')}", f"pacing: {ch.get('pacing', '?')}",
             f"{len(rows)} scena"]
    page = TEMPLATE.read_text()
    title = "Split Screen" if ch.get("format") == "split-screen" else ch.get("format", "Basic").replace("-", " ").title()
    page = (page.replace("__DATA__", json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"))
                .replace("__TITLE__", html.escape(f"Storyboard {label}"))
                .replace("__H1__", f"{html.escape(title)} · <b>{html.escape(label)}</b>")
                .replace("__CHIPS__", "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips if c)))
    (out / "storyboard.html").write_text(page)
    return {"version": v, "dir": out, "html": out / "storyboard.html", "scenes": len(rows)}


def _latest(job) -> Path:
    base = job.dir / "storyboard"
    vs = sorted((d for d in base.glob("v*") if d.name[1:].isdigit()), key=lambda d: int(d.name[1:])) if base.exists() else []
    if not vs:
        raise SystemExit(f"Nema storyboard-a za {job.name} — ccc storyboard {job.name}")
    return vs[-1]


def set_artifact(job, url: str, version: int | None = None) -> Path:
    d = job.dir / "storyboard" / f"v{version}" if version else _latest(job)
    m = json.loads((d / "meta.json").read_text())
    m["artifact"] = url
    (d / "meta.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    return d


def _notes(raw) -> dict[str, dict]:
    """ArtifactData `list` izlaz (lista dokumenata, sa ili bez omotača) → {s01: {verdict, comment}, general: …}."""
    if isinstance(raw, dict):
        raw = raw.get("documents") or raw.get("docs") or raw.get("items") or list(raw.values())
    out = {}
    for d in raw or []:
        if not isinstance(d, dict):
            continue
        x = d.get("data") if isinstance(d.get("data"), dict) else d
        sid = x.get("scene") or d.get("id") or d.get("doc_id")
        if isinstance(sid, str) and "/" in sid:
            sid = sid.rsplit("/", 1)[-1]
        if sid:
            out[sid] = {"verdict": x.get("verdict"), "comment": (x.get("comment") or "").strip()}
    return out


def save_feedback(job, notes_file: Path, version: int | None = None) -> dict:
    """Ocene iz storyboard-a → vN/feedback.json + red po oceni u history/feedback.jsonl (skup za učenje)."""
    d = job.dir / "storyboard" / f"v{version}" if version else _latest(job)
    meta = json.loads((d / "meta.json").read_text())
    scenes = {s["id"]: s for s in json.loads((d / "scenes.json").read_text())}
    src = Path(notes_file)
    if src.is_dir():  # ArtifactData list sa out_dir: <dir>/notes/<doc_id>.json (ili direktno <dir>/<doc_id>.json)
        files = sorted(src.rglob("*.json"))
        raw = []
        for f in files:
            if f.name.startswith("._"):
                continue
            x = json.loads(f.read_text())
            x = x if isinstance(x, dict) else {}
            raw.append({"id": f.stem, **({"data": x["data"]} if isinstance(x.get("data"), dict) else x)})
        notes = _notes(raw)
    else:
        notes = _notes(json.loads(src.read_text()))
    if not notes:
        raise SystemExit("U fajlu nema nijedne ocene/komentara.")
    now = datetime.datetime.now().isoformat(timespec="seconds")
    recs = []
    for sid, n in sorted(notes.items()):
        if not n["verdict"] and not n["comment"]:
            continue
        s = scenes.get(sid)
        rec = {"video": meta["video"], "version": meta["version"], "format": meta.get("format"), "saved": now,
               "artifact": meta.get("artifact"), "scene": sid, "verdict": n["verdict"], "comment": n["comment"]}
        if s:
            rec.update({"kind": s["kind"], "t": f"{mmss(s['start'])}–{mmss(s['end'])}", "dur": round(s["end"] - s["start"], 2),
                        "said": s["said"], "what": s["what"], "why": s["why"], "data": s["data"]})
        elif sid != "general":
            continue
        recs.append(rec)
    (d / "feedback.json").write_text(json.dumps(recs, indent=1, ensure_ascii=False))
    # Skup za učenje: ista verzija istog videa se zamenjuje (ponovni uvoz), sve ostalo ostaje.
    DATASET.parent.mkdir(parents=True, exist_ok=True)
    old = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()] if DATASET.exists() else []
    keep = [r for r in old if not (r.get("video") == meta["video"] and r.get("version") == meta["version"])]
    DATASET.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep + recs))
    c = {k: sum(1 for r in recs if r.get("verdict") == k) for k in VERDICTS}
    return {"dir": d, "records": recs, "counts": c, "scenes": len(scenes), "dataset": len(keep) + len(recs)}


def lessons(kind: str | None = None, last: int = 40) -> str:
    """Sažetak svega naučenog iz storyboard ocena — čita se pre planiranja sledećeg videa."""
    if not DATASET.exists():
        return "Još nema feedback-a (history/feedback.jsonl je prazan)."
    recs = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    if kind:
        recs = [r for r in recs if r.get("kind") == kind or r.get("scene") == "general"]
    vids = sorted({(r["video"], r["version"]) for r in recs})
    lines = [f"Feedback: {len(recs)} ocena iz {len(vids)} storyboard-a ({', '.join(f'{v} v{n}' for v, n in vids)})", ""]
    by: dict[str, dict] = {}
    for r in recs:
        if r.get("kind"):
            b = by.setdefault(r["kind"], {"good": 0, "fix": 0, "redo": 0})
            if r.get("verdict") in b:
                b[r["verdict"]] += 1
    if by:
        lines.append("Po vrsti scene (dobro / popravi / ponovo):")
        for k, b in sorted(by.items(), key=lambda kv: -(kv[1]["fix"] + kv[1]["redo"])):
            n = sum(b.values())
            lines.append(f"  {k:<11} {b['good']:>3} / {b['fix']:>3} / {b['redo']:>3}   ({round(100 * b['good'] / n) if n else 0}% dobro)")
        lines.append("")
    gen = [r for r in recs if r.get("scene") == "general" and r.get("comment")]
    if gen:
        lines.append("Opšti komentari:")
        lines += [f"  [{r['video']} v{r['version']}] {r['comment']}" for r in gen]
        lines.append("")
    bad = [r for r in recs if r.get("scene") != "general" and (r.get("verdict") in ("fix", "redo") or r.get("comment"))]
    if bad:
        lines.append(f"Komentari po scenama (poslednjih {min(last, len(bad))}, najnoviji poslednji):")
        for r in bad[-last:]:
            v = VERDICTS.get(r.get("verdict") or "", "—")
            lines.append(f"  [{r['video']} v{r['version']} {r['scene']} {r.get('kind', '?')} {r.get('t', '')}] {v.upper()}"
                         + (f": {r['comment']}" if r.get("comment") else ""))
            lines.append(f"      govori: {r.get('said', '')[:110]}")
            lines.append(f"      gore:   {r.get('what', '')[:110]}")
    return "\n".join(lines)
