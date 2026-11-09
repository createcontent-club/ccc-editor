"""Gde u snimku zaista ima govora — osnova za SAV tajming (Whisper određuje samo tekst).

Histereza sa dva praga:
  - govor se PRONALAZI jakim pragom (šum + 12 dB), da šum i dah ne prođu kao govor;
  - pa se njegove ivice PROŠIRUJU slabim pragom (šum + 6 dB), da tihi početni i krajnji
    suglasnici (h, f, s, t) ostanu unutar dela.
"""
from __future__ import annotations

import numpy as np

HOP = 0.01      # 10 ms prozori
RATE = 16000


class Energy:
    CLICK = 5       # zvuk ≤ 50 ms je klik/kvrc, ne govor
    JOIN = 5        # rupe ≤ 50 ms unutar reči se zatvaraju
    EXTEND = 15     # ivice se šire slabim pragom najviše 150 ms

    def __init__(self, audio: np.ndarray, floor: float | None = None):
        n = int(HOP * RATE)
        frames = audio[: len(audio) // n * n].reshape(-1, n)
        self.db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
        # Prag se meri na ORIGINALU; za isečen zvuk prosleđujemo floor originala.
        self.floor = float(np.percentile(self.db, 10)) if floor is None else floor
        self.hi = self.db > self.floor + 12
        self.lo = self.db > self.floor + 6
        self.duration = len(self.db) * HOP
        self.runs = self._runs()
        self.mask = np.zeros(len(self.db), dtype=bool)
        for s, e in self.runs:
            self.mask[int(round(s / HOP)):int(round(e / HOP))] = True

    def _runs(self) -> list[tuple[float, float]]:
        runs, k, n = [], 0, len(self.hi)
        while k < n:
            if self.hi[k]:
                s = k
                while k < n and self.hi[k]:
                    k += 1
                runs.append([s, k])
            else:
                k += 1
        merged: list[list[int]] = []
        for s, e in runs:
            if merged and s - merged[-1][1] <= self.JOIN:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        out = []
        for s, e in merged:
            if e - s <= self.CLICK:
                continue
            lim = max(0, s - self.EXTEND)
            while s > lim and self.lo[s - 1]:
                s -= 1
            lim = min(n, e + self.EXTEND)
            while e < lim and self.lo[e]:
                e += 1
            if out and s <= out[-1][1]:
                out[-1] = (out[-1][0], e * HOP)
            else:
                out.append((s * HOP, e * HOP))
        return [(round(s, 2), round(e, 2)) for s, e in out]

    def speech(self, k: int) -> bool:
        return 0 <= k < len(self.mask) and bool(self.mask[k])

    def utterances(self, gap: float) -> list[tuple[float, float]]:
        """Izgovoreni delovi: govor razdvojen tišinom ≥ gap."""
        out: list[list[float]] = []
        for s, e in self.runs:
            if out and s - out[-1][1] < gap:
                out[-1][1] = e
            else:
                out.append([s, e])
        return [(s, e) for s, e in out]

    def gaps(self) -> list[tuple[float, float]]:
        """Tišine između govora (bez početka i kraja snimka)."""
        return [(a[1], b[0]) for a, b in zip(self.runs, self.runs[1:])]


class Voice:
    """GLAS (ne samo zvuk) — osnova za tajming rezova.

    Energy brka uzdah sa govorom: uzdah je +8…+20 dB iznad šuma, a govor +18…+45 dB.
    Zato glas = Silero VAD (neuronska mreža, prepoznaje govor, ignoriše dah) ∪ vrlo jak zvuk
    (> +25 dB, jače od svakog uzdaha), pa se ivice prošire samo na suglasnike odmah uz glas
    (> +20 dB, najviše 80 ms) — 'D' u "Do", 's' u "So".
    Izmereno na test-video-1: uzdah pre "Do" je +8…+16 dB i Silero 0.04 → nije glas.
    """
    CORE_P = 0.5
    MIN_REL = 10.0
    STRONG = 25.0
    CONSONANT = 20.0
    EXTEND = 8      # × 10 ms
    CLICK = 5       # jak zvuk ≤ 50 ms bez Silero potvrde = klik/kvrc
    JOIN = 2        # rupe ≤ 20 ms između ostrva glasa se zatvaraju

    def __init__(self, audio: np.ndarray, floor: float | None = None):
        from faster_whisper.vad import get_vad_model

        base = Energy(audio, floor)
        self.floor, self.rel = base.floor, base.db - base.floor
        n = len(self.rel)
        padded = np.pad(audio, (0, (-len(audio)) % 512))
        probs = np.asarray(get_vad_model()(padded)).reshape(-1)
        idx = np.minimum(len(probs) - 1, (np.arange(n) * int(HOP * RATE)) // 512)
        self.prob = probs[idx]
        # Silero je preosetljiv na tihe zvukove (šapat, pozadina): glas mora biti bar +10 dB iznad šuma.
        silero = (self.prob > self.CORE_P) & (self.rel > self.MIN_REL)
        strong = self.rel > self.STRONG
        # Jak zvuk bez Silero potvrde mora trajati > 50 ms (inače je klik).
        k = 0
        while k < n:
            if strong[k] and not silero[k]:
                j = k
                while j < n and strong[j] and not silero[j]:
                    j += 1
                touches = (k > 0 and silero[k - 1]) or (j < n and silero[j])
                if j - k <= self.CLICK and not touches:
                    strong[k:j] = False
                k = j
            else:
                k += 1
        core = silero | strong
        mask = core.copy()
        for k in range(n):
            if core[k] and (k == 0 or not core[k - 1]):
                b = k
                while b > 0 and k - b < self.EXTEND and self.rel[b - 1] > self.CONSONANT:
                    b -= 1
                    mask[b] = True
            if core[k] and (k == n - 1 or not core[k + 1]):
                e = k
                while e < n - 1 and e - k < self.EXTEND and self.rel[e + 1] > self.CONSONANT:
                    e += 1
                    mask[e] = True
        # Ostrva glasa razdvojena sa ≤ 20 ms su isti zvuk (pad energije usred sloga).
        k = 0
        while k < n:
            if not mask[k]:
                j = k
                while j < n and not mask[j]:
                    j += 1
                if 0 < k and j < n and j - k <= self.JOIN:
                    mask[k:j] = True
                k = j
            else:
                k += 1
        self.mask = mask
        self.duration = n * HOP
        self.runs = []
        k = 0
        while k < n:
            if mask[k]:
                j = k
                while j < n and mask[j]:
                    j += 1
                self.runs.append((round(k * HOP, 2), round(j * HOP, 2)))
                k = j
            else:
                k += 1

    def speech(self, k: int) -> bool:
        return 0 <= k < len(self.mask) and bool(self.mask[k])
