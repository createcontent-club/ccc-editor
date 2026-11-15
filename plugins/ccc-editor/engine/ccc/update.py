"""Da li klijent ima najnoviji CCC Editor — i ako nema, ažuriraj ga (Petar 15.11.).

Zašto: Claude desktop aplikacija postavlja DISABLE_AUTOUPDATER=1, a to po dokumentaciji (plugins/loading.md) gasi i
automatsko ažuriranje pluginova; inače radi samo u interaktivnoj sesiji, posle prve poruke, sa čekanjem do 10 min.
Test 15.11.: instaliran 0.9.0 dok je objavljen 0.20.0. Zato engine sam proverava i ažurira.

- check(): verzija ovog koda (plugin.json) naspram one na GitHub-u (marketplace.json, javni raw fajl). Pita mrežu najviše
  jednom u 6 h (keš u <HOME>/update-check.json), 4 s rok; bez mreže → "skipped", izmena nikad ne staje zbog ovoga.
  Ako je novija verzija već preuzeta u keš pluginova (folder pored ovog koda) → "ready" (treba samo restart).
- apply(): zvanične komande `claude plugin marketplace update` + `claude plugin update`. `claude` se traži na PATH-u,
  u uobičajenim folderima i u Claude desktop aplikaciji (tamo je ugrađen). Sesija koja radi zadržava svoju verziju
  (installed.json se menja tek kad setup prođe iz novog foldera, u sledećoj sesiji), pa izmena ide dalje bez prekida.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from .project import CODE, HOME

MARKETPLACE = "createcontent-club"
PLUGIN = "ccc-editor"
LATEST_URL = "https://raw.githubusercontent.com/createcontent-club/ccc-editor/main/.claude-plugin/marketplace.json"
TTL = 6 * 3600
CACHE = HOME / "update-check.json"


def _v(x: str) -> tuple:
    try:
        return tuple(int(p) for p in str(x).strip().split("."))
    except ValueError:
        return (0,)


def installed_version() -> str | None:
    pj = CODE / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(pj.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError):
        return None  # razvojni folder: nema plugin.json


def _fetch_latest() -> str | None:
    req = urllib.request.Request(LATEST_URL, headers={"User-Agent": "ccc-editor-update-check", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=4) as r:
        data = json.loads(r.read().decode("utf-8"))
    for p in data.get("plugins", []):
        if p.get("name") == PLUGIN:
            return p.get("version")
    return None


def latest_version(force: bool = False) -> tuple[str | None, str]:
    """(verzija, odakle): 'cache' / 'network' / 'offline'."""
    try:
        c = json.loads(CACHE.read_text(encoding="utf-8"))
        if not force and time.time() - c.get("checked", 0) < TTL and c.get("latest"):
            return c["latest"], "cache"
    except (OSError, ValueError):
        c = {}
    try:
        latest = _fetch_latest()
    except Exception:  # bez mreže, GitHub nedostupan, čudan odgovor — nikad ne ruši izmenu
        return c.get("latest"), "offline"
    if latest:
        try:
            CACHE.write_text(json.dumps({"checked": time.time(), "latest": latest}), encoding="utf-8")
        except OSError:
            pass
    return latest, "network"


def downloaded_newer(have: str) -> str | None:
    """Novija verzija već preuzeta u keš pluginova (…/ccc-editor/<verzija>/) → važi posle restarta."""
    best = None
    for d in CODE.parent.iterdir() if CODE.parent.is_dir() else []:
        if d.is_dir() and (d / ".claude-plugin" / "plugin.json").exists() and _v(d.name) > _v(have):
            if best is None or _v(d.name) > _v(best):
                best = d.name
    return best


def check(force: bool = False) -> dict:
    have = installed_version()
    if not have:
        return {"status": "skipped", "reason": "development copy"}
    latest, src = latest_version(force)
    ready = downloaded_newer(have)
    if ready and (not latest or _v(ready) >= _v(latest)):
        return {"status": "ready", "have": have, "latest": ready}
    if not latest:
        return {"status": "skipped", "have": have, "reason": "no internet"}
    if _v(latest) > _v(have):
        return {"status": "available", "have": have, "latest": latest, "source": src}
    return {"status": "current", "have": have, "latest": latest}


def find_claude() -> str | None:
    """`claude` komanda: PATH, uobičajeni folderi, pa Claude desktop aplikacija (ugrađena verzija, najnovija)."""
    p = shutil.which("claude")
    if p:
        return p
    home = Path.home()
    cands = [home / ".local/bin/claude", home / ".claude/local/claude", home / ".npm-global/bin/claude",
             Path("/opt/homebrew/bin/claude"), Path("/usr/local/bin/claude")]
    cands += [home / ".local/bin/claude.exe", home / ".claude/local/claude.exe"]
    for c in cands:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)
    pats = [str(home / "Library/Application Support/Claude/claude-code/*/*/claude.app/Contents/MacOS/claude")]
    appdata = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    if appdata:
        pats.append(str(Path(appdata) / "Claude/claude-code/*/*/claude.exe"))
        pats.append(str(Path(appdata) / "Claude/claude-code/*/claude.exe"))
    found = [f for pat in pats for f in glob.glob(pat) if os.access(f, os.X_OK)]
    ver = lambda f: next((_v(x) for x in Path(f).parts if re.fullmatch(r"\d+\.\d+\.\d+", x)), (0,))  # noqa: E731
    found.sort(key=ver, reverse=True)
    return found[0] if found else None


def apply() -> dict:
    st = check(force=True)
    if st["status"] != "available":
        return st
    exe = find_claude()
    if not exe:
        return {**st, "status": "manual", "reason": "claude command not found"}
    for args in (["plugin", "marketplace", "update", MARKETPLACE], ["plugin", "update", f"{PLUGIN}@{MARKETPLACE}"]):
        try:
            r = subprocess.run([exe, *args], capture_output=True, text=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired) as e:
            return {**st, "status": "manual", "reason": f"{' '.join(args[:3])}: {e}"}
        if r.returncode != 0:
            tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["?"]
            return {**st, "status": "manual", "reason": f"{' '.join(args[:3])}: {tail[0][:160]}"}
    new = downloaded_newer(st["have"])
    if not new:
        return {**st, "status": "manual", "reason": "update ran but no new version appeared"}
    return {**st, "status": "installed", "latest": new}


def line(st: dict) -> str:
    """Jedan red za Claude (skill Step 0 i isporuka)."""
    s = st["status"]
    if s == "current":
        return f"UP_TO_DATE {st['have']}"
    if s == "available":
        return f"UPDATE_AVAILABLE {st['have']} -> {st['latest']}  (run in the background: ccc update)"
    if s == "ready":
        return f"UPDATE_READY {st['latest']}  (already downloaded; the client restarts Claude Code to use it)"
    if s == "installed":
        return f"UPDATE_INSTALLED {st['latest']}  (this chat keeps {st['have']}; new version after a restart)"
    if s == "manual":
        return f"UPDATE_MANUAL {st.get('latest', '?')}  ({st.get('reason', '')})"
    return f"UPDATE_CHECK_SKIPPED: {st.get('reason', '')}"
