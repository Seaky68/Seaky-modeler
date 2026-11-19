"""Voix off gratuite (edge-tts), avec l'heure de chaque mot pour les sous-titres et la bouche de Pâtou."""
import asyncio
import os
import subprocess
import wave

VOIX = os.environ.get("VOIX") or "fr-FR-HenriNeural"
VITESSE = os.environ.get("VITESSE_VOIX") or "+8%"


async def _synthese(texte: str, mp3: str):
    import edge_tts

    com = edge_tts.Communicate(texte, VOIX, rate=VITESSE, boundary="WordBoundary")
    mots = []
    with open(mp3, "wb") as f:
        async for bloc in com.stream():
            if bloc["type"] == "audio":
                f.write(bloc["data"])
            elif bloc["type"] == "WordBoundary":
                debut = bloc["offset"] / 1e7
                mots.append({"texte": bloc["text"], "debut": debut, "fin": debut + bloc["duration"] / 1e7})
    return mots


def parler(texte: str, dossier) -> tuple:
    mp3 = str(dossier / "voix.mp3")
    wav = str(dossier / "voix.wav")
    mots = asyncio.run(_synthese(texte, mp3))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "44100", wav], check=True)
    return wav, mots


def parler_demo(texte: str, dossier) -> tuple:
    """Sans connexion à la voix : silence avec un minutage estimé (pour tester l'animation)."""
    mots, t = [], 0.0
    for m in texte.split():
        d = 0.16 + 0.055 * len(m)
        mots.append({"texte": m.strip(".,!?;:«»"), "debut": t, "fin": t + d})
        t += d + (0.35 if m[-1] in ".!?" else 0.12 if m[-1] in ",;:" else 0.05)
    wav = str(dossier / "voix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\x00\x00" * int(44100 * (t + 0.3)))
    return wav, mots
