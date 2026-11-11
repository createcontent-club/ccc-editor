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
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import formats
from .captions import ACCENT_PALETTE, DEFAULT_ACCENT
from .formats import validate  # noqa: F401  (ccc choices koristi picker.validate)
from .fonts import SETS as FONT_SETS, spec as font_spec
from .project import FONTS

PAGE_DIR = Path(__file__).resolve().parent / "picker"
FONT_DIR = FONTS


def run(job, p: dict, timeout: float = 1800, open_browser: bool = True, start_format: str | None = None) -> dict | None:
    result: dict = {}
    done = threading.Event()

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
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self._page("menu.html")
            if path.startswith("/f/"):
                fid = path[3:].strip("/")
                f = formats.BY_ID.get(fid)
                if not f or f["status"] != "ready":
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
            if self.path != "/submit":
                return self._send(404, b"not found", "text/plain")
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                result.update(formats.validate(data))
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
    if open_browser:
        webbrowser.open(url)
    got = done.wait(timeout)
    server.shutdown()
    return dict(result) if got else None
