"""Envoi de la vidéo finie sur Telegram."""
import os

import requests


def envoyer(video: str, legende: str):
    jeton, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not jeton or not chat:
        print("[telegram] pas de clé Telegram : envoi ignoré")
        return
    with open(video, "rb") as f:
        r = requests.post(f"https://api.telegram.org/bot{jeton}/sendVideo",
                          data={"chat_id": chat, "caption": legende[:1020], "supports_streaming": "true"},
                          files={"video": ("actu.mp4", f, "video/mp4")}, timeout=300)
    if not r.ok:
        raise RuntimeError(f"Telegram : {r.status_code} {r.text[:300]}")
    print("[telegram] vidéo envoyée")
