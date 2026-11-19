"""Outils partagés : appel à Claude, lecture du JSON, chemins."""
import json
import os
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"
RUN = RACINE / "public" / "run"
ASSETS = RACINE / "assets"
MODELE = os.environ.get("MODELE_CLAUDE") or "claude-sonnet-5-5"


def claude(systeme: str, message: str, max_tokens: int = 6000) -> str:
    import anthropic

    client = anthropic.Anthropic()
    r = client.messages.create(
        model=MODELE,
        max_tokens=max_tokens,
        system=systeme,
        messages=[{"role": "user", "content": message}],
    )
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


def lire_json(texte: str):
    """Extrait le premier objet JSON d'une réponse de Claude."""
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", texte, re.S)
    brut = m.group(1) if m else texte[texte.find("{"): texte.rfind("}") + 1]
    return json.loads(brut)


def claude_json(systeme: str, message: str, max_tokens: int = 6000, essais: int = 2):
    derniere = None
    for _ in range(essais):
        try:
            return lire_json(claude(systeme, message, max_tokens))
        except (json.JSONDecodeError, ValueError) as e:
            derniere = e
            message += "\n\nRéponds UNIQUEMENT avec un objet JSON valide."
    raise RuntimeError(f"Réponse JSON illisible : {derniere}")
