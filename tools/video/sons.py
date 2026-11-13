#!/usr/bin/env python3
"""La Brique : bibliothèque de sons maison, synthétisés en code (aucun son téléchargé).

Usage : python3 tools/video/sons.py     écrit les WAV dans tools/video/sons/ (48 kHz, stéréo)
Sons : impact (brique sourde), tick (compteur), whoosh (entrée), swish (filet), rebond (cercle),
tampon (coup de tampon), buzzer.
"""
from pathlib import Path
import wave
import numpy as np

SR = 48000
DOSSIER = Path(__file__).resolve().parent / "sons"
rng = np.random.default_rng(7)


def t(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.002, d=0.2):
    x = np.arange(n) / SR
    return np.minimum(1, x / max(a, 1e-4)) * np.exp(-x / d)


def passe_bas(x, f):
    a = np.exp(-2 * np.pi * f / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def passe_haut(x, f):
    return x - passe_bas(x, f)


def impact():
    x = t(0.6)
    f = 55 * np.exp(-x * 6) + 38
    corps = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.001, 0.18)
    bruit = passe_bas(rng.normal(0, 1, len(x)), 900) * env(len(x), 0.0005, 0.03)
    return corps * 0.9 + bruit * 0.6


def tick():
    x = t(0.05)
    return np.sin(2 * np.pi * 2400 * x) * env(len(x), 0.0005, 0.008) * 0.6 + passe_haut(rng.normal(0, 1, len(x)), 3000) * env(len(x), 0.0002, 0.004) * 0.3


def whoosh():
    x = t(0.55)
    n = rng.normal(0, 1, len(x))
    fen = np.sin(np.pi * x / x[-1]) ** 2
    y = np.zeros_like(n)
    # balayage de filtre : on mélange trois bandes dont le poids glisse dans le temps
    for f, w in ((400, 1 - x / x[-1]), (1500, np.sin(np.pi * x / x[-1])), (4000, x / x[-1])):
        y += passe_bas(passe_haut(n, f * 0.5), f * 1.5) * w
    return y * fen * 0.8


def swish():
    x = t(0.45)
    n = passe_haut(rng.normal(0, 1, len(x)), 2500)
    a = np.where(x < 0.08, x / 0.08, np.exp(-(x - 0.08) / 0.09))
    return n * a * 0.5


def rebond():
    x = t(0.6)
    ton = sum(np.sin(2 * np.pi * f * x) * g for f, g in ((620, 1), (1240, 0.4), (1870, 0.2)))
    return ton * env(len(x), 0.001, 0.12) * 0.5 + impact()[:len(x)] * 0.3


def tampon():
    x = t(0.35)
    coup = passe_bas(rng.normal(0, 1, len(x)), 1800) * env(len(x), 0.0005, 0.04)
    grave = np.sin(2 * np.pi * 90 * x) * env(len(x), 0.001, 0.08)
    return coup * 0.9 + grave * 0.7


def buzzer():
    x = t(0.9)
    s = np.sign(np.sin(2 * np.pi * 220 * x)) * 0.5 + np.sign(np.sin(2 * np.pi * 223 * x)) * 0.5
    return passe_bas(s, 2500) * np.minimum(1, (x[-1] - x) / 0.05) * np.minimum(1, x / 0.01) * 0.35


def ecrire(nom, mono):
    mono = mono / max(1e-9, np.abs(mono).max()) * 0.89
    st = np.stack([mono, mono], axis=1)
    data = (st * 32767).astype("<i2").tobytes()
    with wave.open(str(DOSSIER / f"{nom}.wav"), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data)


if __name__ == "__main__":
    DOSSIER.mkdir(exist_ok=True)
    for nom, f in (("impact", impact), ("tick", tick), ("whoosh", whoosh), ("swish", swish),
                   ("rebond", rebond), ("tampon", tampon), ("buzzer", buzzer)):
        ecrire(nom, f())
        print("son", nom)
