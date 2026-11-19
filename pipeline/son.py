"""Musique originale et bruitages « stop-motion », générés par le programme (aucun droit d'auteur), puis mixage."""
import random
import wave

import numpy as np

SR = 44100


def _lire_wav(chemin) -> np.ndarray:
    with wave.open(str(chemin), "rb") as w:
        brut = w.readframes(w.getnframes())
    return np.frombuffer(brut, dtype=np.int16).astype(np.float32) / 32768


def _ecrire_wav(chemin, x: np.ndarray):
    x = np.clip(x, -1, 1)
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def _env(n, attaque=0.004, decroissance=6.0):
    t = np.arange(n) / SR
    a = np.minimum(1, t / attaque)
    return a * np.exp(-t * decroissance)


def _note(freq, duree, timbre="marimba"):
    n = int(duree * SR)
    t = np.arange(n) / SR
    if timbre == "marimba":
        s = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 4 * t) * np.exp(-t * 30)
        return s * _env(n, 0.002, 7)
    if timbre == "glock":
        s = np.sin(2 * np.pi * freq * 2 * t) + 0.3 * np.sin(2 * np.pi * freq * 5.4 * t) * np.exp(-t * 18)
        return 0.6 * s * _env(n, 0.001, 5)
    if timbre == "basse":  # corde pincée (Karplus-Strong)
        periode = max(2, int(SR / freq))
        buf = np.random.default_rng(int(freq)).uniform(-1, 1, periode)
        out = np.empty(n)
        for i in range(n):
            out[i] = buf[i % periode]
            buf[i % periode] = 0.5 * (buf[i % periode] + buf[(i + 1) % periode]) * 0.996
        return 0.9 * out * _env(n, 0.003, 3)
    raise ValueError(timbre)


def _hz(midi):
    return 440 * 2 ** ((midi - 69) / 12)


def musique(duree: float, graine: int) -> np.ndarray:
    rnd = random.Random(graine)
    bpm = rnd.choice([100, 104, 108, 112])
    temps = 60 / bpm
    tonique = rnd.choice([60, 62, 65, 67])  # do, ré, fa, sol
    grilles = [[0, 9, 5, 7], [0, 5, 7, 5], [0, 4, 9, 7], [0, 7, 9, 5]]
    grille = rnd.choice(grilles)
    gamme = [0, 2, 4, 7, 9, 12, 14, 16]  # pentatonique majeure : toujours joyeux
    n = int((duree + 2) * SR)
    out = np.zeros(n)

    def poser(son, t, gain):
        i = int(t * SR)
        if i >= n:
            return
        fin = min(n, i + len(son))
        out[i:fin] += gain * son[: fin - i]

    motif = [rnd.choice(gamme) if rnd.random() > 0.25 else None for _ in range(8)]
    mesure, t = 0, 0.0
    while t < duree + 1:
        accord = tonique + grille[mesure % 4]
        for b in range(4):
            tb = t + b * temps
            poser(_note(_hz(accord - 24 + (7 if b % 2 else 0)), temps * 0.95, "basse"), tb, 0.5)
            for k, iv in enumerate((0, 4, 7)):
                if b in (1, 3):
                    poser(_note(_hz(accord + iv), temps * 0.6, "marimba"), tb + k * 0.012, 0.18)
            # petit « toc » de bois
            if b in (1, 3):
                m = int(0.03 * SR)
                bruit = np.random.default_rng(mesure * 4 + b).uniform(-1, 1, m) * _env(m, 0.0005, 120)
                poser(np.convolve(bruit, np.ones(4) / 4, "same"), tb, 0.25)
        if mesure % 4 != 3 or rnd.random() < 0.5:
            for k, deg in enumerate(motif):
                if deg is not None and (mesure % 2 == 0 or k < 4):
                    poser(_note(_hz(tonique + 12 + deg), temps * 0.8, "glock"), t + k * temps / 2, 0.16)
        if mesure % 8 == 7:
            motif = [rnd.choice(gamme) if rnd.random() > 0.25 else None for _ in range(8)]
        mesure += 1
        t += 4 * temps
    fondu = int(1.2 * SR)
    out[int(duree * SR) - fondu: int(duree * SR)] *= np.linspace(1, 0, fondu)
    out[int(duree * SR):] = 0
    return out[: int(duree * SR)] / (np.max(np.abs(out)) + 1e-9)


def bruitage(nom: str) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(nom)) % 2 ** 32)
    if nom == "pop":
        n = int(0.12 * SR)
        t = np.arange(n) / SR
        f = 900 * np.exp(-t * 25) + 250
        return 0.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.001, 30)
    if nom == "boing":
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        f = 220 + 160 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 5) + 120 * np.exp(-t * 8)
        return 0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 6)
    if nom == "chute":  # sifflet qui descend puis « plof »
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        f = 1400 - 2600 * t
        s = 0.25 * np.sin(2 * np.pi * np.cumsum(np.maximum(f, 300)) / SR) * np.minimum(1, t * 30)
        m = int(0.12 * SR)
        plof = np.convolve(rng.uniform(-1, 1, m), np.ones(30) / 30, "same") * _env(m, 0.001, 40) * 3
        return np.concatenate([s, plof])
    if nom == "glisse":  # souffle
        n = int(0.35 * SR)
        b = np.convolve(rng.uniform(-1, 1, n), np.ones(12) / 12, "same")
        return 0.7 * b * np.sin(np.linspace(0, np.pi, n)) ** 2
    if nom == "squish":  # pâte écrasée
        n = int(0.18 * SR)
        t = np.arange(n) / SR
        b = np.convolve(rng.uniform(-1, 1, n), np.ones(40) / 40, "same") * 4
        return 0.6 * (b + 0.4 * np.sin(2 * np.pi * (140 - 200 * t) * t)) * _env(n, 0.004, 18)
    if nom == "ding":
        n = int(0.9 * SR)
        t = np.arange(n) / SR
        s = np.sin(2 * np.pi * 1318 * t) + 0.5 * np.sin(2 * np.pi * 1976 * t)
        return 0.35 * s * _env(n, 0.001, 4)
    raise ValueError(nom)


def mixer(voix_wav, debut_voix: float, duree: float, evenements: list, graine: int, sortie):
    n = int(duree * SR)
    mix = np.zeros(n)
    v = _lire_wav(voix_wav)
    i = int(debut_voix * SR)
    mix[i: i + len(v)] += v[: max(0, n - i)]
    # musique plus basse pendant la voix
    mus = musique(duree, graine)
    mix += 0.13 * mus
    for e in evenements:
        s = bruitage(e["type"])
        j = int(e["t"] * SR)
        if j < n:
            mix[j: j + len(s)] += e.get("gain", 0.5) * s[: n - j]
    crete = np.max(np.abs(mix)) + 1e-9
    brut = str(sortie) + ".brut.wav"
    _ecrire_wav(brut, mix * min(1.0, 0.95 / crete))
    # volume homogène d'une vidéo à l'autre (niveau conseillé pour les réseaux sociaux)
    import os
    import subprocess

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", brut, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-ar", str(SR), "-ac", "1", str(sortie)], check=True)
    os.remove(brut)
