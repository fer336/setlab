#!/usr/bin/env python3
"""Genera dos temas de techno sintéticos para probar transicion.py sin música real.

  prueba_A.wav -> 128 BPM, La menor (8A)
  prueba_B.wav -> 131 BPM, Mi menor (9A)

Estructura de cada uno (compases): intro 16 · desarrollo 32 · break 8 · desarrollo 32 · outro 32
"""
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 44100
rng = np.random.default_rng(7)


def bombo(n=int(0.35 * SR)):
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)


def hat(n=int(0.06 * SR)):
    sos = butter(4, 7000, "high", fs=SR, output="sos")
    return sosfilt(sos, rng.standard_normal(n)) * np.exp(-np.arange(n) / SR * 60) * 0.25


def clap(n=int(0.18 * SR)):
    sos = butter(2, [900, 3000], "band", fs=SR, output="sos")
    return sosfilt(sos, rng.standard_normal(n)) * np.exp(-np.arange(n) / SR * 22) * 0.5


def bajo(freq, n):
    t = np.arange(n) / SR
    saw = 2 * ((t * freq) % 1) - 1
    sos = butter(2, 400, "low", fs=SR, output="sos")
    return sosfilt(sos, saw) * np.exp(-t * 9) * 0.5


def pad(freqs, n):
    t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) for f in freqs)
    return s / len(freqs) * 0.18


def poner(dst, src, pos):
    fin = min(len(dst), pos + len(src))
    if pos < fin:
        dst[pos:fin] += src[: fin - pos]


def tema(bpm, raiz_hz, acorde_hz, archivo):
    golpe = 60 / bpm
    compases = 16 + 32 + 8 + 32 + 32
    n = int(compases * 4 * golpe * SR) + SR
    mezcla = np.zeros(n)
    secciones = (["intro"] * 16 + ["dev"] * 32 + ["break"] * 8 + ["dev"] * 32 + ["outro"] * 32)
    k, h, c = bombo(), hat(), clap()
    for comp, sec in enumerate(secciones):
        base = comp * 4 * golpe
        for g in range(4):
            pos = int((base + g * golpe) * SR)
            if sec != "break":
                poner(mezcla, k, pos)
            if sec in ("intro", "dev", "outro"):
                poner(mezcla, h, int((base + (g + 0.5) * golpe) * SR))
            if sec == "dev" and g in (1, 3):
                poner(mezcla, c, pos)
            if sec == "dev":
                for sub in (0.25, 0.5, 0.75):
                    poner(mezcla, bajo(raiz_hz, int(golpe / 4 * SR)), int((base + (g + sub) * golpe) * SR))
        if sec in ("dev", "break"):
            poner(mezcla, pad(acorde_hz, int(4 * golpe * SR)), int(base * SR))
    mezcla /= np.abs(mezcla).max() * 1.1
    estereo = np.stack([mezcla, np.roll(mezcla, 40) * 0.98], axis=1)
    sf.write(archivo, estereo, SR, subtype="PCM_16")
    print(f"{archivo}: {bpm} BPM · {len(mezcla)/SR/60:.1f} min")


if __name__ == "__main__":
    tema(128, 55.0, [220.0, 261.63, 329.63], "prueba_A.wav")   # La menor
    tema(131, 41.2, [164.81, 196.0, 246.94], "prueba_B.wav")   # Mi menor
