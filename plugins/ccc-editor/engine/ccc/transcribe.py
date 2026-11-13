"""Transkripcija po izgovorenim delovima.

Whisper nad celim snimkom "sakriva" ponovljene pokušaje (razvuče reči preko njih i vrati
jednu čistu rečenicu). Zato snimak prvo delimo na izgovorene delove po energiji zvuka, a
Whisper svaki deo transkribuje NEZAVISNO (u paketu) — svaki pokušaj dobija svoj tekst.
"""
from __future__ import annotations

import difflib
import os
import re
import time

from .energy import Energy
from .media import decode_mono
from .project import MODELS

# Whisper inače "počisti" poštapalice iz teksta; ovaj prompt ga tera da ih zapiše.
FILLER_PROMPT = "Umm, let me think like, hmm... Okay, here's what I'm, like, thinking. Uh, so, you know, I mean."
PAD = 0.15  # malo tišine oko svakog dela da Whisper ne odseče prvu/poslednju reč
LONG_PART = 28.0  # s: duži deo paket ne transkribuje do kraja (limit 30 s) → pojedinačna transkripcija


class _Shift:
    """Segment pojedinačne transkripcije pomeren na vreme celog snimka (isti oblik kao segmenti iz paketa)."""
    class _W:
        def __init__(self, w, d):
            self.word, self.start, self.end, self.probability = w.word, w.start + d, w.end + d, w.probability

    def __init__(self, sg, d: float):
        self.text, self.start, self.end = sg.text, sg.start + d, sg.end + d
        self.words = [self._W(w, d) for w in sg.words or []]


def transcribe(audio_path, utterance_gap: float, language: str = "en") -> dict:
    from faster_whisper import BatchedInferencePipeline, WhisperModel

    audio = decode_mono(audio_path)
    energy = Energy(audio)
    utts = energy.utterances(utterance_gap)
    dur = len(audio) / 16000
    t0 = time.time()
    model = WhisperModel(str(MODELS / "whisper" / "large-v3-turbo"), device="cpu", compute_type="int8",
                         cpu_threads=os.cpu_count() or 4)
    if not utts:
        raise SystemExit("CCC_NO_SPEECH: no speech was found in this video's sound (silent, or only music/noise).")
    # Jezik se proverava PRE transkripcije: Whisper je zaključan na engleski, pa bi nemački/srpski govor dao
    # besmislene engleske titlove, a sve provere bi prošle (QA 0.8.0, P0). Uzorak = prvih ~30 s samog govora.
    sample, n = [], 0
    for s, e in utts:
        seg = audio[int(s * 16000):int(e * 16000)]
        sample.append(seg)
        n += len(seg)
        if n >= 30 * 16000:
            break
    import numpy as np
    lang, prob, _ = model.detect_language(audio=np.concatenate(sample)[:30 * 16000])
    detected = {"language": lang, "probability": round(float(prob), 3)}
    if language == "en" and lang != "en" and prob >= 0.6:
        raise SystemExit(f"CCC_NOT_ENGLISH:{lang}:{prob:.2f}: the speech in this video is not English "
                         f"(detected '{lang}', {prob:.0%} sure). The editor supports English speech only.")
    pipe = BatchedInferencePipeline(model)
    clips = [{"start": max(0.0, s - PAD), "end": min(dur, e + PAD)} for s, e in utts]
    segs, _ = pipe.transcribe(audio, language=language, clip_timestamps=clips, word_timestamps=True,
                              batch_size=8, initial_prompt=FILLER_PROMPT, condition_on_previous_text=False)
    segs = list(segs)

    # Paket (BatchedInferencePipeline) transkribuje SAMO prvih 30 s svakog dela, a reči posle toga nestanu ili dobiju
    # "slepljena" vremena; deo segmenta može i da "ispadne" u susedni kratak deo (aazar-trial-1: u41 od 0.35 s sa 58
    # reči). Takve delove ponovo transkribujemo pojedinačno (bez paketa, Whisper sam ide kroz ceo deo).
    redo: dict[int, list] = {}
    for ui, (us, ue) in enumerate(utts):
        inside = [sg for sg in segs if us - PAD <= (sg.start + sg.end) / 2 <= ue + PAD]
        nw = sum(len(sg.words or []) for sg in inside)
        glued = sum(1 for sg in inside for w in sg.words or [] if w.end - w.start < 0.03)
        if ue - us > LONG_PART or (nw and nw / max(0.2, ue - us) > 7.0) or glued > 2:
            s0 = max(0.0, us - PAD)
            clip = audio[int(s0 * 16000):int(min(dur, ue + PAD) * 16000)]
            rs, _ = model.transcribe(clip, language=language, word_timestamps=True, vad_filter=False,
                                     condition_on_previous_text=False, initial_prompt=FILLER_PROMPT)
            redo[ui] = [_Shift(sg, s0) for sg in rs]
    if redo:
        print(f"  ponovo transkribovano bez paketa (dugi/slepljeni delovi): {len(redo)}")

    words: list[dict] = []
    utterances: list[dict] = []
    for ui, (us, ue) in enumerate(utts):
        first = len(words)
        texts = []
        for sg in (redo[ui] if ui in redo else segs):
            mid = (sg.start + sg.end) / 2
            if not (us - PAD <= mid <= ue + PAD):
                continue
            texts.append(sg.text.strip())
            for w in sg.words or []:
                text = w.word.strip()
                if not text:
                    continue
                # Whisper cepa brojeve i složenice ("$3" ",600", "12" "-year") — spajamo ih.
                if len(words) > first and (text[0] in ",.%-" or words[-1]["text"].endswith("-")):
                    words[-1]["text"] += text
                    words[-1]["end"] = round(min(w.end, ue), 3)
                    continue
                words.append({"id": f"w{len(words)}", "text": text, "u": ui,
                              "start": round(max(w.start, us), 3), "end": round(min(w.end, ue), 3),
                              "prob": round(w.probability, 3)})
        # Halucinacija na kratkom šumu: Whisper "čuje" celu frazu ("Okay, here we go.", "We'll be right back.") u
        # delu od 0.1–0.3 s — više od 8 reči u sekundi to ne može da bude govor → deo ostaje bez reči (šum).
        n_new = len(words) - first
        if n_new >= 3 and n_new / max(0.05, ue - us) > 8.0 and ue - us < 1.0:
            del words[first:]
            texts = []
        utterances.append({"id": f"u{ui}", "start": us, "end": ue, "text": " ".join(texts),
                           "from": words[first]["id"] if len(words) > first else None,
                           "to": words[-1]["id"] if len(words) > first else None})
    retime_numbers(audio_path, words, utterances, model)
    return {"language": language, "detected": detected, "words": words, "utterances": utterances,
            "seconds": round(time.time() - t0, 1)}


# ------------------------------------------------------------------ brojevi
NUMBER_PROMPT = ("Thirty six hundred dollars. One hundred and fifty thousand dollars. Twelve percent. "
                 "Nineteen ninety nine. Two thousand and twenty five.")
_HAS_NUMBER = re.compile(r"[\d$€£%]")


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9']", "", t.lower())


def retime_numbers(audio_path, words: list[dict], utterances: list[dict], model=None) -> list[str]:
    """Whisper broj ("$3,600") zapiše kao jedan token i da mu prekratko vreme — pa i susedne reči
    dobiju pogrešna vremena (u test-video-1 je "but" krenuo usred "dollars"). Za svaki izgovoreni deo
    sa brojem ili simbolom radimo drugi prolaz u kom se brojevi pišu rečima ("thirty six hundred
    dollars"), poravnamo ga sa originalnim rečima i preuzmemo vremena. Tekst ostaje originalan."""
    from faster_whisper import WhisperModel

    audio = decode_mono(audio_path)
    if model is None:
        model = WhisperModel(str(MODELS / "whisper" / "large-v3-turbo"), device="cpu", compute_type="int8",
                             cpu_threads=os.cpu_count() or 4)
    changed = []
    for ui, u in enumerate(utterances):
        uw = [w for w in words if w["u"] == ui]
        if not any(_HAS_NUMBER.search(w["text"]) for w in uw):
            continue
        s0 = max(0.0, u["start"] - PAD)
        clip = audio[int(s0 * 16000):int((u["end"] + PAD) * 16000)]
        segs, _ = model.transcribe(clip, language="en", word_timestamps=True, vad_filter=False,
                                   condition_on_previous_text=False, initial_prompt=NUMBER_PROMPT)
        sp = [(w.word.strip(), s0 + w.start, s0 + w.end) for sg in segs for w in sg.words or [] if w.word.strip()]
        if _HAS_NUMBER.search(" ".join(t for t, _, _ in sp)):
            continue  # drugi prolaz je opet napisao cifre — nema boljeg tajminga
        a = [_norm(w["text"]) for w in uw]
        b = [_norm(t) for t, _, _ in sp]
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op == "equal":
                for k in range(i2 - i1):
                    uw[i1 + k]["start"], uw[i1 + k]["end"] = round(sp[j1 + k][1], 3), round(sp[j1 + k][2], 3)
            elif op == "replace" and j2 > j1:
                # npr. ["$3,600"] ↔ ["thirty","six","hundred","dollars"]: raspon se deli srazmerno dužini teksta
                t0, t1 = sp[j1][1], sp[j2 - 1][2]
                lens = [max(1, len(w["text"])) for w in uw[i1:i2]]
                acc = t0
                for k, ln in enumerate(lens):
                    end = t1 if k == len(lens) - 1 else acc + (t1 - t0) * ln / sum(lens)
                    uw[i1 + k]["start"], uw[i1 + k]["end"] = round(acc, 3), round(end, 3)
                    acc = end
                changed += [w["text"] for w in uw[i1:i2]]
    return changed


def listen(audio_path, start: float, end: float) -> list[tuple[float, float, str, float]]:
    """Ponovo preslušaj deo snimka (izvorno vreme, s) — za nesigurne reči: ime koje Whisper nije čuo, pogrešna reč
    u hook-u (test ai-actor-0: "The first…" je bilo "The most…", a ime "Fang Taozi" je bilo progutano u "And")."""
    from faster_whisper import WhisperModel
    audio = decode_mono(audio_path)
    clip = audio[int(max(0.0, start) * 16000):int(end * 16000)]
    model = WhisperModel(str(MODELS / "whisper" / "large-v3-turbo"), device="cpu", compute_type="int8",
                         cpu_threads=os.cpu_count() or 4)
    segs, _ = model.transcribe(clip, language="en", word_timestamps=True, condition_on_previous_text=False)
    return [(round(start + w.start, 2), round(start + w.end, 2), w.word.strip(), round(w.probability, 2))
            for sg in segs for w in sg.words]
