"""Fabrique une vidéo d'actualité en pâte à modeler, de A à Z, puis l'envoie sur Telegram.

    python pipeline/main.py          → vraie vidéo sur l'actualité du jour
    python pipeline/main.py --demo   → vidéo de test, sans clé ni crédit (images dessinées par le code, sans voix)
"""
import json
import os
import random
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import images  # noqa: E402
import plan as planif  # noqa: E402
import son  # noqa: E402
import voix  # noqa: E402
from commun import DATA, RACINE, RUN  # noqa: E402


def preparer_dossier():
    if RUN.exists():
        shutil.rmtree(RUN)
    (RUN / "mascotte").mkdir(parents=True)


def trouver_script(demo: bool):
    if demo:
        d = json.loads((DATA / "demo.json").read_text(encoding="utf-8"))
        return d["script"], d["sources"], [], d["sujet"]
    import actu
    import script as ecriture

    exclus = []
    for essai in range(3):
        info = actu.choisir_sujet(exclus)
        try:
            s = ecriture.ecrire_script(info)
        except RuntimeError as e:
            print(f"[script] {e}")
            exclus.append(info["sujet"])
            continue
        sources = sorted({a["source"] for a in info["articles"]})
        liens = [a["lien"] for a in info["articles"] if a.get("lien")]
        return s, sources, liens, info["sujet"]
    raise RuntimeError("Aucun sujet valable trouvé après 3 essais.")


def fabriquer_images(script: dict, demo: bool, graine: int) -> dict:
    taches = {}
    for i, s in enumerate(script["scenes"]):
        taches[("decor", i)] = ("decor", s["decor"], RUN / f"decor{i}.jpg", graine + i)
        for k, a in enumerate((s.get("acteurs") or [])[:2]):
            taches[(i, k)] = ("acteur", a["description"], RUN / f"acteur{i}_{k}.png", graine * 3 + i * 5 + k)

    def faire(cle):
        genre, desc, chemin, g = taches[cle]
        try:
            if demo:
                (images.decor_demo if genre == "decor" else images.acteur_demo)(g, chemin)
            else:
                (images.decor if genre == "decor" else images.acteur)(desc, chemin)
            return cle, f"run/{chemin.name}"
        except Exception as e:
            print(f"[image] {genre} « {desc[:60]} » ignoré : {e}")
            if genre == "decor":  # un décor est indispensable : décor de secours
                images.decor_demo(g, chemin)
                return cle, f"run/{chemin.name}"
            return cle, None

    with ThreadPoolExecutor(max_workers=4) as ex:
        res = dict(ex.map(faire, taches))
    print(f"[image] {sum(1 for v in res.values() if v)} images prêtes")
    return {k: v for k, v in res.items() if v}


def rendre(sortie: Path):
    commande = ["npx", "remotion", "render", "src/index.ts", "Actu", str(sortie),
                f"--props={RUN / 'plan.json'}", "--log=error", f"--concurrency={min(4, os.cpu_count() or 2)}"]
    chrome = os.environ.get("CHROME") or shutil.which("google-chrome")
    if chrome:
        commande.append(f"--browser-executable={chrome}")
    subprocess.run(commande, cwd=RACINE, check=True)


def main():
    demo = "--demo" in sys.argv
    graine = random.randrange(10 ** 6)
    preparer_dossier()

    script, sources, liens, sujet = trouver_script(demo)
    print(f"[script] {script['titre']} ({len(script['scenes'])} scènes)")

    try:
        dossier_mascotte = images.preparer_mascotte(demo)
    except Exception as e:  # Pâtou sera retentée à la prochaine vidéo
        print(f"[mascotte] création impossible ({e}) : Pâtou de secours pour cette vidéo")
        dossier_mascotte = images.preparer_mascotte(True)
    for f in dossier_mascotte.glob("*.png"):
        shutil.copy(f, RUN / "mascotte" / f.name)

    imgs = fabriquer_images(script, demo, graine)

    texte = " ".join(s["texte"].strip() for s in script["scenes"])
    wav, mots = (voix.parler_demo if demo else voix.parler)(texte, RUN)
    import script as ecriture

    plan, sons = planif.construire(script, mots, imgs, sources, ecriture.date_fr(), graine)
    son.mixer(wav, planif.DEBUT_VOIX, plan["duree"] / planif.FPS, sons, graine, RUN / "audio.wav")
    (RUN / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    sortie = RACINE / "out" / "video.mp4"
    sortie.parent.mkdir(exist_ok=True)
    rendre(sortie)
    print(f"[rendu] {sortie} ({plan['duree'] / planif.FPS:.1f} s)")

    legende = (f"{script['titre']}\n\n{script.get('legende', '')}\n\nSources : {', '.join(sources)}\n"
               + "\n".join(liens[:3])
               + "\n\n⚠️ Sur TikTok, active « Contenu généré par l'IA ».")
    (RACINE / "out" / "legende.txt").write_text(legende, encoding="utf-8")
    if not demo:
        import actu

        actu.ajouter_historique(sujet, script["titre"], liens)
    from telegram import envoyer

    envoyer(str(sortie), legende)


if __name__ == "__main__":
    main()
