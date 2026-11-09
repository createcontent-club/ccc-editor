"""CCC Editing Skills — provera instalacije.

Pokretanje:  .venv/bin/python tools/doctor.py [--quick]
--quick preskače učitavanje Whisper modela i probnu transkripciju.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import os
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
from ccc.project import FONTS, HOME, MODELS, REMOTION, ff_path, remotion_cli  # noqa: E402
QUICK = "--quick" in sys.argv
results: list[tuple[bool, str]] = []


def check(label: str):
    def deco(fn):
        try:
            detail = fn()
            results.append((True, f"{label}{' — ' + detail if detail else ''}"))
        except Exception as e:  # noqa: BLE001
            results.append((False, f"{label} — {type(e).__name__}: {e}"))
        return fn
    return deco


tmp = Path(tempfile.mkdtemp(prefix="ccc-doctor-"))


@check("ffmpeg + ffprobe")
def _():
    for b in ("ffmpeg", "ffprobe"):
        if not shutil.which(b):
            raise RuntimeError(f"{b} nije u PATH-u")
    v = subprocess.run(["ffmpeg", "-hide_banner", "-version"], capture_output=True, text=True).stdout.split()[2]
    filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True).stdout
    need = ["loudnorm", "arnndn", "afftdn", "silencedetect", "deesser", "acompressor", "overlay", "concat", "highpass"]
    missing = [f for f in need if f" {f} " not in filters]
    if missing:
        raise RuntimeError(f"nedostaju filteri: {missing}")
    return f"v{v}, svi potrebni filteri"


@check("Python paketi")
def _():
    import cv2, faster_whisper, imageio_ffmpeg, numpy, PIL  # noqa: F401,E401
    return f"faster-whisper {faster_whisper.__version__}, Pillow {PIL.__version__}, OpenCV {cv2.__version__}"


@check("Fontovi")
def _():
    have = sorted(p.name for p in FONTS.glob("*.[ot]tf"))
    for req in ("Inter-SemiBold.ttf", "Inter-Light.ttf", "Inter-Bold.ttf", "TikTokSans-Variable.ttf",
                "InstrumentSerif-Regular.ttf"):
        if req not in have:
            raise RuntimeError(f"nema {req} — pokreni: bash setup.sh")
    return f"{len(have)} fontova (titlovi: Inter SemiBold, hook: TikTok Sans — oba OFL)"


@check("Titl render (Pillow, CCC stil)")
def _():
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    font = ImageFont.truetype(str(FONTS / "Inter-Bold.ttf"), 62)
    img = Image.new("RGBA", (1080, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((540, 100), "OVO JE TEST", font=font, fill="#FFBF00", anchor="mm")
    glow = img.filter(ImageFilter.GaussianBlur(18))
    out = Image.alpha_composite(glow, img)
    out.save(tmp / "caption.png")
    return "PNG sa glow efektom OK"


@check("Audio lanac (denoise + loudnorm -14 LUFS)")
def _():
    src, dst = tmp / "tone.wav", tmp / "fixed.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=4",
                    "-f", "lavfi", "-i", "anoisesrc=d=4:a=0.02", "-filter_complex", "amix=inputs=2", str(src)],
                   check=True, capture_output=True)
    rn = MODELS / "rnnoise" / "sh.rnnn"
    chain = f"highpass=f=80,arnndn=m='{ff_path(rn)}',deesser,acompressor,loudnorm=I=-14:TP=-1:LRA=11"
    subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-af", chain, "-ar", "48000", str(dst)],
                   check=True, capture_output=True)
    from ccc.audio import loudness
    return f"izlaz {loudness(dst)['lufs']:.1f} LUFS"


@check("Detekcija lica (YuNet)")
def _():
    import cv2
    m = MODELS / "face" / "face_detection_yunet_2023mar.onnx"
    cv2.FaceDetectorYN.create(str(m), "", (320, 320))
    return "model učitan"


@check("Video render (concat + overlay → H.264 1080x1920)")
def _():
    out = tmp / "render.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-y",
        "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=3",
        "-f", "lavfi", "-i", "sine=d=3",
        "-i", str(tmp / "caption.png"),
        "-filter_complex",
        "[0:v]trim=0:1,setpts=PTS-STARTPTS[a];[0:v]trim=2:3,setpts=PTS-STARTPTS[b];"
        "[a][b]concat=n=2:v=1:a=0[v];[v][2:v]overlay=0:1300[out]",
        "-map", "[out]", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)], check=True, capture_output=True)
    info = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(out)],
                                     capture_output=True, text=True).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    return f"{v['width']}x{v['height']} {v['codec_name']}"


@check("Remotion (paketi + Chrome + probni still)")
def _():
    rem = REMOTION
    if not shutil.which("node"):
        raise RuntimeError("Node.js nije dostupan")
    pkg = rem / "node_modules" / "remotion" / "package.json"
    if not pkg.exists():
        raise RuntimeError("paketi nisu instalirani — pokreni instalaciju")
    version = json.loads(pkg.read_text())["version"]
    test = rem / "public" / "test" / "test-talk.mp4"
    if not test.exists():  # probni snimak za CccTest kompoziciju
        test.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ffmpeg", "-hide_banner", "-y", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30:d=6",
                        "-f", "lavfi", "-i", "sine=d=6", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", str(test)], check=True, capture_output=True)
    out = tmp / "still.png"
    r = subprocess.run(remotion_cli("still", "CccTest", str(out), "--frame=20"),
                       cwd=rem, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not out.exists():
        raise RuntimeError("still render pao: " + (r.stderr or r.stdout).strip().splitlines()[-1])
    return f"v{version}, Chrome OK, still 1080×1920 renderovan"


if not QUICK:
    @check("Whisper transkripcija (reči + vreme)")
    def _():
        model_dir = MODELS / "whisper" / "large-v3-turbo"
        if not (model_dir / "model.bin").exists():
            raise RuntimeError("model nije skinut — pokreni: bash setup.sh")
        if not shutil.which("say"):  # van macOS-a nemamo sintezu govora — proveravamo da se model učitava
            from faster_whisper import WhisperModel
            WhisperModel(str(model_dir), device="cpu", compute_type="int8")
            return "model učitan (test govora samo na macOS-u)"
        speech = tmp / "speech.aiff"
        subprocess.run(["say", "-o", str(speech), "This is a quick test of the editing pipeline."], check=True)
        import numpy as np
        from faster_whisper import WhisperModel
        # Dekodiramo sistemskim ffmpeg-om (16 kHz mono float32) — ne oslanjamo se na PyAV,
        # čije novije verzije nisu kompatibilne sa faster-whisper 1.2.x.
        pcm = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(speech), "-ac", "1",
                              "-ar", "16000", "-f", "f32le", "-"], check=True, capture_output=True).stdout
        audio = np.frombuffer(pcm, dtype=np.float32)
        t = time.time()
        model = WhisperModel(str(model_dir), device="cpu", compute_type="int8")
        segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=True)
        words = [w for s in segs for w in s.words]
        if not words:
            raise RuntimeError("nema prepoznatih reči")
        first = words[0]
        return (f"{len(words)} reči, jezik={info.language}, prva '{first.word.strip()}' "
                f"@ {first.start:.2f}s, {time.time() - t:.1f}s ukupno")

print("\nCCC Editing Skills — doctor\n")
for ok, msg in results:
    print(f"  {'✅' if ok else '❌'} {msg}")
shutil.rmtree(tmp, ignore_errors=True)
bad = sum(not ok for ok, _ in results)
print(f"\n{'Sve radi.' if not bad else f'{bad} provera nije prošla.'}\n")
sys.exit(1 if bad else 0)
