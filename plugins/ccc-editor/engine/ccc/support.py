"""`ccc support-info` — jedan blok za Discord podršku (QA 0.8.0, faza 3).

Sve što podrška pita prvo: verzije, sistem, šta instalaciji fali, disk, kraj poslednjeg setup-a, poslednja greška
engine-a i poslednji projekat. Putanja korisničkog foldera se zamenjuje sa "~" (ime korisnika ne ide u chat).
Sačuva se i u <data>/support-info.txt da klijent može da pošalje fajl.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .project import CODE, HOME, REMOTION, WORK


def _safe(s: str) -> str:
    home = str(Path.home())
    return s.replace(home, "~").replace(home.replace("\\", "/"), "~")


def _cmd(args: list[str]) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else "?"
    except (OSError, subprocess.TimeoutExpired):
        return "missing"


def _json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _install_check() -> str:
    try:
        sys.path.insert(0, str(CODE / "setup"))
        import install  # setup/install.py
        return install.check(HOME)
    except Exception as e:  # noqa: BLE001
        return f"(check failed: {type(e).__name__})"


def _last_setup(n: int = 14) -> list[str]:
    f = HOME / "setup.log"
    try:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ["(no setup.log)"]
    starts = [i for i, ln in enumerate(lines) if ln.startswith("===== setup")]
    run = lines[starts[-1]:] if starts else lines
    return run[:2] + (["…"] if len(run) > n + 2 else []) + run[-n:] if len(run) > n + 2 else run


def _last_crash(n: int = 25) -> list[str]:
    logs = sorted((HOME / "logs").glob("crash-*.log")) if (HOME / "logs").exists() else []
    if not logs:
        return ["(none)"]
    lines = logs[-1].read_text(encoding="utf-8", errors="replace").splitlines()
    return [logs[-1].name] + lines[:2] + (["…"] if len(lines) > n else []) + lines[-(n - 2):]


def _project() -> list[str]:
    projects = [d for d in WORK.iterdir() if (d / "project.json").exists()] if WORK.exists() else []
    if not projects:
        return ["(no projects)"]
    last = max(projects, key=lambda d: (d / "project.json").stat().st_mtime)
    p = _json(last / "project.json")
    ch = _json(last / "choices.json")
    src = p.get("source") or {}
    return [f"{len(projects)} projects · last: {last.name} · format {ch.get('format', '?')} · "
            f"{src.get('width')}×{src.get('height')} {src.get('fps', p.get('fps'))} fps {src.get('duration', 0):.0f}s "
            f"{src.get('codec', '')} · {'exported' if p.get('exported') else 'not exported'}"
            + (f" · cleaned {p['cleaned']}" if p.get("cleaned") else "")]


def report() -> str:
    plugin = _json(CODE / ".claude-plugin" / "plugin.json").get("version", "dev")
    inst = _json(HOME / "installed.json").get("version", "not installed")
    node = HOME / "node" / ("node.exe" if os.name == "nt" else "bin/node")
    ffmpeg = HOME / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    py = sys.executable
    mac = platform.mac_ver()[0]
    rem = _json(REMOTION / "node_modules" / "remotion" / "package.json").get("version", "missing")
    try:
        free = shutil.disk_usage(HOME).free / 1024 ** 3
    except OSError:
        free = -1
    try:
        from importlib.metadata import version as pv
        pk = " · ".join(f"{n} {pv(n)}" for n in ("faster-whisper", "ctranslate2", "onnxruntime", "numpy", "yt-dlp"))
    except Exception:  # noqa: BLE001
        pk = "?"
    lines = [
        f"CCC editor support info · {time.strftime('%Y-%m-%d %H:%M')}",
        f"plugin {plugin} · installed {inst} · check: {_install_check()}",
        f"system: {'macOS ' + mac if mac else platform.system() + ' ' + platform.release()} · {platform.machine()} · "
        f"Python {platform.python_version()}",
        f"node {_cmd([str(node), '-v']) if node.exists() else 'missing'} · ffmpeg {'ok' if ffmpeg.exists() else 'missing'} · "
        f"remotion {rem}",
        f"packages: {pk}",
        f"disk free: {free:.1f} GB · data: {HOME}",
        "--- project",
        *_project(),
        "--- last setup",
        *_last_setup(),
        "--- last engine error",
        *_last_crash(),
    ]
    text = _safe("\n".join(lines))
    try:
        (HOME / "support-info.txt").write_text(text + "\n", encoding="utf-8")
    except OSError:
        pass
    return text
