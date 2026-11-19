"""Images en pâte à modeler.

- Décors : fal.ai (FLUX.2 Turbo), un petit plateau miniature vide, format vertical.
- Acteurs : fal.ai sur fond uni, puis détourage (BiRefNet) pour les animer séparément.
- Mascotte Pâtou : créée une seule fois (6 images : 3 expressions x bouche fermée / ouverte), puis réutilisée.
Sans clé fal.ai (mode démo), des images de test en « pâte » sont dessinées par le code.
"""
import io
import math
import os
import random
import time

import requests
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from commun import ASSETS

FAL_IMAGE = os.environ.get("FAL_MODEL") or "fal-ai/flux-2/turbo"
FAL_EDIT = FAL_IMAGE + "/edit"
FAL_DETOURAGE = "fal-ai/birefnet"

STYLE_DECOR = (
    "claymation stop-motion miniature film set, {desc}, handmade plasticine and modelling clay textures with "
    "visible fingerprints and sculpting tool marks, tabletop diorama, soft warm studio lighting, gentle shallow "
    "depth of field, cheerful saturated colors, charming handcrafted British stop-motion look, vertical composition, "
    "empty set without any characters, no people, no animals, no text, no letters, no logo, "
    "clear open floor in the lower half of the image"
)
STYLE_ACTEUR = (
    "a single claymation stop-motion figure: {desc}. Handmade plasticine with visible fingerprints, rounded "
    "friendly shapes, slightly glossy clay, expressive simple face if it is a character, full body entirely visible "
    "with margin around it, centered, front or three-quarter view, isolated on a plain flat light grey background, "
    "soft studio lighting, no text, no letters, no logo, nothing else in the image"
)
MASCOTTE = (
    "a single claymation stop-motion mascot character: a small round chubby creature made of bright orange "
    "plasticine, big white eyes with black pupils, small rosy cheeks, tiny arms and feet, wearing a small blue "
    "reporter cap, holding a tiny black microphone in one hand, friendly closed-mouth smile, visible fingerprints "
    "in the clay, full body entirely visible, front view, centered, isolated on a plain flat light grey background, "
    "soft studio lighting, no text"
)
VARIANTES = {
    "neutre_fermee": None,
    "neutre_ouverte": "Keep exactly the same character, colors, cap, microphone, pose, size and framing. "
                      "Change only the mouth: open it wide as if speaking, showing a dark mouth inside.",
    "content_fermee": "Keep exactly the same character, colors, cap, microphone, pose, size and framing. "
                      "Change only the face: very happy, eyes squinting with joy, big closed smile.",
    "content_ouverte": "Keep exactly the same character, colors, cap, microphone, pose, size and framing. "
                       "Change only the face: very happy, eyes squinting with joy, big open laughing mouth.",
    "surpris_fermee": "Keep exactly the same character, colors, cap, microphone, pose, size and framing. "
                      "Change only the face: surprised, eyes wide open, eyebrows raised, small round closed mouth.",
    "surpris_ouverte": "Keep exactly the same character, colors, cap, microphone, pose, size and framing. "
                       "Change only the face: amazed, eyes wide open, eyebrows raised, big round open O mouth.",
}


# ------------------------------------------------------------------ fal.ai
def _fal(modele: str, donnees: dict) -> dict:
    for essai in range(3):
        try:
            r = requests.post(f"https://fal.run/{modele}", json=donnees, timeout=240,
                              headers={"Authorization": f"Key {os.environ['FAL_KEY']}"})
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(f"{r.status_code} {r.text[:200]}")
            if r.status_code >= 400:
                raise RuntimeError(f"fal.ai {modele} : {r.status_code} {r.text[:300]}")
            return r.json()
        except requests.RequestException as e:
            if essai == 2:
                raise
            print(f"[fal] nouvel essai après : {e}")
            time.sleep(5 * (essai + 1))


def _telecharger(url: str) -> Image.Image:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def _generer(prompt: str, taille) -> str:
    donnees = {"prompt": prompt, "image_size": taille, "num_images": 1, "enable_safety_checker": True,
               "output_format": "png"}
    try:
        return _fal(FAL_IMAGE, donnees)["images"][0]["url"]
    except RuntimeError:
        if isinstance(taille, dict):  # taille sur mesure refusée : format standard
            donnees["image_size"] = "portrait_16_9"
            return _fal(FAL_IMAGE, donnees)["images"][0]["url"]
        raise


def _detourer(url: str) -> Image.Image:
    rep = _fal(FAL_DETOURAGE, {"image_url": url, "output_format": "png", "refine_foreground": True})
    img = _telecharger(rep["image"]["url"]).convert("RGBA")
    return recadrer(img)


def recadrer(img: Image.Image) -> Image.Image:
    alpha = img.getchannel("A").point(lambda a: 255 if a > 40 else 0)
    boite = alpha.getbbox()
    if not boite:
        return img
    l, h = img.size
    m = 6
    return img.crop((max(0, boite[0] - m), max(0, boite[1] - m), min(l, boite[2] + m), min(h, boite[3] + m)))


def decor(desc: str, chemin):
    url = _generer(STYLE_DECOR.format(desc=desc), {"width": 1088, "height": 1920})
    img = _telecharger(url).convert("RGB")
    cadrer_vertical(img).save(chemin, quality=92)


def acteur(desc: str, chemin):
    url = _generer(STYLE_ACTEUR.format(desc=desc), "square_hd")
    _detourer(url).save(chemin)


def cadrer_vertical(img: Image.Image) -> Image.Image:
    l, h = img.size
    cible = 1080 / 1920
    if l / h > cible:
        nl = int(h * cible)
        img = img.crop(((l - nl) // 2, 0, (l - nl) // 2 + nl, h))
    else:
        nh = int(l / cible)
        img = img.crop((0, (h - nh) // 2, l, (h - nh) // 2 + nh))
    return img.resize((1080, 1920), Image.LANCZOS)


def preparer_mascotte(demo: bool):
    """Crée les 6 images de Pâtou si elles n'existent pas encore (une seule fois)."""
    dossier = ASSETS / "mascotte"
    dossier.mkdir(parents=True, exist_ok=True)
    manquantes = [n for n in VARIANTES if not (dossier / f"{n}.png").exists()]
    if not manquantes:
        return dossier
    if demo:  # Pâtou de démonstration, dessinée par le code, jamais enregistrée dans assets/
        from commun import RUN

        tmp = RUN / "mascotte_demo"
        tmp.mkdir(parents=True, exist_ok=True)
        for n in VARIANTES:
            mascotte_demo(n).save(tmp / f"{n}.png")
        return tmp
    print("[mascotte] première création de Pâtou (une seule fois)")
    base_url = _generer(MASCOTTE, "square_hd")
    for nom, consigne in VARIANTES.items():
        if (dossier / f"{nom}.png").exists():
            continue
        url = base_url if consigne is None else _fal(
            FAL_EDIT, {"prompt": consigne, "image_urls": [base_url], "num_images": 1, "output_format": "png"}
        )["images"][0]["url"]
        _detourer(url).save(dossier / f"{nom}.png")
        print(f"[mascotte] {nom} prête")
    return dossier


# ------------------------------------------------------------------ images de démonstration (sans fal.ai)
def _pate(masque: Image.Image, couleur, graine: int) -> Image.Image:
    """Remplit un masque avec une matière « pâte à modeler » : volume, empreintes, petits défauts."""
    rnd = random.Random(graine)
    l, h = masque.size
    base = Image.new("RGB", (l, h), couleur)
    # volume : lumière en haut à gauche, ombre en bas à droite
    flou = masque.filter(ImageFilter.GaussianBlur(max(4, min(l, h) // 14)))
    decale = ImageChops.offset(flou, -max(2, l // 40), -max(2, h // 40))
    lum = ImageChops.subtract(flou, ImageChops.offset(flou, l // 30, h // 30)).point(lambda v: v * 2)
    ombre = ImageChops.subtract(flou, decale).point(lambda v: v * 2)
    clair = Image.new("RGB", (l, h), tuple(min(255, c + 70) for c in couleur))
    fonce = Image.new("RGB", (l, h), tuple(max(0, c - 80) for c in couleur))
    base = Image.composite(clair, base, lum)
    base = Image.composite(fonce, base, ombre)
    bord = ImageChops.subtract(masque, masque.filter(ImageFilter.MinFilter(9))).filter(ImageFilter.GaussianBlur(3))
    base = Image.composite(fonce, base, bord.point(lambda v: v // 2))
    # empreintes de doigts et marques d'outil
    d = ImageDraw.Draw(base)
    for _ in range(max(6, (l * h) // 9000)):
        x, y = rnd.randrange(l), rnd.randrange(h)
        if masque.getpixel((x, y)) < 200:
            continue
        r = rnd.randint(6, 18)
        teinte = tuple(max(0, c - rnd.randint(10, 25)) for c in couleur)
        for k in range(3):
            d.arc((x - r - k * 4, y - r - k * 4, x + r + k * 4, y + r + k * 4), rnd.randint(0, 360),
                  rnd.randint(0, 360), fill=teinte, width=2)
    bruit = Image.effect_noise((l, h), 22).convert("RGB")
    base = Image.blend(base, ImageChops.multiply(base, bruit.point(lambda v: 200 + v // 5)), 0.35)
    out = base.convert("RGBA")
    out.putalpha(masque)
    return out


def decor_demo(graine: int, chemin):
    rnd = random.Random(graine)
    l, h = 1080, 1920
    palettes = [((120, 190, 230), (250, 205, 150), (110, 170, 90)), ((250, 180, 140), (255, 230, 170), (200, 150, 90)),
                ((90, 110, 190), (150, 170, 230), (120, 120, 150)), ((150, 210, 200), (230, 240, 220), (90, 160, 120))]
    ciel, horizon, sol = palettes[graine % len(palettes)]
    img = Image.new("RGB", (l, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = min(1, y / (h * 0.62))
        d.line([(0, y), (l, y)], fill=tuple(int(ciel[i] * (1 - t) + horizon[i] * t) for i in range(3)))
    calque = img.convert("RGBA")
    # collines et nuages en pâte
    for k in range(3):
        m = Image.new("L", (l, h), 0)
        dm = ImageDraw.Draw(m)
        base_y = int(h * (0.55 + k * 0.06))
        pts = [(0, h)] + [(x, base_y - int(90 * math.sin(x / 210 + graine + k) + rnd.randint(0, 25)))
                          for x in range(0, l + 60, 60)] + [(l, h)]
        dm.polygon(pts, fill=255)
        coul = tuple(max(0, c - 25 * k) for c in sol) if k else tuple(min(255, c + 30) for c in sol)
        calque.alpha_composite(_pate(m, coul, graine + k))
    for k in range(3):
        m = Image.new("L", (l, h), 0)
        dm = ImageDraw.Draw(m)
        cx, cy = rnd.randint(100, 980), rnd.randint(180, 700)
        for j in range(4):
            r = rnd.randint(55, 95)
            dm.ellipse((cx + j * 70 - r - 100, cy - r, cx + j * 70 + r - 100, cy + r), fill=255)
        calque.alpha_composite(_pate(m, (250, 250, 245), graine * 7 + k))
    # sol (table du plateau)
    m = Image.new("L", (l, h), 0)
    ImageDraw.Draw(m).rectangle((0, int(h * 0.74), l, h), fill=255)
    calque.alpha_composite(_pate(m, tuple(max(0, c - 40) for c in sol), graine + 99))
    img = calque.convert("RGB").filter(ImageFilter.GaussianBlur(1.2))
    img.save(chemin, quality=92)


def acteur_demo(graine: int, chemin):
    rnd = random.Random(graine)
    couleurs = [(220, 60, 60), (60, 120, 220), (250, 200, 50), (90, 180, 90), (170, 90, 200)]
    c = couleurs[graine % len(couleurs)]
    l, h = 420, 560
    m = Image.new("L", (l, h), 0)
    d = ImageDraw.Draw(m)
    forme = graine % 3
    if forme == 0:  # fusée
        d.polygon([(210, 20), (300, 170), (120, 170)], fill=255)
        d.rounded_rectangle((120, 150, 300, 470), 60, fill=255)
        d.polygon([(120, 380), (40, 520), (130, 470)], fill=255)
        d.polygon([(300, 380), (380, 520), (290, 470)], fill=255)
    elif forme == 1:  # bonhomme
        d.ellipse((130, 20, 290, 180), fill=255)
        d.rounded_rectangle((120, 170, 300, 430), 70, fill=255)
        d.rounded_rectangle((135, 410, 195, 540), 25, fill=255)
        d.rounded_rectangle((225, 410, 285, 540), 25, fill=255)
    else:  # globe sur pied
        d.ellipse((60, 20, 360, 320), fill=255)
        d.rectangle((195, 300, 225, 460), fill=255)
        d.ellipse((110, 440, 310, 530), fill=255)
    img = _pate(m, c, graine)
    dd = ImageDraw.Draw(img)
    if forme == 1:
        for x in (180, 240):
            dd.ellipse((x - 18, 75, x + 18, 115), fill=(255, 255, 255, 255))
            dd.ellipse((x - 8, 88, x + 8, 106), fill=(20, 20, 20, 255))
        dd.arc((175, 110, 245, 150), 20, 160, fill=(60, 20, 20, 255), width=6)
    elif forme == 0:
        dd.ellipse((165, 220, 255, 310), fill=(180, 230, 250, 255), outline=(230, 230, 230, 255), width=10)
    recadrer(img).save(chemin)


def mascotte_demo(nom: str) -> Image.Image:
    l, h = 520, 600
    m = Image.new("L", (l, h), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((60, 90, 460, 520), fill=255)
    d.ellipse((120, 490, 220, 580), fill=255)
    d.ellipse((300, 490, 400, 580), fill=255)
    d.ellipse((20, 300, 110, 390), fill=255)
    d.ellipse((410, 300, 500, 390), fill=255)
    img = _pate(m, (245, 130, 40), 3)
    cap = Image.new("L", (l, h), 0)
    dc = ImageDraw.Draw(cap)
    dc.chord((110, 40, 410, 250), 180, 360, fill=255)
    dc.rounded_rectangle((90, 130, 440, 170), 20, fill=255)
    img.alpha_composite(_pate(cap, (40, 90, 200), 5))
    micro = Image.new("L", (l, h), 0)
    dmi = ImageDraw.Draw(micro)
    dmi.rectangle((450, 330, 470, 430), fill=255)
    dmi.ellipse((432, 280, 488, 340), fill=255)
    img.alpha_composite(_pate(micro, (40, 40, 40), 8))
    d = ImageDraw.Draw(img)
    expr, bouche = nom.split("_")
    for x in (200, 320):
        if expr == "content":
            d.arc((x - 40, 230, x + 40, 300), 200, 340, fill=(30, 20, 20, 255), width=12)
        else:
            r = 48 if expr == "surpris" else 40
            d.ellipse((x - r, 255 - r, x + r, 255 + r), fill=(255, 255, 255, 255))
            d.ellipse((x - 16, 245, x + 16, 277), fill=(15, 15, 15, 255))
    d.ellipse((140, 320, 190, 350), fill=(250, 120, 120, 255))
    d.ellipse((330, 320, 380, 350), fill=(250, 120, 120, 255))
    if bouche == "ouverte":
        if expr == "surpris":
            d.ellipse((225, 340, 295, 430), fill=(90, 20, 25, 255))
        else:
            d.chord((205, 320, 315, 430), 0, 180, fill=(90, 20, 25, 255))
            d.chord((235, 385, 285, 425), 180, 360, fill=(230, 90, 100, 255))
    else:
        if expr == "surpris":
            d.ellipse((245, 355, 275, 385), fill=(90, 20, 25, 255))
        else:
            d.arc((210, 320, 310, 390), 20, 160, fill=(90, 20, 25, 255), width=10)
    return img
