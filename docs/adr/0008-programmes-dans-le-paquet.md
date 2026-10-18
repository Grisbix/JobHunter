# 0008 — Tout le code dans le paquet ; `JobHunter.pyw` lance sans installation

**Statut** : accepté, 2026-10-18 (phase 3.9 et phase 6 du plan, version 2.0).

## Contexte

Après la phase 3, le moteur vivait dans `src/jobhunter`, mais 57 programmes restaient
dans `Scripts/` (pipeline, documents, candidature, audits, sondes), à côté de 14 façades
qui gardaient les anciens noms (`job_sources`, `queue_io`…) et de 55 `sys.path.insert`.
Le paquet seul ne suffisait donc pas à faire tourner JobHunter : un dépôt qui voulait
dépendre d'une version installée devait encore recopier `Scripts/`.

Deux contraintes :

- Les installations par ZIP (sans `pip install`) doivent continuer de marcher, y compris
  si on déplace le dossier — les racines codées en dur ont cassé quatre fois.
- Une installation 1.x se met à jour avec SON `mise_a_jour`, qui contrôlait le nouvel
  arbre en important ses propres noms (`queue_io`, `job_sources`…) : retirer les façades
  aurait fait annuler la 2.0 par toutes les 1.x.

## Décision

- Les programmes entrent dans `jobhunter.programmes` (noms inchangés) ; les façades et
  tous les `sys.path.insert` du code disparaissent. `Scripts/` ne garde que les données.
  Les chemins de données viennent de `jobhunter.racine`, plus de `__file__`.
- Le déplacement a été GÉNÉRÉ (git mv + réécriture des imports par l'arbre syntaxique,
  même nom local, donc même objet) et vérifié par le banc : 0 écart.
- `python -m jobhunter <commande>` lance une commande nommée (`collecte`, `pipeline`…)
  ou tout programme par son nom (`probe_ats`).
- **Sans installation**, `JobHunter.pyw` est l'entrée : sans argument l'application, avec
  arguments la ligne de commande. C'est le seul fichier qui ajoute `src/` au chemin
  d'import (calculé depuis son propre emplacement) ; les `.bat`/`.sh` et la tâche
  planifiée passent par lui. Les étapes lancées en sous-processus héritent de
  `PYTHONPATH` (`racine.exporter_paquet()`).
- **Installé par pip**, le paquet trouve le dossier des données par `JOBHUNTER_RACINE`
  ou en remontant depuis le dossier courant.
- **Passerelle 1.15.0** : `mise_a_jour` contrôle la version installée avec le code de
  celle-ci (`python -m jobhunter maj --controler`). La 1.15 doit précéder la 2.0 ; une
  1.x plus ancienne qui sauterait directement en 2.0 serait ramenée à sa version, sans
  perte.
- Le contrôle d'après mise à jour signale une collecte planifiée qui vise encore
  `Scripts/pipeline_quotidien.py` (à recréer avec `planifier.bat`/`planifier.sh`).

## Conséquences

Un dépôt de données (comme celui de l'auteur) peut dépendre d'une version étiquetée
(`pip install "jobhunter @ git+https://github.com/Grisbix/JobHunter@v2.0.0"`) au lieu de
recopier le code. Les programmes ne sont pas encore typés (exclus de mypy, à résorber).
Les noms historiques (`job_sources`…) restent comme alias locaux dans le code
(`from jobhunter import sources as job_sources`) : un renommage serait un autre chantier.
