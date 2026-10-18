# Contribuer à JobHunter

## Installer l'environnement de développement

```bash
uv sync                                           # .venv + dépendances verrouillées (uv.lock)
uv run python -m playwright install chromium      # navigateur des tests de navigation
uv run pre-commit install                         # contrôles avant chaque commit
```

Python 3.12 ou plus récent. Sans uv : `python -m venv .venv`, puis
`pip install -r requirements.txt ruff pytest pre-commit`.

## Avant chaque commit

```bash
uv run pytest -q                                                   # ~1 450 tests, sans réseau
uv run python outils/banc.py comparer outils/banc_reference.json   # 0 écart attendu
uv run mypy                                                        # types ; strict sur le socle
```

pre-commit lance ruff (lint et format), vérifie YAML/TOML, les gros fichiers, les clés
privées et la cohérence `VERSION` / `pyproject.toml`. La CI GitHub refait tout, sous Windows
et Linux.

**Types.** Toute fonction nouvelle ou modifiée du socle (`stockage`, `profil`, `reseau`,
`racine`, `texte`, `liens`, `scoring`) est annotée — mypy y est strict. Ailleurs, annoter en passant ;
un module entièrement annoté rejoint la liste stricte de `pyproject.toml`.

## Installer le paquet

`uv sync` installe `src/jobhunter` en mode éditable ; `pip install -e .` aussi. La commande
`jobhunter <commande>` existe alors (`jobhunter` seul liste les commandes). Hors du dépôt,
`JOBHUNTER_RACINE` désigne le dossier qui contient `Scripts/` et `profil/` (sinon le paquet
le cherche en remontant depuis le dossier courant). Sans installation : `python JobHunter.pyw
<commande>`.

## Comprendre le code

[`docs/architecture.md`](docs/architecture.md) : paquets, données, pipeline.
[`docs/adr/`](docs/adr/) : les décisions qui ne se rediscutent pas au détour d'une tâche.

## Écrire un test

Dans `tests/`, en pytest, avec les fixtures de `tests/conftest.py` (faux réseau, horloge,
file et suivi jetables, navigateur). Jamais d'affectation directe d'une globale du moteur :
`monkeypatch`. Données fictives et profil d'exemple uniquement. Un test qui a besoin d'un
autre profil le construit et le passe à `profil.utiliser(donnees)`, puis
`profil.recharger()` en fin de test.

## Règles

- **Comportement inchangé, sauf intention explicite.** Le banc le prouve. Un changement
  voulu régénère la référence dans le même commit, et le message dit pourquoi.
- **Un sujet par commit**, message clair qui explique le pourquoi.
- **Le moteur ne connaît personne** : tout ce qui est propre à une personne vit dans
  `profil/profil.json` (voir `AGENTS.md`).
- **Rien à l'import** : ni lecture, ni écriture, ni réseau (`tests/test_effets_import.py`).
  Une valeur tirée du profil s'écrit `_PARESSEUX["NOM"] = lambda: ...` et se lit
  `_ici.NOM` dans son module ([ADR 0007](docs/adr/0007-valeurs-du-profil-paresseuses.md)).
- **`print` pour la sortie d'une commande (`main()`), `logging` pour le reste** :
  `_log = journal.journal(__name__)`.
- **Limites non négociables** : aucune soumission automatique de candidature, aucun
  contournement anti-bot ni résolution de CAPTCHA, aucun mot de passe manipulé par les
  programmes. Détail : `AGENTS.md`.
- Les tests tournent sur le **profil d'exemple** et des **offres fictives**, jamais sur des
  données réelles.

## Publier une version

1. Monter `VERSION` **et** `version` dans `pyproject.toml` (identiques).
2. Ajouter la section `## X.Y.Z — date` en tête de `CHANGELOG.md`.
3. CI verte sur `main`, puis `gh release create vX.Y.Z` avec la section du CHANGELOG :
   l'étiquette sert de référence à la mise à jour des installations par ZIP.
