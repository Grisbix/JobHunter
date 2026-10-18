# 0003 — Verrou par fichier, et le code de sortie 3

**Statut** : accepté.

## Contexte

L'application, le pipeline planifié et les programmes lancés à la main peuvent toucher la
file en même temps. Un verrou cassé « parce qu'il semble vieux » a déjà laissé deux
programmes écrire ensemble.

## Décision

- Exclusion inter-processus par fichier `.lock` (PID et date), réentrante dans un même
  processus ; `rendre_verrou` ne l'est pas — ne rendre que ce qu'on a pris (`tenu`).
- Un verrou tenu par un processus VIVANT ne se casse jamais. Un PID recyclé (processus né
  après le verrou) ne compte pas comme vivant.
- Un programme qui trouve la file occupée sort en **code 3** sans rien modifier. Le pipeline
  et l'app savent l'afficher (« un autre programme travaille, relance plus tard »).

## Conséquences

- Aucune écriture concurrente ; un programme bloqué ne fait aucun dégât.
- Toute requête réseau passe par les fonctions bornées de `jobhunter.reseau`, sinon un
  serveur lent tiendrait le verrou des heures (vu : 12 h 25, le 2026-09-22).
