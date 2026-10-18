# 0006 — Un banc de non-régression avant toute refonte

**Statut** : accepté, 2026-10-17 (phase 0 du plan).

## Contexte

Le moteur décide quelles offres entrent, leur note, la variante de CV et le texte de la
lettre. Une refonte (déplacer 15 000 lignes dans un paquet) doit prouver qu'elle ne change
AUCUNE de ces décisions — les tests unitaires ne couvrent pas tout.

## Décision

- `outils/banc.py` enregistre, pour chaque offre, toutes les décisions et le texte complet
  de la lettre et du CV (date neutralisée), et compare à une référence.
- Référence de CI : 384 offres fictives (`outils/banc_offres.py`), profil d'exemple.
- Sur les vraies données (11 710 offres, 99 lettres et CV) : instantané avant la
  synchronisation, comparaison après — à chaque version.
- Les découpages de fichiers sont GÉNÉRÉS depuis l'arbre syntaxique de l'original par des
  scripts rejouables, jamais retapés.

## Conséquences

Chaque étape des phases 3 à 5 est sortie avec 0 écart. Un changement voulu de décision se
fait dans un commit séparé qui réenregistre la référence et dit pourquoi.
