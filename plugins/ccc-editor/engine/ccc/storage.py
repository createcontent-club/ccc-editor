"""Disk: izvoz u verzijama, čišćenje teških fajlova starih projekata i njihovo vraćanje kad zatrebaju.

QA 0.8.0 (P1-20, faza 2): izvoz je tiho prepisivao prethodni `-CCC-edit.mp4` (i klijentove izmene na njemu), a
svaki projekat je zauvek držao 3–4 GB (normalizovan snimak, zvuk, renderi) — posle 10 videa klijentu nestane diska.
Sve što se ovde briše može da se napravi ponovo iz originalnog snimka; odluke (project.json), izbori i asseti ostaju.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from .project import PUBLIC_JOBS, WORK, Job, same_source

# Teški fajlovi koji se prave ponovo iz originala (normalize → zvuk/slika, audio fix, render).
HEAVY_PUBLIC = ("video.mp4", "video-wide.mp4", "video-reframe.mp4", "voice.wav")
HEAVY_WORK = ("final.mp4", "final.part.mp4", "preview.mp4", "source-audio.wav", "source-audio-fixed.wav",
              "voice-unnormalized.wav", "render-props.json")
HEAVY_DIRS = ("ab", "stills")
AUTO_CLEAN_DAYS = 14
GB = 1024 ** 3


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    if p.is_dir():
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    return 0


def _heavy(job: Job) -> list[Path]:
    return ([job.public / f for f in HEAVY_PUBLIC] + [job.dir / f for f in HEAVY_WORK]
            + [job.dir / d for d in HEAVY_DIRS])


def project_size(job: Job) -> int:
    return _size(job.dir) + _size(job.public)


def last_used(job: Job) -> float:
    try:
        return job.file.stat().st_mtime
    except OSError:
        return 0.0


def clean(job: Job) -> int:
    """Briše teške fajlove projekta (odluke, izbori, asseti i izvezen video ostaju). Vraća oslobođene bajtove."""
    freed = 0
    for f in _heavy(job):
        freed += _size(f)
        shutil.rmtree(f, ignore_errors=True) if f.is_dir() else f.unlink(missing_ok=True)
        (f.parent / f"._{f.name}").unlink(missing_ok=True)  # exFAT/macOS pratioci
    if job.exists:
        used = last_used(job)
        p = job.load()
        p["cleaned"] = time.strftime("%Y-%m-%d")
        p.pop("reframe", None)  # reframe se pravi ponovo zajedno sa snimkom
        job.save(p)
        os.utime(job.file, (used, used))  # čišćenje nije "rad na projektu" — datum poslednje upotrebe ostaje
    return freed


def projects() -> list[Job]:
    return [Job(d.name) for d in sorted(WORK.iterdir()) if (d / "project.json").exists()] if WORK.exists() else []


def auto_clean(skip: str | None = None, days: float = AUTO_CLEAN_DAYS) -> list[tuple[str, int]]:
    """Izvezeni projekti koji nisu dirani `days` dana: teški fajlovi se brišu (pri svakom `prepare`)."""
    out = []
    for job in projects():
        if job.name == skip or time.time() - last_used(job) < days * 86400:
            continue
        try:
            p = job.load()
        except (OSError, json.JSONDecodeError, SystemExit):
            continue
        if not p.get("exported") or p.get("cleaned") and not any(f.exists() for f in _heavy(job)):
            continue
        if not _try_lock(job):
            continue  # neko baš radi na njemu
        freed = clean(job)
        if freed:
            out.append((job.name, freed))
    return out


def _try_lock(job: Job) -> bool:
    try:
        job.lock(wait_s=0)
        return True
    except SystemExit:
        return False


def free_bytes(path: Path) -> int:
    path = Path(path)
    while not path.exists() and path != path.parent:
        path = path.parent
    return shutil.disk_usage(path).free


def need_space(src_size: int) -> int:
    """Procena za novi projekat: normalizovan snimak (~1–2× original) + zvuk + render + rezerva 1 GB."""
    return int(2.2 * src_size) + GB


def space_report() -> str:
    rows = []
    for job in projects():
        s = project_size(job)
        if s > 50 * 1024 ** 2:
            days = (time.time() - last_used(job)) / 86400
            rows.append(f"  {job.name:40s} {s / GB:5.1f} GB · poslednji put pre {days:.0f} d")
    return "\n".join(rows) or "  (nema projekata sa teškim fajlovima)"


def ensure_media(job: Job, p: dict) -> bool:
    """Očišćen (ili ručno obrisan) projekat: snimak i zvuk se prave ponovo iz originala pre komande koja ih traži.
    Vraća True ako je nešto vraćeno."""
    src_audio, video = job.dir / "source-audio.wav", job.public / "video.mp4"
    wide = job.public / "video-wide.mp4"
    if src_audio.exists() and (video.exists() or wide.exists()):
        return False
    s = p.get("source") or {}
    src = Path(s.get("path", ""))
    if not src.is_file() or not same_source(p, src):
        raise SystemExit(f"CCC_SOURCE_MISSING: the original video for '{job.name}' is no longer at {src} (or it changed). "
                         "Its large files were cleaned to save disk space — drag the original video in again "
                         "(same file), or start over with `ccc prepare <video> --force`.")
    from .media import normalize, probe
    print(f"▶ Vraćam snimak projekta iz originala ({src.name}) — teški fajlovi su bili očišćeni…", flush=True)
    info = probe(src)
    norm = normalize(src, info, video, src_audio)
    if abs(float(norm["fps"]) - float(p["fps"])) > 0.01:
        raise SystemExit(f"CCC_SOURCE_MISSING: the video at {src} gives {norm['fps']} fps, the project was made "
                         f"at {p['fps']} fps — it is not the same recording.")
    p.pop("reframe", None)
    if info["width"] > info["height"]:  # horizontalan snimak: original → video-wide.mp4, Split Screen dobija reframe
        from .__main__ import _speaker_video
        _speaker_video(job, p)
    if p.get("audio"):  # audio fix je bio uključen → obrađen izvor ponovo
        from .audio import fix_source, speech_mask
        p["audio"] = {**p["audio"], **fix_source(job, p, speech_mask(src_audio))}
    if p.get("segments"):
        from .audio import finalize_voice
        finalize_voice(job, p)
    p.pop("cleaned", None)
    job.save(p)
    return True


def export_path(src: Path) -> Path:
    """`<ime>-CCC-edit.mp4`; ako postoji → `-v2`, `-v3`… (prethodna verzija ostaje netaknuta)."""
    base = src.with_name(f"{src.stem}-CCC-edit.mp4")
    if not base.exists():
        return base
    i = 2
    while src.with_name(f"{src.stem}-CCC-edit-v{i}.mp4").exists():
        i += 1
    return src.with_name(f"{src.stem}-CCC-edit-v{i}.mp4")


def export(final: Path, src: Path) -> tuple[Path, str | None]:
    """Kopija gotovog videa pored originala (preko .part fajla — nikad pola fajla pod pravim imenom).
    Folder originala nije upisiv (USB samo za čitanje, iCloud, mrežni disk) → Desktop → ostaje u folderu projekta."""
    homes = [src.parent, Path.home() / "Desktop"]
    last_err = None
    for folder in homes:
        dest = export_path(folder / src.name)
        part = dest.with_name(dest.name + ".part")
        try:
            if free_bytes(folder) < final.stat().st_size + 50 * 1024 ** 2:
                raise OSError("disk is full")
            shutil.copyfile(final, part)
            os.replace(part, dest)
            note = None if folder == src.parent else (
                f"the video's own folder ({src.parent}) is not writable ({last_err}) — saved to {folder} instead")
            return dest, note
        except OSError as err:
            last_err = err
            part.unlink(missing_ok=True)
    return final, f"could not copy the video next to the original ({last_err}) — it is at {final}"
