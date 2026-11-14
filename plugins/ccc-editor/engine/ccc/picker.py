"""CCC Editing Style Menu: lokalna stranica gde klijent bira format pa stil; skill čeka izbore.

`./ccc picker <ime> [--format id]` podiže server SAMO na 127.0.0.1 (ništa ne ide na internet) i otvara:
  /            glavni meni — kartice formata (gotovi + "Coming soon")
  /f/<format>  dashboard formata — samo izbori koje taj format dozvoljava (pravila u formats.py)
Kad klijent klikne "Start editing", izbori se provere (formats.validate) i komanda se završava.
Ako klijent ne izabere u roku (timeout), izlaz je kod 2 → skill postavlja ista pitanja u Claude Code-u.
"""
from __future__ import annotations

import json
import mimetypes
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import formats
from .captions import ACCENT_PALETTE, DEFAULT_ACCENT
from .formats import validate  # noqa: F401  (ccc choices koristi picker.validate)
from .fonts import SETS as FONT_SETS, spec as font_spec
from .project import FONTS, HOME

# Šta je klijent već video na stranicama (vodič) — port je svaki put drugi, pa pregledač ne može da zapamti;
# pamti editor na računaru klijenta (PLAN §14, faza 3).
UI_STATE = HOME / "ui-state.json"
UI_KEYS = {"tour_menu", "tour_format"}


def _ui_state() -> dict:
    try:
        d = json.loads(UI_STATE.read_text())
        return {k: bool(v) for k, v in d.items() if k in UI_KEYS} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}

PAGE_DIR = Path(__file__).resolve().parent / "picker"
FONT_DIR = FONTS
# Klijentovi fajlovi za Split Screen (drop zona): ostaju na računaru, u work/<ime>/assets/.
UPLOAD_EXT = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif", ".gif", ".mp4", ".mov", ".m4v", ".webm"}
MAX_UPLOAD = 2 * 1024 ** 3   # 2 GB po fajlu
MAX_FILES = 40


def safe_name(name: str) -> str:
    stem, dot, ext = Path(name).name.rpartition(".")
    stem = re.sub(r"[^\w. -]+", "", stem if dot else ext).strip(" .-") or "file"  # \w: i slova sa kvačicama
    return f"{stem[:60]}.{ext.lower()}" if dot else stem[:60]


NOT_OPENED_S = 90  # pregledač otvara stranicu odmah; ako je niko ne učita za 90 s, nije se otvorio


def run(job, p: dict, timeout: float = 1800, open_browser: bool = True,
        start_format: str | None = None) -> tuple[dict | None, str]:
    """→ (izbori, "ok") · (None, "timeout") · (None, "not_opened") — pregledač nije učitao stranicu (QA 0.8.0, P1-30)."""
    result: dict = {}
    done = threading.Event()
    seen = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # tiho
            pass

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj: dict, code: int = 200):
            self._send(code, json.dumps(obj).encode(), "application/json")

        def _page(self, name: str):
            self._send(200, (PAGE_DIR / name).read_bytes(), "text/html; charset=utf-8")

        def do_GET(self):
            seen.set()
            path = self.path.split("?", 1)[0]
            if path == "/api/ui":
                return self._json(_ui_state())
            if path == "/api/ping":
                return self._json({"ok": not done.is_set()})
            if path in ("/", "/index.html"):
                return self._page("menu.html")
            if path == "/api/assets":
                d = job.dir / "assets"
                files = sorted(f.name for f in d.iterdir() if f.is_file() and not f.name.startswith((".", "_"))) if d.exists() else []
                cf = job.dir / "choices.json"
                notes = {x.get("file"): x.get("note", "") for x in json.loads(cf.read_text()).get("assets", [])} if cf.exists() else {}
                return self._json({"files": [{"file": n, "size": (d / n).stat().st_size, "note": notes.get(n, "")} for n in files]})
            if path.startswith("/asset/"):  # pregled klijentovog fajla na stranici
                name = urllib.parse.unquote(path[len("/asset/"):])
                if name.startswith(("_", ".")) or "/" in name:
                    return self._send(404, b"not found", "text/plain")
                f = (job.dir / "assets" / name).resolve()
                if f.is_file() and (job.dir / "assets").resolve() in f.parents:
                    return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
                return self._send(404, b"not found", "text/plain")
            if path.startswith("/f/"):
                fid = path[3:].strip("/")
                f = formats.BY_ID.get(fid)
                if not f or (f["status"] != "ready" and not formats.DEV):
                    return self._send(302, b"", "text/plain", {"Location": "/"})
                return self._page("format.html")
            if path == "/logo.png":
                return self._send(200, (PAGE_DIR / "logo.png").read_bytes(), "image/png")
            if path == "/api/menu":
                return self._json({"formats": formats.menu(), "video": p["name"]})
            if path.startswith("/api/format/"):
                fid = path[len("/api/format/"):]
                f = formats.BY_ID.get(fid)
                if not f:
                    return self._json({"error": "unknown format"}, 404)
                return self._json({**f, "fixed": formats.fixed(f), "palette": ACCENT_PALETTE,
                                   "default_color": p.get("caption_accent") or DEFAULT_ACCENT, "video": p["name"],
                                   "fonts": {k: {"name": v["name"], "desc": v["desc"], "spec": font_spec(k)}
                                             for k, v in FONT_SETS.items()}})
            for prefix, base in (("/assets/", PAGE_DIR / "assets"), ("/fonts/", FONT_DIR)):
                if path.startswith(prefix):
                    f = (base / path[len(prefix):]).resolve()
                    if f.is_file() and base.resolve() in f.parents:
                        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                        return self._send(200, f.read_bytes(), ctype)
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            path, _, query = self.path.partition("?")
            if path == "/api/ui":  # {"key": "tour_format", "value": true}
                try:
                    data = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 4096)) or b"{}")
                    if data.get("key") in UI_KEYS:
                        st = _ui_state()
                        st[data["key"]] = bool(data.get("value", True))
                        UI_STATE.parent.mkdir(parents=True, exist_ok=True)
                        UI_STATE.write_text(json.dumps(st))
                except (OSError, ValueError):
                    pass
                return self._json({"ok": True})
            if path == "/upload":  # sirovo telo fajla; ime u ?name=
                name = safe_name(urllib.parse.parse_qs(query).get("name", ["file"])[0])
                size = int(self.headers.get("Content-Length", 0))
                ext = Path(name).suffix.lower()
                d = job.dir / "assets"
                if ext not in UPLOAD_EXT:
                    self.rfile.read(size)
                    return self._json({"ok": False, "error": f"{name}: use images (PNG, JPG, WEBP, HEIC) or videos (MP4, MOV)."})
                if size <= 0:
                    return self._json({"ok": False, "error": f"{name}: this file is empty."})
                if size > MAX_UPLOAD:
                    self.rfile.read(size)
                    return self._json({"ok": False, "error": f"{name}: files up to 2 GB."})
                d.mkdir(parents=True, exist_ok=True)
                if len([f for f in d.iterdir() if f.is_file()]) >= MAX_FILES:
                    self.rfile.read(size)
                    return self._json({"ok": False, "error": f"Up to {MAX_FILES} files per video."})
                out, k = d / name, 2
                while out.exists():
                    out, k = d / f"{Path(name).stem}-{k}{ext}", k + 1
                left = size
                with open(out, "wb") as fh:
                    while left > 0:
                        chunk = self.rfile.read(min(left, 4 * 1024 * 1024))
                        if not chunk:
                            break
                        fh.write(chunk)
                        left -= len(chunk)
                if left:
                    out.unlink(missing_ok=True)
                    return self._json({"ok": False, "error": f"{name}: upload interrupted — try again."})
                return self._json({"ok": True, "file": out.name, "size": size})
            if path == "/upload/delete":
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                f = (job.dir / "assets" / Path(str(data.get("file", ""))).name)
                if f.is_file():
                    f.unlink()
                return self._json({"ok": True})
            if path != "/submit":
                return self._send(404, b"not found", "text/plain")
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                result.update(formats.validate(data))
                if formats.get(data.get("format"))["layout"] == "split":  # fajlovi + napomene klijenta
                    d = job.dir / "assets"
                    result["assets"] = [{"file": Path(str(x.get("file", ""))).name, "note": str(x.get("note") or "")[:300]}
                                        for x in data.get("assets") or [] if (d / Path(str(x.get("file", ""))).name).is_file()]
            except (ValueError, json.JSONDecodeError) as err:
                return self._json({"ok": False, "error": str(err)})
            self._json({"ok": True})
            done.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    if start_format:
        url += f"f/{formats.get(start_format)['id']}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Style Menu: {url}", flush=True)
    opened = webbrowser.open(url) if open_browser else True
    if open_browser and (not opened or not seen.wait(NOT_OPENED_S)):
        server.shutdown()
        return None, "not_opened"
    got = done.wait(max(0.0, timeout - (NOT_OPENED_S if open_browser else 0)))
    server.shutdown()
    return (dict(result), "ok") if got else (None, "timeout")
