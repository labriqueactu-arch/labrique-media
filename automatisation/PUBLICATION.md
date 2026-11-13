# Publication directe (sans Metricool)

La Brique publie sur Instagram, Facebook et Threads par les API officielles de Meta, gratuites. Le quota Instagram est de 100 publications par 24 heures glissantes (lu sur le compte le 13 novembre 2026). Un carrousel compte pour une publication. On en utilise 2 par jour.

## Comment ça tourne

1. La tâche du matin pousse le visuel dans `posts/` et une fiche `a_publier/AAAA-MM-JJ-sujet.json` (format dans l'en-tête de `tools/publier.py`).
2. Le push déclenche `.github/workflows/publier.yml`. Il attend l'heure prévue, publie sur les réseaux de la fiche, puis commite le résultat dans `publie/` (identifiants, liens, erreurs).
3. Toutes les 15 minutes, le même workflow publie ce qui est arrivé à échéance, au cas où un déclenchement aurait sauté. Une fiche déjà traitée n'est jamais republiée. Une fiche en retard de plus de 45 minutes est notée « abandonné (retard) ».
4. La tâche du matin lit `publie/` pour remplir le journal et écrire à Anto.

Les jetons vivent dans les secrets GitHub du dépôt. Ils ne sont jamais écrits dans le dépôt ni affichés.

## Secrets du dépôt (Settings, Secrets and variables, Actions)

| Secret | Contenu |
| --- | --- |
| `META_PAGE_TOKEN` | jeton de page longue durée de « La Brique - Hoops » |
| `FB_PAGE_ID` | identifiant de la page |
| `IG_USER_ID` | identifiant du compte Instagram professionnel lié à la page |
| `THREADS_TOKEN` | jeton Threads longue durée |
| `SECRETS_PAT` | facultatif : jeton GitHub à grain fin, ce dépôt seulement, droit « Secrets : lecture et écriture », pour prolonger le jeton Threads tous les 15 jours |

## Vérifier sans publier

Actions, Publication, Run workflow, action `verifier`. Le journal du job affiche la page, le compte Instagram lié, le quota du jour et le compte Threads.

## Jetons

- Le jeton de page obtenu à partir d'un jeton utilisateur longue durée n'expire pas, sauf changement de mot de passe ou retrait des droits.
- Le jeton Threads dure 60 jours. `.github/workflows/jeton-threads.yml` le prolonge le 1er et le 15 de chaque mois si `SECRETS_PAT` existe. Sans lui, il faut le renouveler à la main avant l'échéance.
