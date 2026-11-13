# Commande de production

Un fichier `a_produire/<id>.json` par créneau. Exemple complet : `exemples/commande.json`.

| Champ | Contenu |
| --- | --- |
| `id` | `AAAA-MM-JJ-N-<sujet>`, unique, minuscules et tirets |
| `heure` | heure du Reel, ISO avec fuseau (`2026-11-14T08:00:00+01:00`). Le post sort 10 minutes avant |
| `photos.post`, `photos.video` | `fichier` (`File:…` de Commons, copié de `reperage/*.json`), `joueur`, `recadrage` facultatif [x0, y0, x1, y1] en fractions. Deux photos différentes |
| `post` | fiche `render_ds` : `composant`, `props` (avec `"photo": "@post"`), `rupture` si Éclat hors BRIQUE. Voir `gabarits/GABARITS.md` |
| `video` | fiche `reel.py` format `recap` avec `"photo": "@video"`, `cadre`, `surtitre`, `chiffre`, `prenom`, `nom`, `stats` (2), `punchline`, `fin`, `verdict` (ou null), `voix` (Max, 4 répliques), `duree` 11 à 13 |
| `legende`, `threads`, `alt` | textes du post, sans crédit photo (ajouté par la production) |
| `legende_reel`, `threads_reel` | textes du Reel |
| `essai` | `true` : produit sans publier ni marquer les photos |

Rapport : `produit/<id>.json` (`ok`, `erreurs`, `apercu`). Fiches de publication : `a_publier/<id>-1-post.json` et `-2-reel.json` ; les supprimer avant l'heure annule la publication.
