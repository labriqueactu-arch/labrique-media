# La Brique · procédure quotidienne (sans validation humaine)

Chaque jour, deux créneaux, chacun = un sujet = **un post image + un Reel voix off** sur Instagram, Facebook et Threads.

| Créneau | Tâche | Départ | Commande poussée au plus tard | Post | Reel |
| --- | --- | --- | --- | --- | --- |
| 1 | La Brique · créneau 8 h | 5 h 50 | 7 h 15 | 7 h 50 | 8 h 00 |
| 2 | La Brique · créneau 12 h | 9 h 30 | 11 h 15 | 11 h 50 | 12 h 00 |

Tu décides seul : sujet, verdict, mise en page, montage, voix, légendes. Personne ne valide. Publier est obligatoire : si le sujet idéal bloque, prends le suivant ; si tout bloque, un sujet intemporel (face à face, classement, question nostalgique). Ne contourne jamais un contrôle automatique.

## 0. Démarrage (5 min)

1. Tu es dans le clone de `labriqueactu-arch/labrique-media` (branche main). `git pull`. Lis `CLAUDE.md` (règles absolues).
2. Le conteneur n'a pas d'accès web direct : recherche et lecture de pages par **Firecrawl** (`firecrawl_search`, `firecrawl_scrape`). Le rendu, les photos, la voix et la publication tournent dans **GitHub Actions**, déclenchés par tes `git push`.
3. Journal : Google Sheet `16r1aw-QzSdZdnS96clZfuFiQF2etth_DT4xYI7U9nA4`, onglet `Untitled`, colonnes A à K (date, format, sujet, verdict, pilier, rendez-vous, lien, metricool id → « id publication », statut, montage, joueurs). Lis `Untitled!A1:K600`.
4. Si une ligne du jour porte déjà le statut « réservé créneau N » ou « publié créneau N » pour ton créneau : arrête-toi en une ligne.

## 1. Sujet

- Créneau 1 : la nuit NBA (`python3 tools/nuit.py --json /tmp/nuit.json` si le conteneur atteint ESPN, sinon Firecrawl sur ESPN, NBA.com, AP) et l'EuroLeague de la veille. Un match pas fini à 6 h 55 ne sert pas.
- Créneau 2 : l'actu hors terrain et l'Europe (transferts, contrats, blessures annoncées, déclarations, Français et Belges, EuroLeague, Betclic Élite, BNXT). Sujet différent du créneau 1, joueur différent.
- Sélection : Impact, Débat, Fraîcheur, Proximité (France, Belgique, Europe), chacun de 0 à 2, seuil 5 sur 8. Piliers sur 10 posts : terrain 40 %, décisions 25 %, Europe et les nôtres 20 %, vestiaire 15 %. Jamais le même joueur que le post précédent (colonne K), jamais le même sujet en 10 jours.
- Faits : chaque chiffre sur deux sources ouvertes et lues (`firecrawl_scrape`), la feuille ESPN compte pour une. Au moindre doute, le fait sort.
- Verdict : grille Attente, Impact, Durée, Logique (−1, 0, +1). Total ≥ +2 SWISH, −1 à +1 REBOND (rendez-vous dans 1 à 3 mois), ≤ −2 BRIQUE. Un post sans verdict (Le Chiffre) est permis.
- Réserve la ligne dans le journal dès que le sujet est choisi : statut « réservé créneau N ».

## 2. Photos (deux photos différentes, jamais déjà utilisées)

1. Pousse une demande de repérage : `a_reperer/AAAA-MM-JJ-N-<joueur>.json` = `{"joueur": "Prénom Nom", "recherches": ["Nom Équipe", "Prénom Nom 2026"], "max": 16}`. `git add`, `commit`, `push`.
2. Attends 2 à 3 minutes, `git pull`, regarde `reperage/<nom>.jpg` avec Read et lis `reperage/<nom>.json` : licence, date, « deja_utilisee ».
3. Choisis **deux photos différentes** (ni la même, ni deux recadrages de la même) : maillot de l'équipe actuelle, joueur net et reconnaissable, de préférence seul. S'il y a d'autres joueurs, donne un `recadrage` [x0, y0, x1, y1] en fractions (le quadrillage de la planche est tous les 10 %) qui ne garde que lui, tête comprise.
4. Moins de deux photos valables : change de sujet ou de joueur. Jamais de photo non libre, jamais une photo déjà utilisée.

## 3. Commande

Écris `a_produire/<id>.json` d'après `automatisation/COMMANDE.md` (exemple complet : `automatisation/exemples/commande.json`). `id` = `AAAA-MM-JJ-N-<sujet>`. `heure` = 08:00 ou 12:00, Europe/Brussels avec le décalage (`+01:00` en hiver, `+02:00` en été).

- **Post** : composant et montage d'après `gabarits/GABARITS.md` (fiches d'exemple dans `gabarits/ds/`). Montage différent du post précédent (colonne J). Éclat seulement pour une BRIQUE ou une rupture déclarée.
- **Reel** : format `recap` (voir `tools/video/VIDEO.md`) : chiffre clé, nom, deux stats qui comptent, punchline, question de fin. Voix : Max, `{"id": "Xy5q4w05TJGcKXPWeWoz", "modele": "eleven_v4", "ecart": 0.2}`. Quatre répliques courtes : accroche, joueur et chiffres, contexte, « … ? Ça rentre, ou ça brique ? ». Écris les noms et termes NBA tels qu'ils se prononcent en anglais (« Luka Dončić », « Lakers », « back-to-back »). Durée 11 à 13 s.
- **Légendes** : Instagram et Facebook façon _nba_talks : accroche d'une ligne en MAJUSCULES avec un ou deux emojis, 2 ou 3 phrases de faits, verdict, question finale terminée par 👀👇, sources, exactement 5 hashtags (joueur, équipe, #NBA ou #EuroLeague, #NBAFrance, #LaBrique). Threads : 450 caractères au plus, deux emojis au plus, un seul hashtag. La légende du Reel a une accroche différente, pensée pour des non abonnés. **N'écris pas le crédit photo** : la production l'ajoute.

`git add a_produire/<id>.json`, commit « Commande créneau N : … », push. La production démarre seule.

## 4. Contrôle

1. Toutes les 2 minutes, `git pull` jusqu'à voir `produit/<id>.json` (8 à 10 minutes).
2. `"ok": false` : lis `erreurs` (et l'image `_refuse` si elle existe), corrige la commande (cadre, textes, recadrage, photo), pousse-la de nouveau. Une correction déclenche une nouvelle production.
3. `"ok": true` : regarde `produit/<id>-apercu.jpg` avec Read, comme un directeur artistique. Post, couverture du Reel, deux détourages. Refuse si : un autre joueur dans le détourage, visage mal détouré, texte illisible, faute, faits faux.
4. Refus après production : `git rm a_publier/<id>-*.json`, commit, push (la publication est annulée) ; corrige avec une **nouvelle** commande (nouvel `id`, nouvelles photos si besoin).
5. Sinon, ne touche à rien : la publication attend l'heure et part seule (post 10 minutes avant le Reel).

## 5. Après publication

1. Suis `publie/<id>-1-post.json` et `publie/<id>-2-reel.json` (`git pull` toutes les 2 minutes) jusqu'à leur arrivée.
2. Journal : deux lignes (format « Post » puis « Reel recap »), lien Instagram en colonne G, statut « publié créneau N HH:MM » ou l'erreur exacte, montage, joueurs.
3. Un message final de 5 lignes au plus : sujet, verdict, liens Instagram du post et du Reel, ce qui a coincé.

## Si ça casse

- Push refusé, Firecrawl muet, production en échec trois fois : écris-le dans le journal et dans ton message final. Ne publie jamais par un autre chemin.
- Retard : à 7 h 30 (créneau 1) ou 11 h 30 (créneau 2) sans production réussie, pousse une commande sur un sujet intemporel simple, avec des photos déjà repérées.
