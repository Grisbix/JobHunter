# 0007 — Ce qui vient du profil se calcule à la première lecture

**Statut** : accepté, 2026-10-18 (phase 4 du plan).

## Contexte

Une centaine de constantes de module étaient calculées au chargement à partir du profil
(motifs du filtre d'intitulé, axes et plafonds du scoring, textes de lettre et de
message, secteurs) ou de `Scripts/chemins.json` (dossiers des documents). Importer
`jobhunter.sources.linkedin` lisait donc le profil ; un test ne pouvait pas changer de
profil sans recharger tous les modules ; `premier_lancement` changeait de profil en
cours de route et gardait les valeurs de l'ancien.

## Décision

- Chaque module concerné déclare ces valeurs comme **fabriques** dans son dictionnaire
  `_PARESSEUX`, et son `__getattr__` de module (PEP 562) les calcule à la première
  lecture puis les range dans le module (`jobhunter.paresseux`).
- Dans le module, le code les lit par `_ici.NOM` (`_ici` = le module lui-même) : un nom
  global nu ne passe pas par `__getattr__`. Les autres modules lisent `module.NOM` ou
  `from module import NOM` à l'intérieur d'une fonction ; un `from module import NOM` de
  niveau module y est remplacé par une fabrique qui relit le nom au premier usage.
- Les façades `Scripts/x.py` lancent leur module par `runpy.run_module(...,
  alter_sys=True)` : sans cela `sys.modules["__main__"]` reste la façade et `_ici`
  la désignerait.
- `profil.utiliser(donnees)` injecte un profil en mémoire ; `profil.recharger(fichier)`
  revient au fichier. Les deux oublient les valeurs déjà calculées.
- Les noms et les valeurs ne changent pas : `monkeypatch.setattr(module, "NOM", ...)` et
  les façades ([ADR 0001](0001-facades-alias.md)) continuent de marcher. La façade
  connaît les noms paresseux de ses sous-modules.
- La transformation a été GÉNÉRÉE depuis l'arbre syntaxique, puis vérifiée par le banc
  ([ADR 0006](0006-banc-de-non-regression.md)) : 0 écart.

## Conséquences

Charger tout le moteur ne lit aucun fichier, n'écrit rien et ne sort pas sur le réseau ;
`tests/test_effets_import.py` le vérifie (cliquet). Une nouvelle constante tirée du
profil s'écrit `_PARESSEUX["NOM"] = lambda: ...` et se lit `_ici.NOM` ; une lecture du
profil au niveau module ferait échouer ce test.

mypy voit ces valeurs comme `Any` : c'est le prix de la compatibilité des noms. Les
remplacer par des objets de configuration typés (`Profil`) est possible plus tard, sans
toucher aux appelants extérieurs.
