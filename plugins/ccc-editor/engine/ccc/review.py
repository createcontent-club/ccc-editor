"""Tekstualni prikazi: transkript sa ID-jevima (za Claude-ove odluke) i pregled rezova (stajanje #1)."""
from __future__ import annotations

LABEL = {"filler": "filler", "stutter": "stutter", "retake": "retake", "false-start": "false start",
         "off-script": "off-script", "pause": "pause", "lead-in": "start", "tail": "end", "noise": "breath/noise"}


def fmt_t(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def transcript(p: dict) -> str:
    """Jedan izgovoreni deo po redu, sa opsegom ID-jeva i oznakom šta je već izbačeno —
    dovoljno da Claude odluči o retake-ovima, lažnim počecima i off-script delovima."""
    from .cut import resolve
    removed = resolve(p["words"], p["utterances"], p["decisions"])
    lines = []
    for u in p["utterances"]:
        if not u["from"]:
            lines.append(f"{u['id']} [{fmt_t(u['start'])}] (bez reči: dah/šum) — izbačeno")
            continue
        uw = [w for w in p["words"] if w["u"] == int(u["id"][1:])]
        marks = sorted({removed[w["id"]] for w in uw if w["id"] in removed})
        tag = f"  ⟵ {', '.join(marks)}" if marks else ""
        low = [w["text"] for w in uw if w["prob"] < 0.5]
        unsure = f"  (nesigurno: {' '.join(low)})" if low else ""
        lines.append(f"{u['from']}–{u['to']} [{fmt_t(u['start'])}] {u['text']}{tag}{unsure}")
    return "\n".join(lines)


def cut_review(p: dict) -> str:
    """Transkript sa precrtanim izbačenim delovima i oznakom razloga (+ duge pauze)."""
    removed_word = {}
    for r in p["removed"]:
        for wid in r["words"]:
            removed_word[wid] = r["reason"]
    long_pauses = {}
    for r in p["removed"]:
        if not r["words"] and r["srcEnd"] - r["srcStart"] >= 1.0 and r["reason"] in ("pause", "noise"):
            long_pauses[r["srcStart"]] = r["srcEnd"] - r["srcStart"]

    out, run, run_reason = [], [], None
    pause_marks = sorted(long_pauses.items())

    def flush():
        nonlocal run, run_reason
        if run:
            label = " + ".join(LABEL.get(x, x) for x in run_reason.split("+"))
            out.append(f"~~{' '.join(run)}~~ *[{label}]*")
        run, run_reason = [], None

    for w in p["words"]:
        while pause_marks and pause_marks[0][0] <= w["start"]:
            flush()
            out.append(f"~~⏸ {pause_marks.pop(0)[1]:.1f}s~~")
        r = removed_word.get(w["id"])
        if r:
            if run_reason not in (None, r):
                flush()
            run.append(w["text"])
            run_reason = r
        else:
            flush()
            out.append(w["text"])
    flush()

    counts: dict[str, int] = {}
    for r in p["removed"]:
        for x in r["reason"].split("+"):
            counts[x] = counts.get(x, 0) + 1
    st = p["stats"]
    summary = ", ".join(f"{LABEL.get(k, k)} ×{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    return (" ".join(out) + f"\n\n**Removed:** {summary}\n**Duration:** {fmt_t(st['before'])} → {fmt_t(st['after'])} "
            f"(−{st['before'] - st['after']:.1f}s, {len(p['segments'])} segments)")


# ------------------------------------------------------------------ izveštaj za klijenta (engleski)
HOOK_NAMES = {"box": "TikTok Box", "serif": "Editorial Serif", "color": "Color Block", "stack": "Stacked"}
CAPTION_NAMES = {"clean": "Clean", "karaoke": "Karaoke", "box": "Box Fill", "minimal": "Minimal"}
CLIENT_REASON = {"retake": "repeated take", "false-start": "false start", "off-script": "off-script talk",
                 "filler": "filler word", "stutter": "stutter"}


def client_report(p: dict, exported: str | None) -> str:
    st = p["stats"]
    words = {w["id"]: w for w in p["words"]}
    counts: dict[str, int] = {}
    notable = []
    for r in p["removed"]:
        reasons = r["reason"].split("+")
        for x in reasons:
            counts[x] = counts.get(x, 0) + 1
        if r["words"] and any(x in ("retake", "false-start", "off-script") for x in reasons):
            text = " ".join(words[w]["text"] for w in r["words"])
            label = " + ".join(CLIENT_REASON.get(x, x) for x in reasons)
            notable.append(f'  • {fmt_t(r["srcStart"])} — "{text[:70]}{"…" if len(text) > 70 else ""}" ({label})')
    pauses = sum(counts.get(x, 0) for x in ("pause", "noise", "lead-in", "tail"))
    removed_bits = [f"{counts[k]} {CLIENT_REASON[k]}{'s' if counts[k] > 1 else ''}" for k in CLIENT_REASON if counts.get(k)]
    removed_bits.append(f"{pauses} pauses/breaths")
    ch = p.get("choices") or {}
    hook = p.get("hook")
    lines = []
    lines.append(f"Your edited video is ready: {exported or 'work/' + p['name'] + '/final.mp4'}")
    lines.append(f"Length: {fmt_t(st['before'])} → {fmt_t(st['video'])} (−{st['before'] - st['video']:.1f}s)")
    lines.append("Removed: " + ", ".join(removed_bits))
    if notable:
        lines.append("Cut moments (original video time):")
        lines += notable
    if hook:
        pos = hook.get("position", "")
        lines.append(f"Text hook: {HOOK_NAMES.get(hook['style'], hook['style'])}, "
                     f"{'on the split line' if pos.startswith('na liniji') else 'above your head' if pos.startswith('iznad') else 'below the captions'}"
                     + (f" — moved there because the chosen spot had no room" if "izabrano" in pos else ""))
    else:
        lines.append("Text hook: none")
    cs = p.get("caption_style", "clean")
    lines.append(f"Captions: {CAPTION_NAMES.get(cs, cs)}"
                 + (f" with your color {p.get('caption_accent')}" if cs == "karaoke" and p.get("caption_accent") else ""))
    lines.append("Camera: " + ("zoom on jump cuts" if p.get("camera") else "static"))
    if p.get("audio"):
        lines.append(f"Audio: cleaned and leveled to {p['audio']['after']['lufs']} LUFS (Instagram/TikTok standard)")
    if (p.get("layout") or {}).get("type") == "split":
        from .project import Job
        from .web import real_visuals
        try:
            rv = real_visuals(Job(p["name"]), p)
        except Exception:  # izveštaj nikad ne sme da padne zbog izvora
            rv = []
        if rv:
            lines.append("Real visuals used (with sources — check you're OK showing them):")
            lines += rv
    lines.append("Want changes? Just tell me — e.g. \"bring back the part at 0:22\", \"make the hook shorter\", "
                 "\"switch captions to Clean\".")
    return "\n".join(lines)
