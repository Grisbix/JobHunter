---
paths:
  - Scripts/jutil.py
  - src/jobhunter/stockage/*.py
  - Scripts/job_sources.py
  - Scripts/linkedin_desc.py
  - Scripts/pipeline_quotidien.py
  - Scripts/audit_dispo.py
---
# Verrous, code de sortie 3, requêtes bornées

`jutil.prendre_verrou` / `rendre_verrou` / `garder` implémentent une exclusion
inter-processus par fichier, qui casse le verrou d'un processus mort. Convention du
projet : **un programme qui trouve la file occupée sort en code 3 sans rien modifier.**

`prendre_verrou` est réentrant, `rendre_verrou` ne l'est pas. Une fonction qui prend puis
rend, alors que son appelant tenait le verrou pour tout le programme, le lui retire.
`jutil.tenu(chemin)` répond avant de prendre.

**Un verrou vivant ne se casse pas.** `perime` (30 min) ne s'applique plus qu'à un verrou
dont on ne peut pas lire le propriétaire. Tant que le PID inscrit tourne, on attend, puis
l'appelant sort en code 3. Avant le 2026-09-23, l'âge suffisait : un travail de trois heures
voyait son verrou cassé au bout de trente minutes, par un programme qui allait ensuite
écrire par-dessus.

**Windows recycle les PID.** « Vivant » veut dire : le PID existe ET le processus est né
avant le verrou (`GetProcessTimes` contre l'horodatage du fichier). Le 2026-10-02, le
PID d'une collecte morte a été réattribué à l'extension Chrome : le verrou orphelin
passait pour tenu, et toute collecte sortait en code 3.

**`job_sources.main()` tient deux verrous, pour deux rôles.** Le verrou de
`offres_scan.json` dure toute la collecte : il n'y a qu'un scan à la fois. Celui de
`apply_queue.json` n'est pris que pour la fusion, pendant quelques secondes, avec une
attente de 30 min au lieu de 3. Si la fusion échoue quand même, la collecte est déjà
écrite dans `offres_scan.json`, et `--fusion-seule` la refusionne sans rescanner.
Jusqu'au 2026-09-23, la file était verrouillée pendant tout le scan, soit plus d'une heure.

**Un travail long écrit par lots.** `linkedin_desc.py` collecte hors verrou et écrit
par paquets de 500. Un arrêt ne coûte que le lot en cours.

**Un `timeout=` httpx borne chaque paquet, pas la requête.** Un serveur qui distille un
octet toutes les 19 s tient la connexion indéfiniment. Le 2026-09-22, fr.talent.com a
bloqué ainsi le scan planifié pendant 12 h 25. Dans `job_sources`, **toute** requête passe
par `_get_borne` / `_post_borne` (durée totale, vraie `httpx.Response`) et tout `urlopen`
par `_lire_borne` — qui lit en `read1`, parce que `read(n)` attend que le tampon soit
plein avant de rendre la main. `pipeline_quotidien.etape()` tue en plus toute étape qui
dépasse sa durée maximale — **l'arbre de processus** (`taskkill /T`), sans quoi un enfant
qui garde la sortie ouverte prolonge l'étape — sans tuer le pipeline. Le watchdog de 20 h
lit le journal du pipeline.

