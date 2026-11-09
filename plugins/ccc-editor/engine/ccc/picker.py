"""Style Picker: lokalna stranica gde klijent bira stilove; skill čeka izbore.

`./ccc picker <ime>` podiže server SAMO na 127.0.0.1 (ništa ne ide na internet), otvara stranicu,
čeka da klijent klikne "Start editing", proveri izbore, upiše ih u project.json["choices"] i završi.
Ako klijent ne izabere u roku (timeout), komanda se završava sa kodom 2 → skill postavlja ista
pitanja u Claude Code-u (rezervni put).
"""
from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .captions import ACCENT_PALETTE, DEFAULT_ACCENT, parse_color
from .project import FONTS

PAGE_DIR = Path(__file__).resolve().parent / "picker"
FONT_DIR = FONTS
HOOK_STYLES = {"box", "serif", "color", "stack"}
CAPTION_STYLES = {"clean", "karaoke", "box", "minimal"}


def validate(d: dict) -> dict:
    """Izbori sa stranice → čisti izbori za engine (ValueError sa porukom za klijenta)."""
    text = (d.get("hook_text") or "").strip()
    hook_style = d.get("hook_style")
    if text and hook_style not in HOOK_STYLES:
        raise ValueError("Please pick a hook style.")
    if len(text) > 160:
        raise ValueError("The hook text is too long — keep it under 160 characters.")
    cap = d.get("caption_style")
    if cap not in CAPTION_STYLES:
        raise ValueError("Please pick a caption style.")
    pos = d.get("hook_position") or "below"
    if pos not in ("below", "above"):
        raise ValueError("Unknown hook position.")
    cam = d.get("camera") or "zoom"
    if cam not in ("zoom", "static"):
        raise ValueError("Unknown camera option.")
    color = None
    if d.get("color"):
        try:
            color = parse_color(d["color"])
        except ValueError:
            raise ValueError("That color isn't valid — use a hex like #FF5A1F.")
    return {"hook_text": text, "hook_style": hook_style if text else None, "hook_position": pos,
            "caption_style": cap, "color": color, "camera": cam}


def run(job, p: dict, timeout: float = 1800, open_browser: bool = True) -> dict | None:
    result: dict = {}
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # tiho
            pass

        def _send(self, code: int, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj: dict, code: int = 200):
            self._send(code, json.dumps(obj).encode(), "application/json")

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self._send(200, (PAGE_DIR / "index.html").read_bytes(), "text/html; charset=utf-8")
            if path == "/logo.png":
                return self._send(200, (PAGE_DIR / "logo.png").read_bytes(), "image/png")
            if path == "/config.json":
                return self._json({"palette": ACCENT_PALETTE, "default_color": p.get("caption_accent") or DEFAULT_ACCENT,
                                   "video": p["name"]})
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
                result.update(validate(data))
            except (ValueError, json.JSONDecodeError) as err:
                return self._json({"ok": False, "error": str(err)})
            self._json({"ok": True})
            done.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Style Picker: {url}", flush=True)
    if open_browser:
        webbrowser.open(url)
    got = done.wait(timeout)
    server.shutdown()
    return dict(result) if got else None
