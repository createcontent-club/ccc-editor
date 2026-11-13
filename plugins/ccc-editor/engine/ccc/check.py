"""Automatska provera isečenog videa pre predaje (kriterijumi faze 1).

Sve se meri GLASOM (Voice: Silero + jak zvuk + suglasnici) — istom definicijom kojom se seče.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

from .energy import HOP, Voice
from .media import decode_mono


def _frame(path: Path, t: float, zoom: tuple[float, float, float] | None = None,
           crop: tuple[int, int] | None = None) -> np.ndarray:
    vf = "scale=96:170"
    if crop:  # (y, visina) na 1080×1920 — Split Screen: deo kadra sa govornikom
        vf = f"scale=1080:1920,crop=1080:{crop[1]}:0:{crop[0]},scale=96:{max(2, round(170 * crop[1] / 1920))}"
    if zoom:  # isti zum kao u Remotion-u: skala s oko tačke (ox, oy) na 1080×1920
        s, ox, oy = zoom
        vf = (f"scale=1080:1920,crop={1080 / s:.2f}:{1920 / s:.2f}:{ox - ox / s:.2f}:{oy - oy / s:.2f},"
              "scale=96:170")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).astype(np.float32)


def _runs(mask: np.ndarray, value: bool) -> list[tuple[int, int]]:
    out, k, n = [], 0, len(mask)
    while k < n:
        if mask[k] == value:
            j = k
            while j < n and mask[j] == value:
                j += 1
            out.append((k, j))
            k = j
        else:
            k += 1
    return out


def run_checks(job, p: dict, rendered: Path | None) -> list[tuple[bool, str]]:
    res: list[tuple[bool, str]] = []
    segs, fps, cfg = p["segments"], p["fps"], p["cut"]
    frame = 1 / fps
    src_v = Voice(decode_mono(job.dir / "source-audio.wav"))
    out_v = Voice(decode_mono(job.public / "voice.wav"), floor=src_v.floor)

    def kept(t: float) -> bool:
        return any(g["srcStart"] <= t <= g["srcEnd"] for g in segs)

    # 1. Glas zadržanih reči nije isečen, i nijedna zadržana reč nije ostala bez glasa.
    removed = {w for r in p["removed"] for w in r["words"]}
    clipped, silent = [], []
    # Izolovano ostrvo glasa kraće od MIN_PIECE (klik usana) rez namerno ne zadržava — nije isečen slog.
    from .cut import MIN_PIECE
    blips = [(s, e) for s, e in src_v.runs if e - s < MIN_PIECE]

    def blip(k: int) -> bool:
        t = k * HOP + HOP / 2
        return any(s <= t < e for s, e in blips)

    for w in p["words"]:
        if w["id"] in removed:
            continue
        ks = range(int(w["start"] / HOP), int(w["end"] / HOP) + 1)
        voiced = [k for k in ks if src_v.speech(k) and not blip(k)]
        if not voiced:
            silent.append(f"{w['id']} '{w['text']}'")
        elif any(not kept(k * HOP + HOP / 2) for k in voiced):
            k = next(k for k in voiced if not kept(k * HOP + HOP / 2))
            clipped.append(f"{w['id']} '{w['text']}' @{k * HOP:.2f}s")
    res.append((not clipped, f"isečen glas u zadržanim rečima: {len(clipped)}"
                + (f" → {', '.join(clipped[:5])}" if clipped else "")))
    res.append((not silent, f"zadržane reči bez detektovanog glasa (moguće isečene): {len(silent)}"
                + (f" → {', '.join(silent[:6])}" if silent else "")))

    # 2. Početak i kraj: video kreće na prvom slogu i završava se na poslednjem.
    vm = out_v.mask
    first = int(np.argmax(vm)) * HOP
    # Silero na samom početku fajla nema kontekst i kasni (~40–70 ms na mekom "Th"): meri se na IZVORU — koliko
    # posle početka prvog segmenta kreće prvi glas (test ai-actor-0: lažno "70 ms" dok je izvor kretao na 10 ms).
    s0 = segs[0]["srcStart"]
    k0 = int(s0 / HOP)
    while k0 * HOP < segs[0]["srcEnd"] and not src_v.speech(k0):
        k0 += 1
    first = min(first, max(0.0, k0 * HOP - s0))
    last_end = (len(vm) - int(np.argmax(vm[::-1]))) * HOP
    total = sum(g["vFrames"] for g in segs) / fps
    tail = total - last_end
    res.append((first <= frame, f"početak: glas kreće na {first * 1000:.0f} ms (≤ 1 frejm = {frame * 1000:.0f} ms)"))
    res.append((tail <= frame, f"kraj: posle poslednjeg sloga {max(0, tail) * 1000:.0f} ms (≤ 1 frejm)"))

    # 3. Rupe bez glasa u gotovom zvuku (pauze, uzdasi) — dozvoljeno najviše ~1 frejm.
    gaps = [(a * HOP, (b - a) * HOP) for a, b in _runs(vm, False) if a > 0 and b < len(vm)]
    limit = cfg["max_gap"] + cfg["pre"] + cfg["post"] + HOP
    long_gaps = [(t, d) for t, d in gaps if d > limit]
    def out_to_src(t: float) -> float:
        acc = 0.0
        for s in segs:
            ln = s["srcEnd"] - s["srcStart"]
            if t < acc + ln:
                return s["srcStart"] + t - acc
            acc += ln
        return segs[-1]["srcEnd"]

    kept_words = [w for w in p["words"] if w["id"] not in removed]
    # Rupa u kojoj IZVOR ima glas (kratak suglasnik zadržan u reči — 'd' u "doesn't") nije pauza: Silero ga na
    # isečenom zvuku često ne prepozna jer je kraći od svog prozora (test ai-actor-0).
    def src_voiced(t: float, d: float) -> bool:
        k = t
        while k < t + d:
            if src_v.speech(int(out_to_src(k) / HOP)):
                return True
            k += HOP
        return False
    long_gaps = [(t, d) for t, d in long_gaps if not src_voiced(t, d)]

    def in_word(t: float, d: float) -> bool:  # zatvaranje suglasnika ("bu-t", "re-cursive") nije uzdah
        a, b = out_to_src(t), out_to_src(t + d - 1e-3)
        return b - a < d + 1e-3 and any(w["start"] <= a and b <= w["end"] for w in kept_words)

    # Uzdah = bar 50 ms zvuka iznad +8 dB (u odnosu na pod izvora) u rupi bez glasa, između reči.
    # Gotov zvuk je pojačan (kompresor + -14 LUFS), pa se nivo vraća na skalu izvora — inače bi tiha
    # soba u pauzi (pacing) izgledala kao dah.
    gain = max(0.0, float(np.median(out_v.rel[out_v.mask]) - np.median(src_v.rel[src_v.mask]))) \
        if out_v.mask.any() and src_v.mask.any() else 0.0
    def bump(t: float, d: float) -> int:
        """Frejmovi iznad +8 dB koji NISU rep prethodne reči (zvuk koji samo opada) ni početak sledeće (zvuk koji
        samo raste ka reči — 'F' u "Fourth"): dah je zaseban talas između njih (aazar-trial-1: rupa od 60 ms
        između "it." i "Fourth" je ranije bila "uzdah")."""
        r = out_v.rel[int(t / HOP):int((t + d) / HOP)] - gain
        a, b = 0, len(r)
        # Samo zvuk koji STVARNO opada/raste (> 0.5 dB po frejmu) — ravan dah odmah posle reči nije rep.
        while a + 1 < b and r[a + 1] < r[a] - 0.5:
            a += 1
        while b - 1 > a and r[b - 2] < r[b - 1] - 0.5:
            b -= 1
        return int((r[a:b] > 8).sum()) if b - a > 1 else 0
    breaths = [(t, d) for t, d in gaps if bump(t, d) >= 5 and not in_word(t, d)]
    g = np.array([d for _, d in gaps]) * fps if gaps else np.array([0.0])
    res.append((not long_gaps, f"rupe bez glasa > {limit * 1000:.0f} ms: {len(long_gaps)}"
                + (" → " + ", ".join(f"{t:.2f}s ({d * 1000:.0f} ms)" for t, d in long_gaps[:6]) if long_gaps else "")
                + f" · sve rupe: prosek {g.mean():.2f}, max {g.max():.2f} frejma"))
    res.append((not breaths, f"uzdasi/dah u gotovom zvuku: {len(breaths)}"
                + (" → " + ", ".join(f"{t:.2f}s" for t, _ in breaths[:6]) if breaths else "")))

    # 3b. Titlovi: nijedan trenutak glasa bez titla, poslednji titl traje do kraja videa.
    caps = p.get("captions") or []
    from .render import captions_from
    cap_from = captions_from(p)  # Split Screen: dok traje hook, titl namerno nije na ekranu
    if caps:
        uncovered = []
        for k0, k1 in _runs(vm, True):
            for k in range(k0, k1):
                t = k * HOP + HOP / 2
                if t < cap_from:
                    continue
                if not any(c["start"] <= t < c["end"] for c in caps):
                    uncovered.append(t)
        spans = []
        for t in uncovered:
            if spans and t - spans[-1][1] <= 0.02:
                spans[-1][1] = t
            else:
                spans.append([t, t])
        spans = [(a, b) for a, b in spans if b - a >= 0.02]
        res.append((not spans, f"glas bez titla: {len(spans)}"
                    + (" → " + ", ".join(f"{a:.2f}–{b:.2f}s" for a, b in spans[:6]) if spans else "")))
        gap_end = total - caps[-1]["end"]
        res.append((abs(gap_end) < frame / 2, f"poslednji titl traje do kraja videa (razlika {gap_end * 1000:.0f} ms)"))

    # 3b2. Boja naglaska (Karaoke) mora biti dovoljno svetla da se aktivna reč čita.
    if p.get("caption_style") == "karaoke":
        from .captions import DEFAULT_ACCENT, MIN_ACCENT_LUMINANCE, luminance
        acc = p.get("caption_accent") or DEFAULT_ACCENT
        lum = luminance(acc)
        res.append((lum >= MIN_ACCENT_LUMINANCE,
                    f"boja naglaska {acc}: osvetljenost {lum:.2f} (≥ {MIN_ACCENT_LUMINANCE}"
                    + ("" if lum >= MIN_ACCENT_LUMINANCE else " — pretamna, predloži klijentu svetliju nijansu") + ")"))

    # 3c. Hook: staje u kadar i UI zone, ne preklapa se sa titlom i ne prekriva lice.
    hook = p.get("hook")
    if hook:
        from .captions import half_h
        from .hook import SAFE_BOTTOM, SAFE_TOP, box_widths
        widest = max(box_widths(hook))
        from .captions import to_output_y
        f0 = p.get("face", {})
        face = {k: round(to_output_y(p, f0[k])) for k in ("head_top", "chin") if k in f0}  # na ekranu
        cap_top, cap_bottom = p["captionY"] - half_h(p), p["captionY"] + half_h(p)
        clear_caption = (hook["y"] >= cap_bottom or hook["bottom"] <= cap_top
                         or cap_from >= hook["end"])  # Split: titl kreće tek posle hooka
        clear_face = hook["y"] >= face.get("chin", 0) or hook["bottom"] <= face.get("head_top", 0)
        in_frame = widest <= 960 and hook["y"] >= SAFE_TOP and hook["bottom"] <= SAFE_BOTTOM
        cap_ok = hook["text"][:1] == hook["text"][:1].upper()
        if hook.get("bg"):
            from .hook import LARGE_TEXT_CONTRAST, contrast
            cr = contrast(hook["bg"], hook["fg"])
            res.append((cr >= LARGE_TEXT_CONTRAST, f"hook boja: boks {hook['bg']} / tekst {hook['fg']}, "
                                                   f"kontrast {cr:.1f}:1 (≥ {LARGE_TEXT_CONTRAST} WCAG, krupan tekst)"))
        res.append((clear_caption and clear_face and in_frame and cap_ok,
                    f"hook {hook.get('style', 'box')} ({hook.get('position')}): y {hook['y']}–{hook['bottom']}, titl {cap_top}–{cap_bottom}, "
                    f"lice {face.get('head_top')}–{face.get('chin')}, najširi boks {widest:.0f} px, "
                    f"veliko početno slovo: {'da' if cap_ok else 'NE'}, do {hook['end']:.2f}s"))

    # 3c2. Split Screen: govornik u donjoj polovini, teme ispod linije (titl/hook), lice ceo u kadru.
    lay = p.get("layout") or {}
    if lay.get("type") == "split" and p.get("face"):
        from .captions import to_output_y
        top, chin = to_output_y(p, p["face"]["head_top"]), to_output_y(p, p["face"]["chin"])
        ok = top >= lay["line"] + 40 and chin <= 1920 - 120
        res.append((ok, f"split: linija {lay['line']}, isečak od y {lay.get('cropY')}, teme {top:.0f} (≥ {lay['line'] + 40}), "
                        f"brada {chin:.0f} (≤ 1800)"))

    # 3c3. Split Screen, gornja polovina: plan pokriva ceo video, momenti nisu prekratki, fajlovi postoje.
    if lay.get("type") == "split":
        from .visuals import timeline, validate_plan, warnings
        items, problems = timeline(p)
        problems = validate_plan(p.get("visuals") or {}, job) + problems if p.get("visuals") else ["nema plana"]
        cover = bool(items) and items[0]["start"] == 0 and abs(items[-1]["end"] - total) < frame
        res.append((not problems and cover,
                    f"gornja polovina: {len(items)} momenata, pokriveno 0–{items[-1]['end'] if items else 0:.2f}s od {total:.2f}s"
                    + ("" if not problems else " → " + "; ".join(problems[:4]))))
        from .story import story_warnings
        from .visuals import severity
        for w in warnings(items):
            print(f"  · [{severity(w)}] {w}")
        for w in story_warnings(job, p, items):
            print(f"  · [aim] {w}")
        # Klijentovi fajlovi: svaki je iskorišćen ili prijavljen (skill kaže klijentu koji nije i zašto).
        from .assets import nfc, originals, prepare
        from .web import _from_link, sources
        allf = [nfc(f.name) for f in originals(job)]
        web = [n for n in allf if n.startswith("web-")]
        names = [n for n in allf if not n.startswith("web-")]
        used = set(re.findall(r'"(?:file|logo|image)": "([^"]+)"', json.dumps([x.get("data") or {} for x in items], ensure_ascii=False)))
        used = {nfc(u) for u in used}
        if web:  # pravi asseti sa interneta: svaki iskorišćen mora imati zapis porekla (izvor za izveštaj klijentu)
            src = sources(job)
            no_src = [n for n in web if n in used and n not in src]
            ch = p.get("choices") or {}
            # klijent isključio prave vizuale → sme samo ono što je došlo iz njegovih linkova
            off = [n for n in web if n in used and ch.get("web") is False and not (src.get(n) or {}).get("client_link")
                   and not _from_link(job, (src.get(n) or {}).get("url") or "")]
            res.append((not no_src and not off, f"asseti sa interneta: iskorišćeno {len([n for n in web if n in used])}/{len(web)}"
                                    + (f" · bez zapisa porekla: {', '.join(no_src)}" if no_src else "")
                                    + (f" · klijent je isključio prave vizuale, a iskorišćeno: {', '.join(off)}" if off else "")))
        if names:
            man = prepare(job)
            unused = [n for n in names if n not in used]
            bad = [n for n in names if man.get(n, {}).get("kind") == "error"]
            res.append((True, f"fajlovi klijenta: iskorišćeno {len(names) - len(unused)}/{len(names)}"
                              + (f" · neiskorišćeni (reci klijentu zašto): {', '.join(unused)}" if unused else "")
                              + (f" · ne mogu da se koriste: {', '.join(bad)}" if bad else "")))

    # 3d. Kamera: ni pri najvećem zumu brada ne dolazi do titla, a teme do hooka iznad glave.
    if p.get("camera") and p.get("face"):
        from .camera import max_chin_after_zoom, min_head_after_zoom
        from .captions import half_h
        chin = max_chin_after_zoom(p)
        cap_top = p["captionY"] - half_h(p)
        ok = chin < cap_top
        msg = f"kamera: brada pri najvećem zumu {chin:.0f} < vrh titla {cap_top}"
        if hook and hook.get("position", "").startswith("iznad glave"):
            head = min_head_after_zoom(p)
            ok = ok and hook["bottom"] < head
            msg += f", hook dno {hook['bottom']} < teme {head:.0f}"
        res.append((ok, msg))
        from .camera import hidden_jumps
        missed = hidden_jumps(job, p)
        fps_ = p["fps"]
        starts, f_ = {}, 0
        for i_, g_ in enumerate(segs):
            starts[i_] = f_ / fps_
            f_ += g_["vFrames"]
        res.append((not missed, f"vidljivi skokovi bez promene kadra: {len(missed)}"
                    + (" → " + ", ".join(f"{starts[m['seg']]:.1f}s (skok {m['jump']})" for m in missed[:6]) if missed else "")))

    # 3e. Audio fix: glasnoća za IG/TikTok/Shorts, vrh, klipovanje.
    if p.get("audio"):
        from .audio import TARGET_LUFS, TARGET_TP, loudness
        lm = loudness(job.public / "voice.wav")
        pcm_ = subprocess.run(["ffmpeg", "-v", "error", "-i", str(job.public / "voice.wav"), "-f", "f32le", "-"],
                              capture_output=True, check=True).stdout
        clipped = int((np.abs(np.frombuffer(pcm_, np.float32)) >= 0.999).sum())
        ok = abs(lm["lufs"] - TARGET_LUFS) <= 0.5 and lm["tp"] <= TARGET_TP + 0.05 and clipped == 0
        res.append((ok, f"zvuk: {lm['lufs']} LUFS (cilj {TARGET_LUFS} ±0.5), vrh {lm['tp']} dBTP (≤ {TARGET_TP}), "
                        f"klipovanih uzoraka {clipped}"))

    # 4. Klikovi na rezovima.
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(job.public / "voice.wav"), "-ac", "1", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, dtype=np.float32)
    d = np.abs(np.diff(x))
    typical = float(np.percentile(d, 99.9))
    at, worst = 0.0, 0.0
    for s in segs[:-1]:
        at += s["srcEnd"] - s["srcStart"]
        i = int(at * 48000)
        worst = max(worst, float(d[max(0, i - 48):i + 48].max()))
    res.append((worst <= typical, f"klikovi na rezovima: najveći skok {worst:.4f} (govor p99.9 = {typical:.4f})"))

    # 5. Sinhronizacija: na početku svakog segmenta slika i zvuk se razlikuju ≤ pola frejma.
    acc, prev_f, worst_sync = 0.0, 0, 0.0
    for s in segs:
        audio_src_at_cut = s["srcStart"] + (prev_f / fps - acc)  # izvorno vreme zvuka kad krene slika segmenta
        worst_sync = max(worst_sync, abs(s["vFrom"] / fps - audio_src_at_cut))
        acc += s["srcEnd"] - s["srcStart"]
        prev_f += s["vFrames"]
    res.append((worst_sync <= frame / 2 + 1e-3 and abs(total - p["stats"]["voice"]) < 1e-3,
                f"sinhronizacija: najveće odstupanje slike od zvuka {worst_sync * 1000:.0f} ms (≤ {frame * 500:.0f} ms), "
                f"slika {total:.3f}s / zvuk {p['stats']['voice']:.3f}s"))

    # 6. Pravi frejmovi na pravom mestu (render vs. izvor, sredina 3 segmenta).
    if rendered and rendered.exists():
        src = job.public / "video.mp4"
        diffs, out_f = [], 0
        # Uzorci posle kraja hooka: kutije hooka same pređu prag razlike, pa je kod kratkih videa sa hookom provera
        # padala bez greške (QA 0.8.0, P0). Kandidati = segmenti koji počinju posle hooka, raspoređeni kroz video.
        hook_end = float((p.get("hook") or {}).get("end") or 0.0)
        starts, ff = [], 0
        for s_ in segs:
            starts.append(ff / fps)
            ff += s_["vFrames"]
        cand = [k for k, s_ in enumerate(segs) if s_["vFrames"] >= 2 and starts[k] >= hook_end + 0.1]
        picks = {cand[len(cand) // 4], cand[len(cand) // 2], cand[-1]} if cand else set()
        for k, s in enumerate(segs):
            if k in picks and s["vFrames"] >= 2:
                mid = s["vFrames"] // 2
                cue = next((c for c in p.get("camera") or [] if c["seg"] == k), None)
                zoom = None
                if cue:
                    sc = cue["from"] + (cue["to"] - cue["from"]) * mid / max(1, s["vFrames"])
                    zoom = (sc, cue["ox"], cue["oy"])
                lay = p.get("layout") or {}
                if lay.get("type") == "split":  # donja polovina gotovog videa = isečak izvora od cropY
                    h = 1920 - lay["line"]
                    out_c, src_c = (lay["line"], h), (lay.get("cropY", 0), h)
                else:
                    out_c = src_c = None
                diffs.append(float(np.abs(_frame(rendered, (out_f + mid + 0.5) / fps, crop=out_c)
                                          - _frame(src, (s["vFrom"] + mid + 0.5) / fps, zoom, crop=src_c)).mean()))
            out_f += s["vFrames"]
        if diffs:
            res.append((max(diffs) < 8, f"frejmovi odgovaraju izvoru: razlika {', '.join(f'{v:.1f}' for v in diffs)} (< 8)"))
        else:
            res.append((True, "frejmovi odgovaraju izvoru: video je kraći od hooka — nema kadra za poređenje"))

        # 7. Izvozni fajl se pušta normalno svuda: ≤ 60 fps i trajanje = trajanje zvuka.
        # (aazar-trial-1: Split Screen 2× od snimka od 60 fps = izvoz od 120 fps → telefoni/QuickTime ga puštaju
        # usporeno, pa je 2-minutni video izgledao kao 6 minuta. Nijedna provera to nije uhvatila.)
        from .media import probe
        info = probe(rendered)
        res.append((info["fps"] <= 60.5 and not info["vfr"],
                    f"fps izvoza: {info['fps']:g} (≤ 60, stalan{'' if not info['vfr'] else ' — NIJE stalan'})"))
        res.append((abs(info["duration"] - p["stats"]["voice"]) <= 0.1,
                    f"trajanje izvoza: {info['duration']:.2f}s / zvuk {p['stats']['voice']:.2f}s (razlika ≤ 0.1s)"))
    return res
