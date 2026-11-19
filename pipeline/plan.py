"""Plan d'animation : transforme le script et le minutage de la voix en images clés pour Remotion."""
import re
import unicodedata

FPS = 24
DEBUT_VOIX = 0.7  # secondes : le titre apparaît d'abord
X = {"gauche": 0.34, "centre": 0.52, "droite": 0.7}
HAUTEUR = {"petit": 360, "moyen": 480, "grand": 620}
SOL = 1310  # ligne du sol (pixels depuis le haut), au-dessus de la zone couverte par TikTok
SON_ENTREE = {"pop": "pop", "tombe": "chute", "glisse_gauche": "glisse", "glisse_droite": "glisse"}
SON_ACTION = {"saute": "boing", "tremble": "squish", "tourne": "glisse", "grossit": "pop"}


def norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in t if unicodedata.category(c) != "Mn"))


def repartir_mots(scenes: list, mots: list) -> list:
    """Associe chaque mot prononcé à sa scène, en comptant les lettres (robuste aux mots coupés par la voix)."""
    bornes, cumul = [], 0
    for s in scenes:
        cumul += len(norm(s["texte"]))
        bornes.append(cumul)
    par_scene = [[] for _ in scenes]
    pos = 0
    for m in mots:
        pos += len(norm(m["texte"]))
        i = next((k for k, b in enumerate(bornes) if pos <= b + 1), len(scenes) - 1)
        par_scene[i].append(m)
    # une scène sans mot (rare) récupère un mot de sa voisine
    for i in range(len(scenes)):
        if not par_scene[i]:
            voisine = par_scene[i - 1] if i and len(par_scene[i - 1]) > 1 else None
            if voisine:
                par_scene[i].insert(0, voisine.pop())
    return par_scene


def _f(t: float) -> int:
    return int(round((t + DEBUT_VOIX) * FPS))


def _trouver(mots: list, cible: str, defaut: int) -> int:
    c = norm(cible or "")
    if c:
        for m in mots:
            if norm(m["texte"]) == c:
                return _f(m["debut"])
        for m in mots:
            if c in norm(m["texte"]) or (len(norm(m["texte"])) > 3 and norm(m["texte"]) in c):
                return _f(m["debut"])
    return defaut


def sous_titres(mots: list) -> list:
    groupes, cour = [], []
    for m in mots:
        cour.append(m)
        lettres = sum(len(x["texte"]) for x in cour)
        if len(cour) >= 3 or lettres > 14 or m["texte"][-1:] in ".,!?;:":
            groupes.append(cour)
            cour = []
    if cour:
        groupes.append(cour)
    out = []
    for g in groupes:
        out.append({"debut": _f(g[0]["debut"]), "fin": _f(g[-1]["fin"]) + 2,
                    "mots": [{"texte": m["texte"], "debut": _f(m["debut"]), "fin": _f(m["fin"])} for m in g]})
    for a, b in zip(out, out[1:]):  # pas de trou qui fait clignoter
        if b["debut"] - a["fin"] < 6:
            a["fin"] = b["debut"]
    return out


def construire(script: dict, mots: list, images: dict, sources: list, date: str, graine: int) -> tuple:
    scenes = script["scenes"]
    par_scene = repartir_mots(scenes, mots)
    total = _f(mots[-1]["fin"]) + int(1.4 * FPS)
    sons = [{"t": 0.15, "type": "ding", "gain": 0.45}]
    plan_scenes = []
    for i, (s, ms) in enumerate(zip(scenes, par_scene)):
        debut = 0 if i == 0 else max(_f(ms[0]["debut"]) - 4, plan_scenes[-1]["debut"] + 12)
        if i:
            plan_scenes[-1]["fin"] = debut
            sons.append({"t": debut / FPS, "type": "squish", "gain": 0.35})
        acteurs = []
        for k, a in enumerate((s.get("acteurs") or [])[:2]):
            src = images.get((i, k))
            if not src:
                continue
            base = max(debut, _f(ms[0]["debut"]) if ms else debut) + 6 + k * 10
            fe = max(debut + 4, _trouver(ms, a.get("mot_entree"), base))
            action = a.get("action") if a.get("action") in SON_ACTION else "aucune"
            fa = _trouver(ms, a.get("mot_action"), fe + 30) if action != "aucune" else 0
            fa = max(fa, fe + 14) if action != "aucune" else 0
            entree = a.get("entree") if a.get("entree") in SON_ENTREE else "pop"
            pos = a.get("position") if a.get("position") in X else ("gauche", "droite")[k % 2]
            if acteurs and pos == acteurs[0]["pos"]:
                pos = "droite" if pos != "droite" else "gauche"
            acteurs.append({"src": src, "pos": pos, "x": X[pos] * 1080, "sol": SOL - 20 * k,
                            "hauteur": HAUTEUR.get(a.get("taille"), 480), "entree": entree, "f_entree": fe,
                            "action": action, "f_action": fa, "graine": graine + i * 10 + k})
            sons.append({"t": fe / FPS, "type": SON_ENTREE[entree], "gain": 0.5})
            if action != "aucune":
                sons.append({"t": fa / FPS, "type": SON_ACTION[action], "gain": 0.45})
        plan_scenes.append({"debut": debut, "fin": total, "decor": images[("decor", i)],
                            "mascotte": s.get("mascotte") if s.get("mascotte") in ("neutre", "surpris", "content")
                            else "neutre", "acteurs": acteurs, "graine": graine + i})
    plan = {
        "fps": FPS, "duree": total, "titre": script["titre"], "date": date, "sources": sources,
        "audio": "run/audio.wav",
        "mascotte": {n: f"run/mascotte/{n}.png" for n in
                     ("neutre_fermee", "neutre_ouverte", "content_fermee", "content_ouverte",
                      "surpris_fermee", "surpris_ouverte")},
        "parole": [[_f(m["debut"]), _f(m["fin"])] for m in mots],
        "scenes": plan_scenes,
        "sous_titres": sous_titres(mots),
        "graine": graine,
    }
    return plan, sons
