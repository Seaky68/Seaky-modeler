# L'actu en pâte à modeler

Trois fois par jour, ce programme choisit **une actualité du jour** (toujours un sujet différent), en fait une
vidéo TikTok de 30 à 45 secondes **animée façon stop-motion en pâte à modeler**, et vous l'envoie **sur Telegram**.
La vidéo est présentée par **Pâtou**, une petite mascotte orange en pâte à modeler, toujours la même.

## Ce que fait le programme
1. **L'actualité** : il lit les flux RSS de `data/flux.txt` (franceinfo, Le Monde, 20 Minutes, Google Actualités…).
   Claude choisit un sujet léger, avec une info concrète à montrer en images, et jamais un sujet déjà traité
   aujourd'hui ou hier (`data/historique.json`).
   **Aucun drame** : pas de morts, guerres, attentats, catastrophes, faits divers ni polémiques politiques.
2. **Le script** : Claude lit les articles et écrit le texte et la mise en scène (décors, figurines, moment où
   chacune apparaît et bouge). **Un deuxième passage vérifie chaque fait** à partir des articles et corrige
   si besoin. Aucune personne réelle ni marque n'est dessinée : une personnalité devient un personnage générique.
3. **Les images** (fal.ai, FLUX.2 Turbo) : un décor miniature par scène et 1 ou 2 figurines, détourées pour être
   animées séparément.
4. **La voix** (edge-tts, gratuite), avec le minutage de chaque mot.
5. **La musique et les bruitages** sont composés par le programme : marimba, glockenspiel, « pop », « boing »,
   pâte écrasée… Aucun droit d'auteur.
6. **L'animation** (Remotion) façon stop-motion : 12 poses par seconde, la pâte qui « vibre » légèrement à
   chaque pose, figurines qui tombent, s'écrasent, sautent, tournent, Pâtou qui parle et change d'expression,
   transitions en boule de pâte, sous-titres mot par mot, sources affichées à la fin.
7. La vidéo et une légende prête à copier (titre, hashtags, sources) arrivent sur Telegram.

## Installation (environ 10 minutes, une seule fois)
1. Créez un **nouveau dépôt** sur GitHub, par exemple `actu-pate` (bouton **New** sur github.com).
2. Sur la page du dépôt, cliquez sur **uploading an existing file** (ou **Add file**, puis **Upload files**).
   Faites glisser **tout le contenu** du dossier `actu-pate` (les dossiers `pipeline`, `src`, `public`, `data`,
   `assets` et les fichiers `package.json`, `package-lock.json`, `requirements.txt`, `tsconfig.json`,
   `README.md`, `.gitignore`), puis **Commit changes**.
3. Créez le workflow : **Add file**, puis **Create new file**. Comme nom, tapez exactement
   `.github/workflows/actu.yml`. Collez le contenu du fichier `actu.yml` fourni, puis **Commit changes**.
4. Ajoutez les 4 clés, les mêmes que pour vos autres projets : **Settings**, puis **Secrets and variables**,
   puis **Actions**, puis **New repository secret** :
   `ANTHROPIC_API_KEY`, `FAL_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## Premier essai
Onglet **Actions**, puis **Actu en pâte à modeler** à gauche, puis **Run workflow**.
- Cochez **Vidéo de démonstration** pour un essai gratuit (images dessinées par le code, sans voix).
- Laissez décoché pour une vraie vidéo sur l'actu du jour. Comptez 6 à 10 minutes.

**La première vraie vidéo crée Pâtou** (6 images : 3 expressions, bouche ouverte et fermée), puis l'enregistre
dans `assets/mascotte/`. Toutes les vidéos suivantes réutilisent la même Pâtou. Si elle ne vous plaît pas,
supprimez les fichiers de `assets/mascotte/` : une nouvelle Pâtou sera créée à la vidéo suivante.

## Réglages (facultatifs)
**Settings**, puis **Secrets and variables**, puis **Actions**, onglet **Variables** :
- `VOIX` : une autre voix, par exemple `fr-FR-DeniseNeural` ou `fr-FR-RemyMultilingualNeural`
  (par défaut : `fr-FR-HenriNeural`).
- `VITESSE_VOIX` : par exemple `+15%` pour une voix plus rapide (par défaut : `+8%`).
- `MODELE_CLAUDE` : un autre modèle Claude (par défaut : `claude-sonnet-5-5`).
- `FAL_MODEL` : un autre modèle d'images fal.ai (par défaut : `fal-ai/flux-2/turbo`).

**Horaires** : 8 h 13, 12 h 43 et 18 h 13 (heure de Paris en hiver). Pour les changer, modifiez les lignes
`cron` du workflow (heures en UTC).

**Sources** : ajoutez ou retirez des flux RSS dans `data/flux.txt`, un par ligne.

## À savoir
- **Coût estimé** : environ 25 à 35 centimes par vidéo (Claude + 5 à 10 images fal.ai), soit environ
  25 à 30 € par mois pour 3 vidéos par jour. La voix, la musique et le rendu sont gratuits.
- **Minutes GitHub** : chaque vidéo prend environ 8 à 10 minutes. Un dépôt **privé** a 2 000 minutes gratuites
  par mois, partagées avec vos autres dépôts : 3 vidéos par jour en utilisent environ 800.
  Un dépôt **public** n'a pas de limite (vos clés restent secrètes dans les deux cas).
- **À chaque publication sur TikTok**, activez **« Contenu généré par l'IA »** dans *Plus d'options*.
- **Relisez avant de publier** : c'est de l'actualité. Le programme vérifie les faits, mais une erreur reste
  possible. Les liens des articles sont dans le message Telegram.
- Les décors et figurines sont des créations originales « dans l'esprit » du stop-motion britannique :
  ne demandez pas de reproduire des personnages existants (droits d'auteur).

## Organisation des fichiers
- `pipeline/` : le programme Python (actu, script, images, voix, son, plan d'animation, Telegram).
- `src/` : l'animation Remotion (stop-motion, Pâtou, sous-titres, transitions).
- `data/flux.txt` : les flux RSS lus chaque jour.
- `data/historique.json` : les sujets déjà traités (rempli automatiquement, 7 jours gardés).
- `data/demo.json` : le script de la vidéo de démonstration.
- `assets/mascotte/` : Pâtou (créée automatiquement à la première vraie vidéo).
- `public/fonts/` : la police Fredoka (licence libre OFL).
