#!/usr/bin/env python3
"""La Brique : mesures pour les contrôles des Reels (numpy seul, aucune dépendance réseau).

  dynamisme(mp4)        différence moyenne entre images consécutives (sur 255) et fenêtres molles
  hauteur(wav)          F0 par trame de 10 ms (YIN), NaN hors voix
  variation_f0(wav)     écart type de la hauteur en demi-tons, sur les trames voisées
  blancs(wav, mots)     blancs dans la parole, à partir des temps des mots

Usage : python3 tools/video/analyse.py fichier.mp4|fichier.wav   affiche les mesures
"""
import json, subprocess, sys
import numpy as np

SR = 16000


def lire_audio(p, sr=SR, debut=None, fin=None):
    cmd = ["ffmpeg", "-v", "error"]
    if debut is not None:
        cmd += ["-ss", str(debut)]
    cmd += ["-i", str(p)]
    if fin is not None:
        cmd += ["-t", str(fin - (debut or 0))]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.int16)
    return x.astype(np.float64) / 32768


def hauteur(x, sr=SR, fmin=70, fmax=400, hop=160, win=800, seuil=0.15):
    """YIN : fonction de différence normalisée, premier creux sous le seuil, interpolation parabolique."""
    tmin, tmax = int(sr / fmax), int(sr / fmin)
    f = []
    rms_ref = np.sqrt(np.mean(x ** 2)) + 1e-9
    for i in range(0, len(x) - win - tmax, hop):
        s = x[i:i + win + tmax]
        if np.sqrt(np.mean(s[:win] ** 2)) < 0.25 * rms_ref:
            f.append(np.nan); continue
        d = np.array([np.sum((s[:win] - s[tau:tau + win]) ** 2) for tau in range(tmax + 1)])
        c = np.cumsum(d[1:]); dn = np.ones_like(d); dn[1:] = d[1:] * np.arange(1, tmax + 1) / np.maximum(c, 1e-12)
        sous = np.nonzero(dn[tmin:tmax] < seuil)[0]
        if not len(sous):
            f.append(np.nan); continue
        tau = tmin + sous[0]
        while tau + 1 < tmax and dn[tau + 1] < dn[tau]:
            tau += 1
        a, b, cc = dn[tau - 1], dn[tau], dn[min(tau + 1, tmax)]
        den = a - 2 * b + cc
        tau_f = tau + (0.5 * (a - cc) / den if abs(den) > 1e-12 else 0)
        f.append(sr / tau_f)
    return np.array(f)


def variation_f0(x, sr=SR):
    """Écart type de la hauteur en demi-tons (trames voisées, sauts d'octave écartés)."""
    f = hauteur(x, sr)
    v = f[~np.isnan(f)]
    if len(v) < 20:
        return 0.0
    st = 12 * np.log2(v / np.median(v))
    # médiane glissante sur 5 trames pour écarter les erreurs d'octave isolées
    m = np.array([np.median(st[max(0, i - 2):i + 3]) for i in range(len(st))])
    st = st[np.abs(st - m) < 3]
    st = st[np.abs(st) < 12]
    return float(np.std(st))


def dynamisme(mp4, fps=30, l=135, h=240):
    """135 × 240 : le grain fin s'efface à cette taille, seul le vrai mouvement compte."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", f"scale={l}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, h, l).astype(np.float32)
    return np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))


def fenetres_molles(d, seuil, fenetre=0.7, fps=30):
    """Fenêtres glissantes de 0,7 s dont la différence moyenne reste sous le seuil : [(début, moyenne)]."""
    n = max(1, round(fenetre * fps))
    if len(d) < n:
        return []
    moy = np.convolve(d, np.ones(n) / n, mode="valid")
    out, i = [], 0
    while i < len(moy):
        if moy[i] < seuil:
            j = i
            while j < len(moy) and moy[j] < seuil:
                j += 1
            out.append((round(i / fps, 2), round(float(moy[i:j].min()), 2)))
            i = j
        else:
            i += 1
    return out


def blancs(mots, voulus=()):
    """Blancs entre mots consécutifs ; voulus : temps (s) des silences placés exprès."""
    res = []
    for (m0, _, f0), (m1, d1, _) in zip(mots, mots[1:]):
        g = d1 - f0
        if not any(f0 - 0.05 <= v <= d1 + 0.05 for v in voulus):
            res.append((round(f0, 2), round(g, 2), m0))
    return res


if __name__ == "__main__":
    p = sys.argv[1]
    if p.endswith(".mp4"):
        d = dynamisme(p)
        print(json.dumps({"diff_moyenne_135x240": round(float(d.mean()), 2), "fenetres_molles_1.2": fenetres_molles(d, 1.2)}, ensure_ascii=False))
    x = lire_audio(p)
    print(json.dumps({"variation_f0_demi_tons": round(variation_f0(x), 2)}))
