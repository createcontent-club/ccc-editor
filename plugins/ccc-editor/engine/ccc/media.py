"""Prijem snimka: ffprobe, normalizacija za Remotion, dekodiranje zvuka."""
from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

import numpy as np

STANDARD_FPS = (23.976, 24, 25, 29.97, 30, 50, 59.94, 60)


def run(*args: str) -> None:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"Komanda nije uspela: {' '.join(args[:3])}…\n{r.stderr[-1500:]}")


def _frac(x: str | None) -> float:
    """"30000/1001" → 29.97; "0/0", prazno ili neispravno → 0 (ne ZeroDivisionError)."""
    try:
        f = Fraction(x or "0/1")
        return float(f)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _num(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _mean_volume(path: Path, index: int) -> float:
    """Prosečna glasnoća audio trake (prvih 60 s) u dB — za izbor trake sa govorom kad ih ima više."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-t", "60", "-i", str(path), "-map", f"0:a:{index}", "-af",
                        "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        if "mean_volume:" in line:
            return _num(line.split("mean_volume:")[1].split("dB")[0], -120.0)
    return -120.0


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
                       capture_output=True, text=True)
    try:
        info = json.loads(r.stdout) if r.returncode == 0 else None
    except json.JSONDecodeError:
        info = None
    if not info or not info.get("streams"):
        raise SystemExit("CCC_BAD_FILE: this file can't be read as a video (it may be damaged or not a video).")
    # Prvi "video" tok može biti omot/naslovna slika (m4a sa slikom) — preskače se.
    vids = [s for s in info["streams"] if s.get("codec_type") == "video"
            and not (s.get("disposition") or {}).get("attached_pic")]
    auds = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    if not vids:
        raise SystemExit("CCC_NO_VIDEO: this file has no video picture (only sound or a cover image).")
    v = vids[0]
    r_fps = _frac(v.get("r_frame_rate")) or _frac(v.get("avg_frame_rate")) or 30.0
    avg_fps = _frac(v.get("avg_frame_rate")) or r_fps
    rotation = 0
    for sd in v.get("side_data_list", []):
        rotation = int(_num(sd.get("rotation"), rotation))
    rotation = int(_num(v.get("tags", {}).get("rotate"), rotation)) % 360
    w, h = int(v["width"]), int(v["height"])
    if rotation in (90, 270):
        # iPhone čuva uspravan snimak kao 1920×1080 + rotacija 90/270 — prikazan je 1080×1920 (QA 0.8.0, P0).
        w, h = h, w
    # Trajanje: kontejner, pa tokovi (WebM iz browsera često nema trajanje kontejnera).
    dur = _num((info.get("format") or {}).get("duration")) or max(
        [_num(s.get("duration")) for s in vids + auds] + [0.0])
    if dur <= 0:
        rr = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
                            capture_output=True, text=True)
        for line in rr.stderr.splitlines()[::-1]:
            if "time=" in line:
                hh, mm, ss = line.split("time=")[1].split()[0].split(":")
                dur = int(hh) * 3600 + int(mm) * 60 + float(ss)
                break
    # Audio traka: kad ih ima više, uzima se ona sa govorom (najglasnija), ne uvek prva (prva je često tiha).
    a_idx = 0
    if len(auds) > 1:
        vols = [_mean_volume(path, i) for i in range(len(auds))]
        a_idx = max(range(len(auds)), key=lambda i: vols[i])
    a = auds[a_idx] if auds else None
    v_start, a_start = _num(v.get("start_time")), _num(a.get("start_time")) if a else 0.0
    transfer = (v.get("color_transfer") or "").lower()
    return {
        "codec": v["codec_name"],
        "width": w,
        "height": h,
        "fps": round(r_fps, 3),
        "vfr": abs(r_fps - avg_fps) > 0.05,
        "rotation": rotation,
        "duration": dur,
        "has_audio": a is not None,
        "audio_channels": int(a.get("channels") or 0) if a else 0,
        "audio_index": a_idx,
        "audio_tracks": len(auds),
        # zvuk koji počinje kasnije/ranije od slike (screen recorder, browser, neki Android) — poravnava se u
        # normalize, inače svaki rez i titl kasni za ovoliko (QA 0.8.0, P0)
        "av_offset": round(a_start - v_start, 3) if a else 0.0,
        "hdr": transfer in ("smpte2084", "arib-std-b67"),
        "bit_depth": 10 if "10" in (v.get("pix_fmt") or "") else 8,
    }


def nearest_standard_fps(fps: float) -> float:
    return min(STANDARD_FPS, key=lambda s: abs(s - fps))


def normalize(src: Path, info: dict, video_out: Path, audio_out: Path) -> dict:
    """Video bez zvuka za Remotion (+ CFR ako treba) i zvuk u punom kvalitetu (WAV 48 kHz)."""
    video_out.parent.mkdir(parents=True, exist_ok=True)
    audio_out.parent.mkdir(parents=True, exist_ok=True)
    fps = info["fps"]
    w, h = info["width"], info["height"]
    # Uspravan snimak koji nije tačno 9:16 (Android 9:20, 3:4, 4:5…) → tačno 1080×1920 (cover): lice, titlovi i
    # hook se računaju u tom kadru. Bez ovoga Basic je crtao sliku uvećanu/odsečenu (QA 0.8.0, P0).
    portrait_off = h > w and abs(w / h - 9 / 16) > 0.01
    odd = (w % 2) or (h % 2)
    hdr = bool(info.get("hdr"))
    deep = info.get("bit_depth", 8) > 8  # 10-bit (i SDR) → 8-bit yuv420p
    reencode = info["vfr"] or info["rotation"] or info["codec"] not in ("h264", "hevc") \
        or abs(nearest_standard_fps(fps) - fps) > 0.01 or portrait_off or odd or hdr or deep
    if reencode:
        if info["vfr"]:  # VFR telefon: najbliži standardni fps prosečnom (ne uvek 30 — 60 fps telefon ostaje 60)
            fps = nearest_standard_fps(info["fps"]) if info["fps"] <= 61 else 60.0
        else:
            fps = nearest_standard_fps(fps)
        vf = []
        if hdr:  # iPhone HDR (HLG/PQ, 10-bit) → SDR bt709 8-bit, da svi koraci vide istu sliku kao gledalac
            vf.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
                      "zscale=t=bt709:m=bt709:r=tv")
        vf.append(f"fps={fps}")
        if portrait_off:
            vf.append("scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920")
        else:
            vf.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")  # libx264 + yuv420p traže parne dimenzije
        args = ["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-map", "0:v:0", "-an", "-vf", ",".join(vf),
                "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
                "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                "-movflags", "+faststart", str(video_out)]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0 and hdr:  # ffmpeg bez zscale-a: bar 8-bit, bez tonemap-a
            args[args.index("-vf") + 1] = ",".join(vf[1:])
            r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"CCC_CONVERT_FAILED: the video couldn't be converted.\n{r.stderr[-1200:]}")
    else:
        run("ffmpeg", "-hide_banner", "-y", "-i", str(src), "-map", "0:v:0", "-an", "-c", "copy",
            "-movflags", "+faststart", str(video_out))
    if info["has_audio"]:
        af = []
        off = float(info.get("av_offset") or 0.0)
        if off > 0.01:  # zvuk kreće posle slike → tišina na početku, da uzorak 0 = prvi kadar
            af.append(f"adelay={int(round(off * 1000))}:all=1")
        elif off < -0.01:  # zvuk kreće pre slike → odseci višak
            af.append(f"atrim=start={-off:.3f},asetpts=PTS-STARTPTS")
        args = ["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-map", f"0:a:{info.get('audio_index', 0)}", "-vn"]
        if af:
            args += ["-af", ",".join(af)]
        if int(info.get("audio_channels") or 0) > 2:  # 5.1/više kanala → stereo (analiza i čišćenje očekuju ≤ 2)
            args += ["-ac", "2"]
        run(*args, "-ar", "48000", "-c:a", "pcm_s24le", str(audio_out))
    return {"fps": fps, "reencoded": bool(reencode), "portrait_fit": bool(portrait_off), "hdr_to_sdr": bool(hdr)}


def decode_mono(path: Path, rate: int = 16000) -> np.ndarray:
    """Zvuk kao mono float32 (za Whisper i analizu energije) — preko ffmpeg-a, ne PyAV."""
    pcm = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)
