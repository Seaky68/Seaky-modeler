"""Script de la vidéo : Claude écrit le texte et la mise en scène, puis un deuxième passage vérifie les faits."""
import datetime as dt
import json

from commun import claude_json

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
        "novembre", "décembre"]

FORMAT = """{
 "titre": "titre à l'écran, 45 caractères max, accrocheur, sans point final",
 "scenes": [
  {
   "texte": "ce que dit la voix off dans cette scène (1 à 3 phrases courtes)",
   "decor": "IN ENGLISH: the miniature clay set for this scene, a place or backdrop only, NO people, NO animals, NO text",
   "mascotte": "neutre | surpris | content",
   "acteurs": [
    {"description": "IN ENGLISH: ONE clay figure or object, full body, simple, e.g. 'a small red rocket with white fins'",
     "position": "gauche | centre | droite",
     "taille": "petit | moyen | grand",
     "entree": "pop | tombe | glisse_gauche | glisse_droite",
     "mot_entree": "un mot EXACT du texte de la scène, au moment où l'acteur apparaît",
     "action": "aucune | saute | tremble | tourne | grossit",
     "mot_action": "un mot EXACT du texte de la scène, ou vide"}
   ]
  }
 ],
 "legende": "légende TikTok : une phrase + 4 à 6 hashtags (#actu #info ...)",
 "faits": ["chaque fait chiffré ou précis utilisé, avec la source qui le donne"]
}"""

REGLES = """Règles du script :
- Langue : français parlé, simple, vivant, tutoiement du spectateur. Ton léger, bienveillant, jamais moqueur envers
  des personnes réelles. Aucune opinion politique.
- Durée : 95 à 125 mots AU TOTAL, en 4 ou 5 scènes.
- Scène 1 : une accroche forte en une phrase (question ou fait étonnant), qui donne envie de rester.
- Scènes du milieu : les faits essentiels (qui, quoi, où, quand, chiffres clés), un fait par scène.
- Dernière scène : une conclusion courte puis « Abonne-toi pour l'actu de demain ! ».
- N'utilise QUE des faits présents dans les articles fournis. Aucun chiffre, nom ou date inventé.
  Si les articles se contredisent, garde la version la plus prudente.
- Arrondis les chiffres compliqués (« près de 3 millions »), et explique ou évite les sigles obscurs.

Règles des images (style figurines en pâte à modeler, petits décors miniatures) :
- Chaque scène a un décor différent et 1 ou 2 acteurs (personnages ou objets en pâte à modeler).
- AUCUNE personne réelle reconnaissable, AUCUN nom propre de personne, de marque, d'équipe ou de logo dans
  les descriptions anglaises. Une personnalité devient un personnage générique (« a little clay man in a grey
  suit holding a microphone »). Une marque devient un objet générique (« a blue smartphone »).
- Aucun texte ni chiffre dessiné dans les images.
- Les acteurs : formes simples et lisibles, un seul sujet par description, vus de face ou de trois quarts.
- Deux acteurs d'une même scène : positions différentes (gauche et droite)."""


def date_fr() -> str:
    d = dt.date.today()
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]} {d.year}"


def sources_txt(info: dict) -> str:
    blocs = []
    for i, a in enumerate(info["articles"], 1):
        corps = a.get("texte") or a.get("resume", "")
        blocs.append(f"### Article {i} — {a['source']}\nTitre : {a['titre']}\n{corps}")
    return "\n\n".join(blocs)


def ecrire_script(info: dict) -> dict:
    systeme = ("Tu écris des vidéos TikTok d'actualité de 40 secondes, animées en pâte à modeler façon stop-motion, "
               "présentées par Pâtou, une petite mascotte en pâte à modeler.")
    message = f"""Nous sommes le {date_fr()}. Sujet : {info['sujet']}

Articles sources :
{sources_txt(info)}

{REGLES}

Réponds UNIQUEMENT en JSON avec ce format :
{FORMAT}"""
    script = claude_json(systeme, message, max_tokens=4000)
    return verifier(script, info)


def verifier(script: dict, info: dict) -> dict:
    rep = claude_json(
        "Tu es vérificateur de faits, très rigoureux.",
        f"""Compare ce script de vidéo aux articles sources.

Articles :
{sources_txt(info)}

Script :
{json.dumps(script, ensure_ascii=False, indent=1)}

Vérifie :
1. Chaque fait, chiffre, nom, date et lieu du texte parlé est-il bien dans les articles ? Rien d'exagéré ?
2. Les descriptions anglaises contiennent-elles un nom de personne réelle, de marque, d'équipe ou un logo ?
   (interdit : remplacer par un personnage ou objet générique)
3. Le sujet évite-t-il bien les drames (morts, violences, guerres, catastrophes) ?

Réponds en JSON :
{{"ok": true ou false, "problemes": ["..."], "script": le script COMPLET corrigé (identique s'il n'y a rien à corriger),
  "drame": true si le sujet lui-même est un drame}}""",
        max_tokens=5000,
    )
    if rep.get("drame"):
        raise RuntimeError("Le vérificateur a jugé le sujet trop dramatique, il sera changé.")
    for p in rep.get("problemes") or []:
        print(f"[vérif] corrigé : {p}")
    corrige = rep.get("script") or script
    if not corrige.get("scenes"):
        corrige = script
    return corrige
