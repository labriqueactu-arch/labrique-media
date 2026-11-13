# Reels La Brique

`python3 tools/video/reel.py fiche.json sortie.mp4` rend un Reel 1080 × 1920 de 9 à 13 s en motion design, avec voix off et sons maison. `--frames 0,1,6` sort seulement des images de contrôle (quelques secondes). `--essai` ne marque pas la photo comme utilisée.

Rendu d'un recap de 11,5 s : environ 40 s sur le Mac. Fichier : environ 8 Mo, H.264, yuv420p, 30 i/s, AAC 48 kHz, −14 LUFS.

## Format « recap » (exemple : `exemples/recap_doncic.json`)

| Temps | Image | Voix |
| --- | --- | --- |
| 0 s | surtitre et chiffre géant déjà à l'écran, joueur qui entre, coup sourd | réplique 1 : l'accroche |
| réplique 2 | nom en typo mixte, pastilles qui comptent avec ticks | réplique 2 : le joueur et ses chiffres |
| réplique 3 | punchline en Instrument Serif italique (et sceau du verdict s'il y en a un) | réplique 3 : le contexte |
| réplique 4 | carte de fin « Ça rentre ou ça brique ? » et @labrique.hoops | réplique 4 : la question |
| fin | retour à la première image, pour la boucle | |

Les repères de la timeline suivent la voix : chaque réplique démarre 0,22 s après la précédente. Le fond suit le verdict comme pour l'image.

## Règles tenues par les contrôles

Texte de 40 px au moins, dans la zone sûre (250 px en haut, 420 px en bas, 140 px à droite), 8 mots au plus à l'écran hors carte de fin, rien sur le visage, visage jamais coupé, photo jamais utilisée deux fois (`banque/utilisees.json`), son à −14 LUFS. Un refus laisse `sortie_refuse.jpg`.

## Voix

Piper, modèle local `voix/fr_FR-tom-medium.onnx` (voix d'homme française, jeu de données sous AGPLv3), aucun appel réseau. Écris les noms difficiles en phonétique dans le texte de la voix (« Donchitch ») et garde l'orthographe exacte à l'écran. La voix est celle d'un narrateur : jamais l'imitation d'un joueur.

## Sons

`python3 tools/video/sons.py` régénère `sons/` : impact, tick, whoosh, swish, rebond, tampon, buzzer. Tous synthétisés en code. Aucune musique dans le fichier.
