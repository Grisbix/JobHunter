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
uv run pytest -q                                                   # 27 suites, sans réseau
uv run python outils/banc.py comparer outils/banc_reference.json   # 0 écart attendu
```

pre-commit lance ruff (lint et format), vérifie YAML/TOML, les gros fichiers, les clés
privées et la cohérence `VERSION` / `pyproject.toml`. La CI GitHub refait tout, sous Windows
et Linux.

## Règles

- **Comportement inchangé, sauf intention explicite.** Le banc le prouve. Un changement
  voulu régénère la référence dans le même commit, et le message dit pourquoi.
- **Un sujet par commit**, message clair qui explique le pourquoi.
- **Le moteur ne connaît personne** : tout ce qui est propre à une personne vit dans
  `profil/profil.json` (voir `AGENTS.md`).
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
