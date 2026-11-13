"""Split Screen — pravi asseti sa interneta (PLAN.md §12). Claude istražuje (WebSearch/WebFetch), engine preuzima.

Hijerarhija (skill): klijentov fajl → klijentov link → PRAVI asset sa interneta → native rekreacija → pravi brojevi
→ custom animacija → kinetički naslov.

Komande:
  ccc fetch <ime> <url> --for wID [--as ime]       slika / SVG (SVG → PNG u Chrome-u) → assets/web-<ime>.*
  ccc shot  <ime> <url> --for wID [--find "tekst" | --selector css] [--mobile] [--as ime]
                                                   screenshot stranice: cookie baneri zatvoreni, lepljiva zaglavlja
                                                   sklonjena, skrol do teksta; vraća koordinate dela (za fokus/highlight)
  ccc logo  <ime> "<brend>" [--domain x.com]       kandidati za logo (sajt, Wikimedia, Simple Icons) + pregled
  ccc clip  <ime> <url> --for wID --from s --to s  kratak video isečak (yt-dlp), ≤ 20 s
  ccc research <ime>                               research.json (entiteti → asseti) + šta je preuzeto
Svaki preuzeti fajl ima zapis porekla u assets/_sources.json (URL, izvor, vreme, za koju reč) — bez toga se ne koristi.
Natpis izvora se NE prikazuje na ekranu (odluka korisnika); izvori idu samo u izveštaj klijentu.
"""
from __future__ import annotations

import datetime
import glob
import html
import json
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from .assets import adir, nfc
from .project import REMOTION

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
IMG_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg", "image/webp": ".webp", "image/gif": ".gif",
             "image/svg+xml": ".svg", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico", "image/avif": ".avif"}
MAX_BYTES = 40 * 1024 * 1024
SIMPLE_ICONS = "https://cdn.jsdelivr.net/npm/simple-icons@13.21.0/icons/{slug}.svg"
MAX_CLIP = 20.0


# ------------------------------------------------------------------ poreklo
def sources_file(job) -> Path:
    return adir(job) / "_sources.json"


def sources(job) -> dict:
    f = sources_file(job)
    return json.loads(f.read_text()) if f.exists() else {}


def client_links(job) -> list[str]:
    cf = job.dir / "choices.json"
    return (json.loads(cf.read_text()).get("links") or []) if cf.exists() else []


def _from_link(job, url: str) -> str | None:
    """Link klijenta iz kog je fajl došao (ista adresa bez #/utm, ili X objava sa istim ID-jem)."""
    norm = lambda u: re.sub(r"[?#].*$", "", u).rstrip("/").lower().replace("://www.", "://")
    tid = re.search(r"[?&]id=(\d+)|/status/(\d+)", url)
    tid = tid and (tid.group(1) or tid.group(2))
    for u in client_links(job):
        if norm(u) == norm(url) or (tid and re.search(rf"/status/{tid}\b", u)):
            return u
    return None


def _record(job, name: str, url: str, kind: str, for_word: str | None, extra: dict | None = None) -> None:
    s = sources(job)
    link = _from_link(job, url)
    s[nfc(name)] = {**({"client_link": link} if link else {}), "url": url, "source": urllib.parse.urlparse(url).netloc.removeprefix("www.") or "local",
                    "kind": kind, "for": for_word, "retrieved": datetime.datetime.now().isoformat(timespec="seconds"),
                    **(extra or {})}
    sources_file(job).write_text(json.dumps(s, indent=1, ensure_ascii=False))


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50] or "asset"


def _target(job, stem: str, ext: str) -> Path:
    d = adir(job)
    d.mkdir(parents=True, exist_ok=True)
    out, k = d / f"web-{_slug(stem)}{ext}", 2
    while out.exists():
        out, k = d / f"web-{_slug(stem)}-{k}{ext}", k + 1
    return out


# ------------------------------------------------------------------ Chrome (iz Remotion-a) + webshot.mjs
def chrome_path() -> str:
    pats = [str(REMOTION / "node_modules" / ".remotion" / "chrome-headless-shell" / "*" / "*" / n)
            for n in ("chrome-headless-shell", "chrome-headless-shell.exe")]
    for p in pats:
        hits = glob.glob(p)
        if hits:
            return hits[0]
    raise SystemExit("Nema headless Chrome-a (Remotion) — pokreni setup ponovo (bootstrap).")


def _webshot(opts: dict) -> dict:
    node = shutil.which("node") or "node"
    try:
        r = subprocess.run([node, str(Path(__file__).with_name("webshot.mjs")), json.dumps({"chrome": chrome_path(), **opts})],
                           capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "the page took too long (90 s)"}
    line = (r.stdout.strip().splitlines() or ["{}"])[-1]
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return {"ok": False, "error": (r.stderr or "screenshot failed").strip().splitlines()[-1][:200]}


def _svg_to_png(svg: Path, out: Path, width: int = 1200, color: str | None = None) -> None:
    """SVG → PNG sa providnom pozadinom (Chrome crta SVG tačno kao pregledač)."""
    tmp = Path(tempfile.mkdtemp(prefix="ccc-svg-"))
    try:
        src = svg.read_text(errors="ignore")
        if color:  # jednobojni logoi (Simple Icons) — boja da se vidi na pločici
            src = src.replace("<svg ", f'<svg fill="{color}" ', 1)
        (tmp / "logo.svg").write_text(src)
        (tmp / "page.html").write_text(
            f'<html><body style="margin:0;background:transparent"><img src="logo.svg" style="display:block;width:{width // 2}px;'
            f'height:auto;max-height:{width // 2}px;object-fit:contain"></body></html>')
        res = _webshot({"url": (tmp / "page.html").as_uri(), "out": str(out), "svg": True})
        if not res.get("ok"):
            raise SystemExit(f"SVG nije prebačen u PNG: {res.get('error')}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ fetch
def _download(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8", "Accept-Language": "en-US,en"})
    with urllib.request.urlopen(req, timeout=30) as r:
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise SystemExit("Fajl je veći od 40 MB — preskočeno.")
    return data, ctype


def fetch(job, url: str, for_word: str | None, as_name: str | None = None) -> str:
    """Slika / SVG sa interneta → assets/web-*.png|jpg|… (+ poreklo)."""
    if url.startswith("data:"):
        raise SystemExit("Data URL nije podržan — potreban je pravi link na sliku.")
    try:
        data, ctype = _download(url)
    except SystemExit:
        raise
    except Exception as err:  # noqa: BLE001
        raise SystemExit(f"Preuzimanje nije uspelo ({type(err).__name__}: {err}) — probaj drugi izvor.")
    ext = IMG_TYPES.get(ctype) or Path(urllib.parse.urlparse(url).path).suffix.lower()
    if ctype.startswith("text/html") or ext in ("", ".html", ".htm", ".php"):
        raise SystemExit("Ovo je web stranica, ne slika — za stranicu koristi `ccc shot`.")
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico", ".avif"):
        raise SystemExit(f"Nepodržan tip ({ctype or ext}) — potrebna je slika (PNG, JPG, WEBP, SVG).")
    stem = as_name or Path(urllib.parse.urlparse(url).path).stem or "image"
    if ext == ".svg" or data.lstrip()[:5] in (b"<svg ", b"<?xml"):
        tmp = Path(tempfile.mkdtemp(prefix="ccc-")) / "x.svg"
        tmp.write_bytes(data)
        out = _target(job, stem, ".png")
        _svg_to_png(tmp, out)
        shutil.rmtree(tmp.parent, ignore_errors=True)
    elif ext in (".ico", ".avif"):  # Pillow → PNG
        from io import BytesIO

        from PIL import Image
        im = Image.open(BytesIO(data))
        out = _target(job, stem, ".png")
        im.save(out)
    else:
        out = _target(job, stem, ".jpg" if ext == ".jpeg" else ext)
        out.write_bytes(data)
    _record(job, out.name, url, "image", for_word)
    return out.name


def check_url(url: str) -> str:
    """Pun http(s) link; "theverge.com/…" dobija https://. Inače jasna poruka umesto greške iz pregledača."""
    u = (url or "").strip()
    if re.match(r"^(www\.)?[a-z0-9-]+(\.[a-z0-9-]+)+(/\S*)?$", u, re.I):
        u = "https://" + u
    if not re.match(r"^https?://[^\s/]+\.[^\s/]+", u, re.I):
        raise SystemExit(f"Nije link: {url!r} — potreban je pun link (https://…).")
    return u


WALL_HINT = {
    "bot check": "sajt blokira automatske posete (bot/captcha provera)",
    "page not found": "stranica ne postoji (404)",
    "paywall": "članak je iza paywall-a",
    "login wall": "stranica traži prijavu",
    "empty or blocked page": "stranica je prazna ili blokirana",
}


# ------------------------------------------------------------------ shot
def _blank_share(png: Path) -> float:
    """Koliki deo snimka je prazan (jednobojni redovi): prazno mesto za reklamu, beli prostor, neučitana stranica."""
    from PIL import Image, ImageStat
    im = Image.open(png).convert("L")
    im.thumbnail((200, 200))
    w, h = im.size
    flat = sum(1 for y in range(h) if ImageStat.Stat(im.crop((0, y, w, y + 1))).stddev[0] < 4)
    return flat / max(1, h)


def shot(job, url: str, for_word: str | None, find: str | None = None, selector: str | None = None,
         mobile: bool = False, as_name: str | None = None, crop: bool = False, keep: bool = False,
         marks: list[str] | None = None) -> tuple[str, dict]:
    host = urllib.parse.urlparse(url).netloc.removeprefix("www.") or "page"
    out = _target(job, as_name or (host + ("-" + find[:30] if find else "")), ".png")
    res = _webshot({"url": url, "out": str(out), "mobile": mobile, "find": find, "selector": selector, "crop": crop,
                    "marks": marks or []})
    if not res.get("ok"):
        out.unlink(missing_ok=True)
        raise SystemExit(f"Screenshot nije uspeo: {res.get('error') or 'nepoznata greška'} — probaj drugu stranicu ili izvor.")
    wall = res.get("wall")
    if wall and not keep:
        (adir(job) / "_candidates").mkdir(exist_ok=True)
        bad = adir(job) / "_candidates" / (out.stem + "-blocked.png")
        out.replace(bad)  # samo za pregled — van liste asseta, bez porekla
        raise SystemExit(f"Nije sačuvano: {WALL_HINT.get(wall, wall)} ({host}). Pregled: {bad} — ako je slika ipak dobra, "
                         f"ponovi sa --keep; inače drugi izvor (zvanični sajt, druga vest, Wikipedia) ili `news`/`post` kartica.")
    blank = _blank_share(out)
    if blank > 0.5 and not keep and not crop:
        wall = "empty"
        (adir(job) / "_candidates").mkdir(exist_ok=True)
        bad = adir(job) / "_candidates" / (out.stem + "-blocked.png")
        out.replace(bad)
        raise SystemExit(f"Nije sačuvano: {blank:.0%} snimka je prazno (mesto za reklamu, beo prostor ili neučitan sadržaj). "
                         f"Pregled: {bad} — skroluj do sadržaja (--find), probaj --mobile ili drugi izvor; --keep ako je ipak dobro.")
    if crop and not res.get("found"):
        out.unlink(missing_ok=True)
        raise SystemExit(f"Element \"{selector or find}\" nije nađen, pa nema šta da se iseče — proveri link "
                         f"(objava obrisana/privatna?) ili uzmi ceo ekran bez --crop.")
    _record(job, out.name, res.get("url") or url, "screenshot", for_word,
            {"title": res.get("title"), "rect": res.get("rect"), "find": find, "mobile": mobile, "w": res.get("w"), "h": res.get("h"),
             "crop": crop, "marks": [m for m in res.get("marks") or [] if m.get("rect")], "partial": res.get("partial")})
    return out.name, res


# ------------------------------------------------------------------ logo kandidati
def _brand_words(brand: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", brand.lower()) if len(w) > 1 or len(brand.strip()) == 1] or [brand.lower()]


def _site_logo_urls(domain: str, brand: str = "") -> list[tuple[str, str]]:
    base = f"https://{domain.removeprefix('https://').removeprefix('http://').strip('/')}/"
    try:
        req = urllib.request.Request(base, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            page = r.read(2_000_000).decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return []
    out = []
    for tag in re.findall(r"<link[^>]+>", page, re.I):
        rel = (re.search(r'rel=["\']([^"\']+)', tag, re.I) or [None, ""])[1].lower()
        href = (re.search(r'href=["\']([^"\']+)', tag, re.I) or [None, ""])[1]
        if href and ("apple-touch-icon" in rel or "mask-icon" in rel or (rel.strip() in ("icon", "shortcut icon") and ".svg" in href)):
            out.append((urllib.parse.urljoin(base, html.unescape(href)), f"site ({rel})"))
    words = _brand_words(brand) if brand else []
    for tag in re.findall(r"<img[^>]+>", page, re.I):
        # samo slika koja NOSI ime brenda (alt/src) — ne logoi klijenata iz "trusted by" traka
        if re.search(r"logo", tag, re.I) and (not words or any(re.search(rf"\b{re.escape(w)}", tag, re.I) for w in words)):
            src = (re.search(r'src=["\']([^"\']+)', tag, re.I) or [None, ""])[1]
            if src and not src.startswith("data:"):
                out.append((urllib.parse.urljoin(base, html.unescape(src)), "site (logo image)"))
    return out[:4]


def _wikimedia_logo_urls(brand: str) -> list[tuple[str, str]]:
    q = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
                                "gsrsearch": f"{brand} logo", "gsrlimit": 4, "prop": "imageinfo", "iiprop": "url",
                                "iiurlwidth": 1000})
    try:
        req = urllib.request.Request(f"https://commons.wikimedia.org/w/api.php?{q}", headers={"User-Agent": "ccc-editor/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            pages = (json.load(r).get("query") or {}).get("pages") or {}
    except Exception:  # noqa: BLE001
        return []
    out = []
    for pg in sorted(pages.values(), key=lambda x: x.get("index", 99)):
        ii = (pg.get("imageinfo") or [{}])[0]
        url = ii.get("thumburl") or ii.get("url")
        if url:
            out.append((url, f"Wikimedia Commons ({pg.get('title', '')[5:60]})"))
    return out


def logo(job, brand: str, domain: str | None) -> str:
    cands = []
    if domain:
        cands += _site_logo_urls(domain, brand)
    words = _brand_words(brand)
    for url, src in _wikimedia_logo_urls(brand):
        title = src.lower()
        if not any(re.search(rf"(?<![a-z0-9]){re.escape(w)}(?![a-z0-9])", title) for w in words):
            continue  # naslov fajla ne pominje brend (npr. "Logo of Twitter" za X, "Cleveland Notion Co")
        if re.search(r"prohibit|\bban|\bno[ _-]|crossed|parody|fan[ _-]|unofficial|\bold\b|former|histor|retro|\b(19|200|201)\d", title):
            src = "⚠ verovatno nije aktuelni zvanični logo — " + src
        cands.append((url, src))
    cands.append((SIMPLE_ICONS.format(slug=re.sub(r"[^a-z0-9]", "", brand.lower())), "Simple Icons (monochrome, aktuelan znak)"))
    d = adir(job) / "_candidates"
    d.mkdir(parents=True, exist_ok=True)
    from PIL import Image, ImageDraw
    tiles, lines = [], []
    for i, (url, src) in enumerate(cands, 1):
        try:
            data, ctype = _download(url)
            p = d / f"{_slug(brand)}-{i}"
            if (IMG_TYPES.get(ctype) == ".svg") or url.endswith(".svg") or data.lstrip()[:4] == b"<svg":
                (p.with_suffix(".svg")).write_bytes(data)
                _svg_to_png(p.with_suffix(".svg"), p.with_suffix(".png"), 600)
            else:
                from io import BytesIO
                Image.open(BytesIO(data)).save(p.with_suffix(".png"))
            im = Image.open(p.with_suffix(".png")).convert("RGBA")
            tiles.append((i, im, src))
            lines.append(f"{i}. {src} · {im.width}×{im.height} · {url}")
        except Exception:  # noqa: BLE001
            lines.append(f"{i}. {src} · ✗ nije preuzet · {url}")
    if tiles:
        sheet = Image.new("RGB", (260 * len(tiles), 300), (235, 235, 238))
        dr = ImageDraw.Draw(sheet)
        for k, (i, im, src) in enumerate(tiles):
            im.thumbnail((220, 220))
            bg = Image.new("RGB", (240, 240), (255, 255, 255))
            bg.paste((30, 30, 34), (120, 0, 240, 240))  # pola svetlo / pola tamno: vide se i tamni i svetli logoi
            bg.paste(im, ((240 - im.width) // 2, (240 - im.height) // 2), im)
            sheet.paste(bg, (k * 260 + 10, 10))
            dr.text((k * 260 + 14, 262), f"{i}. {src.replace('⚠', '!')[:34]}", fill="black")
        sp = d / f"{_slug(brand)}-candidates.jpg"
        sheet.save(sp, quality=88)
        lines.append(f"pregled: {sp}")
    if not tiles:
        return "\n".join(lines) + (f"\n✗ nema nijednog kandidata za \"{brand}\" — probaj --domain <zvanični sajt>, "
                                    "ili pokaži brend bez logoa (ikonica + ime, ili screenshot sajta)")
    return "\n".join(lines) + ("\n→ izaberi logo TAČNO tog brenda (ne pod-proizvod, npr. Meta ≠ Meta AI), aktuelan "
                                "(uporedi sa zvaničnim sajtom): ccc fetch <ime> <url> --for <wID> --as logo-<brend>")


# ------------------------------------------------------------------ clip (yt-dlp)
class _Quiet:
    """yt-dlp bez ispisa — greške vraćamo kao jednu jasnu poruku."""
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def clip(job, url: str, for_word: str | None, start: float, end: float, as_name: str | None = None) -> str:
    if end <= start:
        raise SystemExit("--to mora biti posle --from")
    if end - start > MAX_CLIP:
        raise SystemExit(f"Isečak najviše {MAX_CLIP:.0f} s — uzmi samo deo o kome se priča.")
    try:
        import yt_dlp
        from yt_dlp.utils import download_range_func
    except ImportError:
        raise SystemExit("yt-dlp nije instaliran — pokreni setup ponovo (bootstrap).")
    from .assets import _ffmpeg
    tmp = Path(tempfile.mkdtemp(prefix="ccc-clip-"))
    opts = {"format": "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/bv*[height<=1080]+ba/b",
            "outtmpl": str(tmp / "clip.%(ext)s"), "quiet": True, "no_warnings": True, "noplaylist": True,
            "download_ranges": download_range_func(None, [(start, end)]), "force_keyframes_at_cuts": True,
            "ffmpeg_location": _ffmpeg(), "merge_output_format": "mp4", "noprogress": True, "logger": _Quiet()}
    def fail(err) -> SystemExit:
        shutil.rmtree(tmp, ignore_errors=True)
        msg = re.sub(r"^ERROR:\s*(\[[^\]]+\]\s*)?", "", str(err).splitlines()[0])[:160]
        return SystemExit(f"Video nije preuzet ({msg}) — probaj drugi izvor ili screenshot.")
    try:  # prvo samo podaci: postoji li video i koliko traje (jasna poruka umesto greške iz ffmpeg-a)
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True, "logger": _Quiet()}) as y:
            meta = y.extract_info(url, download=False)
    except Exception as err:  # noqa: BLE001
        raise fail(err)
    dur = float(meta.get("duration") or 0)
    if meta.get("is_live"):
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit("Ovo je živi prenos — uzmi snimak (VOD) ili screenshot.")
    if dur and start >= dur - 0.3:
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit(f"Video traje samo {dur:.1f} s — --from {start:g} je posle kraja.")
    if dur and end > dur:
        end = dur
        opts["download_ranges"] = download_range_func(None, [(start, end)])
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(url, download=True)
    except Exception as err:  # noqa: BLE001
        shutil.rmtree(tmp, ignore_errors=True)
        msg = re.sub(r"^ERROR:\s*(\[[^\]]+\]\s*)?", "", str(err).splitlines()[0])[:160]
        raise SystemExit(f"Video nije preuzet ({msg}) — probaj drugi izvor ili screenshot.")
    files = sorted(tmp.glob("clip.*"))
    if not files:
        shutil.rmtree(tmp, ignore_errors=True)
        raise SystemExit("Video nije preuzet — probaj drugi izvor ili screenshot.")
    out = _target(job, as_name or (info.get("title") or "clip")[:40], files[0].suffix.lower())
    shutil.move(str(files[0]), out)
    shutil.rmtree(tmp, ignore_errors=True)
    _record(job, out.name, url, "video", for_word, {"title": info.get("title"), "from": start, "to": end,
                                                    "channel": info.get("channel") or info.get("uploader")})
    return out.name


# ------------------------------------------------------------------ research.json
def research_summary(job) -> str:
    f = job.dir / "research.json"
    src = sources(job)
    lines = []
    cf = job.dir / "choices.json"
    ch = json.loads(cf.read_text()) if cf.exists() else {}
    if ch.get("web") is False:
        lines.append("✗ klijent je ISKLJUČIO prave vizuale sa interneta — bez pretrage; samo linkovi koje je dao (ako ih ima), "
                     "njegovi fajlovi i animirani šabloni")
    else:
        lines.append("✓ pravi vizuali sa interneta: uključeno")
    for u in ch.get("links") or []:
        got = [n for n, s in src.items() if s.get("client_link") == u]
        lines.append(f"  link klijenta (nivo 1 — iskoristi ga): {u}" + (f" → {', '.join(got)}" if got else " → još nije preuzet"))
    if f.exists():
        r = json.loads(f.read_text())
        for e in r.get("entities", []):
            st = e.get("status", "?")
            mark = {"found": "✓", "not found": "✗", "skipped": "·"}.get(st, "?")
            lines.append(f"{mark} {e.get('name')} ({e.get('type', '?')}) · reči {', '.join(e.get('words', []))} · "
                         f"želimo: {e.get('want', '?')} · {', '.join(e.get('assets', [])) or st}")
    else:
        lines.append("(nema research.json — napravi ga po uputstvu u skill-u: entiteti iz transkripta → asseti)")
    if src:
        lines.append("preuzeto:")
        for name, s in src.items():
            lines.append(f"  {name} ← {s['source']} ({s['kind']}{', za ' + s['for'] if s.get('for') else ''})")
    return "\n".join(lines)


def _pretty_source(url: str) -> str:
    """Izvor koji klijent može da otvori i razume: Wikimedia thumb → stranica fajla, X embed → objava."""
    u = urllib.parse.urlparse(url)
    host = u.netloc.removeprefix("www.")
    if host.endswith("wikimedia.org"):
        m = re.search(r"/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)", u.path)
        page = f"https://commons.wikimedia.org/wiki/File:{m.group(1)}" if m else url.split("?")[0]
        return f"Wikimedia Commons · {page}"
    if host == "platform.twitter.com":
        tid = urllib.parse.parse_qs(u.query).get("id", [""])[0]
        return f"X · https://x.com/i/status/{tid}" if tid else "X"
    clean = url.split("#")[0]
    if u.query and re.search(r"utm_|fbclid|gclid", u.query):
        clean = clean.split("?")[0]
    return f"{host} · {clean}" if clean else host


def _label(kind: str, d: dict, key: str, s: dict) -> str:
    """Kratak opis pravog vizuala za klijentov izveštaj (engleski)."""
    name = d.get("name") or d.get("label") or ""
    if key == "avatar":
        return f"{d.get('name') or 'author'} profile photo"
    if key == "logo" and kind == "news":
        return f"{d.get('outlet') or 'outlet'} logo"
    if key == "image" and kind == "news":
        return f"article image ({d.get('outlet') or s.get('source')})"
    if kind == "logo" or (key == "file" and d.get("icon") is None and kind == "flow"):
        return f"{name or s.get('source')} logo"
    if kind == "photo":
        return f"photo of {name}" if name else "photo"
    if kind == "post":
        return f"{(d.get('platform') or 'social').capitalize()} post" + (f" by {d['name']}" if d.get("name") else "")
    if kind == "screenshot" and s.get("source") == "platform.twitter.com":
        return "X post"
    if kind == "screenshot":
        return f"screenshot of {(s.get('title') or s.get('source') or '').split(' | ')[0][:60]}"
    if kind == "video":
        return f"video clip: {s.get('title') or s.get('source')}"
    return s.get("title") or kind


def real_visuals(job, p: dict) -> list[str]:
    """Svi pravi vizuali iz plana sa izvorom (iz _sources.json) + izvori brojeva (`source` na stat/chart).
    Na ekranu se izvor nikad ne prikazuje — ide samo u izveštaj."""
    from .review import fmt_t
    from .visuals import _out_time
    src = sources(job)
    wstart = {w["id"]: w["start"] for w in p.get("words", [])}

    def when(wid: str | None) -> str:
        t = _out_time(p, wstart[wid]) if wid in wstart and p.get("segments") else None
        return f"{fmt_t(t)} " if t is not None else ""
    out: list[str] = []
    seen: set[tuple] = set()

    def add(line: str) -> None:
        if line not in seen:
            seen.add(line)
            out.append(line)

    def walk(kind: str, d, at: str | None) -> None:
        if isinstance(d, list):
            for x in d:
                walk(kind, x, at)
            return
        if not isinstance(d, dict):
            return
        for key in ("file", "logo", "image", "avatar"):
            v = d.get(key)
            f = v.get("file") if isinstance(v, dict) else v
            if isinstance(f, str) and nfc(f) in src:
                s = src[nfc(f)]
                add(f"  • {when(d.get('at') if isinstance(d.get('at'), str) else at)}{_label(kind, d, key, s)} — {_pretty_source(s.get('url') or '')}")
        for v in d.values():
            if isinstance(v, (list, dict)):
                walk(kind, v, at)

    for it in (p.get("visuals") or {}).get("items", []):
        d = it.get("data") or {}
        walk(it.get("kind", ""), d, it.get("from"))
        if it.get("kind") in ("stat", "chart") and d.get("source"):
            what = d.get("value") or d.get("label") or it["kind"]
            add(f"  • {when(it.get('from'))}number \"{what}\" — {d['source']}")
    return out
