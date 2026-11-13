"""CCC editor — installs everything the editor needs into one data folder (macOS + Windows).

Run by setup/bootstrap.sh with the data folder's Python:
    python setup/install.py --home <data folder>

Idempotent: every step is skipped when it's already done, so it is safe to run again (e.g. after a plugin
update — only what changed is redone). Messages are English: Claude relays them to the client.
Nothing here needs admin rights; everything lands inside <data folder>.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent          # plugin (or dev) folder with the code
IS_WIN = os.name == "nt"
EXE = ".exe" if IS_WIN else ""

FONTS = {  # all OFL / freely redistributable (Google Fonts, rsms/inter)
    "TikTokSans-Variable.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/tiktoksans/TikTokSans%5Bopsz%2Cslnt%2Cwdth%2Cwght%5D.ttf",
    "InstrumentSerif-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentserif/InstrumentSerif-Regular.ttf",
    "Montserrat-Variable.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",  # Style Menu
    # Font choices for captions + hook (engine/ccc/fonts.py)
    "Poppins-Light.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Light.ttf",
    "Poppins-SemiBold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-SemiBold.ttf",
    "Poppins-Bold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Bold.ttf",
    "Poppins-ExtraBold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-ExtraBold.ttf",
    "PlusJakartaSans-Variable.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf",
    "BricolageGrotesque-Variable.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/bricolagegrotesque/BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf",
}
INTER_ZIP = "https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip"
INTER_FILES = ["Inter-Light.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"]
MODELS = {
    "rnnoise/sh.rnnn": "https://github.com/GregorR/rnnoise-models/raw/master/somnolent-hogwash-2018-09-01/sh.rnnn",
    "rnnoise/bd.rnnn": "https://github.com/GregorR/rnnoise-models/raw/master/beguiling-drafter-2018-08-30/bd.rnnn",
    "face/face_detection_yunet_2023mar.onnx":
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
}
REMOTION_FILES = ["package.json", "package-lock.json", ".npmrc", "tsconfig.json", "remotion.config.ts"]


def step(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"  ✓ {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"  ✗ {msg}", flush=True)
    print("SETUP_FAILED", flush=True)
    sys.exit(1)


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ccc-editor-setup"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f)
        tmp.replace(dest)
    except Exception as e:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        fail(f"Download failed ({url.split('/')[2]}): {e}. Check the internet connection and run setup again.")


# ------------------------------------------------------------------ Node.js (official build, no installer)
def node_paths(home: Path) -> tuple[Path, Path]:
    base = home / "node"
    if IS_WIN:
        return base / "node.exe", base / "node_modules" / "npm" / "bin" / "npm-cli.js"
    return base / "bin" / "node", base / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js"


def install_node(home: Path) -> Path:
    node, _ = node_paths(home)
    if node.exists():
        ok(f"Node.js {subprocess.run([str(node), '-v'], capture_output=True, text=True).stdout.strip()} (already installed)")
        return node
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(platform.machine().lower(), "x64")
    with urllib.request.urlopen("https://nodejs.org/dist/index.json", timeout=60) as r:
        releases = json.load(r)
    rel = next(x for x in releases if x["lts"])  # newest LTS
    ver = rel["version"]
    if IS_WIN:
        name, kind = f"node-{ver}-win-{arch}.zip", "zip"
    else:
        name, kind = f"node-{ver}-darwin-{arch}.tar.gz", "tar"
    url = f"https://nodejs.org/dist/{ver}/{name}"
    with tempfile.TemporaryDirectory() as td:
        arc = Path(td) / name
        download(url, arc)
        out = Path(td) / "x"
        if kind == "zip":
            with zipfile.ZipFile(arc) as z:
                z.extractall(out)
        else:
            with tarfile.open(arc) as t:
                t.extractall(out, filter="data") if sys.version_info >= (3, 12) else t.extractall(out)
        top = next(out.iterdir())
        if (home / "node").exists():
            shutil.rmtree(home / "node")
        shutil.move(str(top), str(home / "node"))
    if not IS_WIN:
        node.chmod(node.stat().st_mode | stat.S_IEXEC)
    ok(f"Node.js {ver}")
    return node


# ------------------------------------------------------------------ ffmpeg (full build from the imageio-ffmpeg wheel)
def install_ffmpeg(home: Path) -> None:
    import imageio_ffmpeg
    src = Path(imageio_ffmpeg.get_ffmpeg_exe())
    dst = home / "bin" / f"ffmpeg{EXE}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists() or dst.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dst)
        dst.chmod(dst.stat().st_mode | stat.S_IEXEC)
    filters = subprocess.run([str(dst), "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    missing = [f for f in ("loudnorm", "ebur128", "afftdn", "arnndn", "deesser", "acompressor", "alimiter", "highpass")
               if f" {f} " not in filters]
    if missing:
        fail(f"ffmpeg is missing filters: {missing}")
    ok("ffmpeg (all audio filters)")


# ------------------------------------------------------------------ Remotion project (code synced from the plugin)
def install_remotion(home: Path, node: Path) -> None:
    rem = home / "remotion"
    rem.mkdir(parents=True, exist_ok=True)
    src = CODE / "remotion"
    for f in REMOTION_FILES:
        if (src / f).exists():
            shutil.copy2(src / f, rem / f)
    if (rem / "src").exists():
        shutil.rmtree(rem / "src")
    shutil.copytree(src / "src", rem / "src")
    _, npm_cli = node_paths(home)
    env = {**os.environ, "PATH": str(node.parent) + os.pathsep + os.environ.get("PATH", "")}
    lock = rem / "package-lock.json"
    stamp = rem / ".installed-lock"
    if not (rem / "node_modules" / "remotion").exists() or not stamp.exists() or stamp.read_text() != lock.read_text():
        r = subprocess.run([str(node), str(npm_cli), "ci" if lock.exists() else "install", "--no-audit", "--no-fund"],
                           cwd=rem, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            fail("Installing the video engine (Remotion) failed:\n" + "\n".join(r.stderr.splitlines()[-8:]))
        stamp.write_text(lock.read_text() if lock.exists() else "")
    ok("video engine (Remotion)")
    cli = rem / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    r = subprocess.run([str(node), str(cli), "browser", "ensure"], cwd=rem, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        fail("Downloading the render browser failed:\n" + "\n".join((r.stderr or r.stdout).splitlines()[-6:]))
    ok("render browser (Chrome Headless Shell)")


# ------------------------------------------------------------------ fonts + models
def install_fonts(home: Path) -> None:
    fonts = home / "tools" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    if not all((fonts / f).exists() for f in INTER_FILES):
        with tempfile.TemporaryDirectory() as td:
            z = Path(td) / "inter.zip"
            download(INTER_ZIP, z)
            with zipfile.ZipFile(z) as zz:
                for f in INTER_FILES:
                    (fonts / f).write_bytes(zz.read(f"extras/ttf/{f}"))
                (fonts / "Inter-LICENSE.txt").write_bytes(zz.read("LICENSE.txt"))
    for name, url in FONTS.items():
        download(url, fonts / name)
    pub = home / "remotion" / "public" / "fonts"
    pub.mkdir(parents=True, exist_ok=True)
    for f in fonts.glob("*.ttf"):
        if not (pub / f.name).exists():
            shutil.copy2(f, pub / f.name)
    ok("fonts (Inter, TikTok Sans, Instrument Serif, Montserrat, Poppins, Plus Jakarta Sans, Bricolage Grotesque)")


def install_models(home: Path, skip_whisper: bool) -> None:
    models = home / "tools" / "models"
    for rel, url in MODELS.items():
        download(url, models / rel)
    ok("noise + face models")
    if skip_whisper:
        return
    target = models / "whisper" / "large-v3-turbo"
    if (target / "model.bin").exists():
        ok("speech model (already downloaded)")
        return
    print("  … downloading the speech model (~1.6 GB, one time)", flush=True)
    from faster_whisper import download_model
    download_model("large-v3-turbo", output_dir=str(target))
    ok("speech model")


# ------------------------------------------------------------------ auto-update
MARKETPLACE = "createcontent-club"
REPO = "createcontent-club/ccc-editor"


def enable_auto_update() -> None:
    """New formats reach the client without them doing anything: turn on auto-update for our marketplace.
    Claude Code leaves it off for non-Anthropic marketplaces; the documented switch is `autoUpdate` on the
    marketplace's `extraKnownMarketplaces` entry in the user's settings. A choice the client made (true or
    false) is never overwritten, and an unreadable settings file is left alone."""
    if not (CODE / ".claude-plugin" / "plugin.json").exists():
        return  # development copy, not an installed plugin
    cfg = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").expanduser()
    f = cfg / "settings.json"
    try:
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() and f.read_text(encoding="utf-8").strip() else {}
        if not isinstance(data, dict):
            return
    except (OSError, ValueError):
        print("  · automatic updates: couldn't read Claude's settings — turn them on in /plugin → Marketplaces", flush=True)
        return
    mk = data.setdefault("extraKnownMarketplaces", {})
    entry = mk.setdefault(MARKETPLACE, {"source": {"source": "github", "repo": REPO}})
    if not isinstance(entry, dict) or "autoUpdate" in entry:
        return
    entry["autoUpdate"] = True
    try:
        cfg.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + ".ccc-tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, f)
        ok("automatic updates turned on (new formats arrive by themselves)")
    except OSError:
        print("  · automatic updates: couldn't save — turn them on in /plugin → Marketplaces", flush=True)


def main() -> None:
    # Windows: konzola/pipe u cp1252 ne može da ispiše "→ ✓ ✗" (QA 0.8.0, P0) — uvek UTF-8.
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", required=True)
    ap.add_argument("--no-whisper", action="store_true", help="skip the 1.6 GB speech model (testing only)")
    a = ap.parse_args()
    home = Path(a.home).expanduser().resolve()
    home.mkdir(parents=True, exist_ok=True)
    print(f"CCC editor setup → {home}", flush=True)

    step("1/4 Node.js")
    node = install_node(home)
    step("2/4 ffmpeg + fonts + models")
    install_ffmpeg(home)
    install_fonts(home)
    install_models(home, a.no_whisper)
    step("3/4 Video engine")
    install_remotion(home, node)
    step("4/4 Done")
    enable_auto_update()
    version = json.loads((CODE / ".claude-plugin" / "plugin.json").read_text()).get("version", "dev") \
        if (CODE / ".claude-plugin" / "plugin.json").exists() else "dev"
    (home / "installed.json").write_text(json.dumps({"version": version, "code": str(CODE)}, indent=1))
    ok(f"installed (version {version})")
    print("SETUP_OK", flush=True)


if __name__ == "__main__":
    main()
