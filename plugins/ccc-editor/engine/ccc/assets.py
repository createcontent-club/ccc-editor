"""Split Screen — klijentovi fajlovi za gornju polovinu (drop zona na dashboardu ili `ccc assets --add`).

Fajlovi ostaju na računaru: work/<ime>/assets/<original>. `ccc assets <ime>` ih priprema za render i za Claude-a:
  _ready/    slike: ispravljena rotacija (EXIF), najviše 2000 px, JPG/PNG; video/GIF: H.264 MP4 bez zvuka, ≤ 1280 px,
             + poslednji kadar (JPG) za "zamrzavanje" kad je klip kraći od momenta
  _preview/  pregled za Claude-a: slika (sličica) ili 4 kadra iz videa sa vremenima — Claude ih pogleda (Read) i
             postavi svaki fajl na rečenicu o kojoj klijent govori
  _manifest.json  vrsta, dimenzije, trajanje, napomena klijenta, greška (ako fajl ne može da se koristi)
Keš po veličini + vremenu izmene: ponovno pokretanje obrađuje samo nove fajlove.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".gif"}
MAX_IMG = 2000
MAX_VID_W = 1280
LOW_RES = 500  # px (duža strana): ispod ovoga fajl je mali na ekranu


def nfc(name: str) -> str:
    """Isti oblik imena svuda (macOS čuva č/ć/í… rastavljeno — NFD; Claude i JSON pišu NFC)."""
    return unicodedata.normalize("NFC", name)


def uid(name: str) -> str:
    """Bezbedno ASCII ime za interne kopije (render, pregled) — bez problema sa slovima i razmacima."""
    return hashlib.sha1(nfc(name).encode()).hexdigest()[:12]


def adir(job) -> Path:
    return job.dir / "assets"


def originals(job) -> list[Path]:
    d = adir(job)
    if not d.exists():
        return []
    return sorted(f for f in d.iterdir() if f.is_file() and not f.name.startswith((".", "_")))


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return "ffmpeg"


def _probe(f: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:stream_tags=rotate:format=duration", "-of", "json", str(f)],
                       capture_output=True, text=True)
    try:
        j = json.loads(r.stdout or "{}")
        st = (j.get("streams") or [{}])[0]
        return {"w": int(st.get("width") or 0), "h": int(st.get("height") or 0),
                "duration": float((j.get("format") or {}).get("duration") or 0)}
    except (ValueError, TypeError):
        return {"w": 0, "h": 0, "duration": 0.0}


def _open_image(f: Path) -> Image.Image:
    if f.suffix.lower() in (".heic", ".heif"):
        try:
            import pillow_heif  # type: ignore
            pillow_heif.register_heif_opener()
        except ImportError:
            if sys.platform == "darwin":  # macOS ume HEIC bez dodatnih paketa
                tmp = f.with_name(f".{f.stem}-heic.jpg")
                subprocess.run(["sips", "-s", "format", "jpeg", str(f), "--out", str(tmp)], capture_output=True)
                if tmp.exists():
                    im = Image.open(tmp)
                    im.load()
                    tmp.unlink()
                    return im
            raise ValueError("HEIC photo — please export it as JPG or PNG")
    im = Image.open(f)
    im.load()
    return im


def _image(f: Path, ready: Path, preview: Path, u: str) -> dict:
    im = ImageOps.exif_transpose(_open_image(f))  # fotografije sa telefona: prava rotacija
    alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if alpha else "RGB")
    im.thumbnail((MAX_IMG, MAX_IMG))
    if not alpha and "logo" in f.stem.lower():  # logo na beloj podlozi → bela podloga postaje providna (pločica, ne beo kvadrat)
        cut = _knock_out_white(im)
        if cut is not None:
            im, alpha = cut, True
    out = ready / (u + (".png" if alpha else ".jpg"))
    im.save(out, **({} if alpha else {"quality": 90}))
    th = im.convert("RGB")
    th.thumbnail((640, 640))
    th.save(preview / (u + ".jpg"), quality=85)
    return {"kind": "image", "ready": out.name, "w": im.width, "h": im.height, **_edge(im), **_logo_tone(im),
            **_face(out)}


def _knock_out_white(im: Image.Image):
    """Bela (skoro bela) podloga koja dodiruje ivice → providna. Samo kad je ivica slike skoro sva bela."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    border = [px[x, y] for x in range(0, w, max(1, w // 60)) for y in (0, h - 1)] + \
             [px[x, y] for y in range(0, h, max(1, h // 60)) for x in (0, w - 1)]
    white = sum(1 for c in border if min(c) >= 232)
    if white < 0.9 * len(border):
        return None
    from PIL import ImageDraw
    rgba = rgb.convert("RGBA")
    marker = (255, 0, 255, 0)
    for xy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if min(rgba.getpixel(xy)[:3]) >= 232:
            ImageDraw.floodfill(rgba, xy, marker, thresh=40)
    data = [(0, 0, 0, 0) if c == marker else c for c in rgba.getdata()]
    rgba.putdata(data)
    return rgba


def _face(img: Path) -> dict:
    """Lice na fotografiji (osoba) → kamera ide ka njemu i nikad ga ne iseče. Zaseban proces (OpenCV, kao ccc.face)."""
    import os
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([sys.executable, "-m", "ccc.face", "--image", str(img)], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(root)}, timeout=60)
    try:
        f = json.loads((r.stdout.strip().splitlines() or ["null"])[-1])
    except json.JSONDecodeError:
        f = None
    return {"face": f} if f else {}


def _edge(im: Image.Image) -> dict:
    """Boja ivice slike i da li je jednobojna (screenshot telefona, beo sajt) → podloga gornje polovine u toj boji,
    da se slika stopi u celinu i može da se naglasi bilo koji deo bez vidljivih ivica. Dovoljne su 3 od 4 strane
    iste boje (sajtovi često imaju tamno zaglavlje gore)."""
    rgb = im.convert("RGB")
    rgb.thumbnail((400, 400))
    w, h = rgb.size
    px = rgb.load()
    b = max(2, min(w, h) // 60)
    sides = {
        "top": [px[x, y] for x in range(w) for y in range(b)],
        "bottom": [px[x, y] for x in range(w) for y in range(h - b, h)],
        "left": [px[x, y] for y in range(h) for x in range(b)],
        "right": [px[x, y] for y in range(h) for x in range(w - b, w)],
    }
    allpx = [c for v in sides.values() for c in v]
    med = tuple(sorted(c[i] for c in allpx)[len(allpx) // 2] for i in range(3))
    close = lambda c: sum(abs(c[i] - med[i]) for i in range(3)) <= 36  # noqa: E731
    good = [k for k, v in sides.items() if sum(1 for c in v if close(c)) / max(1, len(v)) >= 0.9]
    return {"edge": "#%02X%02X%02X" % med, "edgeUniform": len(good) >= 3, "edgeSides": good}


def _logo_tone(im: Image.Image) -> dict:
    """Taman logo (crn/tamnosiv na providnom) → na tamnoj neon pločici se prikazuje beo, da se vidi."""
    if im.mode != "RGBA":
        return {}
    small = im.copy()
    small.thumbnail((200, 200))
    vals = [(r * 0.2126 + g * 0.7152 + b * 0.0722) / 255 for r, g, b, a in small.getdata() if a > 128]
    if not vals:
        return {}
    return {"dark": sum(vals) / len(vals) < 0.3}


def _video(f: Path, ready: Path, preview: Path, u: str) -> dict:
    info = _probe(f)
    if not info["w"] or info["duration"] <= 0:
        raise ValueError("can't read this video — try exporting it again as MP4")
    out = ready / (u + ".mp4")
    r = subprocess.run([_ffmpeg(), "-v", "error", "-y", "-i", str(f), "-an", "-vf",
                        f"scale='min({MAX_VID_W},iw)':-2:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                        "-preset", "veryfast", "-movflags", "+faststart", str(out)], capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        raise ValueError("can't convert this video — try exporting it again as MP4")
    info = _probe(out)
    last = ready / (u + "-last.jpg")
    subprocess.run([_ffmpeg(), "-v", "error", "-y", "-sseof", "-0.1", "-i", str(out), "-frames:v", "1", "-q:v", "3", str(last)],
                   capture_output=True)
    # Pregled: 4 kadra sa vremenom, da Claude vidi šta se dešava u klipu.
    frames = []
    for k in range(4):
        t = info["duration"] * (k + 0.5) / 4
        fr = preview / f".{u}-{k}.jpg"
        subprocess.run([_ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(out), "-frames:v", "1",
                        "-vf", "scale=320:-2", str(fr)], capture_output=True)
        if fr.exists():
            frames.append((t, Image.open(fr).convert("RGB")))
            fr.unlink()
    if frames:
        h = max(im.height for _, im in frames)
        sheet = Image.new("RGB", (330 * len(frames), h + 34), "white")
        dr = ImageDraw.Draw(sheet)
        for k, (t, im) in enumerate(frames):
            sheet.paste(im, (k * 330, 0))
            dr.text((k * 330 + 6, h + 8), f"{t:.1f}s", fill="black")
        sheet.save(preview / (u + ".jpg"), quality=85)
    return {"kind": "video", "ready": out.name, "last": last.name if last.exists() else None,
            "w": info["w"], "h": info["h"], "duration": round(info["duration"], 2)}


def prepare(job, notes: dict | None = None) -> dict:
    """Pripremi sve fajlove (keš) → manifest {ime: {...}}."""
    d = adir(job)
    ready, preview = d / "_ready", d / "_preview"
    man_f = d / "_manifest.json"
    man = json.loads(man_f.read_text()) if man_f.exists() else {}
    names = {nfc(f.name) for f in originals(job)}
    man = {k: v for k, v in man.items() if k in names}
    if not names:
        return {}
    ready.mkdir(parents=True, exist_ok=True)
    preview.mkdir(parents=True, exist_ok=True)
    for f in originals(job):
        key = [f.stat().st_size, int(f.stat().st_mtime)]
        name, u = nfc(f.name), uid(f.name)
        if man.get(name, {}).get("key") == key:
            continue
        ext = f.suffix.lower()
        try:
            if ext in IMAGE_EXT:
                info = _image(f, ready, preview, u)
            elif ext in VIDEO_EXT:
                info = _video(f, ready, preview, u)
            else:
                raise ValueError("unsupported file type")
            info["preview"] = str(preview / (u + ".jpg"))
        except Exception as err:  # noqa: BLE001 — svaki problem sa fajlom se prijavljuje klijentu, ne ruši edit
            info = {"kind": "error", "error": str(err) if isinstance(err, ValueError) else "can't open this file"}
        info["key"] = key
        man[name] = info
    for name, note in (notes or {}).items():
        if nfc(name) in man:
            man[nfc(name)]["note"] = note
    man_f.write_text(json.dumps(man, indent=1, ensure_ascii=False))
    return man


def shape(w: int, h: int) -> str:
    if not w or not h:
        return ""
    r = w / h
    return "vertical" if r < 0.8 else "horizontal" if r > 1.25 else "square"


def describe(man: dict) -> str:
    if not man:
        return "(nema klijentovih fajlova)"
    lines = []
    for i, (name, m) in enumerate(man.items(), 1):
        if m["kind"] == "error":
            lines.append(f"{i:2d}. {name} · ✗ {m['error']}")
            continue
        dims = f"{m['w']}×{m['h']} ({shape(m['w'], m['h'])})"
        if max(m["w"], m["h"]) < LOW_RES:
            dims += f" · ⚠ niska rezolucija — biće mala na ekranu (ne razvlači se više od 2×); ako je bitna, traži veću"
        dur = f" · {m['duration']:.1f}s" if m["kind"] == "video" else ""
        note = f" · napomena: \"{m['note']}\"" if m.get("note") else ""
        lines.append(f"{i:2d}. {name} · {m['kind']} {dims}{dur}{note}\n     pregled: {m.get('preview')}")
    return "\n".join(lines)


def add(job, src: Path, note: str = "") -> str:
    """Fajl iz četa (npr. izmena posle isporuke) → assets/ + choices.json."""
    from .picker import UPLOAD_EXT, safe_name
    if src.suffix.lower() not in UPLOAD_EXT:
        raise SystemExit(f"{src.name}: use images (PNG, JPG, WEBP, HEIC) or videos (MP4, MOV).")
    d = adir(job)
    d.mkdir(parents=True, exist_ok=True)
    name = safe_name(src.name)
    out, k = d / name, 2
    while out.exists():
        out, k = d / f"{Path(name).stem}-{k}{Path(name).suffix}", k + 1
    shutil.copy2(src, out)
    cf = job.dir / "choices.json"
    if cf.exists():
        ch = json.loads(cf.read_text())
        ch.setdefault("assets", []).append({"file": out.name, "note": note})
        cf.write_text(json.dumps(ch, indent=1, ensure_ascii=False))
    return out.name
