"""Jingle promo originale (nessun copyright): synth anni '80, 128 BPM, Do maggiore.
Giro C - G - Am - F, cassa dritta, clap, charleston, basso a ottave, stab di accordi
"supersaw" in levare e arpeggio a campanella. Genera un loop lungo quanto serve."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 128
BEAT = 60 / BPM
BAR = 4 * BEAT


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def env(n, a=0.005, d=0.15, s=0.0, r=0.05, hold=None):
    t = np.arange(n) / SR
    e = np.where(t < a, t / a, s + (1 - s) * np.exp(-(t - a) / d))
    if hold is not None:
        rel = t > hold
        e[rel] *= np.exp(-(t[rel] - hold) / r)
    return e


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def saw(f, n, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f + phase) % 1) - 1


def square(f, n):
    t = np.arange(n) / SR
    return np.sign(np.sin(2 * np.pi * f * t))


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * 0.9


def clap():
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    x = hp(lp(np.random.randn(n), 4000), 900)
    e = np.exp(-t * 18) + 0.6 * np.exp(-np.maximum(0, t - 0.012) * 40) * (t > 0.012)
    return x * e * 0.35


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    return hp(np.random.randn(n), 7000) * np.exp(-t * (18 if open_ else 70)) * 0.12


def supersaw(notes, dur):
    n = int(dur * SR)
    x = np.zeros(n)
    for m in notes:
        for det in (-0.12, -0.05, 0, 0.05, 0.12):
            x += saw(midi(m + det), n, np.random.rand())
    x = lp(x / (len(notes) * 5), 5200)
    return x * env(n, 0.004, 0.09, 0.0) * 0.55


def bass(m, dur):
    n = int(dur * SR)
    x = 0.6 * saw(midi(m), n) + 0.4 * square(midi(m), n)
    return lp(x, 900) * env(n, 0.003, 0.12, 0.35, 0.03, hold=dur * 0.8) * 0.45


def bell(m, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * midi(m) * t + 1.8 * np.sin(2 * np.pi * midi(m) * 3.5 * t) * np.exp(-t * 6))
    return x * np.exp(-t * 7) * 0.16


# Do - Sol - Lam - Fa
CHORDS = [(60, 64, 67), (59, 62, 67), (57, 60, 64), (57, 60, 65)]
ROOTS = [36, 43, 45, 41]
ARP = [[72, 76, 79, 84], [71, 74, 79, 83], [69, 72, 76, 81], [69, 72, 77, 81]]


def jingle(seconds: float, seed: int = 3) -> np.ndarray:
    np.random.seed(seed)
    n = int((seconds + 2) * SR)
    out = np.zeros(n)

    def put(x, t):
        i = int(t * SR)
        if i >= n:
            return
        out[i:i + len(x)] += x[: n - i]

    k, c = kick(), clap()
    bars = int(seconds / BAR) + 2
    for b in range(bars):
        t0 = b * BAR
        ch, root, arp = CHORDS[b % 4], ROOTS[b % 4], ARP[b % 4]
        for beat in range(4):
            tb = t0 + beat * BEAT
            put(k, tb)
            if beat in (1, 3):
                put(c, tb)
            put(hat(open_=(beat == 3)), tb + BEAT / 2)
            put(hat(), tb)
            put(supersaw(ch, BEAT * 0.45), tb + BEAT / 2)          # stab in levare
            for e8 in range(2):                                      # basso a ottave
                put(bass(root + 12 * e8, BEAT / 2 * 0.9), tb + e8 * BEAT / 2)
        for s16 in range(16):                                        # arpeggio
            put(bell(arp[s16 % 4] + (12 if s16 >= 12 else 0), BEAT / 2), t0 + s16 * BEAT / 4)
    out = out[: int(seconds * SR)]
    # "ta-dan" finale: accordo pieno di Do sugli ultimi 1.2 s
    tail = supersaw((48, 60, 64, 67, 72), 1.2) * 1.6
    tail *= env(len(tail), 0.005, 0.6, 0.0)
    put_at = len(out) - len(tail)
    out[put_at:] = out[put_at:] * np.linspace(1, 0, len(tail)) + tail
    out /= np.max(np.abs(out)) + 1e-9
    return (out * 0.9).astype(np.float32)


