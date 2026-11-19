"""Actualité du jour : lit les flux RSS, choisit un sujet léger pas encore traité, récupère le texte des articles."""
import calendar
import datetime as dt
import html
import json
import re
import time

import feedparser
import requests

from commun import DATA, claude_json

UA = {"User-Agent": "Mozilla/5.0 (compatible; actu-pate/1.0)"}
HISTORIQUE = DATA / "historique.json"

CRITERES = """Règles de choix (strictes) :
- AUCUN drame : pas de morts, blessés graves, attentats, guerres, conflits armés, catastrophes avec victimes,
  faits divers criminels, violences, agressions, procès criminels, maladies graves, suicides, accidents mortels.
- Évite aussi les polémiques politiques clivantes et les sujets qui reposent sur l'opinion.
- Préfère : sciences, espace, animaux, nature, technologie, inventions, sport (résultats, records), culture,
  cinéma, jeux vidéo, insolite, consommation pratique, économie concrète du quotidien, records, découvertes.
- Le sujet doit être une VRAIE information du jour, factuelle, compréhensible en 40 secondes, avec quelque chose
  de concret à montrer en images (objets, lieux, animaux, véhicules…).
- Le sujet doit être différent de ceux déjà traités (liste fournie), y compris d'un autre angle du même événement.
- Préfère un sujet repris par plusieurs sources de la liste."""


def charger_historique() -> dict:
    if HISTORIQUE.exists():
        return json.loads(HISTORIQUE.read_text(encoding="utf-8"))
    return {}


def ajouter_historique(sujet: str, titre: str, liens: list):
    h = charger_historique()
    jour = dt.date.today().isoformat()
    h.setdefault(jour, []).append({"sujet": sujet, "titre": titre, "liens": liens})
    limite = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    h = {j: v for j, v in sorted(h.items()) if j >= limite}
    HISTORIQUE.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")


def deja_traites() -> list:
    h = charger_historique()
    limite = (dt.date.today() - dt.timedelta(days=2)).isoformat()
    return [x["sujet"] for j, v in h.items() if j >= limite for x in v]


def lire_flux(heures: int = 30) -> list:
    adresses = [l.strip() for l in (DATA / "flux.txt").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
    seuil = time.time() - heures * 3600
    articles, vus = [], set()
    for url in adresses:
        try:
            r = requests.get(url, headers=UA, timeout=20)
            r.raise_for_status()
            flux = feedparser.parse(r.content)
        except Exception as e:  # un flux en panne ne bloque pas les autres
            print(f"[flux] {url} ignoré : {e}")
            continue
        source = flux.feed.get("title", url).split(" - ")[0].strip()
        n = 0
        for e in flux.entries:
            date = e.get("published_parsed") or e.get("updated_parsed")
            if date and calendar.timegm(date) < seuil:
                continue
            titre = (e.get("title") or "").strip()
            cle = titre.lower()[:80]
            if not titre or cle in vus:
                continue
            vus.add(cle)
            resume = html.unescape(re.sub(r"<[^>]+>", " ", e.get("summary", "") or ""))
            resume = " ".join(resume.split())[:300]
            articles.append({"source": source, "titre": titre, "resume": resume, "lien": e.get("link", "")})
            n += 1
        print(f"[flux] {source} : {n} articles récents")
    return articles


def texte_article(url: str) -> str:
    try:
        import trafilatura

        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        return (trafilatura.extract(r.text, include_comments=False, include_tables=False) or "")[:6000]
    except Exception as e:
        print(f"[article] {url} illisible : {e}")
        return ""


def choisir_sujet(exclus: list = ()) -> dict:
    articles = lire_flux()
    if len(articles) < 5:
        raise RuntimeError("Trop peu d'articles récents dans les flux RSS (voir data/flux.txt).")
    articles = articles[:150]
    liste = "\n".join(f"{i}. [{a['source']}] {a['titre']} — {a['resume']}" for i, a in enumerate(articles))
    faits = deja_traites() + list(exclus)
    rep = claude_json(
        "Tu es rédacteur en chef d'une chaîne TikTok française d'actualité en pâte à modeler, ton léger et bienveillant.",
        f"""Voici les titres de l'actualité des dernières 24 heures :

{liste}

Sujets déjà traités ces deux derniers jours (à NE PAS refaire) :
{chr(10).join('- ' + s for s in faits) or '- (aucun)'}

{CRITERES}

Choisis UN sujet. Réponds en JSON :
{{"sujet": "résumé du sujet en une phrase", "numeros": [numéros de TOUS les articles de la liste qui parlent de ce sujet],
  "pourquoi": "une phrase"}}""",
        max_tokens=800,
    )
    choix = [articles[i] for i in rep["numeros"] if isinstance(i, int) and 0 <= i < len(articles)]
    if not choix:
        raise RuntimeError("Claude n'a choisi aucun article valide.")
    print(f"[actu] Sujet : {rep['sujet']} ({len(choix)} article(s)) — {rep.get('pourquoi', '')}")
    for a in choix[:4]:
        a["texte"] = texte_article(a["lien"]) if a["lien"] else ""
    return {"sujet": rep["sujet"], "articles": choix[:4]}
