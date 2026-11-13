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

# Every download is pinned (fixed commit / release + SHA-256): a cut-off download, a proxy's HTML page or a changed
# upstream file is caught and downloaded again instead of staying broken forever (QA 0.8.0, P1-2). When CCC updates a
# font or model, the new hash reaches every client with the next plugin update (P2: same file name never refreshed).
GF = "https://raw.githubusercontent.com/google/fonts/29b4ec6df2522a8aee279414b78a07910b065874/ofl"
FONTS = {  # all OFL / freely redistributable (Google Fonts, rsms/inter): name → (url, sha256)
    "TikTokSans-Variable.ttf": (f"{GF}/tiktoksans/TikTokSans%5Bopsz%2Cslnt%2Cwdth%2Cwght%5D.ttf",
                                "0e7f0a3e924c9a86478fc6fc2946de2e4ab8fc704ed72ee40434ade94bb9b0c6"),
    "InstrumentSerif-Regular.ttf": (f"{GF}/instrumentserif/InstrumentSerif-Regular.ttf",
                                    "498efd461f6ddfcb7a111bf9a565709d2085d48201d501ead960d93e84ffbb88"),
    "Montserrat-Variable.ttf": (f"{GF}/montserrat/Montserrat%5Bwght%5D.ttf",  # Style Menu
                                "0f7b311b2f3279e4eef9b2f968bcdbab6e28f4daeb1f049f4f278a902bcd82f7"),
    # Font choices for captions + hook (engine/ccc/fonts.py)
    "Poppins-Light.ttf": (f"{GF}/poppins/Poppins-Light.ttf", "650ba57fa99d12ec40c31ccfb680be656be4497fbe14164617d67e32ffe9cd46"),
    "Poppins-SemiBold.ttf": (f"{GF}/poppins/Poppins-SemiBold.ttf", "d3bf1bdaf0550e83da9ac0b1d1d9fe6db086835a83aa28578e609a394b9a0286"),
    "Poppins-Bold.ttf": (f"{GF}/poppins/Poppins-Bold.ttf", "983676516167748b74de6f4771fb384c664fd913acb8b471122ecacf5da5ea6c"),
    "Poppins-ExtraBold.ttf": (f"{GF}/poppins/Poppins-ExtraBold.ttf", "f2ab17c1a63a0ecc12c2461848fc8a469395e3cd2d641803e889c643d9f958e1"),
    "PlusJakartaSans-Variable.ttf": (f"{GF}/plusjakartasans/PlusJakartaSans%5Bwght%5D.ttf",
                                     "89b3fb38aa0d275d7a731d0d817a4f1622b316b4d7fbdedcf02ee9099ff68bc8"),
    "BricolageGrotesque-Variable.ttf": (f"{GF}/bricolagegrotesque/BricolageGrotesque%5Bopsz%2Cwdth%2Cwght%5D.ttf",
                                        "413e7357809ddd12fd80a96a8a396de0e401638d4acd3cb3e37532f0472ac682"),
}
INTER_ZIP = ("https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip",
             "9883fdd4a49d4fb66bd8177ba6625ef9a64aa45899767dde3d36aa425756b11e")
INTER_FILES = {"Inter-Light.ttf": "164414f0aacbe98a7e64addc43f7b3bfd2e32f7b90e101feeab227f14c371bda",
               "Inter-SemiBold.ttf": "78a843fade9d4612a5567302fb595b56976eb5fcebf4fea5a5912d638bafcde3",
               "Inter-Bold.ttf": "288316099b1e0a47a4716d159098005eef7c0066921f34e3200393dbdb01947f"}
MODELS = {
    "rnnoise/sh.rnnn": ("https://github.com/GregorR/rnnoise-models/raw/3eee541a283fd3b8f81b85b1748e3b9ccbefa04d/"
                        "somnolent-hogwash-2018-09-01/sh.rnnn", "70bb6685eb0c2a1d18e2918dca3fbfbd39317010b1802eb1b6ea73a92f3fdec0"),
    "rnnoise/bd.rnnn": ("https://github.com/GregorR/rnnoise-models/raw/3eee541a283fd3b8f81b85b1748e3b9ccbefa04d/"
                        "beguiling-drafter-2018-08-30/bd.rnnn", "ae3f7411e1e6a884f839a4a145c394408398f09854dbc1216ee02faafc98a17b"),
    "face/face_detection_yunet_2023mar.onnx": (
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/48b10fa505aeb51fbd127fc60a5c660040e823b7/"
        "models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"),
}
WHISPER = {"repo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo", "revision": "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
           "model.bin": (1617884929, "e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da")}
REMOTION_FILES = ["package.json", "package-lock.json", ".npmrc", "tsconfig.json", "remotion.config.ts"]
GB = 1024 ** 3


class SetupError(Exception):
    """kind: network | disk | permission | os | other — Claude tells the client what to do per kind."""
    def __init__(self, msg: str, kind: str = "other"):
        super().__init__(msg)
        self.kind = kind


def step(msg: str) -> None:
    print(f"\n▶ {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"  ✓ {msg}", flush=True)


def fail(msg: str, kind: str = "other") -> None:
    raise SetupError(msg, kind)


def sha256(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _looks_html(p: Path) -> bool:
    """Proxy / captive portal / 404 page saved under a font or model name."""
    with open(p, "rb") as f:
        head = f.read(512).lstrip().lower()
    return head.startswith((b"<!doctype", b"<html", b"<?xml")) or b"<head" in head


def good(dest: Path, sha: str | None) -> bool:
    if not dest.exists() or dest.stat().st_size == 0:
        return False
    return sha256(dest) == sha if sha else not _looks_html(dest)


def download(url: str, dest: Path, sha: str | None = None, tries: int = 3, timeout: int = 120) -> None:
    """Download to .part, verify (SHA-256 or at least "not an HTML page"), then rename. A broken existing file
    (wrong hash) is downloaded again. Network problems are retried with a pause."""
    import time
    import urllib.error
    if good(dest, sha):
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    host = url.split("/")[2]
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ccc-editor-setup"})
            with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if not good(tmp, sha):
                last = "the downloaded file was damaged or not the right file"
            else:
                tmp.replace(dest)
                return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            if isinstance(e, OSError) and getattr(e, "errno", None) == 28:  # ENOSPC
                tmp.unlink(missing_ok=True)
                fail("The disk is full.", "disk")
            last = str(getattr(e, "reason", e))
        tmp.unlink(missing_ok=True)
        time.sleep(2 * (i + 1))
    fail(f"Download from {host} failed ({last}). Check the internet connection and run setup again.", "network")


# ------------------------------------------------------------------ Node.js (official build, no installer)
def node_paths(home: Path) -> tuple[Path, Path]:
    base = home / "node"
    if IS_WIN:
        return base / "node.exe", base / "node_modules" / "npm" / "bin" / "npm-cli.js"
    return base / "bin" / "node", base / "lib" / "node_modules" / "npm" / "bin" / "npm-cli.js"


def macos_version() -> tuple[int, int]:
    v = platform.mac_ver()[0] or "0.0"
    parts = [int(x) for x in v.split(".")[:2] if x.isdigit()] + [0, 0]
    return parts[0], parts[1]


def node_major() -> int:
    """Node 24+ needs macOS 13.5 — "newest LTS" broke setup on older Macs (QA 0.8.0, P1-1)."""
    if sys.platform == "darwin" and macos_version() < (13, 5):
        return 22
    return 24


def install_node(home: Path) -> Path:
    node, _ = node_paths(home)
    if node.exists():
        r = subprocess.run([str(node), "-v"], capture_output=True, text=True)
        if r.returncode == 0:
            ok(f"Node.js {r.stdout.strip()} (already installed)")
            return node
        print("  · the installed Node.js doesn't run on this computer — installing a compatible one", flush=True)
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(platform.machine().lower(), "x64")
    major = node_major()
    try:
        with urllib.request.urlopen("https://nodejs.org/dist/index.json", timeout=60) as r:
            releases = json.load(r)
    except Exception as e:  # noqa: BLE001
        fail(f"Can't reach nodejs.org ({e}). Check the internet connection and run setup again.", "network")
    rel = next(x for x in releases if x["version"].startswith(f"v{major}."))  # newest of the pinned major
    ver = rel["version"]
    name, kind = (f"node-{ver}-win-{arch}.zip", "zip") if IS_WIN else (f"node-{ver}-darwin-{arch}.tar.gz", "tar")
    base = f"https://nodejs.org/dist/{ver}"
    try:
        with urllib.request.urlopen(f"{base}/SHASUMS256.txt", timeout=60) as r:
            sums = dict(line.split()[::-1] for line in r.read().decode().splitlines() if line.strip())
    except Exception as e:  # noqa: BLE001
        fail(f"Can't reach nodejs.org ({e}). Check the internet connection and run setup again.", "network")
    with tempfile.TemporaryDirectory() as td:
        arc = Path(td) / name
        download(f"{base}/{name}", arc, sums.get(name))
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


def _run(args: list, cwd: Path, env: dict, timeout: int, what: str):
    """Subprocess with a time limit — setup used to hang forever on a stalled npm or browser download (P1-6)."""
    try:
        return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail(f"{what} took longer than {timeout // 60} minutes (slow or blocked internet). Run setup again.", "network")


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
        r = _run([str(node), str(npm_cli), "ci" if lock.exists() else "install", "--no-audit", "--no-fund"],
                 rem, env, 1800, "Installing the video engine (Remotion)")
        if r.returncode != 0:
            err = r.stderr or ""
            kind = "network" if any(x in err for x in ("ETIMEDOUT", "ECONNRESET", "ENOTFOUND", "EAI_AGAIN", "network")) \
                else "disk" if "ENOSPC" in err else "other"
            fail("Installing the video engine (Remotion) failed:\n" + "\n".join(err.splitlines()[-8:]), kind)
        stamp.write_text(lock.read_text() if lock.exists() else "")
    ok("video engine (Remotion)")
    cli = rem / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    r = _run([str(node), str(cli), "browser", "ensure"], rem, env, 900, "Downloading the render browser")
    if r.returncode != 0:
        fail("Downloading the render browser failed:\n" + "\n".join((r.stderr or r.stdout).splitlines()[-6:]), "network")
    ok("render browser (Chrome Headless Shell)")


# ------------------------------------------------------------------ fonts + models
def install_fonts(home: Path) -> None:
    fonts = home / "tools" / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    if not all(good(fonts / f, h) for f, h in INTER_FILES.items()):
        with tempfile.TemporaryDirectory() as td:
            z = Path(td) / "inter.zip"
            download(*INTER_ZIP[:1], z, INTER_ZIP[1])
            with zipfile.ZipFile(z) as zz:
                for f in INTER_FILES:
                    (fonts / f).write_bytes(zz.read(f"extras/ttf/{f}"))
                (fonts / "Inter-LICENSE.txt").write_bytes(zz.read("LICENSE.txt"))
    for name, (url, h) in FONTS.items():
        download(url, fonts / name, h)
    pub = home / "remotion" / "public" / "fonts"
    pub.mkdir(parents=True, exist_ok=True)
    for f in fonts.glob("*.ttf"):  # render copy follows the verified font (updated font → updated copy)
        if not (pub / f.name).exists() or (pub / f.name).stat().st_size != f.stat().st_size:
            shutil.copy2(f, pub / f.name)
    ok("fonts (Inter, TikTok Sans, Instrument Serif, Montserrat, Poppins, Plus Jakarta Sans, Bricolage Grotesque)")


def whisper_ok(target: Path) -> bool:
    size, _ = WHISPER["model.bin"]
    return (target / "model.bin").exists() and (target / "model.bin").stat().st_size == size \
        and all((target / f).exists() for f in ("config.json", "tokenizer.json", "vocabulary.json", "preprocessor_config.json"))


def install_models(home: Path, skip_whisper: bool) -> None:
    models = home / "tools" / "models"
    for rel, (url, h) in MODELS.items():
        download(url, models / rel, h)
    ok("noise + face models")
    if skip_whisper:
        return
    target = models / "whisper" / "large-v3-turbo"
    if whisper_ok(target):
        ok("speech model (already downloaded)")
        return
    print("  … downloading the speech model (~1.6 GB, one time)", flush=True)
    from huggingface_hub import snapshot_download
    for i in range(3):
        try:
            snapshot_download(WHISPER["repo"], revision=WHISPER["revision"], local_dir=str(target),
                              allow_patterns=["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json",
                                              "vocabulary.json"])
            break
        except Exception as e:  # noqa: BLE001
            if "No space left" in str(e) or getattr(e, "errno", None) == 28:
                fail("The disk is full.", "disk")
            if i == 2:
                fail(f"Downloading the speech model failed ({str(e).splitlines()[0][:160]}). Check the internet "
                     "connection and run setup again — it continues where it stopped.", "network")
    if not whisper_ok(target) or sha256(target / "model.bin") != WHISPER["model.bin"][1]:
        (target / "model.bin").unlink(missing_ok=True)
        fail("The speech model download was damaged — run setup again.", "network")
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


def code_version() -> str:
    pj = CODE / ".claude-plugin" / "plugin.json"
    return json.loads(pj.read_text()).get("version", "dev") if pj.exists() else "dev"


def _ver(v: str) -> tuple:
    try:
        return tuple(int(x) for x in str(v).split("."))
    except ValueError:
        return ()


def missing_parts(home: Path) -> list[str]:
    """What a working install must have (fast: sizes/hashes of small files, size of the big model).
    `--check` used to look only at the version — a deleted model or font stayed broken (P2)."""
    node, _ = node_paths(home)
    out = []
    if not node.exists():
        out.append("Node.js")
    if not (home / "bin" / f"ffmpeg{EXE}").exists():
        out.append("ffmpeg")
    fonts = home / "tools" / "fonts"
    bad = [n for n, (_, h) in FONTS.items() if not good(fonts / n, h)] + [n for n, h in INTER_FILES.items() if not good(fonts / n, h)]
    if bad:
        out.append("fonts (" + ", ".join(bad[:3]) + ")")
    if any(not good(home / "tools" / "models" / r, h) for r, (_, h) in MODELS.items()):
        out.append("noise/face models")
    if not whisper_ok(home / "tools" / "models" / "whisper" / "large-v3-turbo"):
        out.append("speech model")
    rem = home / "remotion"
    if not (rem / "node_modules" / "remotion").exists() or not (rem / "src").exists():
        out.append("video engine")
    if not any((rem / "node_modules" / ".remotion").glob("chrome-headless-shell*")):
        out.append("render browser")
    return out


def check(home: Path) -> str:
    inst = home / "installed.json"
    if not inst.exists():
        return "NOT_INSTALLED"
    have = json.loads(inst.read_text()).get("version", "")
    want = code_version()
    if want != "dev" and have != want and _ver(have) < _ver(want):
        return "UPDATE_NEEDED"
    miss = missing_parts(home)
    if miss:
        return "REPAIR_NEEDED: " + ", ".join(miss)
    return "INSTALLED"


def free_space_needed(home: Path) -> int:
    miss = missing_parts(home)
    need = 0.5 * GB
    need += 1.7 * GB if "speech model" in miss else 0
    need += 0.9 * GB if "video engine" in miss or "render browser" in miss else 0
    need += 0.3 * GB if "Node.js" in miss else 0
    return int(need)


def install(home: Path, no_whisper: bool) -> None:
    if sys.platform == "darwin" and macos_version() < (12, 0):
        fail(f"This Mac runs macOS {'.'.join(map(str, macos_version()))}; the CCC editor needs macOS 12 (Monterey) or "
             "newer. Update macOS in System Settings → General → Software Update.", "os")
    if IS_WIN and platform.machine().lower() in ("arm64", "aarch64"):
        fail("Windows on ARM isn't supported yet — the editor needs a Windows PC with an Intel/AMD processor or a Mac.", "os")
    inst = home / "installed.json"
    if inst.exists():  # a stale Claude session with an older plugin must not downgrade a newer install (P1-4)
        have, want = json.loads(inst.read_text()).get("version", ""), code_version()
        if want != "dev" and _ver(have) > _ver(want):
            ok(f"a newer version ({have}) is already installed — restart Claude Code to use it")
            print("SETUP_OK", flush=True)
            return
    need, free = free_space_needed(home), shutil.disk_usage(home).free
    if free < need:
        fail(f"Not enough disk space: setup needs about {need / GB:.1f} GB free, the disk has {free / GB:.1f} GB. "
             "Free some space (empty the Trash, delete large old files) and run setup again.", "disk")
    print(f"CCC editor setup → {home}", flush=True)
    step("1/4 Node.js")
    node = install_node(home)
    step("2/4 ffmpeg + fonts + models")
    install_ffmpeg(home)
    install_fonts(home)
    install_models(home, no_whisper)
    step("3/4 Video engine")
    install_remotion(home, node)
    step("4/4 Done")
    enable_auto_update()
    version = code_version()
    (home / "installed.json").write_text(json.dumps({"version": version, "code": str(CODE)}, indent=1))
    ok(f"installed (version {version})")
    print("SETUP_OK", flush=True)


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
    ap.add_argument("--check", action="store_true", help="INSTALLED / UPDATE_NEEDED / REPAIR_NEEDED: … / NOT_INSTALLED")
    a = ap.parse_args()
    home = Path(a.home).expanduser().resolve()
    if a.check:
        print(check(home))
        return
    home.mkdir(parents=True, exist_ok=True)
    try:
        install(home, a.no_whisper)
    except SetupError as e:
        print(f"  ✗ {e}", flush=True)
        print(f"SETUP_FAILED\nSETUP_REASON: {e.kind}", flush=True)
        sys.exit(1)
    except KeyboardInterrupt:
        print("SETUP_FAILED\nSETUP_REASON: interrupted", flush=True)
        sys.exit(1)
    except Exception as e:  # noqa: BLE001 — never a bare traceback for the client (P1-6)
        import errno
        import traceback
        traceback.print_exc(file=sys.stdout)  # goes to setup.log for support
        kind = "disk" if getattr(e, "errno", None) == errno.ENOSPC else \
            "permission" if isinstance(e, PermissionError) else \
            "network" if isinstance(e, (ConnectionError, TimeoutError)) or "urlopen" in str(e) else "other"
        print(f"  ✗ {type(e).__name__}: {str(e)[:200]}", flush=True)
        print(f"SETUP_FAILED\nSETUP_REASON: {kind}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
