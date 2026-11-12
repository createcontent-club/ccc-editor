"""CCC engine — komande:

  ./ccc doctor [--quick]             provera instalacije (alati, fontovi, modeli, Remotion)
  ./ccc name <video>                 ime projekta za ovaj snimak (bezbedno: mala slova, cifre, crtice)
  ./ccc prepare <video>              prijem + normalizacija + transkripcija + automatski rezovi
  ./ccc transcript <ime>             rečenice sa ID-jevima reči (za odluke o retake-ovima)
  ./ccc remove <ime> w12-w20 <razlog>  izbaci reči (retake | false-start | off-script | filler | …)
  ./ccc keep <ime> w30-w31           vrati reči (poništava automatsko ili ručno izbacivanje)
  ./ccc cut <ime>                    ponovo izračunaj rezove (posle izmena podešavanja)
  ./ccc review <ime>                 pregled rezova za stajanje #1
  ./ccc render <ime> [--final]       preview (540×960) ili final (1080×1920)
  ./ccc check <ime>                  automatska provera (reči, pauze, klikovi, sinhronizacija, frejmovi)
  ./ccc previews <ime>               primeri svih stilova za Style Picker (jednom, iz agencijskog snimka)
  ./ccc picker <ime> [--format F]    otvori CCC Editing Style Menu (format → stil), sačekaj izbore → work/<ime>/choices.json
                                     (radi i dok priprema još traje; kod 2 = klijent nije izabrao u roku)
  ./ccc choices <ime> k=v …          upiši/izmeni izbore bez stranice (format, hook_text, hook_style, hook_position,
                                     caption_style, color, camera; Split: top_style, web=on|off, links="url url")
                                     — rezervni put i izmene posle isporuke
  ./ccc formats                      formati u meniju i šta svaki preuzima iz Basic-a (pravila u engine/ccc/formats.py)
  ./ccc build <ime>                  izbori → titlovi, kamera, hook, zvuk, final render, provera, izvoz, izveštaj
  ./ccc report <ime>                 izveštaj za klijenta (engleski)
  ./ccc word <ime> wID "tekst"       ispravi tekst reči u titlu (npr. ime brenda) — tajming i rezovi ostaju
  ./ccc keys <ime>                   glavne reči po titlu (Minimal stil)
  ./ccc key <ime> <br. titla> <reč>  ručno postavi glavnu reč titla (Minimal)
  ./ccc approve <ime> <korak>        zabeleži odobrenje: cut | captions | hook | camera | audio | final
  ./ccc captions <ime> [--style S] [--color C]
                                     titlovi: clean (Stil 1) | karaoke (Stil 2, C = boja naglaska) | box (Stil 3) | minimal (Stil 4)
  ./ccc retime <ime>                 tačnija vremena reči oko brojeva/simbola (bez ponovne transkripcije i rezova)
  ./ccc hook <ime> "tekst" [--style S] [--color C]
                                     text hook: box (Stil 1) | serif (Stil 2) | color (Stil 3) | stack (Stil 4, deli se sa "|"); C = boja brenda;
                                     --position below (ispod titla) | above (iznad glave)
  ./ccc camera <ime> [--off]         pokreti kamere: punch-in na rezovima + spor push-in, centar na licu
  ./ccc audio <ime> [--off]          audio fix: izmeri → šum/de-esser/kompresor → -14 LUFS; A/B fajlovi u work/<ime>/ab/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .audio import loudness
from .project import DEFAULT_CUT, PACING, SPLIT_LINE, Job


def _recut(job: Job, p: dict) -> dict:
    from . import cut
    from .audio import finalize_voice, loudness
    from .energy import Voice
    from .media import decode_mono

    src_audio = job.dir / "source-audio.wav"
    # Podešavanja = trenutni CCC standard; projekat može da prepiše pojedina polja kroz "cut_override".
    p["cut"] = {**DEFAULT_CUT, **PACING.get(p.get("pacing") or "fast", {}), **p.get("cut_override", {})}
    voice = Voice(decode_mono(src_audio))
    removed = cut.resolve(p["words"], p["utterances"], p["decisions"])
    p["segments"], p["removed"] = cut.compute(p["words"], p["utterances"], removed, voice, p["fps"], p["cut"])
    after = sum(s["srcEnd"] - s["srcStart"] for s in p["segments"])
    video_dur = sum(s["vFrames"] for s in p["segments"]) / p["fps"]
    finalize_voice(job, p)  # sa audio fix-om: obrađen izvor + -14 LUFS; bez njega: sirov isečen zvuk
    voice_dur = float(__import__("subprocess").run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(job.public / "voice.wav")],
        capture_output=True, text=True).stdout.strip())
    p["stats"] = {"before": round(p["source"]["duration"], 2), "after": round(after, 3),
                  "video": round(video_dur, 3), "voice": round(voice_dur, 3)}
    p["approved"]["cut"] = False
    job.save(p)
    return p


def _build(job: Job, name: str) -> None:
    """Izbori klijenta → gotov video. Svaki korak je ista komanda koju bi pokrenuo i ručno."""
    from .check import run_checks
    from .review import client_report

    f = job.dir / "choices.json"
    p = job.load()
    choices = json.loads(f.read_text()) if f.exists() else p.get("choices")
    if not choices:
        raise SystemExit("Nema izbora klijenta (work/<ime>/choices.json) — pokreni ./ccc picker ili postavi pitanja.")
    from .formats import get as get_format
    choices.setdefault("format", "basic")  # projekti pre menija formata = Basic
    fmt = get_format(choices["format"])
    from .formats import DEV
    if fmt["status"] != "ready" and not DEV:
        raise SystemExit(f"Format {fmt['id']} još nije spreman (status {fmt['status']}).")
    p["choices"] = choices
    p["font"] = choices.get("font") or "ccc"  # set fontova: titlovi + hook (meri ga i hook, i render)
    p["pacing"] = choices.get("pacing") or "fast"
    if fmt.get("layout") == "split":  # 50/50: sadržaj gore, govornik dole (crop računa korak Titlovi)
        p["layout"] = {"type": "split", "line": SPLIT_LINE, **{k: v for k, v in (p.get("layout") or {}).items()
                                                              if k == "cropY"}}
    else:
        p.pop("layout", None)
    job.save(p)
    from .fonts import get as get_font
    print(f"▶ Format: {fmt['title']} · font: {get_font(p['font'])['name']} · pacing: {p['pacing']}")
    print("▶ Rezovi (pacing)"); main(["cut", name])
    color, cs, hs = choices.get("color"), choices["caption_style"], choices.get("hook_style")

    print("▶ Titlovi"); main(["captions", name, "--style", cs] + (["--color", color] if color and cs == "karaoke" else []))
    print("▶ Kamera"); main(["camera", name] + ([] if choices.get("camera", "zoom") == "zoom" else ["--off"]))
    print("▶ Hook")
    if choices.get("hook_text") and hs:
        main(["hook", name, choices["hook_text"], "--style", hs, "--position", choices.get("hook_position", "below")]
             + (["--color", color] if color and hs in ("color", "stack") else []))
    else:
        main(["hook", name, ""])
    print("▶ Zvuk"); main(["audio", name])
    print("▶ Render"); main(["render", name, "--final"])

    p = job.load()
    print("▶ Provera")
    res = run_checks(job, p, job.dir / "final.mp4")
    for ok, msg in res:
        print(f"  {'✅' if ok else '❌'} {msg}")
    if not all(ok for ok, _ in res):
        print("! Provera nije prošla — ispravi pa ponovo ./ccc build (video NIJE izvezen).")
        sys.exit(1)

    src = Path(p["source"]["path"])
    dest = src.with_name(f"{src.stem}-CCC-edit.mp4")
    try:
        shutil.copy(job.dir / "final.mp4", dest)
        p["exported"] = str(dest)
    except OSError:
        p["exported"] = str(job.dir / "final.mp4")
    job.save(p)
    print("\n" + client_report(p, p["exported"]))


def _range(spec: str) -> tuple[str, str]:
    a, _, b = spec.partition("-")
    return a, (b or a)


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(prog="ccc", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("prepare"); sp.add_argument("video"); sp.add_argument("--name")
    sub.add_parser("name").add_argument("video")
    sub.add_parser("doctor").add_argument("--quick", action="store_true")
    sub.add_parser("formats")
    for c in ("transcript", "cut", "review", "check", "retime", "previews", "build", "report", "keys"):
        sub.add_parser(c).add_argument("name")
    sr = sub.add_parser("remove"); sr.add_argument("name"); sr.add_argument("words"); sr.add_argument("reason")
    sk = sub.add_parser("keep"); sk.add_argument("name"); sk.add_argument("words")
    sn = sub.add_parser("render"); sn.add_argument("name"); sn.add_argument("--final", action="store_true")
    su = sub.add_parser("audio"); su.add_argument("name"); su.add_argument("--off", action="store_true")
    sc = sub.add_parser("camera"); sc.add_argument("name"); sc.add_argument("--off", action="store_true")
    sp_c = sub.add_parser("captions"); sp_c.add_argument("name")
    sp_c.add_argument("--style", choices=["clean", "karaoke", "box", "minimal"], help="stil titla (podrazumevano: dosadašnji ili clean)")
    sp_c.add_argument("--color", help="boja naglaska za Karaoke: hex (#FF5A1F) ili naziv (yellow, green, blue…)")
    sh = sub.add_parser("hook"); sh.add_argument("name"); sh.add_argument("text", nargs="?", default="")
    sh.add_argument("--style", choices=["box", "serif", "color", "stack"], help="stil hooka (podrazumevano: dosadašnji ili box)")
    sh.add_argument("--color", help="boja brenda za Stil 3/4 (hex ili naziv); podrazumevano: boja brenda iz titlova")
    sh.add_argument("--position", choices=["below", "above", "line"],
                    help="below = ispod titla (podrazumevano), above = iznad glave, line = linija podele (Split Screen)")
    spk = sub.add_parser("picker"); spk.add_argument("name")
    spk.add_argument("--timeout", type=float, default=1800, help="sekunde čekanja na izbor (podrazumevano 30 min)")
    spk.add_argument("--no-open", action="store_true", help="ne otvaraj pregledač (samo ispiši adresu)")
    spk.add_argument("--format", help="otvori direktno dashboard ovog formata (npr. basic), bez glavnog menija")
    sq = sub.add_parser("choices"); sq.add_argument("name"); sq.add_argument("pairs", nargs="*")
    sv = sub.add_parser("visuals"); sv.add_argument("name"); sv.add_argument("--set", dest="plan")
    # Pravi asseti sa interneta (Split Screen, PLAN §12) — engine/ccc/web.py
    sf = sub.add_parser("fetch"); sf.add_argument("name"); sf.add_argument("url"); sf.add_argument("--for", dest="for_word")
    sf.add_argument("--as", dest="as_name")
    ss = sub.add_parser("shot"); ss.add_argument("name"); ss.add_argument("url"); ss.add_argument("--for", dest="for_word")
    ss.add_argument("--find"); ss.add_argument("--selector"); ss.add_argument("--mobile", action="store_true")
    ss.add_argument("--crop", action="store_true", help="samo traženi element (npr. objava), ne ceo ekran")
    ss.add_argument("--as", dest="as_name")
    ss.add_argument("--keep", action="store_true", help="sačuvaj i kad engine misli da je zid (pogledao si sliku i dobra je)")
    sl = sub.add_parser("logo"); sl.add_argument("name"); sl.add_argument("brand"); sl.add_argument("--domain")
    sc2 = sub.add_parser("clip"); sc2.add_argument("name"); sc2.add_argument("url"); sc2.add_argument("--for", dest="for_word")
    sc2.add_argument("--from", dest="t_from", type=float, required=True); sc2.add_argument("--to", dest="t_to", type=float, required=True)
    sc2.add_argument("--as", dest="as_name")
    sub.add_parser("research").add_argument("name")
    sa2 = sub.add_parser("assets"); sa2.add_argument("name"); sa2.add_argument("--add", dest="add_file")
    sa2.add_argument("--note", default="")
    sw = sub.add_parser("word"); sw.add_argument("name"); sw.add_argument("id"); sw.add_argument("text")
    sy = sub.add_parser("key"); sy.add_argument("name"); sy.add_argument("index", type=int); sy.add_argument("word")
    sa = sub.add_parser("approve"); sa.add_argument("name"); sa.add_argument("gate", choices=["cut", "captions", "hook", "camera", "audio", "final"])
    a = ap.parse_args(argv)

    if a.cmd == "doctor":
        import subprocess
        from .project import CODE
        r = subprocess.run([sys.executable, str(CODE / "tools" / "doctor.py")] + (["--quick"] if a.quick else []))
        sys.exit(r.returncode)

    if a.cmd == "formats":
        from . import formats as F
        for f in F.FORMATS:
            print(f"{f['id']:14s} {f['status']:6s} {f['title']}")
            if f["status"] == "ready" or f["elements"] != F.fmt("x", "", "")["elements"]:
                for el, rules in f["elements"].items():
                    print(f"    iz Basic-a: {el:9s} " + ", ".join(f"{k}={v}" for k, v in rules.items()))
                for el in set(F.BASIC) - set(f["elements"]):
                    print(f"    iz Basic-a: {el:9s} — NE KORISTI SE")
            for o in f["own"]:
                print(f"    sopstveno:  {o}")
        return

    if a.cmd == "name":
        from .project import slug
        print(slug(Path(a.video).stem))
        return

    if a.cmd == "picker":  # ne zavisi od pripreme — izbori idu u zaseban fajl
        from .picker import run as run_picker
        job = Job(a.name)
        p = job.load() if job.exists else {"name": a.name}
        choices = run_picker(job, p, a.timeout, not a.no_open, a.format)
        if choices is None:
            print("! Klijent nije izabrao stil u roku — postavi pitanja u Claude Code-u.")
            sys.exit(2)
        job.dir.mkdir(parents=True, exist_ok=True)
        (job.dir / "choices.json").write_text(json.dumps(choices, indent=1, ensure_ascii=False))
        print("✓ izbori: " + json.dumps(choices, ensure_ascii=False))
        return

    if a.cmd in ("fetch", "shot", "logo", "clip", "research"):  # pravi asseti sa interneta (engine/ccc/web.py)
        from . import web
        job = Job(a.name)
        cf = job.dir / "choices.json"
        if a.cmd in ("fetch", "shot", "clip"):
            a.url = web.check_url(a.url)
        if a.cmd != "research" and cf.exists() and json.loads(cf.read_text()).get("web") is False \
                and not (a.cmd != "logo" and web._from_link(job, a.url)):
            raise SystemExit("Klijent je isključio prave vizuale sa interneta (dashboard) — dozvoljeni su samo njegovi linkovi "
                             f"({', '.join(web.client_links(job)) or 'nema ih'}). Koristi animirane šablone ili njegove fajlove.")
        if a.cmd == "fetch":
            print(f"✓ preuzeto: {web.fetch(job, a.url, a.for_word, a.as_name)}")
        elif a.cmd == "shot":
            name, res = web.shot(job, a.url, a.for_word, a.find, a.selector, a.mobile, a.as_name, a.crop, a.keep)
            r = res.get("rect")
            print(f"✓ screenshot: {name} · {res.get('w')}×{res.get('h')} · \"{(res.get('title') or '')[:70]}\""
                  + (f" · deo \"{a.find or a.selector}\": x {r['x']} y {r['y']} w {r['w']} h {r['h']} (za focus/highlight)" if r else "")
                  + ("" if res.get("found") else f" · ⚠ \"{a.find or a.selector}\" nije nađen na stranici"))
        elif a.cmd == "logo":
            print(web.logo(job, a.brand, a.domain))
        elif a.cmd == "clip":
            print(f"✓ isečak: {web.clip(job, a.url, a.for_word, a.t_from, a.t_to, a.as_name)}")
        else:
            print(web.research_summary(job))
        return

    if a.cmd == "assets":  # Split Screen: klijentovi fajlovi — priprema + pregled za Claude-a (engine/ccc/assets.py)
        from .assets import add, describe, prepare
        job = Job(a.name)
        if a.add_file:
            print(f"✓ dodat fajl: {add(job, Path(a.add_file).expanduser(), a.note)}")
        cf = job.dir / "choices.json"
        notes = {x["file"]: x.get("note", "") for x in json.loads(cf.read_text()).get("assets", [])} if cf.exists() else {}
        print(describe(prepare(job, notes)))
        return

    if a.cmd == "choices":  # ne zavisi od pripreme
        from .picker import validate
        job = Job(a.name)
        f = job.dir / "choices.json"
        cur = json.loads(f.read_text()) if f.exists() else {}
        new_fmt = next((kv.partition("=")[2].strip() for kv in a.pairs if kv.startswith("format=")), None)
        if new_fmt and new_fmt != cur.get("format", "basic"):  # drugi format = njegova pravila; tekst i boja ostaju
            cur = {k: cur[k] for k in ("hook_text", "color") if k in cur}
        for kv in a.pairs:
            k, sep, v = kv.partition("=")
            if not sep:
                raise SystemExit(f"Očekujem ključ=vrednost, dobio: {kv}")
            cur[k.strip()] = v.strip() or None
        try:
            clean = validate(cur)
        except ValueError as err:
            raise SystemExit(str(err))
        if cur.get("assets") and clean.get("top_style"):  # Split Screen: klijentovi fajlovi + napomene ostaju
            clean["assets"] = cur["assets"]
        job.dir.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(clean, indent=1, ensure_ascii=False))
        print("✓ izbori: " + json.dumps(clean, ensure_ascii=False))
        return

    if a.cmd == "prepare":
        from .media import normalize, probe
        from .transcribe import transcribe
        src = Path(a.video).expanduser().resolve()
        from .project import slug
        job = Job(a.name or slug(src.stem))
        info = probe(src)
        if not info["has_audio"]:
            raise SystemExit("Snimak nema zvuk — nema šta da se transkribuje.")
        if info["width"] > info["height"]:
            print("! Horizontalan snimak — reframe u 9:16 još ne postoji, render će biti horizontalan.")
        print(f"▶ Prijem: {info['width']}×{info['height']}, {info['fps']} fps, {info['duration']:.1f}s, {info['codec']}")
        job.dir.mkdir(parents=True, exist_ok=True)
        norm = normalize(src, info, job.public / "video.mp4", job.dir / "source-audio.wav")
        print(f"  {'re-enkodovano (CFR)' if norm['reencoded'] else 'video kopiran bez gubitka'} → {norm['fps']} fps")
        print("▶ Transkripcija (Whisper, deo po deo)…")
        tr = transcribe(job.dir / "source-audio.wav", DEFAULT_CUT["utterance_gap"])
        print(f"  {len(tr['utterances'])} izgovorenih delova, {len(tr['words'])} reči za {tr['seconds']}s")
        p = {
            "version": 1, "name": job.name, "source": {"path": str(src), **info}, "fps": norm["fps"],
            "media": {"video": job.public_rel("video.mp4"), "voice": job.public_rel("voice.wav")},
            "language": tr["language"], "words": tr["words"], "utterances": tr["utterances"],
            "cut": dict(DEFAULT_CUT), "decisions": [], "approved": {"cut": False},
        }
        p = _recut(job, p)
        print(f"▶ Automatski rezovi: {p['stats']['before']}s → {p['stats']['after']}s")
        print(f"  Projekat: {job.file}")
        return

    job = Job(a.name)
    p = job.load()
    if a.cmd == "transcript":
        from .review import transcript
        print(transcript(p))
    elif a.cmd in ("remove", "keep"):
        frm, to = _range(a.words)
        ids = {w["id"] for w in p["words"]}
        if frm not in ids or to not in ids:
            raise SystemExit(f"Nepoznat ID reči: {a.words}")
        d = {"from": frm, "to": to, "action": a.cmd}
        if a.cmd == "remove":
            d["reason"] = a.reason
        p["decisions"].append(d)
        p = _recut(job, p)
        print(f"✓ {a.cmd} {frm}–{to} · trajanje {p['stats']['after']}s")
    elif a.cmd == "cut":
        p = _recut(job, p)
        print(f"✓ {p['stats']['before']}s → {p['stats']['after']}s, {len(p['segments'])} segmenata")
    elif a.cmd == "review":
        from .review import cut_review
        text = cut_review(p)
        (job.dir / "review.md").write_text(text)
        print(text)
    elif a.cmd == "retime":
        from .transcribe import retime_numbers
        changed = retime_numbers(job.dir / "source-audio.wav", p["words"], p["utterances"])
        job.save(p)
        print(f"✓ novi tajming za: {', '.join(changed) or 'ništa'} — pokreni ./ccc captions")
    elif a.cmd == "captions":
        from .captions import build, caption_y
        from .energy import Voice
        from .media import decode_mono
        voice = Voice(decode_mono(job.dir / "source-audio.wav"))
        p["caption_style"] = a.style or p.get("caption_style") or "clean"
        if a.color:
            from .captions import parse_color
            try:
                p["caption_accent"] = parse_color(a.color)
            except ValueError as err:
                raise SystemExit(str(err))
        p["captions"] = build(p, voice.runs, p["caption_style"])
        p["captionY"], face = caption_y(job, p)
        if face.get("faces"):
            p["face"] = face
        if (p.get("layout") or {}).get("type") == "split":
            from .captions import split_place
            split_place(p)
        if p.get("hook"):  # rezovi/lice su se možda promenili → hook ponovo
            from .hook import build as build_hook
            p["hook"] = build_hook(p, p["hook"]["text"], p["hook"].get("style", "box"), p["hook"].get("bg"),
                                   p["hook"].get("placement", "below"))
        job.save(p)
        accent = f" · naglasak {p.get('caption_accent') or 'podrazumevani'}" if p["caption_style"] == "karaoke" else ""
        print(f"✓ {len(p['captions'])} titlova ({p['caption_style']}{accent}) · y={p['captionY']} · lice: {face}")
        for c in p["captions"][:12]:
            print(f"  {c['start']:6.2f}–{c['end']:6.2f}  {c['text']}")
    elif a.cmd == "audio":
        from .audio import ab_files, after_profile, finalize_voice, fix_source, speech_mask
        if a.off:
            p["audio"] = None
            finalize_voice(job, p)
            job.save(p)
            print("✓ audio fix isključen (sirov isečen zvuk)")
        else:
            src_mask = speech_mask(job.dir / "source-audio.wav")
            p["audio"] = fix_source(job, p, src_mask)
            finalize_voice(job, p)
            from .energy import Voice
            from .media import decode_mono
            floor = Voice(decode_mono(job.dir / "source-audio.wav")).floor
            p["audio"]["after_profile"] = after_profile(job, speech_mask(job.public / "voice.wav", floor))
            before, after = ab_files(job, p)
            job.save(p)
            au, b0, b1 = p["audio"], p["audio"]["before"], p["audio"]["after_profile"]
            print(f"✓ audio fix ({au['tier']}):")
            for w in au["why"]:
                print(f"  · {w}")
            print(f"  glasnoća: {loudness(job.dir / 'source-audio.wav')['lufs']} → {au['after']['lufs']} LUFS, "
                  f"vrh {au['after']['tp']} dBTP (pojačanje {au['after']['gain_db']} dB)")
            print(f"  šištanje {b0['sibilance']}% → {b1['sibilance']}% · vazduh >9 kHz {b0['air']}% → {b1['air']}% · "
                  f"šum {b0['noise']} → {b1['noise']} dBFS")
            print(f"  A/B: {before}\n       {after}")
    elif a.cmd == "camera":
        from .camera import build as build_camera, summary
        p["camera"] = [] if a.off else build_camera(job, p)
        if p.get("hook"):
            from .hook import build as build_hook
            p["hook"] = build_hook(p, p["hook"]["text"], p["hook"].get("style", "box"), p["hook"].get("bg"),
                                   p["hook"].get("placement", "below"))
        job.save(p)
        print("✓ kamera isključena" if a.off else f"✓ kamera: {summary(p['camera'])}")
    elif a.cmd == "hook":
        if not a.text.strip():
            p["hook"] = None
            job.save(p)
            print("✓ hook uklonjen")
        else:
            if not p.get("face") or "head_top" not in p["face"] or "captionY" not in p:
                raise SystemExit("Prvo pokreni ./ccc captions (hook se postavlja u odnosu na titl i lice).")
            from .hook import box_widths, build as build_hook
            prev = p.get("hook") or {}
            color = None
            if a.color:
                from .captions import parse_color
                try:
                    color = parse_color(a.color)
                except ValueError as err:
                    raise SystemExit(str(err))
            p["hook"] = build_hook(p, a.text.strip(), a.style or prev.get("style") or "box", color or prev.get("bg"),
                                   a.position or prev.get("placement") or "below")
            job.save(p)
            h = p["hook"]
            colors = f", boks {h['bg']} / tekst {h['fg']}" if h.get("bg") else ""
            print(f"✓ hook ({h['style']}{colors}): {len(h['lines'])} reda, {h['position']}, y {h['y']}–{h['bottom']}, traje 0–{h['end']:.2f}s")
            for line, w in zip(h["lines"], box_widths(h)):
                print(f"  [{line}]  {w:.0f} px")
            if not h["fits"]:
                print(f"! Hook ima {len(h['lines'])} reda i ne staje ni ispod titla ni iznad glave — treba kraći tekst.")
    elif a.cmd == "build":
        _build(job, a.name)
    elif a.cmd == "report":
        from .review import client_report
        print(client_report(p, p.get("exported")))
    elif a.cmd == "word":
        w = next((w for w in p["words"] if w["id"] == a.id), None)
        if not w:
            raise SystemExit(f"Nepoznat ID reči: {a.id}")
        old, w["text"] = w["text"], a.text.strip()
        for u in p["utterances"]:  # i tekst izgovorenog dela, da transkript bude tačan
            if u.get("from") and w["u"] == int(u["id"][1:]):
                u["text"] = " ".join(x["text"] for x in p["words"] if x["u"] == w["u"])
        job.save(p)
        print(f"✓ {a.id}: '{old}' → '{w['text']}'")
        if p.get("captions"):
            main(["captions", a.name])
    elif a.cmd == "keys":
        for i, c in enumerate(p.get("captions") or [], 1):
            ws = [w["text"] for w in c.get("wt", [])]
            k = c.get("key", 0)
            print(f"{i:3d} [{c['start']:5.1f}s] " + " ".join(w.upper() if j == k else w for j, w in enumerate(ws)))
    elif a.cmd == "key":
        caps = p.get("captions") or []
        if not 1 <= a.index <= len(caps):
            raise SystemExit(f"Titl {a.index} ne postoji (ima ih {len(caps)}).")
        c = caps[a.index - 1]
        if a.word.lower() not in [w["text"].lower() for w in c.get("wt", [])]:
            raise SystemExit(f"Reč '{a.word}' nije u titlu: {c['text']}")
        p.setdefault("key_overrides", {})[c["words"][0]] = a.word
        job.save(p)
        main(["captions", a.name])
    elif a.cmd == "visuals":  # Split Screen: plan gornje polovine (engine/ccc/visuals.py)
        from .visuals import describe, save_plan
        if a.plan:
            save_plan(job, p, Path(a.plan))
            job.save(p)
            print("✓ plan gornje polovine sačuvan")
        print(describe(p) or "(nema plana — gornja polovina je prazna)")
    elif a.cmd == "previews":
        from .energy import Voice
        from .media import decode_mono
        from .previews import build as build_previews
        voice = Voice(decode_mono(job.dir / "source-audio.wav"))
        made = build_previews(job, p, voice.runs)
        print(f"✓ {len(made)} primera stilova u engine/ccc/picker/assets/")
    elif a.cmd == "approve":
        import datetime
        p["approved"][a.gate] = datetime.datetime.now().isoformat(timespec="seconds")
        job.save(p)
        print(f"✓ odobreno: {a.gate} ({p['approved'][a.gate]})")
    elif a.cmd == "check":
        from .check import run_checks
        out = job.dir / "final.mp4"
        out = out if out.exists() else job.dir / "preview.mp4"
        res = run_checks(job, p, out)
        for ok, msg in res:
            print(f"  {'✅' if ok else '❌'} {msg}")
        if not all(ok for ok, _ in res):
            sys.exit(1)
    elif a.cmd == "render":
        from .render import render
        out, secs = render(job, p, preview=not a.final)
        print(f"✓ {out} ({secs:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1:])
