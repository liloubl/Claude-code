# Installation

> **Pour l'utilisateur :** ouvre ce dossier dans Claude Code et envoie ce message :
>
> ```
> Lis INSTALL.md et installe tout. Occupe-toi de la partie technique.
> ```
>
> Tu n'as aucune commande a recopier. L'agent verifie ta machine, t'explique ce qui manque,
> et attend ton "go" avant de toucher a quoi que ce soit.

---

## Protocole pour l'agent

Ce qui suit t'est destine. Ne le transforme pas en tutoriel terminal pour l'utilisateur.

### Regles pendant toute l'installation

- **Une etape a la fois.** Jamais la sequence complete d'un coup.
- **Tu executes, l'utilisateur ne recopie rien.**
- **Tu ne modifies rien avant son "go".**
- Un outil absent n'est pas une erreur : dis-le calmement.
- Si une manipulation lui incombe vraiment (installer Homebrew), guide-le pour cette seule
  etape puis reprends la main.
- Termine par un vrai test sur un vrai fichier. Pas de "c'est installe" sans preuve.

### 1. Diagnostiquer, sans rien modifier

```bash
python3 tools/check_env.py
```

Traduis le JSON en francais simple, trois lignes maximum. Annonce le temps que va prendre
l'installation selon ce qui manque (compter ~20 min si tout est a faire, dont le
telechargement du modele). Puis **attends "go"**.

### 2. ffmpeg

- macOS : `brew install ffmpeg`. Homebrew absent, envoie-le sur https://brew.sh d'abord.
- Windows : `winget install Gyan.FFmpeg`, puis verifie dans un **nouveau** terminal.
- Linux : `sudo apt install ffmpeg`.

### 3. Node.js 22 ou plus (requis par HyperFrames)

- macOS : `brew install node`
- Windows : `winget install OpenJS.NodeJS.LTS`
- Linux : nodesource, ou le gestionnaire de la distribution.

Node 20 fonctionne encore mais affiche un avertissement. Node 22+ est la cible.

### 4. Les dependances du projet

```bash
npm install
```

Installe HyperFrames et son Chrome de rendu. C'est le plus gros telechargement apres le modele.

### 5. Pillow (mesure de la largeur des sous-titres)

```bash
python3 -m pip install --user Pillow
```

Sans Pillow, la largeur est estimee au caractere : des sous-titres peuvent passer sur deux lignes.

### 6. whisper.cpp + le modele

```bash
git clone https://github.com/ggml-org/whisper.cpp ~/.cache/reel-cut/whisper-src
cmake -B ~/.cache/reel-cut/whisper-src/build -S ~/.cache/reel-cut/whisper-src
cmake --build ~/.cache/reel-cut/whisper-src/build --config Release -j
mkdir -p ~/.cache/reel-cut/whisper
curl -L -o ~/.cache/reel-cut/whisper/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

Prends `large-v3-turbo`, pas `large-v3` : bien plus leger et rapide, precision quasi identique.
`cmake` absent : `brew install cmake` (macOS) ou `winget install Kitware.CMake` (Windows).

`check_env.py` trouve tout seul le binaire et le modele a ces emplacements. Ailleurs, renseigne
`whisperCli` et `whisperModel` dans `config.json`.

### 7. La banque de sons

```bash
python3 tools/make_sfx.py
```

Genere quatre SFX avec ffmpeg, localement. Libres de droits, rien a telecharger.

### 8. La configuration

```bash
cp config.example.json config.json
```

Format vertical 1080x1920 par defaut, sous-titres blancs. Tout est modifiable ensuite, et
**aucune couleur n'est ecrite en dur dans les compositions**.

### 9. Verifier

```bash
python3 tools/check_env.py
```

`ready: true`. Sinon, reprends le point qui bloque. Les `warnings` ne bloquent pas : une machine
a moins de 4 coeurs fonctionne, elle est seulement plus lente a transcrire.

### 10. Le premier montage

Demande le rush, glisse-le dans `rushes/`, puis suis les skills :
`.claude/skills/derush/SKILL.md`, puis `.claude/skills/montage/SKILL.md`.

Lis-les avant d'agir. Le protocole de decision du derush s'y trouve, et il n'est pas negociable.
