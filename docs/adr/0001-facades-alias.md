# 0001 — Les anciens modules deviennent des alias du paquet

**Statut** : accepté, 2026-10-18 (phases 3.1 à 3.7). Les alias `Scripts/x.py` sont retirés en 2.0 ([0008](0008-programmes-dans-le-paquet.md)) ; la façade de paquet (`_facade`) reste.

## Contexte

Le moteur vivait dans `Scripts/` : une centaine de programmes qui s'importent par leur nom
(`import queue_io`, `from job_sources import title_ok`), plus les scripts personnels des
utilisateurs, les tâches planifiées et les lignes de commande du README. Le déplacer dans
`src/jobhunter` sans casser tout cela exigeait de garder les anciens noms.

Une copie des noms (`from jobhunter.stockage.file import *`) aurait cassé les tests : un
`monkeypatch.setattr(queue_io, "CHEMIN", ...)` aurait modifié la copie, pas le code réel —
et un test qui croit rediriger la file écrirait dans la vraie.

## Décision

- `Scripts/x.py` remplace son entrée dans `sys.modules` par le module du paquet :
  `import queue_io` **est** `jobhunter.stockage.file`. Lancé directement, il exécute le
  module par `runpy`.
- Un ancien gros module découpé (`job_sources`, `tailor_application`, `web_nav`,
  `JobHunter.pyw`) devient un paquet dont `jobhunter._facade` fait une façade : lire un nom
  le cherche dans les sous-modules ; l'affecter va au module qui le possède ; le `delattr`
  de sortie de `unittest.mock.patch` remet la valeur d'origine.
- Un nom réglable de l'extérieur (`KEYWORDS`, `MONDE`, `_get_borne`, polices du thème) n'est
  jamais importé par copie dans un autre sous-module : il s'y lit `_proprietaire.NOM`.

## Conséquences

- Rien ne change pour les appelants ; `test_coherence_imports.py` vérifie que chaque
  `module.nom` utilisé entre modules existe encore.
- Coût : un niveau d'indirection à comprendre. Les façades disparaissent quand le paquet
  s'installe par `pip` et que les appelants importent `jobhunter.*` (phase 6).
