# Reels La Brique

`python3 tools/video/reel.py fiche.json sortie.mp4` rend un Reel 1080 × 1920 en motion design, avec voix off et sons maison. `--frames 0,1,6` sort seulement des images de contrôle. `--essai` ne marque pas la photo comme utilisée.

Depuis le 14/11/2026, toute fiche porte `"version": 2` (Reels dynamiques, `dynamique.py`). Une fiche sans `version` passe encore par l'ancien moteur (`scene.js`), gardé pour comparer.

Rendu d'un recap de 10 s : environ 25 s sur le Mac. Fichier : environ 11 à 13 Mo, H.264, yuv420p, 30 i/s, AAC 48 kHz, −14 LUFS.

## Format « recap » version 2 (exemples : `exemples/recap2_sga.json`, `exemples/recap2_doncic.json`)

La voix fixe tout. Chaque phrase a un rôle, et chaque rôle a son plan :

| Rôle | Plan | Entrée | À l'écran |
| --- | --- | --- | --- |
| `accroche` | chiffre géant et joueur, déjà en mouvement à l'image 1 | punch in, flash de 2 images, impact | `ecran` mot à mot sur la voix |
| `joueur` | fond encre, joueur plein cadre | whip pan avec flou | nom révélé au masque, `stats` qui claquent sur leur `mot` |
| `contexte` | gros plan visage, fond os | poussée et flash | sous-titres mot à mot |
| `verdict` | fond du verdict | volet en briques, silence pulsé à 120 BPM | tampon qui claque (ondes pour SWISH, vibration pour REBOND, éclats pour BRIQUE) |
| `punch` | cadrage serré décalé | coupe sèche | sous-titres en Instrument Serif, tampon en petit |
| `question` | carte de fin | volet en briques | « Ça rentre ou ça brique ? » mot à mot, éclats sur BRIQUE, coupe sèche vers l'accroche (boucle) |

Fiche : `format`, `version`, `verdict` (ou null), `photo`, `source_photo`, `cadre`, `chiffre`, `prenom`, `nom`, `stats` (`a`, `suffixe`, `de` facultatif, `mot`), `fin`, `voix` (`id`, `modele`, `stabilite`, `style`, `phrases` : `role`, `texte`, `ecran` pour l'accroche, `silence_avant` pour le verdict, `ton` et `sous_titres` facultatifs). La durée suit la voix, plus 0,75 s de carte de fin.

Boîte à outils (`motion.js`, réutilisable) : courbes expo, back, elastic ; punch in ; tremblement ; flash ; flou directionnel ; compteurs qui accélèrent puis freinent ; volet en briques ; découpe et calage des mots. Caméra 2.5D dans `recap2.js` : poussée continue, flottement, punch in sur chaque mot et sur la grille de tempo, parallaxe, joueur qui respire avec contour lumineux, balayage de lumière, grain animé, garde qui garde les visages dans le cadre.

## Voix

ElevenLabs, voix Max `Xy5q4w05TJGcKXPWeWoz`, modèle `eleven_v4`. Tout le script part en une requête `with-timestamps`, une balise de ton par phrase (`dynamique.TONS`, alternée avec `TONS_ALT`). Les blancs sont resserrés à 0,12 s dans une phrase et 0,16 s entre phrases, le silence voulu est posé, le débit est ramené vers 3,6 mots/s (hauteur conservée). Jusqu'à 4 prises : la plus expressive gagne. Cache : `~/.cache/labrique-voix`. Jamais l'imitation d'une personne réelle.

Mixage : voix avec passe-haut, présence à 3 kHz, de-esser, compression légère ; sons sous la voix avec ducking d'environ 6 dB ; loudnorm à −14 LUFS, −1,5 dBTP.

## Règles tenues par les contrôles (refus avec `sortie_refuse.jpg`)

Anciennes : texte de 40 px au moins, zone sûre (250 px en haut, 420 px en bas, 140 px à droite), 8 mots au plus à l'écran hors carte de fin, rien sur un visage, visage jamais coupé, photo jamais utilisée deux fois, polices chargées, ffprobe, −14 LUFS ± 1,5.

Nouvelles (`dynamique.py`, mesures dans `analyse.py`) :
- dynamisme : différence moyenne entre images (135 × 240) d'au moins 1,6 sur toute fenêtre de 0,7 s ; les anciens Reels sont à 0,04
- accroche : texte lisible et mouvement dès l'image 1, premier mot avant 0,25 s
- voix : débit de 3,2 à 4,1 mots/s, variation de hauteur d'au moins 5 demi-tons (ancienne voix : 3,9 à 4), aucun blanc de plus de 0,6 s hors silence voulu
- sous-titres : décalage sous 80 ms
- durée : 8 à 11,5 s

Les seuils ne baissent jamais pour faire passer un rendu.

## Sons

`python3 tools/video/sons.py` régénère `sons/` : impact, tick, whoosh, swish, rebond, tampon, buzzer. Tous synthétisés en code. Aucune musique dans le fichier.
