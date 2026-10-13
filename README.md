# reel-cut

Monte tes Reels face-camera en parlant a ton IA. Elle derushe, sous-titre et anime.
Toi, tu corriges en francais.

Tu tournes en lisant ton script, phrase par phrase, en te trompant autant que tu veux, en
laissant tourner entre chaque prise. Tu donnes le fichier a ton agent. Il garde la meilleure
prise de chaque phrase, supprime les blancs et les rates, pose les sous-titres mot a mot et
les zooms, et te rend une composition que tu peux encore modifier a l'infini.

## Le principe

Un modele de langage est incapable de donner un timestamp de coupe fiable. Il hallucine des
secondes et te coupe au milieu d'un mot. C'est pour ca que les outils de montage IA sortent
de la bouillie.

La solution n'est pas d'attendre un meilleur modele. C'est d'arreter de lui demander ce qu'il
ne sait pas faire.

- **Ou couper** : des outils deterministes. Transcription mot a mot, detection des silences.
  Chaque coupe tombe au milieu d'un silence mesure. Jamais sur un mot.
- **Quoi garder** : le raisonnement de l'IA. Elle lit le texte de chaque ilot de parole, le
  compare a ton script, et choisit la prise.

Deux roles, deux outils. C'est tout le secret.

## Le second principe : rien n'est grave

Le derush est la seule etape qui touche a la video. Tout le reste (sous-titres, zooms,
habillage) vit dans une composition **HyperFrames**. Donc tout reste modifiable, dans Studio,
sans jamais re-encoder. Tu changes un mot, tu deplaces un zoom, tu re-rends.

## Demarrage

1. Il te faut Claude Code (ou un agent equivalent) et un abonnement Claude.
2. Ouvre ce dossier dans Claude Code.
3. Envoie : `Lis INSTALL.md et installe tout. Occupe-toi de la partie technique.`
4. Reponds "go" quand il te le propose.
5. Glisse ton rush dans `rushes/` et demande-lui de le monter.

## Cout

**Zero.** Tout le systeme est local et open source : ffmpeg, whisper.cpp, Python, HyperFrames.
Rien ne quitte ta machine, aucune cle API, aucun abonnement a un service de transcription.

Le seul cout, c'est ton abonnement a l'agent IA.

## Ce dont tu as besoin

|  | Minimum | Confortable |
|---|---|---|
| Machine | Mac M1+ ou Windows 10/11 64 bits | Mac Apple Silicon |
| RAM | 8 Go | 16 Go |
| Disque | 10 Go | 20 Go |
| CPU | 2 coeurs (lent) | 8 coeurs |

Sur une machine a 2 coeurs sans GPU, la transcription tourne autour du temps reel : dix minutes
de rush, dix minutes d'attente. Sur un Mac Apple Silicon, c'est plusieurs fois plus rapide.

## Le pipeline

```
rushes/ma_video.mp4
   │  transcribe.py        transcription locale mot a mot
   ▼  work/<slug>_words.json
   │  cut_plan.py          ilots de parole + frontieres dans les silences
   ▼  work/<slug>_plan.json      <- l'IA decide ici : keep / reason
   │  build_cut.py         coupe ffmpeg + table de correspondance
   ▼  assets/<slug>_cut.mp4 + work/<slug>_map.json
   │  build_overlays.py    recalage + phrases verbatim + scoring
   ▼  work/<slug>_overlays.json   <- l'IA decide ici : keep / punch
   │  build_composition.py composition HyperFrames (overlays + camera)
   ▼  index.html           -> npx hyperframes preview / render
```

## Les scripts

| Script | Role |
|---|---|
| `check_env.py` | Diagnostic machine. Ne modifie rien. |
| `transcribe.py` | Transcription locale mot a mot (whisper.cpp). |
| `cut_plan.py` | Plan de coupe deterministe. |
| `build_cut.py` | Coupe ffmpeg + table de correspondance des temps. |
| `build_overlays.py` | Overlays : recalage + decoupage verbatim + scoring. |
| `make_sfx.py` | Synthetise la banque de SFX libres de droits (une fois). |
| `build_composition.py` | Composition HyperFrames (video + overlays + camera + SFX). |

Chacun sort du JSON et fait une seule chose.

## Les doctrines appliquees

L'habillage ne sort pas de nulle part. Deux doctrines validees en production le gouvernent,
et elles font foi :

**Camera** — deux mouvements, rien d'autre. Un *drift* (2-4% d'echelle sur un segment entier,
imperceptible, son seul role est d'empecher le cadre de paraitre fige) et un *punch-in* (saut
de +7-8% sur un temps fort, puis retombee). Les punchs sont **rares** : deux par minute
maximum. Un zoom doit se lire comme la decision d'un cadreur sur le moment qu'on veut
souligner. Des zooms constants ou aleatoires font remarquer le montage au lieu du propos.

**Son** — un whoosh 0,06 seconde avant chaque punch, un clic presque subliminal sur chaque
jointure de coupe. Les sons sont synthetises sur ta machine, donc libres de droits. Meme regle
que pour les zooms : un son partout, et plus rien ne ressort.

**Texte** — la rarete est la valeur. Environ cinq overlays par minute, pas un de plus. Texte
strictement verbatim, revele **mot par mot** avec une avance de 0,12 seconde pour que le mot
apparaisse *sur* la voix et non apres. Placements alternes (gauche, droite, bandeau haut,
centre bas), jamais deux fois au meme endroit d'affilee. Blanc gras sur l'image, ombre en
trois couches, aucune plaque derriere le texte.

## Ce que ca ne fait pas

Pas de motion design, pas de musique, pas de b-roll. C'est volontaire.
Le derush et les overlays sont les etapes que tout le monde deteste et que personne
n'automatise correctement. Le reste viendra.
