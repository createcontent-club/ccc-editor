"""Audio fix: izmeri → izaberi lanac → primeni → glasnoća na isečenom zvuku.

Redosled (zašto):
  1. Obrada (highpass, šum, de-esser, kompresor) ide na CEO izvorni zvuk — uklanjanje šuma
     radi bolje sa kontekstom, a rezovi se ne menjaju (detekcija glasa koristi sirov zvuk).
  2. Sečenje (isti segmenti kao pre) → mikro-fade na rezovima.
  3. Glasnoća se meri i podešava na ISEČENOM zvuku (izbacivanje pauza menja prosek):
     -14 LUFS (IG/TikTok/Shorts), vrh ≤ -1 dBTP, limiter bez "pumpanja".
Svaki korak se uključuje samo ako ga merenje traži; izveštaj kaže šta je izmereno i zašto.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

from .assemble import build_voice
from .media import decode_mono, run
from .project import MODELS, ff_path

TARGET_LUFS, TARGET_TP = -14.0, -1.0
LIMIT_DB = -1.5  # limiter po uzorku; ostavlja mesta za true-peak
WORK_SPEECH_DB = -22.0  # radni nivo govora (medijana glasa) pre de-essera i kompresora


# ------------------------------------------------------------------ merenja
def loudness(path: Path) -> dict:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summ = out[out.rfind("Summary:"):]
    get = lambda k: float(re.search(rf"{k}:\s+(-?[\d.]+|-inf)", summ).group(1).replace("-inf", "-120"))
    return {"lufs": get("I"), "lra": get("LRA"), "tp": get("Peak")}


def _band(sig: np.ndarray, lo: float, hi: float) -> float:
    S = np.abs(np.fft.rfft(sig * np.hanning(len(sig)))) ** 2
    f = np.fft.rfftfreq(len(sig), 1 / 48000)
    return float(S[(f >= lo) & (f < hi)].sum() / max(S.sum(), 1e-20))


def profile(path: Path, voice_mask: np.ndarray) -> dict:
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ar", "48000", "-"],
                         capture_output=True, check=True).stdout
    ch = 2 if subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=channels", "-of", "csv=p=0",
                              str(path)], capture_output=True, text=True).stdout.strip() == "2" else 1
    x = np.frombuffer(pcm, np.float32).reshape(-1, ch)
    corr = float(np.corrcoef(x[:, 0], x[:, 1])[0, 1]) if ch == 2 else 1.0
    lvl = [20 * np.log10(np.sqrt((x[:, c] ** 2).mean()) + 1e-12) for c in range(ch)]
    mono = x.mean(axis=1)
    n = 480
    fr = mono[: len(mono) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-12)
    m = voice_mask[: len(db)]
    if len(m) < len(db):
        m = np.concatenate([m, np.zeros(len(db) - len(m), bool)])
    speech = np.concatenate(fr[np.where(m)[0][:4000]]) if m.any() else mono
    return {
        "channels": ch, "corr": round(corr, 3), "channel_db": [round(float(v), 1) for v in lvl],
        "peak": round(float(20 * np.log10(np.abs(x).max() + 1e-12)), 1),
        "clipped": int((np.abs(x) >= 0.999).sum()),
        "noise": round(float(np.median(db[~m])), 1) if (~m).any() else -90.0,
        "speech": round(float(np.median(db[m])), 1) if m.any() else -30.0,
        "sibilance": round(100 * _band(speech, 5000, 9000), 1),
        "air": round(100 * _band(speech, 9000, 24000), 2),
        "rumble": round(100 * _band(speech, 0, 80), 2),
    }


# ------------------------------------------------------------------ odluke
def plan(prof: dict) -> dict:
    steps, why = [], []
    # Kanali: dual-mono → identični kanali; jedan kanal prazan/tih → uzmi glasniji.
    if prof["channels"] == 2 and prof["corr"] < 0.98 and abs(prof["channel_db"][0] - prof["channel_db"][1]) > 15:
        c = 0 if prof["channel_db"][0] > prof["channel_db"][1] else 1
        steps.append(f"pan=stereo|c0=c{c}|c1=c{c}")
        why.append(f"jedan kanal je {abs(prof['channel_db'][0] - prof['channel_db'][1]):.0f} dB tiši → koristi se glasniji")
    elif prof["channels"] == 2:
        steps.append("pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1")
        why.append("glas je mono (oba kanala ista)" if prof["corr"] >= 0.98 else "kanali spojeni u mono")

    steps.append("highpass=f=80:poles=2")
    why.append("highpass 80 Hz: brum, udarci u mikrofon")

    noise, snr = prof["noise"], prof["speech"] - prof["noise"]
    if noise <= -65 and snr >= 30:
        tier = "čist"
        steps.append(f"afftdn=nr=6:nf={max(-80, round(noise))}")
    elif noise <= -50 and snr >= 20:
        tier = "srednji šum"
        steps.append(f"afftdn=nr=12:nf={max(-80, round(noise))}")
    else:
        tier = "jak šum"
        steps.append(f"arnndn=m='{ff_path(MODELS / 'rnnoise' / 'sh.rnnn')}':mix=0.8")
        steps.append(f"afftdn=nr=12:nf={max(-80, round(noise))}")
    why.append(f"šum {noise} dBFS, SNR {snr:.0f} dB → {tier}")

    # De-esser i kompresor zavise od apsolutnog nivoa (izmereno: deesser i=0.4 na -28 dBFS ne radi
    # ništa, na radnom nivou spušta "s" vrhove 4.6 dB) → govor prvo na stalni radni nivo.
    pre = WORK_SPEECH_DB - prof["speech"]
    steps.append(f"volume={pre:.2f}dB")
    why.append(f"govor {prof['speech']} → {WORK_SPEECH_DB} dBFS (radni nivo za de-esser i kompresor)")

    if prof["sibilance"] > 10:
        steps.append("deesser=i=0.5:m=0.5:f=0.5")
        why.append(f"šištanje {prof['sibilance']}% (5–9 kHz) → jači de-esser (\"s\" vrhovi ≈ -7 dB)")
    elif prof["sibilance"] > 8:
        steps.append("deesser=i=0.4:m=0.5:f=0.5")
        why.append(f"šištanje {prof['sibilance']}% → umeren de-esser (\"s\" vrhovi ≈ -4.5 dB)")

    thr_db = WORK_SPEECH_DB + 6  # kompresor hvata samo glasnije delove govora
    steps.append(f"acompressor=threshold={10 ** (thr_db / 20):.5f}:ratio=2.5:attack=5:release=120:knee=4")
    why.append(f"kompresor 2.5:1 od {thr_db:.0f} dBFS")
    return {"tier": tier, "chain": ",".join(steps), "why": why}


# ------------------------------------------------------------------ primena
def _normalize(src: Path, dst: Path, total: float) -> dict:
    """Pojačanje do -14 LUFS + limiter; drugi prolaz ispravlja ostatak posle limitera."""
    gain = TARGET_LUFS - loudness(src)["lufs"]
    limit = 10 ** (LIMIT_DB / 20)
    for _ in range(2):
        run("ffmpeg", "-hide_banner", "-y", "-i", str(src), "-af",
            f"volume={gain:.2f}dB,alimiter=limit={limit:.4f}:attack=5:release=50:level=0,atrim=0:{total:.5f}",
            "-ar", "48000", "-c:a", "pcm_s24le", str(dst))
        m = loudness(dst)
        if abs(m["lufs"] - TARGET_LUFS) <= 0.3:
            break
        gain += TARGET_LUFS - m["lufs"]
    return {**m, "gain_db": round(gain, 2)}


def fix_source(job, p: dict, voice_mask: np.ndarray) -> dict:
    src = job.dir / "source-audio.wav"
    prof = profile(src, voice_mask)
    pl = plan(prof)
    # float32: posle pojačanja vrhovi privremeno prelaze 0 dBFS — limiter ih tek na kraju vraća na -1 dBTP.
    run("ffmpeg", "-hide_banner", "-y", "-i", str(src), "-af", pl["chain"], "-ar", "48000", "-c:a", "pcm_f32le",
        str(job.dir / "source-audio-fixed.wav"))
    return {"before": prof, **pl}


def finalize_voice(job, p: dict) -> float:
    """Isečen zvuk → voice.wav. Sa audio fix-om: iz obrađenog izvora + glasnoća na -14 LUFS."""
    video_dur = sum(s["vFrames"] for s in p["segments"]) / p["fps"]
    fixed = job.dir / "source-audio-fixed.wav"
    out = job.public / "voice.wav"
    if not p.get("audio") or not fixed.exists():
        return build_voice(job.dir / "source-audio.wav", p["segments"], out, p["cut"]["fade"], video_dur)
    tmp = job.dir / "voice-unnormalized.wav"
    build_voice(fixed, p["segments"], tmp, p["cut"]["fade"], video_dur, codec="pcm_f32le")
    p["audio"]["after"] = _normalize(tmp, out, video_dur)
    tmp.unlink(missing_ok=True)
    return video_dur


def ab_files(job, p: dict) -> tuple[Path, Path]:
    """A/B za slušanje: PRE = isečen sirov zvuk samo pojačan na -14 LUFS (fer poređenje), POSLE = voice.wav."""
    video_dur = sum(s["vFrames"] for s in p["segments"]) / p["fps"]
    ab = job.dir / "ab"
    ab.mkdir(exist_ok=True)
    raw = ab / "raw-cut.wav"
    build_voice(job.dir / "source-audio.wav", p["segments"], raw, p["cut"]["fade"], video_dur)
    before, after = ab / "PRE-samo-glasnoca.wav", ab / "POSLE-audio-fix.wav"
    _normalize(raw, before, video_dur)
    raw.unlink(missing_ok=True)
    shutil.copy(job.public / "voice.wav", after)
    return before, after


def after_profile(job, voice_mask_out: np.ndarray) -> dict:
    return profile(job.public / "voice.wav", voice_mask_out)


def speech_mask(path: Path, floor: float | None = None) -> np.ndarray:
    from .energy import Voice
    return Voice(decode_mono(path), floor=floor).mask
