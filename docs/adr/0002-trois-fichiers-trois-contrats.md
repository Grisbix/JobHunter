# 0002 — Trois fichiers de données, trois contrats d'accès

**Statut** : accepté (2026-09, repris en phase 3.1).

## Contexte

Treize programmes réécrivaient `apply_queue.json` en entier pour changer un champ, sans
verrou : des modifications se perdaient. Les descriptions d'annonces pesaient 64 % du
fichier. Et `suivi.json`, la seule donnée qu'aucun scan ne retrouve, était écrit depuis un
instantané mémoire : un clic « postulé » dans l'app effaçait les relances notées entre-temps.

## Décision

- **File** : lecture par `stockage.file.charger()` (sans verrou, les écritures étant
  atomiques) ; écriture uniquement par `transaction()` — verrou, relecture fraîche À
  L'INTÉRIEUR du verrou, écriture atomique à la sortie, annulation si le bloc lève.
- **Descriptions** : fichier annexe, réinjecté et ressorti par le stockage, invisible pour
  les appelants. `transaction(descriptions=False)` évite de le lire.
- **Suivi** : `stockage.suivi.poser()` écrit une entrée sur l'état relu sous verrou.
- Jamais de `json.load` / `json.dump` direct sur ces fichiers.

## Conséquences

- Plus de perte silencieuse ; la file pèse un tiers de son ancien poids.
- Toute suppression automatique doit épargner les offres présentes dans le suivi.
- Piège corrigé en 1.9.0 : les chemins se comparent résolus — `Path("apply_queue.json")`
  depuis `Scripts/` perdait les descriptions.
